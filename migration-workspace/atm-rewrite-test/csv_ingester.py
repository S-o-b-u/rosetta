import os
import csv
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load root .env file for Neo4j credentials
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env')))

class CSVGraphIngester:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def ingest_call_graph(self, csv_file_path: str, migration_id: str):
        """
        Reads OpenRewrite CallGraph.csv and merges nodes and edges into Neo4j.
        """
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"CSV not found: {csv_file_path}")
            
        with open(csv_file_path, mode='r', encoding='utf-8') as f:
            # OpenRewrite outputs metadata comments at the top. We must skip them.
            lines = []
            for line in f:
                if not line.startswith('#'):
                    lines.append(line)
            
            reader = csv.DictReader(lines)
            
            with self.driver.session() as session:
                for row in reader:
                    # fromSourceSet,fromClass,fromName,fromArguments,fromType,action,toClass,toName,toArguments,toType,returnType
                    from_class = row.get("fromClass", "")
                    from_name = row.get("fromName", "")
                    to_class = row.get("toClass", "")
                    to_name = row.get("toName", "")
                    action = row.get("action", "CALL") # CALL, REFERENCE, etc.
                    
                    if not from_class or not from_name or not to_class or not to_name:
                        continue
                        
                    # Build Fully Qualified Names
                    source_fqn = f"{from_class}.{from_name}"
                    target_fqn = f"{to_class}.{to_name}"
                    
                    # Construct Cypher query
                    # Using Service label for compatibility with current Rosetta architecture
                    query = """
                    MERGE (s:Service {name: $source_fqn, migration_id: $migration_id})
                    MERGE (t:Service {name: $target_fqn, migration_id: $migration_id})
                    MERGE (s)-[:DEPENDS_ON {action: $action, migration_id: $migration_id}]->(t)
                    """
                    
                    session.run(
                        query,
                        source_fqn=source_fqn,
                        target_fqn=target_fqn,
                        action=action,
                        migration_id=migration_id
                    )

def get_neo4j_context(migration_id: str, target_method_fqn: str) -> dict:
    """
    Queries Neo4j to retrieve the subgraph for a given target method FQN.
    """
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "rosetta_hackathon2026")
    
    nodes = []
    edges = []
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        query = """
        MATCH (s:Service {name: $method_name, migration_id: $migration_id})-[r]->(target)
        RETURN s.name AS source_name, labels(s)[0] AS source_label,
               type(r) AS rel_type, r.action AS action,
               target.name AS target_name, labels(target)[0] AS target_label
        """
        results = session.run(query, method_name=target_method_fqn, migration_id=migration_id)
        
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
    return {
        "migration_id": migration_id,
        "nodes": nodes,
        "edges": edges
    }

if __name__ == "__main__":
    import pprint
    import glob
    
    # Locate the CSV
    csv_dir = os.path.join(os.path.dirname(__file__), "target", "rewrite", "datatables")
    csv_files = glob.glob(os.path.join(csv_dir, "*", "org.openrewrite.table.CallGraph.csv"))
    
    if not csv_files:
        print("[!] CallGraph.csv not found. Run 'mvnw rewrite:run' first.")
        exit(1)
        
    csv_file = csv_files[0]
    test_migration_id = "atm-rewrite-test-1"
    
    print(f"[*] Found CSV: {csv_file}")
    print(f"[*] Ingesting into Neo4j with migration_id '{test_migration_id}'...")
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "rosetta_hackathon2026")
    
    ingester = CSVGraphIngester(uri, user, password)
    try:
        ingester.ingest_call_graph(csv_file, test_migration_id)
        print("[+] Ingestion complete.")
        
        # Test querying the subgraph
        test_method = "ASimulatorSystem.Login.actionPerformed"
        print(f"\n[*] Querying subgraph for {test_method}...")
        context = get_neo4j_context(test_migration_id, test_method)
        
        print(f"[+] Found {len(context['nodes'])} nodes and {len(context['edges'])} edges:")
        pprint.pprint(context)
        
    except Exception as e:
        print(f"[-] Error: {e}")
    finally:
        ingester.close()
