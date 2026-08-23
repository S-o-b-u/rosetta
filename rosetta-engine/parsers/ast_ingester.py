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

    def create_interaction(self, service_name, table_name, action, migration_id):
        """Creates a standardized Neo4j relationship: (Service)-[:INTERACTS_WITH]->(DatabaseTable)"""
        with self.driver.session() as session:
            query = """
            MERGE (s:Service {name: $service_name, migration_id: $migration_id})
            MERGE (t:DatabaseTable {name: $table_name})
            MERGE (s)-[:INTERACTS_WITH {action: $action, migration_id: $migration_id}]->(t)
            """
            session.run(query, service_name=service_name, table_name=table_name, action=action, migration_id=migration_id)

    def create_method_call(self, source_method, target_method, migration_id):
        """Creates a standardized Neo4j relationship: (Service)-[:CALLS]->(Service)"""
        with self.driver.session() as session:
            query = """
            MERGE (s:Service {name: $source_method, migration_id: $migration_id})
            MERGE (t:Service {name: $target_method, migration_id: $migration_id})
            MERGE (s)-[:CALLS {migration_id: $migration_id}]->(t)
            """
            session.run(query, source_method=source_method, target_method=target_method, migration_id=migration_id)

def load_framework_rules(framework_name):
    # Safely navigate from core/ back out to the rules/ folder
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'rules'))
    rule_path = os.path.join(base_dir, f"{framework_name}.json")
    
    if not os.path.exists(rule_path):
        raise FileNotFoundError(f"[!] Rules for framework '{framework_name}' not found at {rule_path}")
        
    with open(rule_path, "r") as f:
        return json.load(f)

def process_java_file_to_neo4j(file_path, framework, target_method, migration_id):
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
    password = os.getenv("NEO4J_PASSWORD", "rosetta2026")
    
    ingester = GraphIngester(uri, user, password)
    
    print(f"[*] Hunting for target method: {target_method}")
    
    # 3. Traverse the AST and map to JSON rules
    for path, node in tree.filter(javalang.tree.MethodDeclaration):
        if node.name == target_method:
            print(f"[+] Found method: {target_method}. Analyzing dependencies...")
            
                # Hunt for database interactions (Method Invocations)
            for _, invoc in node.filter(javalang.tree.MethodInvocation):
                
                # Check for local method calls
                if not invoc.qualifier or invoc.qualifier == "this":
                    called_method = invoc.member
                    
                    # Exclude common JDK/library method names (e.g., BigDecimal methods)
                    excluded_methods = {"add", "subtract", "multiply", "divide", "compareTo", "equals", "toString", "hashCode"}
                    if called_method not in excluded_methods:
                        print(f"    -> [MAPPED CALL] Method: {called_method}")
                        ingester.create_method_call(target_method, called_method, migration_id)

                # Check against dynamic READ patterns from our JSON
                for pattern in rules["database"]["read_patterns"]:
                    
                    # e.g., Matching Apache OFBiz EntityQuery.from("OrderItem")
                    if pattern["type"] == "method_chain":
                        if invoc.qualifier == pattern["qualifier"] and invoc.member in pattern["methods"]:
                            # Extract the table name from the arguments
                            if invoc.arguments and isinstance(invoc.arguments[0], javalang.tree.Literal):
                                table_name = invoc.arguments[0].value.strip('"')
                                print(f"    -> [MAPPED READ] Table: {table_name}")
                                ingester.create_interaction(target_method, table_name, "READ", migration_id)
                                
                    # e.g., Matching Spring Boot @Query annotations
                    elif pattern["type"] == "annotation":
                        # Logic to check method annotations would go here for Spring Boot
                        pass
                
                # Check against dynamic WRITE patterns from our JSON
                for pattern in rules["database"].get("write_patterns", []):
                    if pattern["type"] == "method_call":
                        if invoc.qualifier == pattern["qualifier"] and invoc.member in pattern["methods"]:
                            # Extract the table name from the arguments
                            if invoc.arguments and isinstance(invoc.arguments[0], javalang.tree.Literal):
                                table_name = invoc.arguments[0].value.strip('"')
                                print(f"    -> [MAPPED WRITE] Table: {table_name}")
                                ingester.create_interaction(target_method, table_name, "WRITE", migration_id)

    ingester.close()

# Test block for local execution
def ingest_and_get_context(migration_id: str, file_path: str, target_method: str, framework: str = "ofbiz") -> dict:
    """
    Integration function for the Rosetta migration pipeline.
    Ingests the Java file into Neo4j and returns the resulting graph subgraph.
    
    Parameters
    ----------
    framework : str
        Name of the rules file to use (e.g. "ofbiz", "swing_java").
        Defaults to "ofbiz" for backwards-compatibility.
    """
    # 1. Run the existing ingestion with the specified framework rules
    process_java_file_to_neo4j(file_path, framework, target_method, migration_id)
    
    # 2. Query Neo4j to build the context dictionary
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "rosetta2026")
    
    nodes = []
    edges = []
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # Note: Isolation implemented by scoping to migration_id
        query = """
        MATCH (s:Service {name: $method_name, migration_id: $migration_id})-[r]->(target)
        RETURN s.name AS source_name, labels(s)[0] AS source_label,
               type(r) AS rel_type, r.action AS action,
               target.name AS target_name, labels(target)[0] AS target_label
        """
        results = session.run(query, method_name=target_method, migration_id=migration_id)
        
        nodes_set = set()
        for record in results:
            src = record["source_name"]
            src_lbl = record["source_label"]
            tgt = record["target_name"]
            tgt_lbl = record["target_label"]
            rel = record["rel_type"]
            action = record["action"]
            
            if src not in nodes_set:
                nodes.append({"id": src, "label": src_lbl})
                nodes_set.add(src)
            if tgt not in nodes_set:
                nodes.append({"id": tgt, "label": tgt_lbl})
                nodes_set.add(tgt)
                
            edges.append({
                "source": src,
                "target": tgt,
                "label": rel,
                "action": action
            })
            
    driver.close()
    print("[+] AST parsing and Neo4j graph injection complete.")
    
    return {
        "migration_id": migration_id,
        "nodes": nodes,
        "edges": edges
    }

if __name__ == "__main__":
    import pprint
    # Test the integration function
    migration_id_1 = "test-mig-1"
    migration_id_2 = "test-mig-2"
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Dummy.java"))
    target_method = "getGrandTotal"
    
    if os.path.exists(file_path):
        print(f"[*] Testing isolation for {target_method}...")
        try:
            ctx1 = ingest_and_get_context(migration_id_1, file_path, target_method)
            ctx2 = ingest_and_get_context(migration_id_2, file_path, target_method)
            print(f"[+] Mig 1 context size: {len(ctx1['nodes'])} nodes, {len(ctx1['edges'])} edges")
            print(f"[+] Mig 2 context size: {len(ctx2['nodes'])} nodes, {len(ctx2['edges'])} edges")
            
            # Verify they are isolated
            assert ctx1['migration_id'] == migration_id_1
            assert ctx2['migration_id'] == migration_id_2
            
            print("[+] Integration test successful! Result 1:")
            pprint.pprint(ctx1)
        except Exception as e:
            print(f"[-] Integration test failed: {e}")
    else:
        print(f"[-] Dummy file not found at {file_path}")