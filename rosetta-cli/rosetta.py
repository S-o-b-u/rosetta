import argparse
import os
import sys
import json
import subprocess
import time
import warnings

# Suppress LangChain / Google GenAI SDK warnings about AFC and model configs
warnings.filterwarnings("ignore", message=".*Direct use of automatic function calling.*")
warnings.filterwarnings("ignore", message=".*uses fixed sampling defaults.*")


# Force UTF-8 output on Windows and filter rogue SDK prints
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    
    class FilteredStderr(io.TextIOWrapper):
        def write(self, s):
            if "Direct use of automatic function calling" in s:
                return len(s)
            return super().write(s)
            
    sys.stderr = FilteredStderr(sys.stderr.buffer, encoding="utf-8", errors="replace")
else:
    # On other platforms, just patch stderr directly to filter
    class FilteredStderr:
        def __init__(self, stream):
            self._stream = stream
        def write(self, s):
            if "Direct use of automatic function calling" in s:
                return len(s)
            return self._stream.write(s)
        def flush(self):
            self._stream.flush()
        def __getattr__(self, name):
            return getattr(self._stream, name)
            
    sys.stderr = FilteredStderr(sys.stderr)


# ==========================================
# PATH MAGIC: Connect CLI to Engine
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
engine_path = os.path.join(current_dir, "..", "rosetta-engine")
sys.path.append(engine_path)

# ==========================================
# RICH CONSOLE SETUP
# ==========================================
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.rule import Rule
    from rich.text import Text
    from rich.live import Live
    from rich import box
    from rich.columns import Columns
    from rich.padding import Padding
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console(highlight=False) if RICH_AVAILABLE else None


def _print(msg, style=""):
    if RICH_AVAILABLE:
        console.print(msg, style=style)
    else:
        print(msg)


def _rule(title="", style="bold cyan"):
    if RICH_AVAILABLE:
        console.print(Rule(title, style=style))
    else:
        print(f"\n{'='*60}  {title}  {'='*60}")


def _banner():
    if RICH_AVAILABLE:
        banner = Panel.fit(
            "[bold cyan]R O S E T T A[/bold cyan]\n"
            "[dim]Legacy to Cloud-Native Migration Engine[/dim]\n"
            "[dim]Powered by Gemini | LangGraph | FastAPI[/dim]",
            border_style="cyan",
            padding=(1, 4),
        )
        console.print(banner)
    else:
        print("\n" + "="*60)
        print("  ROSETTA -- Legacy to Cloud-Native Migration Engine")
        print("="*60)


# ==========================================
# PIPELINE STAGE PRINTER
# ==========================================

PIPELINE_STAGES = [
    ("🔬", "Discovery Agent",    "Analyzing legacy Java — extracting business logic & formula IR"),
    ("🏗️ ", "Architecture Agent", "Generating async FastAPI service from extracted IR"),
    ("🧪", "Validator",          "Running T1 + T3 golden-file + shadow equivalence tiers"),
]

def _print_pipeline_stages(active_idx: int = -1):
    if not RICH_AVAILABLE:
        return
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column(width=4)
    table.add_column(width=22)
    table.add_column()
    for i, (icon, name, desc) in enumerate(PIPELINE_STAGES):
        if i < active_idx:
            style, prefix = "green", "✅"
        elif i == active_idx:
            style, prefix = "bold yellow", "▶ "
        else:
            style, prefix = "dim", "  "
        table.add_row(f"{prefix}{icon}", f"[{style}]{name}[/{style}]", f"[dim]{desc}[/dim]")
    console.print(table)


