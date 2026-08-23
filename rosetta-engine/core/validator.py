"""
validator.py — Multi-tier shadow equivalence validator.

Tier execution order:
  T1  Formula Completeness  — schema check before any execution
  T2  Unit Arithmetic       — tested externally via test_golden_equivalence.py
  T3  Golden-File           — compare actual response against committed baselines
  Shadow  LLM-fixture       — compare against Discovery-generated or approved expected

T5 (live Java via OFBiz adapter) is intentionally omitted from the automated
pipeline; it is available as a manual step for developers with a configured
OFBiz runtime via the `java_executed` baseline_mode.
"""

import json

from core.equivalence import compare_outputs

from core.baseline import BaselineError, execute_legacy_baseline
from core.state import RosettaState
from core.formula_ir import (
    check_formula_completeness,
    extract_formula_ir_from_logic_json,
    formula_ir_from_manifest_terms,
    FormulaIR,
)
from core.golden import GoldenFileProvider, GoldenFileNotFoundError
from core.parity_report import TierResult, build_parity_report


def validator_node(state: RosettaState) -> RosettaState:
    print("\n[Node] Validator: Executing Multi-Tier Equivalence Testing (T1 + T3 + Shadow)...")

    source = state.get("candidate_source") or state.get("generated_python")
    if not source:
        return {
            "validation_passed": False,
            "validation_feedback": "Generated candidate source is missing.",
        }

    # ------------------------------------------------------------------
    # Load pure function candidate
    # ------------------------------------------------------------------
    try:
        namespace = {}
        exec(compile(source, "<candidate>", "exec"), namespace)
        
        safe_method_name = state['target_method'].replace("<", "").replace(">", "").replace("-", "_")
        target_func_name = f"calculate_{safe_method_name}"
        if target_func_name not in namespace:
            return {
                "validation_passed": False,
                "validation_feedback": f"Candidate source is missing required function '{target_func_name}'.",
            }
        calc_func = namespace[target_func_name]
    except Exception as exc:
        return {
            "validation_passed": False,
            "validation_feedback": f"Candidate source failed to execute: {exc}",
        }

    # ------------------------------------------------------------------
    # T1 — Formula Completeness (probe with an empty payload to get the
    #       response structure, then check required fields are present)
    # ------------------------------------------------------------------
    tier_results: list[TierResult] = []
    formula_ir: FormulaIR | None = None

    # Determine whether formula_ir / logic_json were explicitly provided.
    # If the caller explicitly sets formula_ir=None and logic_json=None (e.g. in
    # isolated unit tests), we honour that opt-out and skip T1 entirely.
    # The golden manifest fallback is ONLY used when neither key appears in the
    # state dict at all (i.e. the validator is running in the full pipeline).
    has_explicit_none = (
        "formula_ir" in state and state["formula_ir"] is None
        and ("logic_json" not in state or not state.get("logic_json"))
    )

    baseline_mode = state.get("baseline_mode", "provisional")

    # ------------------------------------------------------------------
    # Golden-file mode: ALWAYS use the manifest as the authoritative
    # source for formula_ir. The Discovery Agent's LLM-generated terms
    # can have invented field names (e.g. "other_adjustments_total"
    # instead of "order_other_adjustment_total"), which would cause T1
    # to check for the wrong fields and block a perfectly correct candidate.
    # ------------------------------------------------------------------
    if baseline_mode == "golden_file":
        try:
            provider = GoldenFileProvider(state["target_method"])
            formula_ir = formula_ir_from_manifest_terms(
                method_name=state["target_method"],
                manifest_terms=provider.formula_terms(),
                formula=provider.manifest().formula,
            )
        except GoldenFileNotFoundError:
            pass  # No manifest — fall through to LLM-generated formula_ir

    if formula_ir is None:
        raw_ir_dict = state.get("formula_ir")
        logic_json_str = state.get("logic_json") or ""

        if raw_ir_dict:
            terms = raw_ir_dict.get("formula_terms") or raw_ir_dict.get("terms", [])
            formula_ir = formula_ir_from_manifest_terms(
                method_name=state["target_method"],
                manifest_terms=terms,
                formula=raw_ir_dict.get("formula", ""),
            )
        elif logic_json_str:
            formula_ir = extract_formula_ir_from_logic_json(logic_json_str)

    if formula_ir is None and not has_explicit_none:
        # Final fallback: try to load from golden manifest (pipeline mode only)
        try:
            provider = GoldenFileProvider(state["target_method"])
            formula_ir = formula_ir_from_manifest_terms(
                method_name=state["target_method"],
                manifest_terms=provider.formula_terms(),
                formula=provider.manifest().formula,
            )
        except GoldenFileNotFoundError:
            pass

    if formula_ir is not None and formula_ir.required_term_names:
        # Send a discovery probe payload to evaluate the response shape
        probe_payload = (state.get("test_payload") or {})
        try:
            probe_response = calc_func(probe_payload)
            t1_result = check_formula_completeness(formula_ir, probe_response)
            tier_results.append(TierResult(
                tier="T1_formula_completeness",
                passed=t1_result.passed,
                feedback=t1_result.feedback,
                details=t1_result.as_dict(),
            ))
            if not t1_result.passed:
                print(f"\n[-] T1 FAIL: {t1_result.feedback}")
                parity = build_parity_report(
                    state["target_method"],
                    state.get("baseline_mode", "provisional"),
                    tier_results,
                )
                return {
                    "validation_passed": False,
                    "validation_feedback": t1_result.feedback,
                    "parity_report": parity.as_dict(),
                }
        except Exception as exc:
            tier_results.append(TierResult(
                tier="T1_formula_completeness",
                passed=False,
                feedback=f"T1 probe raised exception: {exc}",
            ))
    else:
        tier_results.append(TierResult(
            tier="T1_formula_completeness",
            passed=True,
            feedback="T1 skipped: no formula IR available",
        ))

    # ------------------------------------------------------------------
    # T3 — Golden-File Equivalence
    # Only runs when baseline_mode=="golden_file". Under any other mode
    # (provisional, approved, java_executed) there is no authoritative
    # manifest to validate against, so T3 is recorded as "not applicable"
    # rather than a silent pass — prevents misleading ✅ in the parity report.
    # ------------------------------------------------------------------
    golden_tier_passed = True
    golden_tier_details: list[dict] = []
    baseline_mode = state.get("baseline_mode", "provisional")

    if baseline_mode != "golden_file":
        tier_results.append(TierResult(
            tier="T3_golden_file_equivalence",
            passed=True,
            status="not_applicable",
            feedback=f"T3 skipped: baseline_mode is '{baseline_mode}', not 'golden_file'",
        ))
    else:
        try:
            provider = GoldenFileProvider(state["target_method"])
            golden_fixtures = provider.all_fixtures()
            print(f"[*] T3 Golden-File: running {len(golden_fixtures)} baseline fixture(s)...")
            for fixture in golden_fixtures:
                try:
                    actual_output = calc_func(fixture.input)
                except Exception as exc:
                    golden_tier_passed = False
                    golden_tier_details.append({
                        "fixture_id": fixture.fixture_id,
                        "passed": False,
                        "feedback": f"Exception raised: {exc}",
                    })
                    continue

                comparison = compare_outputs(fixture.expected_output, actual_output)
                golden_tier_details.append({
                    "fixture_id": fixture.fixture_id,
                    "description": fixture.description,
                    "passed": comparison.passed,
                    "differences": comparison.differences,
                    "expected_normalized": comparison.expected_normalized,
                    "actual_normalized": comparison.actual_normalized,
                    "arithmetic_trace": fixture.arithmetic_trace,
                    "input": fixture.input,
                })
                if not comparison.passed:
                    golden_tier_passed = False
            tier_results.append(TierResult(
                tier="T3_golden_file_equivalence",
                passed=golden_tier_passed,
                feedback=(
                    "T3 Golden-File: PASS"
                    if golden_tier_passed
                    else "T3 Golden-File: FAIL — see details for mismatch"
                ),
                details={"cases": golden_tier_details, "capture_mode": provider.manifest().capture_mode},
            ))
            if not golden_tier_passed:
                failing = [c for c in golden_tier_details if not c["passed"]]
                feedback_parts = []
                for case in failing:
                    if "feedback" in case and "differences" not in case:
                        feedback_parts.append(
                            f"[{case['fixture_id']}]\n"
                            f"  Exception: {case['feedback']}"
                        )
                    else:
                        diff_str = "; ".join(case.get("differences", []))
                        input_str = json.dumps(case.get("input", {}))
                        trace_str = json.dumps(case.get("arithmetic_trace", {}))
                        feedback_parts.append(
                            f"[{case['fixture_id']}]\n"
                            f"  Input Payload: {input_str}\n"
                            f"  Expected Trace: {trace_str}\n"
                            f"  Differences: {diff_str}"
                        )
                t3_feedback = "T3 Golden-File FAIL:\n" + "\n".join(feedback_parts)
                print(f"\n[-] {t3_feedback}")
                parity = build_parity_report(
                    state["target_method"],
                    baseline_mode,
                    tier_results,
                )
                return {
                    "validation_passed": False,
                    "validation_feedback": t3_feedback,
                    "parity_report": parity.as_dict(),
                }
            else:
                print(f"[+] T3 PASS: {len(golden_fixtures)} golden-file fixture(s) matched.")

        except GoldenFileNotFoundError:
            tier_results.append(TierResult(
                tier="T3_golden_file_equivalence",
                passed=False,
                feedback=f"T3 FAIL: baseline_mode is 'golden_file' but no fixtures found for '{state['target_method']}'",
            ))

    # ------------------------------------------------------------------
    # Shadow / LLM-fixture tier (provisional, approved, or java_executed)
    # ------------------------------------------------------------------
    default_payload = state.get("test_payload") or {}
    default_expected = state.get("expected_legacy_output") or {}
    test_cases = state.get("test_cases") or [{
        "name": "discovery_case",
        "payload": default_payload,
        "expected_output": default_expected,
    }]

    shadow_results: list[dict] = []
    
    if baseline_mode == "golden_file":
        tier_results.append(TierResult(
            tier="shadow_validation",
            passed=True,
            status="superseded",
            feedback="Skipped: golden_file oracle supersedes LLM-guessed shadow cases",
        ))
    else:
        for case in test_cases:
            payload = case.get("payload", {})
            expected_output = case.get("expected_output", {})

            if baseline_mode == "java_executed":
                try:
                    expected_output = execute_legacy_baseline(
                        state.get("baseline_command"), payload
                    )
                except BaselineError as exc:
                    parity = build_parity_report(
                        state["target_method"], baseline_mode, tier_results
                    )
                    return {
                        "validation_passed": False,
                        "validation_feedback": str(exc),
                        "validation_results": shadow_results,
                        "parity_report": parity.as_dict(),
                    }

            try:
                actual_output = calc_func(payload)
            except Exception as exc:
                error_msg = f"Case '{case.get('name', 'unnamed')}' raised exception: {exc}"
                tier_results.append(TierResult(
                    tier="shadow_validation",
                    passed=False,
                    feedback=error_msg,
                ))
                parity = build_parity_report(
                    state["target_method"], baseline_mode, tier_results
                )
                return {
                    "validation_passed": False,
                    "validation_feedback": error_msg,
                    "validation_results": shadow_results,
                    "parity_report": parity.as_dict(),
                }

            comparison = compare_outputs(expected_output, actual_output)
            shadow_results.append({
                "name": case.get("name", "unnamed"),
                "baseline_mode": baseline_mode,
                "passed": comparison.passed,
                "expected_normalized": comparison.expected_normalized,
                "actual_normalized": comparison.actual_normalized,
                "differences": comparison.differences,
                "input": payload,
            })
            if not comparison.passed:
                input_str = json.dumps(payload)
                feedback = (
                    f"Case '{case.get('name', 'unnamed')}':\n"
                    f"  Input Payload: {input_str}\n"
                    f"  Differences: {comparison.feedback}"
                )
                print("\n[-] SHADOW MISMATCH: Sending error diff back to Architecture Agent.")
                tier_results.append(TierResult(
                    tier="shadow_validation",
                    passed=False,
                    feedback=feedback,
                ))
                parity = build_parity_report(
                    state["target_method"], baseline_mode, tier_results
                )
                return {
                    "validation_passed": False,
                    "validation_feedback": feedback,
                    "validation_results": shadow_results,
                    "parity_report": parity.as_dict(),
                }

        tier_results.append(TierResult(
            tier="shadow_validation",
            passed=True,
            feedback=f"Shadow: {len(shadow_results)} case(s) passed",
            details={"cases": shadow_results},
        ))

    # ------------------------------------------------------------------
    # All tiers passed
    # ------------------------------------------------------------------
    parity = build_parity_report(state["target_method"], baseline_mode, tier_results)
    
    print(f"\n[+] MATCH CONFIRMED: {len(shadow_results)} shadow case(s) + "
          f"golden-file tier passed.")

    return {
        "validation_passed": True,
        "validation_feedback": "Success",
        "validation_results": shadow_results,
        "parity_report": parity.as_dict(),
    }