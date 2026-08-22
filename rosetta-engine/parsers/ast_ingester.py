import os
import json
import javalang
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Ensure we load the root .env file so Neo4j and API keys don't throw validation errors
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))


class GraphIngester:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_interaction(self, service_name, table_name, action):
        """Creates a standardized Neo4j relationship: (Service)-[:INTERACTS_WITH]->(DatabaseTable)"""
        with self.driver.session() as session:
            query = """
            MERGE (s:Service {name: $service_name})
            MERGE (t:DatabaseTable {name: $table_name})
            MERGE (s)-[:INTERACTS_WITH {action: $action}]->(t)
            """
            session.run(query, service_name=service_name, table_name=table_name, action=action)

def load_framework_rules(framework_name):
    # Safely navigate from core/ back out to the rules/ folder
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'rules'))
    rule_path = os.path.join(base_dir, f"{framework_name}.json")
    
    if not os.path.exists(rule_path):
        raise FileNotFoundError(f"[!] Rules for framework '{framework_name}' not found at {rule_path}")
        
    with open(rule_path, "r") as f:
        return json.load(f)

def process_java_file_to_neo4j(file_path, framework, target_method):
    print(f"[*] Loading dynamic AST mapping rules for: {framework.upper()}")
    rules = load_framework_rules(framework)
    
    print(f"[*] Parsing Java file: {os.path.basename(file_path)}")
    with open(file_path, "r") as f:
        java_code = f.read()
        
    # 1. Parse the AST
    tree = javalang.parse.parse(java_code)
    
    # 2. Connect to Neo4j
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    ingester = GraphIngester(uri, user, password)
    
    print(f"[*] Hunting for target method: {target_method}")
    
    # 3. Traverse the AST and map to JSON rules
    for path, node in tree.filter(javalang.tree.MethodDeclaration):
        if node.name == target_method:
            print(f"[+] Found method: {target_method}. Analyzing dependencies...")
            
            # Hunt for database interactions (Method Invocations)
            for _, invoc in node.filter(javalang.tree.MethodInvocation):
                
                # Check against dynamic READ patterns from our JSON
                for pattern in rules["database"]["read_patterns"]:
                    
                    # e.g., Matching Apache OFBiz EntityQuery.from("OrderItem")
                    if pattern["type"] == "method_chain":
                        if invoc.qualifier == pattern["qualifier"] and invoc.member in pattern["methods"]:
                            # Extract the table name from the arguments
                            if invoc.arguments and isinstance(invoc.arguments[0], javalang.tree.Literal):
                                table_name = invoc.arguments[0].value.strip('"')
                                print(f"    -> [MAPPED READ] Table: {table_name}")
                                ingester.create_interaction(target_method, table_name, "READ")
                                
                    # e.g., Matching Spring Boot @Query annotations
                    elif pattern["type"] == "annotation":
                        # Logic to check method annotations would go here for Spring Boot
                        pass

    ingester.close()
    print("[+] AST parsing and Neo4j graph injection complete.")

# Test block for local execution
if __name__ == "__main__":
    pass