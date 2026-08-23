# ATM Simulator — Full Codebase Migration: Implementation Plan

**Goal:** migrate the entire 13-file ATM-Simulator-System to certified microservices, with real (non-provisional) parity evidence — not the fabricated-credential result from the earlier `actionPerformed` attempt.

**Explicit non-goal of this plan:** this does not touch, block, or deprioritize the OFBiz certified path. See Section 0.

---

## 0. Ground rules

1. **OFBiz stays exactly as certified.** `getSubTotal`, `getTotalShipping`, `getGrandTotal`, `getFXConversion` are proven, working, and must not regress. Nothing in this plan modifies `agents.py`, `validator.py`, or `orchestrator.py` in a way that changes behavior for the existing `provisional`/`golden_file` baseline modes used by OFBiz today — all new capability is additive (new baseline modes, new nodes, new CLI subcommand), gated behind explicit flags.
2. **The quarantined ATM artifact stays quarantined.** `modern-invoices/_experiments/atm-login/` is not touched or "upgraded in place" — this plan produces new, properly-migrated artifacts under a fresh path (e.g. `modern-invoices/atm/`) once the real pipeline exists. The old fabricated result is not to be silently overwritten and re-labeled certified.
3. **Prove the mechanism on one chain before scaling to all 13 files.** Phase 0 exists specifically to avoid discovering a fundamental design problem after building batch orchestration for the whole codebase. Do not skip ahead to Phase 5 because it "should work."
4. **Every phase gate is a explicit go/no-go, evidenced by a real run, not a description of intended behavior.** This project has hit "described as fixed, log still shows the bug" more than once this session — each phase below ends with a specific artifact to check before moving on.

---

## 1. Current state (what's already true, what isn't)

| Piece | Status |
|---|---|
| OpenRewrite `FindCallGraph` on ATM (Maven-wrapped copy) | ✅ Done — 31 nodes / 48 edges extracted, confirmed real (not the ATM app that migrated wrong, the call-graph extraction itself) |
| CSV → Neo4j ingestion of that graph | ✅ Done, per your last update — Neo4j ingestion confirmed working for this data |
| Cross-file context reaching Discovery Agent | ❌ Not built — this is the actual root cause of the `actionPerformed` failure |
| Dependency-ordered batch migration | ❌ Not built — pipeline only migrates one target method at a time today |
| Swing/UI boilerplate stripping rules | ❌ Not built |
| DB-backed (side-effect) parity testing | ❌ Not built — validator only compares return values, not database state |
| `java_executed` adapter (any codebase) | ❌ Blocked — OFBiz's is stuck on the Java 26/Gradle issue; ATM's own build/DB story is unverified |

---

## 2. Phase 0 — Prove the mechanism on one chain

**Target:** `Login.actionPerformed()` → `Conn.connect()`. Chosen because it's the exact chain that broke, it's a 2-hop dependency (simplest non-trivial case), and it touches every open gap above without requiring all 13 files solved.

