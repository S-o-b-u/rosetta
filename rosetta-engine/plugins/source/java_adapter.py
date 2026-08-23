import os
import csv
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))


class JavaSourceAdapter:
    """
    Source adapter for Java codebases.

    Two ingestion paths:
      1. OpenRewrite fast-path  — if `call_graph_csv_path` is supplied, parse the
         pre-generated CallGraph.csv (highest accuracy, no javalang needed).
      2. javalang fallback      — regex + AST-based parsing using framework rules
         (used for OFBiz and any project without a pre-generated call graph).

    The `source_framework` parameter selects which rules/*.json file controls
    which method calls are labelled as READ / WRITE interactions.
    Defaults to "ofbiz" for backwards-compatibility.
    """

    def ingest_and_get_context(
        self,
        migration_id: str,
        file_path: str,
        target_method: str,
        source_framework: str = "ofbiz",
        call_graph_csv_path: str = None,
    ) -> dict:
        """
        Parses the Java source, ingests into Neo4j, returns AST context dict.

        Parameters
        ----------
        migration_id : str
            Unique migration run ID for Neo4j node isolation.
        file_path : str
            Path to the legacy Java source file.
        target_method : str
            The method name to analyse.
        source_framework : str
            Framework identifier — selects rules/<source_framework>.json.
            Defaults to "ofbiz".
        call_graph_csv_path : str | None
            Optional path to an OpenRewrite CallGraph.csv.  When provided,
            the CSV fast-path is used instead of javalang.
        """
        # ----------------------------------------------------------------
        # FAST-PATH: OpenRewrite CSV is available
        # ----------------------------------------------------------------
        if call_graph_csv_path and os.path.exists(call_graph_csv_path):
            print(f"[*] OpenRewrite fast-path: ingesting call graph from CSV...")
            return self._ingest_from_csv(
                migration_id, call_graph_csv_path, target_method, file_path
            )

        # ----------------------------------------------------------------
        # FALLBACK: javalang AST parser + framework rules
        # ----------------------------------------------------------------
        print(f"[*] javalang fallback: parsing {os.path.basename(file_path)} with framework='{source_framework}'...")
        from parsers.ast_ingester import process_java_file_to_neo4j
        process_java_file_to_neo4j(file_path, source_framework, target_method, migration_id)
        return self._query_neo4j(migration_id, target_method, use_fqn=False)

    # ------------------------------------------------------------------
    # PRIVATE: OpenRewrite CSV ingestion
    # ------------------------------------------------------------------
    def _ingest_from_csv(self, migration_id: str, csv_path: str, target_method: str, target_file_path: str) -> dict:
        """
        Reads an OpenRewrite CallGraph.csv (skipping # comment headers),
        merges nodes and edges into Neo4j using FQNs (Class.Method),
        and stores the physical file path.
        """
        import os
        import csv
        from neo4j import GraphDatabase
        
        # Build class-to-file map
        class_to_file = {}
        for root, _, files in os.walk(os.getcwd()):
            if "rosetta-engine" in root or ".venv" in root: continue
            for f in files:
                if f.endswith('.java'):
                    full_path = os.path.join(root, f)
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as fp:
                            content = fp.read()
                        package_name = ""
                        for line in content.split('\n'):
                            line = line.strip()
                            if line.startswith("package "):
                                package_name = line.replace("package ", "").replace(";", "").strip()
                                break
                        class_name = f.replace(".java", "")
                        fqn = f"{package_name}.{class_name}" if package_name else class_name
                        class_to_file[fqn] = os.path.relpath(full_path, start=os.getcwd())
                    except Exception:
                        pass

        uri      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
        user     = os.getenv("NEO4J_USER",     "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "rosetta_hackathon2026")

        driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            with open(csv_path, mode='r', encoding='utf-8') as f:
                lines = [line for line in f if not line.startswith('#')]

            reader = csv.DictReader(lines)
            with driver.session() as session:
                for row in reader:
                    from_class = row.get("fromClass", "")
                    from_name  = row.get("fromName",  "")
                    to_class   = row.get("toClass",   "")
                    to_name    = row.get("toName",    "")
                    action     = row.get("action",    "CALL")

                    if not (from_class and from_name and to_class and to_name):
                        continue

                    source_fqn = f"{from_class}.{from_name}"
                    target_fqn = f"{to_class}.{to_name}"
                    
                    source_file = class_to_file.get(from_class, "")
                    target_file = class_to_file.get(to_class, "")

                    session.run(
                        """
                        MERGE (s:Service {name: $src, migration_id: $mid})
                        ON CREATE SET s.file_path = $src_file
                        ON MATCH SET s.file_path = $src_file
                        MERGE (t:Service {name: $tgt, migration_id: $mid})
                        ON CREATE SET t.file_path = $tgt_file
                        ON MATCH SET t.file_path = $tgt_file
                        MERGE (s)-[:DEPENDS_ON {action: $action, migration_id: $mid}]->(t)
                        """,
                        src=source_fqn,
                        tgt=target_fqn,
                        src_file=source_file,
                        tgt_file=target_file,
                        action=action,
                        mid=migration_id,
                    )
            print(f"[+] OpenRewrite CSV ingested into Neo4j (migration_id={migration_id})")
        finally:
            driver.close()

        # Query back using FQN — the method name alone is not unique across classes
        # Find candidates: any FQN whose method-part matches target_method
        return self._query_neo4j(migration_id, target_method, use_fqn=True)

    # ------------------------------------------------------------------
    # PRIVATE: Neo4j context query
    # ------------------------------------------------------------------
    def _query_neo4j(self, migration_id: str, target_method: str, use_fqn: bool) -> dict:
        """
        Queries the Neo4j subgraph for target_method.

        use_fqn=True  : matches any node whose name ends with '.<target_method>'
                        (for OpenRewrite-ingested data where names are FQNs).
        use_fqn=False : exact match on name == target_method
                        (for javalang-ingested OFBiz data).
        """
        uri      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
        user     = os.getenv("NEO4J_USER",     "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "rosetta_hackathon2026")

        nodes, edges = [], []

        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            with driver.session() as session:
                if use_fqn:
                    # For ATM / OpenRewrite data: match by FQN suffix
                    query = """
                    MATCH (s:Service {migration_id: $mid})-[r]->(target:Service {migration_id: $mid})
                    WHERE s.name ENDS WITH ('.' + $method)
                    RETURN s.name  AS source_name, labels(s)[0] AS source_label,
                           type(r) AS rel_type,    r.action     AS action,
                           target.name AS target_name, labels(target)[0] AS target_label
                    """
                else:
                    # For OFBiz / javalang data: exact match
                    query = """
                    MATCH (s:Service {name: $method, migration_id: $mid})-[r]->(target)
                    RETURN s.name  AS source_name, labels(s)[0] AS source_label,
                           type(r) AS rel_type,    r.action     AS action,
                           target.name AS target_name, labels(target)[0] AS target_label
                    """

                results = session.run(query, method=target_method, mid=migration_id)

                nodes_set = set()
                for record in results:
                    src     = record["source_name"]
                    src_lbl = record["source_label"]
                    tgt     = record["target_name"]
                    tgt_lbl = record["target_label"]
                    rel     = record["rel_type"]
                    action  = record["action"]

                    if src not in nodes_set:
                        nodes.append({"id": src, "label": src_lbl})
                        nodes_set.add(src)
                    if tgt not in nodes_set:
                        nodes.append({"id": tgt, "label": tgt_lbl})
                        nodes_set.add(tgt)

                    edges.append({"source": src, "target": tgt, "label": rel, "action": action})

            driver.close()
            print(f"[+] Graph context: {len(nodes)} nodes, {len(edges)} edges for '{target_method}'.")

        except Exception as e:
            print(f"[!] Neo4j query failed: {e}")
            raise

        return {
            "migration_id": migration_id,
            "nodes": nodes,
            "edges": edges,
        }
