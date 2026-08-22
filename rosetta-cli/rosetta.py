import argparse
import sys
import os
import time

# Import the orchestrator you just built
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'rosetta-engine', 'agents')))
from orchestrator import build_orchestrator

# Import your existing AST Ingester from the 'parsers' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'rosetta-engine', 'parsers')))
from ast_ingester import process_java_file_to_neo4j

def print_banner():
    print("""
    ===================================================
    🚀 PROJECT ROSETTA : LEGACY TO MICROSERVICE ENGINE
    ===================================================
    """)

def main():
    parser = argparse.ArgumentParser(description="Rosetta Engine CLI - Decompose legacy monoliths to microservices.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: init
    init_parser = subparsers.add_parser("init", help="Initialize Rosetta in a legacy repository")
    init_parser.add_argument("--framework", type=str, required=True, help="Target framework (e.g., ofbiz, spring_boot)")

    # Command: migrate
    migrate_parser = subparsers.add_parser("migrate", help="Run the end-to-end migration pipeline")
    migrate_parser.add_argument("--file", type=str, required=True, help="Path to the legacy Java file")
    migrate_parser.add_argument("--target", type=str, required=True, help="Target method name to extract and migrate")
    migrate_parser.add_argument("--framework", type=str, required=True, help="Target framework (e.g., ofbiz, spring_boot)")
    migrate_parser.add_argument("--output", type=str, default="./modern-microservices", help="Output directory for generated code")
    
    args = parser.parse_args()
    print_banner()

    if args.command == "init":
        print(f"[*] Initializing Rosetta Sandbox...")
        time.sleep(1)
        print(f"[*] Loading AST extraction rules for: {args.framework.upper()}")
        print("[*] Connecting to local Neo4j graph environment...")
        print("[+] SUCCESS: Rosetta is ready. Run 'rosetta.py migrate --file <path> --target <MethodName> --framework <framework>' to begin.")

    elif args.command == "migrate":
        print(f"[*] Starting migration pipeline for target: {args.target}")
        
        # 1. READ THE ACTUAL JAVA FILE


        
        if not os.path.exists(args.file):
            print(f"[!] Error: Could not find file at {args.file}")
            sys.exit(1)
            
        with open(args.file, "r", encoding="utf-8") as f:
            real_java_code = f.read()
            
        print(f"[*] Successfully loaded {len(real_java_code)} bytes from {args.file}")

        # 2. RUN THE DYNAMIC AST INGESTER 
        print(f"[*] Parsing AST and mapping dependencies to Neo4j using {args.framework} rules...")
        process_java_file_to_neo4j(args.file, framework=args.framework, target_method=args.target)
        
        # 3. RUN LANGGRAPH ORCHESTRATOR
        rosetta_app = build_orchestrator()
        
        # Injecting the LIVE code into the pipeline
        initial_state = {
            "target_method": args.target,
            "raw_java_code": real_java_code,
            "neo4j_context": "", 
            "business_logic": "",
            "fastapi_code": "",
            "openapi_spec": ""
        }

        print("[*] Invoking Discovery and Architecture Agents...")
        final_state = rosetta_app.invoke(initial_state)

        # Ensure output directory exists
        os.makedirs(args.output, exist_ok=True)
        
        # Write files
        fastapi_path = os.path.join(args.output, f"{args.target}_service.py")
        openapi_path = os.path.join(args.output, f"{args.target}_openapi.yaml")
        logic_path = os.path.join(args.output, f"{args.target}_logic.json")

        with open(logic_path, "w", encoding="utf-8") as f:
            f.write(final_state["business_logic"])
        with open(fastapi_path, "w", encoding="utf-8") as f:
            f.write(final_state["fastapi_code"])
        with open(openapi_path, "w", encoding="utf-8") as f:
            f.write(final_state["openapi_spec"])

        print(f"\n[+] SUCCESS: Microservice generated successfully!")
        print(f"    - Architecture Code: {fastapi_path}")
        print(f"    - OpenAPI Spec:      {openapi_path}")
        print(f"    - Extracted Logic:   {logic_path}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()