### 2.1 Steps
1. From the existing `CallGraph.csv`, confirm the edge `Login.actionPerformed → Conn.connect` is present. (Done: it's actually `Conn.<init>`, and the SQL query is directly in `Login.java`).
2. Migrate `Conn.<init>()` alone, first, as a trivial utility. This becomes the "already-certified callee."
3. **Scoped Side-Effect Rule (Option 2)**: Add a rule for `swing_java` that allows the Architecture Agent to write real DB access code (e.g. `sqlite3` or `mysql-connector`) *specifically* for methods where the DB query *is* the entire business decision (like authentication in `actionPerformed`). For other methods where a fetch is followed by calculation, keep the function pure.
4. **Security Guardrail (NON-NEGOTIABLE)**: The legacy SQL uses string concatenation (`cardno = '"+cardno+"'`), which is a SQL injection vulnerability. The Architecture Agent must be strictly instructed to use **parameterized queries** in the generated *candidate function*.
5. **DB Setup**: Stand up a SQLite test database locally with a schema that *exactly* matches the real MySQL `bankmanagementsystem` tables (e.g., `login` with `formno, cardno, pin`).
6. **Golden File Oracle**: Manually author `golden_file` fixtures for `actionPerformed` that cover BOTH directions: a seeded row with matching cardno/pin (should authenticate) AND a seeded row with a wrong pin or no row at all (should reject).

### 2.2 Gate
`Login.actionPerformed()` migrates using `--baseline-mode golden_file`. Verify by hand: does the generated candidate function use parameterized queries? Does it actually execute against the seeded SQLite database and pass the T3 Golden File tier on both happy and sad paths?

**Do not proceed to Phase 5 until this passes.** If Phase 0 fails, the problem is in the mechanism, not the scale, and building batch orchestration on top of a broken mechanism just produces 13 fabricated results instead of one.

---

## 3. Phase 1 — OpenRewrite graph → dependency-ordered migration queue

**Goal:** turn the CSV/Neo4j call graph into an actual execution order, not just a browsable diagram.

1. Write a small `build_migration_order(graph)` function: topological sort of the `CALLS` edges, leaves (no outbound calls) first. Methods with no dependencies migrate first; methods depending on already-migrated methods come next; anything left after all resolvable nodes are placed (i.e., cycles, or calls into code Rosetta can't parse — e.g. a raw JDBC driver call) gets flagged for manual handling, not silently skipped.
2. Store this as a queue, e.g. `migration_plan.json`: ordered list of `{method, file, depends_on: [...]}`.
3. **Cross-file context injection (the actual fix for the root cause):** when Discovery Agent processes a method with `depends_on` entries, don't hand it the raw graph edge — hand it the **already-certified callee's real signature, parameters, and a one-line contract summary** (e.g. `connect(cardno: str, pin: str) -> bool  # true if credentials match a row in ACCOUNTS table`). This is what stops Discovery Agent from inventing behavior for a call it can see exists but doesn't understand.

### Gate
Re-run Phase 0's `actionPerformed` migration through this new mechanism specifically (if you skipped straight to building it, come back and verify against Phase 0's target). Confirm the generated code actually calls into (or faithfully replicates) the real `connect()` logic — not a fresh invention.

---

## 4. Phase 2 — Swing/UI boundary rules

**Goal:** stop Discovery Agent from trying to migrate GUI code as if it were business logic.

1. New rules file, `rules/swing_java.json`, following the same pattern as `ofbiz.json`/`spring_boot.json` etc. from the extension plan's rules engine. Mark as "strip, don't migrate":
   - `javax.swing.*`, `java.awt.*` imports and the fields/methods that only touch them
   - `JOptionPane` dialog calls (map these conceptually to HTTP response status/messages instead, not to a UI call in generated code)
   - Layout/construction code (`setLayout`, `add(component)`, `pack()`, etc.)
2. Discovery Agent's boilerplate-stripping step (the same one that already removes OFBiz's `Delegator`/`GenericValue` noise) gets a second ruleset applied when `source_lang`/target codebase is ATM — extract the *decision logic* inside an `actionPerformed` handler (which button, what validation, what happens on success/failure) while discarding the UI plumbing around it.
3. This determines what the generated FastAPI/Express response actually *is* — e.g. a failed login becomes `{"success": false, "reason": "invalid_credentials"}` with a 401, not a call to show a dialog.