def _print_parity_report(parity_report: dict, target: str):
    """Render the full parity tier report using Rich tables."""
    if not RICH_AVAILABLE:
        from core.parity_report import ParityReport, TierResult
        tiers = [TierResult(**t) for t in parity_report.get("tiers", [])]
        report = ParityReport(
            method=parity_report.get("method", target),
            baseline_mode=parity_report.get("baseline_mode", "unknown"),
            overall_passed=parity_report.get("overall_passed", False),
            tiers=tiers
        )
        print(report.render_console())
        return

    overall = parity_report.get("overall_passed", False)
    passed_count = parity_report.get("tiers_passed", 0)
    total_count = parity_report.get("tiers_total", 0)
    oracle = parity_report.get("baseline_mode", "unknown")

    # Header panel
    status_color = "green" if overall else "red"
    status_text = "✅ ALL TIERS PASSED" if overall else "❌ SOME TIERS FAILED"
    console.print()
    console.print(Panel(
        f"[bold {status_color}]{status_text}[/bold {status_color}]\n"
        f"[dim]Method:[/dim]  [bold]{target}[/bold]\n"
        f"[dim]Oracle:[/dim]  [cyan]{oracle}[/cyan]\n"
        f"[dim]Score:[/dim]   [{status_color}]{passed_count}/{total_count} tiers passed[/{status_color}]",
        title="[bold white]🔍 PARITY REPORT[/bold white]",
        border_style=status_color,
        padding=(0, 2),
    ))

    # Tier table
    tier_table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold white on dark_blue",
        border_style="blue",
        title="[bold]Validation Tier Results[/bold]",
    )
    tier_table.add_column("Status", width=8, justify="center")
    tier_table.add_column("Tier", width=30)
    tier_table.add_column("Feedback", overflow="fold")

    tier_labels = {
        "T1_formula_completeness":   "T1 — Formula Completeness",
        "T3_golden_file_equivalence": "T3 — Golden-File Equivalence",
        "shadow_validation":          "Shadow — LLM Fixture Comparison",
    }

    for tier in parity_report.get("tiers", []):
        status = tier.get("status")
        if status == "superseded":
            icon = "[bold yellow]➖ SKIP[/bold yellow]"
        elif status == "not_applicable":
            icon = "[bold yellow]➖ N/A[/bold yellow]"
        else:
            icon = "[bold green]✅ PASS[/bold green]" if tier["passed"] else "[bold red]❌ FAIL[/bold red]"
            
        label = tier_labels.get(tier["tier"], tier["tier"])
        feedback = tier.get("feedback", "")
        if status in ("superseded", "not_applicable"):
            label = f"[dim]{label} ({status})[/dim]"
            feedback_styled = f"[dim]{feedback}[/dim]"
        elif tier["passed"]:
            feedback_styled = f"[dim]{feedback}[/dim]"
        else:
            feedback_styled = f"[red]{feedback}[/red]"
            
        tier_table.add_row(icon, label, feedback_styled)

    console.print(tier_table)

    # Golden file detail table (if T3 ran)
    for tier in parity_report.get("tiers", []):
        if tier["tier"] == "T3_golden_file_equivalence":
            cases = tier.get("details", {}).get("cases", [])
            if cases:
                _print_golden_detail_table(cases)


def _print_golden_detail_table(cases: list):
    """Show per-fixture golden file results."""
    if not RICH_AVAILABLE or not cases:
        return

    case_table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold white",
        title="[bold]T3 — Golden Fixture Breakdown[/bold]",
        border_style="dim",
    )
    case_table.add_column("Fixture", width=34)
    case_table.add_column("Status", width=10, justify="center")
    case_table.add_column("Description", overflow="fold")

    for case in cases:
        status = "[green]✅ PASS[/green]" if case["passed"] else "[red]❌ FAIL[/red]"
        desc = case.get("description", "")
        if not case["passed"]:
            diffs = case.get("differences", [])
            desc = "[red]" + "; ".join(diffs[:2]) + "[/red]"
        case_table.add_row(case["fixture_id"], status, desc)

    console.print(case_table)


def _print_test_results(test_output: str):
    """Parse and pretty-print pytest output."""
    if not RICH_AVAILABLE:
        print(test_output)
        return

    lines = test_output.splitlines()
    passed = failed = 0
    test_rows = []

    for line in lines:
        if "PASSED" in line:
            name = line.split("::")[1].split(" ")[0] if "::" in line else line
            test_rows.append(("[green]✅ PASS[/green]", name.strip()))
            passed += 1
        elif "FAILED" in line and "::" in line:
            name = line.split("::")[1].split(" ")[0]
            test_rows.append(("[red]❌ FAIL[/red]", name.strip()))
            failed += 1
        elif "subtests passed" in line or "passed" in line:
            # Summary line
            if RICH_AVAILABLE:
                color = "green" if failed == 0 else "red"
                console.print(f"\n[bold {color}]  {line.strip()}[/bold {color}]")

    if not test_rows:
        console.print(test_output)
        return

    t = Table(box=box.SIMPLE, show_header=True, header_style="bold white",
              title="[bold]Test Suite Results[/bold]")
    t.add_column("Result", width=12, justify="center")
    t.add_column("Test Name")
    for status, name in test_rows:
        t.add_row(status, name)
    console.print(t)


