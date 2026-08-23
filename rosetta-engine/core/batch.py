from neo4j import Driver
import graphlib

def build_migration_order(driver: Driver) -> list[dict]:
    """
    Query the Neo4j graph for all Service nodes and their CALLS edges.
    Return a list of dictionaries containing {fqn, file_path, depends_on} 
    in topological order (callees before callers), so that leaf nodes 
    are migrated first and context can be injected upward.
    """
    query = """
    MATCH (n:Service)
    OPTIONAL MATCH (n)-[:DEPENDS_ON]->(callee:Service)
    RETURN n.name AS caller, n.file_path as file_path, callee.name AS callee
    """
    
    with driver.session() as session:
        result = session.run(query)
        
        deps = {}
        node_info = {}
        for record in result:
            caller = record["caller"]
            callee = record["callee"]
            file_path = record["file_path"] or ""
            
            if caller not in deps:
                deps[caller] = set()
                node_info[caller] = file_path
                
            if callee and callee != caller:
                deps[caller].add(callee)
                if callee not in deps:
                    deps[callee] = set()
                    node_info[callee] = ""
                    
    ts = graphlib.TopologicalSorter(deps)
    order = list(ts.static_order())
    
    return [
        {
            "fqn": node,
            "file_path": node_info.get(node, ""),
            "depends_on": list(deps.get(node, set()))
        }
        for node in order
    ]
