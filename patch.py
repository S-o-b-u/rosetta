import os
import re

rosetta_path = os.path.join("rosetta-cli", "rosetta.py")
with open(rosetta_path, "r", encoding="utf-8") as f:
    content = f.read()

batch_code = """
# ==========================================
# BATCH COMMAND
# ==========================================

def batch(args):
    from core.batch import build_migration_order
    from core.pipeline import build_pipeline
    from core.dlq import write_dlq
    from neo4j import GraphDatabase
    import json
    import os
    
    _banner()
    uri      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
    user     = os.getenv("NEO4J_USER",     "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "rosetta_hackathon2026")

    _print("[bold cyan][*] Connecting to Neo4j to retrieve batch migration order...[/bold cyan]")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    order = build_migration_order(driver)
    
    _print(f"[bold green][+] Queued {len(order)} methods for batch migration.[/bold green]")
    
    migrated_dependencies = {}
    dlq_methods = set()
    
    rosetta_pipeline = build_pipeline()
    
    import uuid
    run_id = f"batch-{uuid.uuid4().hex[:6]}"
    
    for i, item in enumerate(order):
        fqn = item["fqn"]
        file_path = item["file_path"]
        depends_on = item["depends_on"]
        
        target_method = fqn.split(".")[-1]
        
        _rule(title=f"Batch {i+1}/{len(order)}: {fqn}", style="bold magenta")
        
        # 1. DLQ Cascade check
        blocked_by = next((d for d in depends_on if d in dlq_methods), None)
        if blocked_by:
            _print(f"[bold red][!] Cascading failure: {fqn} blocked by DLQ dependency {blocked_by}[/bold red]")
            dlq_methods.add(fqn)
            # Create a mock state for logging
            mock_state = {"output": args.output, "parity_report": {}, "validation_results": []}
            write_dlq(fqn, file_path, "dependency_unresolved", mock_state, blocked_on=blocked_by)
            continue
            
        if not file_path or not os.path.exists(file_path):
            _print(f"[bold red][!] Source file not found for {fqn} (file_path: {file_path})[/bold red]")
            dlq_methods.add(fqn)
            mock_state = {"output": args.output, "parity_report": {}, "validation_results": []}
            write_dlq(fqn, file_path, "provider_error", mock_state)
            continue
            
        # 2. Setup state
        initial_state = {
            "migration_id": f"{run_id}-{target_method}",
            "file_path": file_path,
            "target_method": target_method,
            "source_lang": args.source_lang,
            "source_framework": args.framework,
            "target_framework": args.target_framework,
            "baseline_mode": args.baseline_mode,
            "output": args.output,
            "migrated_dependencies": migrated_dependencies,
        }
        
        _print(f"[dim]Migrating {target_method} from {file_path}[/dim]")
        
        try:
            # 3. Invoke pipeline
            final_state = rosetta_pipeline.invoke(initial_state)
            
            # 4. Check success
            if final_state.get("validation_passed", False):
                _print(f"[bold green][+] {fqn} migrated successfully![/bold green]")
                
                # Extract Contract
                contract = {
                    "signature": final_state.get("pure_function_source", "").split("def ")[-1].split(":")[0] if "def " in final_state.get("pure_function_source", "") else f"{target_method}(...)",
                    "summary": "Migrated dependency.",
                    "example": {}
                }
                
                # Attempt to load first fixture as example
                manifest_path = os.path.join("rosetta-engine", "tests", "baselines", target_method, "_manifest.json")
                if os.path.exists(manifest_path):
                    with open(manifest_path, "r") as mf:
                        manifest = json.load(mf)
                        if "cases" in manifest and manifest["cases"]:
                            fixture_path = os.path.join(os.path.dirname(manifest_path), manifest["cases"][0])
                            with open(fixture_path, "r") as ff:
                                fix_data = json.load(ff)
                                contract["example"] = {
                                    "input": fix_data.get("input", fix_data.get("action", {})),
                                    "output": fix_data.get("output", fix_data.get("expected", {}))
                                }
                
                migrated_dependencies[fqn] = contract
            else:
                _print(f"[bold red][!] {fqn} failed validation.[/bold red]")
                dlq_methods.add(fqn)
                write_dlq(fqn, file_path, "validation_failure", final_state)
                
        except Exception as e:
            if "RateLimit" in str(e) or "429" in str(e):
                reason = "provider_error"
                _print(f"[bold red][!] LLM Provider Rate Limit on {fqn}: {e}[/bold red]")
            else:
                reason = "provider_error"
                _print(f"[bold red][!] Engine Exception on {fqn}: {e}[/bold red]")
                
            dlq_methods.add(fqn)
            mock_state = {"output": args.output, "parity_report": {}, "validation_results": []}
            write_dlq(fqn, file_path, reason, mock_state)
            
    _rule(title="Batch Summary", style="bold cyan")
    _print(f"Total: {len(order)} | Migrated: {len(migrated_dependencies)} | DLQ: {len(dlq_methods)}")

"""

# Insert `batch` before `def main():`
content = content.replace("def main():", batch_code + "\ndef main():")

arg_code = """
    # ---- batch ----
    batch_parser = subparsers.add_parser("batch", help="Run dependency-ordered migration queue for full codebase")
    batch_parser.add_argument("--source-lang",       default="java",      help="Source language parser plugin (default: java)")
    batch_parser.add_argument("--framework",          default="swing_java", help="Source framework rules to use: ofbiz, swing_java, etc.")
    batch_parser.add_argument("--target-framework",   default="fastapi",   help="Target framework generator plugin (default: fastapi)")
    batch_parser.add_argument("--output", default="./modern-invoices", help="Output directory")
    batch_parser.add_argument(
        "--baseline-mode",
        choices=["provisional", "approved", "golden_file", "java_executed"],
        default="golden_file",
        help="Oracle for equivalence validation"
    )

    args = parser.parse_args()"""

content = content.replace("    args = parser.parse_args()", arg_code)

hook_code = """    elif args.command == "plan":
        plan(args)
    elif args.command == "batch":
        batch(args)"""

content = content.replace('    elif args.command == "plan":\n        plan(args)', hook_code)

with open(rosetta_path, "w", encoding="utf-8") as f:
    f.write(content)
print("rosetta.py patched.")