### Gate
Pick one UI-heavy method (e.g. whatever `Signup.java`'s form-handling looks like) and manually confirm the generated code contains real validation logic and no leftover Swing artifacts (no `JFrame`, no `setVisible`, etc. in the output).

---

## 5. Phase 3 — DB-backed parity testing

**Goal:** the validator needs to handle methods with side effects (`deposit`, `withdraw`, `signup` — anything that writes to the database), not just pure return-value comparison.

### 5.1 Baseline strategy decision — check before committing
Two paths, and this needs a quick feasibility check before picking one, the same way `java_executed` for OFBiz turned out to be blocked by something not discovered until attempted:
- **`java_executed`**: requires the real ATM app + its DB actually runnable locally. Check: does the Ant/NetBeans build even compile in your current environment (same category of risk as OFBiz's Java 26 issue, unverified for this project)? Is the DB (likely MySQL/Derby, check `Conn.java` for the connection string) reachable and seedable with known test data?
- **`golden_file`**: hand-author fixtures by manually tracing what a real deposit/withdrawal *should* produce given known starting balances — same pattern already proven successful on `getGrandTotal`. Likely faster to stand up for a schema this small, and doesn't depend on getting a second legacy build environment working.

**Recommendation:** attempt `golden_file` first for this codebase specifically, given `java_executed` is already a known pain point on OFBiz and there's no evidence yet the ATM build is any easier. Revisit `java_executed` for ATM only if golden-file fixtures prove too hard to hand-verify (e.g. if the balance logic has hidden rules not visible from reading the code alone).

### 5.2 Validator extension
1. Add a DB snapshot/restore step around any test case for a side-effecting method — same pattern already specified for OFBiz's parity testing in the earlier hackathon plan, actually implemented now: snapshot before, run candidate, capture resulting DB state, restore, compare state diff against the golden fixture's expected state (not just the return value).
2. This is a genuinely new validator capability — a new tier, distinct from `T1`/`T3`/`shadow`. Name it explicitly (e.g. `T4_db_state_equivalence`) rather than overloading `T3`, so the parity report continues to honestly label what actually ran — consistent with the trust-in-labeling work already done this session.

### Gate
One side-effecting method (`deposit` is the simplest — single balance update) passes `T4` with a real before/after DB diff shown in the parity report, not just a return-value match.

---

## 6. Phase 4 — Batch migration command

**Goal:** `rosetta migrate-all --dir ATM-Simulator-System --graph migration_plan.json`, only built once Phases 0-3 are individually proven.

1. Walks the dependency-ordered queue from Phase 1.
2. For each method: run the existing single-method pipeline, with cross-file context injection (Phase 1) and UI-boundary stripping (Phase 2) active, using `golden_file` or `java_executed` per Phase 3's decision.
3. On any method's failure after retry cap: **do not halt the whole batch.** Log to the DLQ (already built for OFBiz — reuse it directly), skip to the next independently-resolvable method, and continue. A full-codebase run should degrade gracefully per-method, not all-or-nothing.
4. Final output: a batch summary — X/13 certified, Y in DLQ for manual review, with the same per-method parity reports as today.

### Gate
Full run completes (not necessarily 13/13 passing — some may need manual DLQ review) and produces a coherent summary. This is the actual "full migration" deliverable.

---

## 7. Sequencing summary

```
Phase 0  Prove mechanism on Login → Conn chain           [BLOCKS everything below]
   │
   ▼
Phase 1  Dependency ordering + context injection
   │
   ▼
Phase 2  Swing/UI boundary rules                          [can run in parallel with Phase 3]
   │
   ▼
Phase 3  DB-backed parity (T4 tier)                       [can run in parallel with Phase 2]
   │
   ▼
Phase 4  Batch migration command
   │
   ▼
Full ATM certification run
```

Phases 2 and 3 don't depend on each other and can be split across teammates once Phase 1 lands. Phase 0 is a hard blocker for all of it — it's the one that determines whether the whole approach works at all.

---

## 8. Risk register

| Risk | Mitigation |
|---|---|
| Phase 0 chain still fabricates behavior even with context injection | Stop and reassess before building anything else — this would mean the root-cause diagnosis was incomplete |
| ATM's real DB/build environment has its own version-compatibility surprise (like OFBiz's Java 26 issue) | Golden-file-first strategy (Section 5.1) avoids depending on this at all for the first pass |
| Cycles or unresolvable edges in the call graph | Flagged explicitly in Phase 1's queue-builder, routed to manual handling, not silently dropped |
| Batch run partially fails | DLQ (already built) absorbs per-method failures without blocking the whole run |
| This work starts absorbing time budgeted for OFBiz's remaining items (DLQ verification, `list-failed`, `java_executed`) | Explicit team decision needed on relative priority — this plan doesn't make that call for you |

---

## 9. Definition of done

- [ ] Phase 0: `Login.actionPerformed → Conn.connect` migrates with real (non-fabricated, non-provisional) parity evidence
- [ ] Phase 1: dependency-ordered queue built from the OpenRewrite graph; cross-file context reaches Discovery Agent
- [ ] Phase 2: `atm_swing.json` rules strip UI boilerplate; verified on one UI-heavy method
- [ ] Phase 3: `T4_db_state_equivalence` tier exists and passes on `deposit` with real DB diff evidence
- [ ] Phase 4: `migrate-all` runs the full 13-file codebase, produces a batch summary, degrades gracefully via DLQ on individual failures
- [ ] OFBiz's certified path (`getSubTotal`, `getTotalShipping`, `getGrandTotal`, `getFXConversion`) still passes, unchanged, at the end of this work