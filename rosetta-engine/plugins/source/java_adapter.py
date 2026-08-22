import os
from parsers.ast_ingester import process_java_file_to_neo4j
from neo4j import GraphDatabase

class JavaSourceAdapter:
    def ingest_and_get_context(self, migration_id: str, file_path: str, target_method: str) -> dict:
        """
        Parses the Java file, ingests it into Neo4j, and returns the AST context.
        """
        # 1. Run the existing ingestion (hardcoding "ofbiz" as the framework for now)
        process_java_file_to_neo4j(file_path, "ofbiz", target_method, migration_id)
        
        # 2. Query Neo4j to build the context dictionary
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "rosetta2026")
        
        nodes = []
        edges = []
        
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            with driver.session() as session:
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
        except Exception as e:
            print(f"[!] Neo4j connection or query failed: {e}")
            raise e
            
        return {
            "migration_id": migration_id,
            "nodes": nodes,
            "edges": edges
        }