# ==========================================
# MONKEY-PATCH AGENT PRINT TO INTERCEPT STAGES
# ==========================================

_stage_idx = {"current": -1}


def _stage_hook(msg: str):
    """Called when a pipeline node starts."""
    if not RICH_AVAILABLE:
        _real_print(msg)
        return
    if "Discovery" in msg:
        _stage_idx["current"] = 0
        console.print()
        _print_pipeline_stages(0)
    elif "Architecture" in msg:
        _stage_idx["current"] = 1
        console.print()
        _print_pipeline_stages(1)
    elif "Validator" in msg:
        _stage_idx["current"] = 2
        console.print()
        _print_pipeline_stages(2)
    else:
        console.print(f"[dim]{msg}[/dim]")


# Intercept node prints by patching builtins.print during pipeline
import builtins
_real_print = builtins.print

def _intercepting_print(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    if any(kw in msg for kw in ["[Agent]", "[Node]"]):
        _stage_hook(msg)
    elif msg.strip().startswith("[+]"):
        if RICH_AVAILABLE:
            console.print(f"[green]{msg}[/green]")
        else:
            _real_print(msg)
    elif msg.strip().startswith("[-]") or msg.strip().startswith("[!]"):
        if RICH_AVAILABLE:
            console.print(f"[red]{msg}[/red]")
        else:
            _real_print(msg)
    elif msg.strip().startswith("[*]"):
        if RICH_AVAILABLE:
            console.print(f"[cyan]{msg}[/cyan]")
        else:
            _real_print(msg)
    else:
        _real_print(*args, **kwargs)


# ==========================================
# TEST COMMAND
# ==========================================

def run_tests(args):
    _banner()
    _rule("Running Equivalence Test Suite", style="bold cyan")

    # Use the same Python interpreter that is running this script.
    # The user always invokes the CLI with the correct venv python, so this is reliable.
    python_exe = sys.executable

    test_dir = os.path.join(engine_path, "tests")
    filter_arg = ["-k", args.filter] if hasattr(args, "filter") and args.filter else []
    verbose = ["-v"] if not (hasattr(args, "quiet") and args.quiet) else []
    cmd = [python_exe, "-m", "pytest", test_dir] + verbose + filter_arg + ["--tb=short", "--no-header"]

    if RICH_AVAILABLE:
        console.print(f"\n[dim]Running:[/dim] [cyan]{' '.join(cmd)}[/cyan]\n")

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=engine_path)
    output = result.stdout + result.stderr

    _print_test_results(output)

    if result.returncode == 0:
        if RICH_AVAILABLE:
            console.print(Panel("[bold green]✅ All tests passed — equivalence pipeline is green![/bold green]",
                                border_style="green"))
        else:
            print("\n✅ All tests passed!")
    else:
        if RICH_AVAILABLE:
            console.print(Panel("[bold red]❌ Some tests failed. See details above.[/bold red]",
                                border_style="red"))
        else:
            print("\n❌ Some tests failed.")

    return result.returncode


# ==========================================
# MIGRATE COMMAND
# ==========================================

def extract_java_method(java_code: str, method_name: str) -> str:
    import re
    pattern = re.compile(rf"(public|protected|private|static|\s)+[\w\<\>\[\]]+\s+{method_name}\s*\(")
    match = pattern.search(java_code)
    if not match:
        return java_code
    
    start_idx = match.start()
    brace_start = java_code.find("{", start_idx)
    if brace_start == -1:
        return java_code
        
    brace_count = 0
    end_idx = -1
    for i in range(brace_start, len(java_code)):
        if java_code[i] == "{":
            brace_count += 1
        elif java_code[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                end_idx = i
                break
                
    if end_idx != -1:
        return java_code[start_idx:end_idx+1].strip()
    return java_code

def migrate(args):
    _banner()

    try:
        from core.golden import list_available_methods
        if args.baseline_mode != "golden_file" and args.target in list_available_methods():
            _print("[green][*] Golden manifest detected — upgrading baseline to: golden_file[/green]")
            args.baseline_mode = "golden_file"
    except Exception:
        pass  # Failsafe if golden module isn't loaded

    if RICH_AVAILABLE:
        info_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        info_table.add_column(style="dim", width=20)
        info_table.add_column()
        info_table.add_row("Target Method", f"[bold cyan]{args.target}[/bold cyan]")
        info_table.add_row("Legacy File", f"[yellow]{args.file}[/yellow]")
        info_table.add_row("Output Dir", f"[yellow]{args.output}[/yellow]")
        info_table.add_row("Baseline Mode", f"[magenta]{args.baseline_mode}[/magenta]")
        console.print(Panel(info_table, title="[bold]Migration Config[/bold]", border_style="cyan"))
    else:
        print(f"\n🚀 Migrating: {args.target}  |  Baseline: {args.baseline_mode}")

    if not os.path.exists(args.file):
        _print(f"[red][!] Error: Legacy file not found: {args.file}[/red]")
        return

    with open(args.file, "r", encoding="utf-8") as f:
        full_java_code = f.read()
        
    java_code = extract_java_method(full_java_code, args.target)
    
    if RICH_AVAILABLE and len(java_code) < len(full_java_code):
        console.print(f"[green][+] Extracted {args.target}() — reduced payload from {len(full_java_code)} to {len(java_code)} chars.[/green]")

    os.makedirs(args.output, exist_ok=True)

    import uuid
    migration_id = f"mig-{uuid.uuid4().hex[:8]}"

    initial_state = {
        "migration_id":          migration_id,
        "file_path":             args.file,
        "target_method":         args.target,
        "source_lang":           args.source_lang,
        "target_framework":      args.target_framework,
        "java_code":             java_code,
        "test_payload":          {},
        "expected_legacy_output":{},
        "formula_ir":            None,
        "pure_function_source":  None,
        "wrapped_service_source":None,
        "candidate_source":      None,
        "test_cases":            None,
        "baseline_mode":         args.baseline_mode,
        "baseline_command":      args.baseline_command,
        "validation_results":    None,
        "parity_report":         None,
        "retry_count":           0,
    }

    _rule("Agentic Pipeline", style="bold cyan")
    _print_pipeline_stages(-1)

    try:
        from core.graph import rosetta_pipeline
    except ImportError as e:
        _print(f"[red][!] Critical Error: Could not connect to LangGraph engine. Details: {e}[/red]")
        sys.exit(1)

    # Install print interceptor
    builtins.print = _intercepting_print
    try:
        final_state = rosetta_pipeline.invoke(initial_state)
    finally:
        builtins.print = _real_print

    _print_pipeline_stages(3)  # all done
    console.print() if RICH_AVAILABLE else None

    if not final_state.get("validation_passed"):
        if RICH_AVAILABLE:
            console.print(Panel(
                f"[bold red]Migration Failed[/bold red]\n\n"
                f"[red]{final_state.get('validation_feedback', 'Unknown error')}[/red]",
                title="❌ Result",
                border_style="red",
            ))
        else:
            print(f"\n[!] MIGRATION FAILED: {final_state.get('validation_feedback')}")
        return

    # ---- Print Parity Report ----
    parity_report = final_state.get("parity_report")
    if parity_report:
        _print_parity_report(parity_report, args.target)

    # ---- Write artifacts ----
    _rule("Writing Artifacts", style="bold green")
    base_name = os.path.join(args.output, args.target)

    written = []

    if final_state.get("logic_json"):
        path = f"{base_name}_logic.json"
        with open(path, "w", encoding="utf-8") as f:
            f.write(final_state["logic_json"])
        written.append(("📄", "Logic JSON",     path))

    if parity_report:
        path = f"{base_name}_parity_report.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(parity_report, f, indent=2, default=str)
        written.append(("🔍", "Parity Report",  path))

    if final_state.get("pure_function_source"):
        path = f"{base_name}_function.py"
        with open(path, "w", encoding="utf-8") as f:
            f.write(final_state["pure_function_source"])
        written.append(("🧠", "Pure Logic",     path))

    service_artifact_path = None
    if final_state.get("wrapped_service_source"):
        ext = final_state.get("service_extension", ".py")
        path = f"{base_name}_service{ext}"
        with open(path, "w", encoding="utf-8") as f:
            f.write(final_state["wrapped_service_source"])
        written.append(("🚀", "Microservice",   path))
        service_artifact_path = path

    main_path = os.path.join(args.output, "main.py")
    if not os.path.exists(main_path):
        _write_main(main_path)
        written.append(("🚪", "Domain Wrapper", main_path))

    if RICH_AVAILABLE:
        art_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        art_table.add_column(width=4)
        art_table.add_column(width=20)
        art_table.add_column(style="dim")
        for icon, label, path in written:
            art_table.add_row(icon, f"[green]{label}[/green]", path)
        console.print(art_table)

        default_run_cmd = f"python {os.path.join(args.output, 'main.py')}"
        entry_cmd = final_state.get('entry_command', 'python')
        if service_artifact_path:
            run_cmd = f"{entry_cmd} {service_artifact_path}"
        else:
            run_cmd = default_run_cmd
        
        console.print(Panel(
            "[bold green]✅ Migration Certified![/bold green]\n\n"
            f"[dim]Start the domain service:[/dim]\n"
            f"  [cyan]{run_cmd}[/cyan]\n\n"
            f"[dim]Check parity via API:[/dim]\n"
            f"  [cyan]GET http://localhost:8001/parity/{args.target}[/cyan]",
            border_style="green",
            title="🎉 Done",
        ))
    else:
        for icon, label, path in written:
            print(f"  {icon} {label}: {path}")
        entry_cmd = final_state.get('entry_command', 'python')
        if service_artifact_path:
            run_cmd = f"{entry_cmd} {service_artifact_path}"
        else:
            run_cmd = f"python {main_path}"
        print(f"\n✅ Migration Certified! Run: {run_cmd}")


def _write_main(main_path: str):
    content = """import os
import sys
import importlib
from pathlib import Path
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Rosetta Domain Service")

current_dir = Path(__file__).parent

# Auto-load engine for parity endpoint
engine_path = current_dir.parent / "rosetta-engine"
if str(engine_path) not in sys.path:
    sys.path.insert(0, str(engine_path))

# Auto-discover and mount all generated _service.py routers
for filename in os.listdir(current_dir):
    if filename.endswith("_service.py"):
        module_name = filename[:-3]
        try:
            spec = importlib.util.spec_from_file_location(module_name, current_dir / filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "router"):
                app.include_router(module.router)
                print(f"[+] Mounted: {module_name}")
        except Exception as e:
            print(f"[!] Failed to load {filename}: {e}")

# Mount parity endpoint if available
try:
    from modern_invoices_parity import router as parity_router
    app.include_router(parity_router)
except Exception:
    try:
        import importlib.util, sys
        parity_path = current_dir / "parity_endpoint.py"
        if parity_path.exists():
            spec = importlib.util.spec_from_file_location("parity_endpoint", parity_path)
            parity_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(parity_mod)
            app.include_router(parity_mod.router)
            print("[+] Mounted: parity_endpoint")
    except Exception as e:
        print(f"[!] Parity endpoint not loaded: {e}")

@app.get("/health")
async def health_check():
    return {"status": "operational", "services": [
        f for f in os.listdir(current_dir) if f.endswith("_service.py")
    ]}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
"""
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(content)


# ==========================================
# PLAN COMMAND
# ==========================================

def plan(args):
    _banner()
    _rule(f"Scanning Monolith: {args.dir}", style="bold cyan")

    java_files = []
    for root, _, files in os.walk(args.dir):
        for file in files:
            if file.endswith(".java"):
                rel_path = os.path.relpath(os.path.join(root, file), args.dir)
                java_files.append(rel_path)

    if not java_files:
        _print("[red][!] No Java files found.[/red]")
        return

    _print(f"[cyan][*] Discovered [bold]{len(java_files)}[/bold] Java files. Mapping bounded contexts...[/cyan]")

    from core.agents import llm, extract_code_block
    from langchain_core.prompts import PromptTemplate

    prompt = PromptTemplate.from_template("""
    You are an Enterprise Architect analyzing a legacy Java monolith.
    Below is a list of file paths from the codebase.
    
    Group these files into logical "Bounded Contexts" (e.g., OrderManagement, Accounting, Inventory).
    
    Return a JSON object formatted specifically for a Neo4j / React-Force-Graph visualization.
    The JSON MUST have this exact schema:
    {{
      "nodes": [
        {{"id": "DomainName", "group": 1, "label": "Bounded Context"}},
        {{"id": "FileName.java", "group": 2, "label": "Legacy Class"}}
      ],
      "edges": [
        {{"source": "FileName.java", "target": "DomainName", "label": "BELONGS_TO"}}
      ]
    }}
    
    File Tree:
    {tree}
    
    Output ONLY valid JSON wrapped in a ```json``` block.
    """)

    tree_text = "\n".join(java_files[:100])
    chain = prompt | llm
    response = chain.invoke({"tree": tree_text})
    graph_json = extract_code_block(response.content, "json")

    os.makedirs(args.output, exist_ok=True)
    output_path = os.path.join(args.output, "roadmap_graph.json")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(graph_json)

    try:
        parsed = json.loads(graph_json)
        nodes = len(parsed.get("nodes", []))
        edges = len(parsed.get("edges", []))
        contexts = [n for n in parsed.get("nodes", []) if n.get("group") == 1]
        if RICH_AVAILABLE:
            stat_table = Table(box=box.SIMPLE, show_header=False)
            stat_table.add_column(style="dim", width=22)
            stat_table.add_column()
            stat_table.add_row("Java files scanned", str(len(java_files)))
            stat_table.add_row("Graph nodes", str(nodes))
            stat_table.add_row("Graph edges", str(edges))
            stat_table.add_row("Bounded contexts", str(len(contexts)))
            for ctx in contexts:
                stat_table.add_row("", f"[cyan]• {ctx['id']}[/cyan]")
            console.print(Panel(stat_table, title="[bold]Roadmap Blueprint[/bold]", border_style="green"))
    except Exception:
        pass

    _print(f"[green][+] Blueprint saved: {output_path}[/green]")
    _print("[dim]   → Pass to your React frontend for Neo4j Force-Graph visualization.[/dim]")


# ==========================================
# MAIN
# ==========================================


# ==========================================
# BATCH COMMAND
# ==========================================

def batch(args):
    from core.batch import build_migration_order
    from core.graph import rosetta_pipeline
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


def main():
    parser = argparse.ArgumentParser(
        description="Project Rosetta: Legacy to Cloud-Native Migration Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the full test suite
  python rosetta-cli/rosetta.py test

  # Run only T3 golden-file tests
  python rosetta-cli/rosetta.py test --filter golden

  # Run only T4 property tests
  python rosetta-cli/rosetta.py test --filter property

  # Migrate a Java method (with golden-file validation)
  python rosetta-cli/rosetta.py migrate \\
      --file ofbiz-framework/.../ShoppingCart.java \\
      --target getGrandTotal \\
      --baseline-mode golden_file

  # Generate a monolith roadmap
  python rosetta-cli/rosetta.py plan --dir ofbiz-framework
        """
    )
    subparsers = parser.add_subparsers(dest="command")

    # ---- test ----
    test_parser = subparsers.add_parser("test", help="Run the equivalence test suite")
    test_parser.add_argument("--filter", "-k", default=None,
                             help="pytest -k filter expression (e.g. 'golden', 'property', 'T2')")
    test_parser.add_argument("--quiet", "-q", action="store_true",
                             help="Less verbose output")

    # ---- migrate ----
    migrate_parser = subparsers.add_parser("migrate", help="Migrate a legacy Java method to a FastAPI microservice")
    migrate_parser.add_argument("--file", required=True, help="Path to the legacy Java source file")
    migrate_parser.add_argument("--target", required=True, help="Name of the method to migrate")
    migrate_parser.add_argument("--source-lang", default="java", help="Source language parser plugin (default: java)")
    migrate_parser.add_argument("--target-framework", default="fastapi", help="Target framework generator plugin (default: fastapi)")
    migrate_parser.add_argument("--output", default="./modern-invoices", help="Output directory")
    migrate_parser.add_argument(
        "--baseline-mode",
        choices=["provisional", "approved", "golden_file", "java_executed"],
        default="provisional",
        help=(
            "Oracle for equivalence validation:\n"
            "  provisional  — LLM-synthesized (development only)\n"
            "  approved     — reviewed fixture values\n"
            "  golden_file  — committed baseline JSONs (recommended)\n"
            "  java_executed — live OFBiz adapter (requires --baseline-command)"
        ),
    )
    migrate_parser.add_argument(
        "--baseline-command",
        help="External Java adapter command (stdin=JSON payload, stdout=JSON response)",
    )

    # ---- plan ----
    plan_parser = subparsers.add_parser("plan", help="Generate a Neo4j roadmap graph of the legacy monolith")
    plan_parser.add_argument("--dir", required=True, help="Root directory of the legacy Java codebase")
    plan_parser.add_argument("--output", default="./dashboard/data", help="Output directory for graph JSON")


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

    args = parser.parse_args()

    if args.command == "test":
        sys.exit(run_tests(args))
    elif args.command == "migrate":
        migrate(args)
    elif args.command == "plan":
        plan(args)
    elif args.command == "batch":
        batch(args)
    else:
        _banner()
        parser.print_help()


if __name__ == "__main__":
    main()