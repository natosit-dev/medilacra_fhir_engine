# Lucifer — ADT/DFT Contract-Betrayal Experiment
## Gap Analysis and High-Level MVP Build Plan

- **Status:** Proposed / documentation only — not implemented or accepted
- **Recorded:** 2026-11-20
- **Target repository:** [natosit-dev/medilacra_fhir_engine](https://github.com/natosit-dev/medilacra_fhir_engine)
- **Working branch:** `experiment/lucifer-adt-dft-20261120`
- **Base:** `main` at `35b4b88c5c7e71da5965c5731c5efeac22673492`
- **Message scope:** HL7 v2.5 **ADT** and **DFT** only; initial A01, P03, and A03 scenario
- **Source-of-intent appendix:** [Raw prompt history](LUCIFER_ADT_DFT_RAW_PROMPT_HISTORY_2026-11-20.md)
- **Implementation state:** Existing source inspected; no new production or test code is claimed by this plan.

## 1. Purpose and ontology

**Research question:** Can a receiver successfully accept syntactically credible HL7 ADT/DFT messages, violate the explicitly specified meaning of those messages, create an authoritative-looking financial assertion, and preserve that false assertion after contradictory evidence arrives?

Lucifer is **betrayal**, not generic compound corruption. The specified interface contract is the object betrayed. The upstream ADT/DFT messages need not be corrupted.

Keep four distinct objects:

1. **Source reality:** What the synthetic encounter and transactions actually did.
2. **Source representation:** The ordered ADT/DFT messages emitted about that reality.
3. **Semantic contract:** The versioned sender/receiver obligations that define the local meaning of ambiguous fields, missingness, transaction progression, finalization, and updates.
4. **Materialized consumer assertion:** What the receiver actually stores and claims about the encounter, with its own ID, timestamps, and provenance.

Successful message parsing, ACKs, record IDs, and timestamps establish facts about handling; they do not independently establish that the *asserted financial value* is true.

A key distinction: Beatrice is the faithful representation of a known synthetic universe, **not reality itself**. Do not collapse reality, reference materialization, the message stream, or the consumer's reported fact into one truth category.

## 2. Bounded first experiment — LUCIFER-FIN-001, “The Immortal Zero”

**Credible worst outcome:** A synthetic visit accumulates $400 in charges, yet the receiving system permanently asserts an encounter total of $0.00. The $0 record has a valid identifier and creation timestamp; later DFT charges and a discharge report do not revise it.

**Illustrative scenario sequence (actual synthetic times to be frozen in the scenario manifest):**

| Order | HL7 event | Faithful interpretation required by scenario contract | Betrayed receiver result |
| --- | --- | --- | --- |
| 1 | ADT^A01 | Encounter admitted; PV1-45 blank; final PV1-47 total not yet available | Empty field parsed as NULL, then defaulted to $0.00; first financial assertion persisted with ID and timestamp |
| 2 | DFT^P03 | FT1-11 charge +$125.00 tied to same visit | Persisted encounter total still $0.00 |
| 3 | DFT^P03 | FT1-11 charge +$275.00; source accumulated charges $400.00 | Persisted total still $0.00 |
| 4 | ADT^A03 | Discharge; PV1-45 populated; PV1-47 reports final **total charges** $400.00 | Existing first-write record not reconciled |
| 5 | Consumer projection/query | Contract-defined final encounter total $400.00 | Returns $0.00 as if authoritative |

**Terminology:** PV1-47 is *Total Charges*, not inherently an adjudicated insurance **claim total**. The MVP examines a contract-defined synthetic encounter-charge total. Do not claim the experiment models full claim adjudication.

**HL7 semantics boundary:** PV1-45 = Discharge Date/Time is notoriously workflow/interface-dependent. The scenario contract deliberately defines blank PV1-45 as “this source has not yet reported discharge” and says when PV1-47 is or is not populated. These rules are **local contract terms**, not universal claims about HL7. In HL7 v2, an empty field is not interchangeable with the explicit null/delete token `""`. The NULL conversion occurs **after parsing**, in receiver mapping, before zero defaulting.

**Persistence mechanism:** model a receiver policy that saves the earliest asserted total and declines subsequent update/reconciliation. The identifier and record-creation timestamp may be accurate even while the monetary assertion is false. Contractual betrayal is evidenced by the discrepancy between agreed update obligations and actual materialized state.

**Experimental control:** replay the **same faithful ordered messages** through a contract-faithful receiver and a Lucifer receiver. They receive identical input; their mappings and persistence policies differ. Do not falsify the source messages to manufacture the outcome.

## 3. Experimental grammar and method

**Composite first:** Define and record every material variable. Execute the *whole* event sequence and observe whether the predicted persistent falsehood occurs. Repeat with the same scenario and fixed variables to establish reproducibility.

**Only after an unexpected result:** Isolate a candidate mechanism or protective control, inspect evidence, then recombine and repeat. Isolation is diagnostic follow-up; it is not a gate before observing the full coupled failure. A failure to reproduce may indicate a safeguard or a defective test construction; do not prejudge either.

Two separate, non-interchangeable claims:

- **Deterministic reproducibility:** Identical source seed, Inferno seed, scenario contract, event stream, receiver policy, software revision, and effective configuration yield equivalent semantic outcomes and (excluding run-creation metadata) identical canonical artifacts.
- **Mechanistic reproducibility:** The same betrayal mechanism arises under multiple valid variations; **deferred** until the initial case is demonstrated.

Do not declare the receiver incorrect merely because it differs from a preferred convention; record and evaluate the precise, versioned obligation that it violated.

## 4. Codebase inventory and harvest basis

The **target repository is the unified Medilacra FHIR Engine repo**, with the original MVP-0 source retained at `apps/mvp0/`. The name “FHIR Engine” does **not** narrow Lucifer's first message scope to FHIR.

Inspected target paths at branch creation:

- `apps/mvp0/experiments/disco_inferno/`: `run_experiment.py`, `corruptions.py`, `compare.py`, `materialize.py`, `exports.py`, `reporting.py`, `process_control.py`, `offline_sdoh.py`, existing README and evidence directories.
- `apps/mvp0/hl7_demo/messages.py`: `build_adt()` currently builds A01; `build_dft()` builds P03.
- `apps/mvp0/hl7_demo/segments.py`: PV1 includes fields 44 and 45; PV1-47 is not populated. FT1 includes FT1-11; FT1-1 is fixed to `1` in its segment builder, needing care if several FT1s appear within one message.
- `apps/mvp0/hl7_demo/generators.py`: generated encounters currently have an admit and discharge datetime; transaction timestamps and IDs are not all deterministic.
- `apps/mvp0/experiments/disco_inferno/exports.py`: bulk HL7 exports currently include ADT^A01, DFT^P03 and other message families; its use is reusable, but Lucifer needs ordered per-event output.

**Related upstream work, not present in target main:** `natosit-dev/medilacra` branch `experiment/disco-inferno-lucifer` has a newer `experiments/disco_inferno/lucifer.py` and `tests/test_disco_inferno_lucifer.py`. That implementation models two **synthetic privacy-evidence** deceptions (“phantom violation” and “concealed violation”) by modifying tabular evidence about invented access events. It **does not** yet implement ADT/DFT financial progression, the versioned interface contract, or persistent receiver state. Treat it as a source to selectively harvest, not as a working DFT test or evidence of external-system behavior. It also explicitly does not make legal HIPAA findings.

**Existing capabilities worth reusing:** seeded synthetic world generation; Beatrice/Inferno separation; controlled corruption receipts; DuckDB source materialization; dated export/ZIP bundles; process control; offline mode; existing Streamlit app integration. Preserve the current app architecture; do not make a new UI or deployment a prerequisite.

**Architectural caution:** the Engine repo's historical milestone documents distinguish generator/domain functions, application orchestration, and independent evaluation. The accepted unified Streamlit shell does not mean the Engine must internally own every receiver and assertion mechanism. Place the scenario adapter near Disco Inferno; keep receiver execution/state comparison clearly separated and reusable.

## 5. Gap analysis

| Capability | Observed state | Gap / MVP work |
| --- | --- | --- |
| Patient, encounter, charge generation | Existing synthetic models and generators | Reuse with a deterministic event-profile override |
| Beatrice, comparison, manifest, bundle | Existing Disco Inferno primitives | Extend to an event-sourced witness and downstream assertions |
| ADT A01 and DFT P03 builders | Present under `apps/mvp0/hl7_demo` | Reuse and make the scenario timeline/event identity explicit |
| ADT A03 discharge | Not exposed by the inspected `build_adt` A01 path | Add scenario-specific discharge message building |
| Active encounter and withheld final total | Generator normally has discharge datetime from start | Represent encounter **state at each event**, not just final snapshot |
| PV1-47 | Existing `seg_pv1` leaves it blank | Add contract-driven, conditional total-charge population |
| FT1 events | FT1-11 amounts exist; DFT builder supports a list | Emit incremental P03 events with consistent visit linkage; handle FT1-1 numbering for multiple FT1s |
| Time determinism | MSH clock/control IDs, generated UUIDs and transaction dates not fully seed-controlled | Inject fixed synthetic event clock and deterministic control/transaction/visit IDs |
| Contract | No dedicated ADT/DFT financial semantic contract object identified | Add versioned, machine-readable contract with human-readable obligations |
| Receiver state | No Lucifer financial receiver/persistence fixture in target | Implement local faithful and betrayed policies with durable snapshots |
| Replay/evidence | Existing exports and comparator are primarily model/corruption based | Retain ordered inbound messages, per-message receiver mapping traces, state snapshots, final assertion |
| Lucifer provenance | Existing upstream privacy fixture only; absent from target | Document selective harvest and preserve privacy case as distinct experimental branch/fixture |
| Tests | Existing Disco tests protect model invariants | Add sequence, contract, replay, persistence, determinism, and comparison tests |

**Assessment boundary:** source inspection, not test execution. Do not present missing features as formally proven absent from every branch or integration; the table describes inspected paths of target `main` at the pinned base commit.

## 6. High-level build sequence

### Phase A — Contract and event witness

Create `LUCIFER-FIN-001` configuration with:
- HL7 version and message profiles; explicit fields and interpretation obligations;
- patient/encounter/visit identity and consistency rules (`PID-3`, `PV1-19`, `FT1-2`, `MSH-10`);
- sender-specific meaning of blank PV1-45, availability of PV1-47, and finalization/update conditions;
- FT1 charges, currency, posting order, DFT aggregation semantics, and permitted corrections;
- replay seeds (default reality `42`, Inferno `666`), fixed synthetic clock, expected final charge total;
- separate expected outcomes for faithful and betrayed receiver policies.

Add an immutable event ledger to the DuckDB witness. Preserve the original source-reality tables. Do not mutate Beatrice while running Lucifer.

### Phase B — Ordered ADT/DFT projection

Reuse existing HL7 message builders and extend minimally:
- A01 active encounter / blank PV1-45 and PV1-47 according to contract;
- sequential DFT^P03 charge events;
- A03 discharge with populated PV1-45 and contract-defined final PV1-47;
- deterministic timestamps, unique message control IDs, and consistent visit identifiers.

Store canonical wire bytes with actual HL7 segment terminators (CR) and explicit message boundaries. Check syntax and required fields; distinguish wire validity from the **local semantic contract**.

**Scope is ADT and DFT only.** No ORU, ORM, FHIR, X12, CRD/DTR/PAS, or insurer adjudication in the first build.

### Phase C — Faithful versus Lucifer receiving policies

Implement one small, offline local receiver/parser **that consumes the generated HL7 stream**, not a hand-built final DataFrame. Add a transparent sequence of field extraction, meaning resolution, persistence decision, and consumer-visible query.

- **Faithful:** absent final total remains unavailable; changes reconcile as required; final assertion is $400.00.
- **Lucifer:** absent value → parsed missing/NULL → default $0.00 → write once with new persistent ID and stored-at timestamp → ignore or fail to reconcile incoming charges and final A03 update.

Store traces for both with receipt/processing time separated from event time. These are *simulated mappings and policies*, not assertions about a named EHR or clearinghouse.

### Phase D — Composite replay, evidence, and diagnosis

Run complete sequence on both receivers, compare final assertions with Beatrice and contract. Repeat with fixed inputs and compare normalized outputs/hashes. If expected outcome is not reproduced, diagnose via isolated variables and **recombine** to validate mechanism. Retain failed experiments with their actual observations; do not rewrite expectations to force a green result.

### Phase E — Inspectable artifact bundle and modest app entry

Use existing `apps/mvp0/experiments/disco_inferno` ZIP/report/manifest facilities. Add one CLI-accessible scenario invocation first, then optionally expose it in the existing unified Streamlit shell. No new web service, multiuser support, or externally hosted SUT is needed for MVP.

## 7. Proposed output contract

```text
lucifer_fin_001/<run-id>/
  contract.yaml                   # Versioned semantic agreement
  scenario.json                   # Inputs, seeds, synthetic timeline, effective configuration
  beatrice.duckdb                 # Immutable synthetic source and event witness
  messages.hl7                    # Ordered ADT / DFT inputs, wire-preserving
  receiver_trace.jsonl            # Per-message extraction/mapping/persistence decisions
  receiver_states.duckdb          # Faithful / Lucifer state snapshots
  assertions.json                 # Explicit claimed totals and certainty/status
  comparison.md                   # Contract obligation / actual / contradiction
  manifest.json                   # Source revision, config, hashes, run metadata
  DISCO_INFERNO_LUCIFER_<run-id>.zip
```

**Timestamp semantics:** distinguish occurred-at, sent-at, received-at, persisted-at, and artifact-generated-at. The synthetic clock is fixed for replay; physical run creation time need not be fixed. ID uniqueness is evaluated independently of whether a claim is true.

## 8. MVP acceptance and falsification criteria

Accept the MVP implementation only when:
1. Same fixed inputs yield the same canonical ADT/DFT messages and equivalent receiver states.
2. Both receivers consume the **same** ordered wire stream, with a versioned, inspectable contract.
3. Beatrice remains unchanged; its accumulated/final charges sum to **$400.00** for the example case.
4. The faithful receiver respects missingness and updates to the correct final $400.00.
5. The Lucifer receiver's combined policy yields the persistent $0.00 assertion *after* the A03 and both DFT events, retaining real metadata about its own record creation.
6. Comparison states exactly which contract obligations are broken, with per-event lineage.
7. The final report distinguishes **observed test result**, **expected synthetic outcome**, **inference about mechanism**, and **unresolved uncertainty**.
8. Replays that do **not** exhibit betrayal are retained and diagnosed; tests must not simply assert that deception was manufactured by the fixture.

These are **planned acceptance tests**; none is currently claimed to pass in the new FHIR Engine branch.

## 9. Open decisions, assumptions, and scope limits

- Whether A03 alone is the finalization trigger, or the local contract requires another explicitly declared event/condition. For MVP, use A03 and document that choice.
- Whether downstream contract says reconcile to latest PV1-47, recalculate using FT1, or both. Define clearly; do **not** infer universal rules from HL7.
- How FT1 adjustments, cancellations, credits, duplicate transmissions, and message reordering behave. Exclude initially or freeze a precise policy; do not silently normalize.
- Receiver's first-write key and asserted record ID must be distinguishable from MSH-10, FT1-2 and visit ID.
- Ensure a literal `0` is distinguishable from blank, SQL NULL, explicit HL7 delete, unknown, incomplete, and finalized zero.
- Source code from the original Medilacra Lucifer branch may be harvested selectively, but source/commit/path provenance must be recorded; avoid silently replacing target baseline files.
- This is **synthetic local reproduction**. No claim that SHN, an EHR, claims system, or regulator has exhibited this defect. No certification, HIPAA finding, or general conformance verdict.
- Do not expand to other message families, introduce a universal entropy score, or build a new app/deployment for a single scenario.

## 10. Design lineage and decision log

| Date | Decision / premise | Provenance |
| --- | --- | --- |
| 2026-08-30 | Name-first Disco Inferno; controlled damage, Beatrice, seeds, Charon/Null/Cerberus grammar | Original Medilacra Disco Inferno history and MVP docs |
| 2026-09-11 | Lucifer repurposed from generic compound damage to **betrayal** | User-origin prompt preserved in September provenance documents |
| 2026-11-20 | Worst outcome can be continued operation producing believable falsehoods | Conversation prompt citing an earlier assistant statement, followed by user request to build Lucifer |
| 2026-11-20 | PV1-45 ambiguity and explicit interface specifications are *the contractual seam* | User correction |
| 2026-11-20 | Composite scenario first; fix variables and reproduce; isolate **after** unexpected outcome; recombine | User correction |
| 2026-11-20 | ADT and DFT only for initial implementation | User scope decision |
| 2026-11-20 | New branch off Medilacra FHIR Engine; plan and full raw prompts under `docs/` | User instruction |

This is a **prospective build plan**. Earlier interpretations are not retroactively described as original August design. Historical prompt quotations and their attribution are preserved in the [prompt appendix](LUCIFER_ADT_DFT_RAW_PROMPT_HISTORY_2026-11-20.md).

## 11. Traceable sources

**Primary design/provenance documents supplied for this conversation:**
- `Disco_Inferno_Story_v1.1_2026-09-14.docx` (2026-09-14): story, prior implementation and Lucifer-as-betrayal distinction.
- `Disco_Inferno_Name_Design_Lineage_Current_Meaning_v1.2_SANITIZED.docx` (2026-09-11): source/evidence classes, chronological naming, explicit Lucifer reinterpretation and synthetic/legal boundaries.

**Inspected source and historical implementations:**
- [Target FHIR Engine repo, pinned base](https://github.com/natosit-dev/medilacra_fhir_engine/tree/35b4b88c5c7e71da5965c5731c5efeac22673492)
- [Target Disco Inferno code](https://github.com/natosit-dev/medilacra_fhir_engine/tree/main/apps/mvp0/experiments/disco_inferno)
- [Target HL7 message builders](https://github.com/natosit-dev/medilacra_fhir_engine/blob/main/apps/mvp0/hl7_demo/messages.py)
- [Target HL7 segment builders](https://github.com/natosit-dev/medilacra_fhir_engine/blob/main/apps/mvp0/hl7_demo/segments.py)
- [Original Medilacra Lucifer implementation](https://github.com/natosit-dev/medilacra/blob/experiment/disco-inferno-lucifer/experiments/disco_inferno/lucifer.py)
- [Original Lucifer tests](https://github.com/natosit-dev/medilacra/blob/experiment/disco-inferno-lucifer/tests/test_disco_inferno_lucifer.py)
- [Target architecture/topology history](MILESTONES_AND_APP_TOPOLOGY_2026-10-21.md), [release decision log](RELEASE_DECISIONS_2026-10-23.md), [harvest scope](HARVEST_SCOPE.md).

**Version note:** All source claims above reflect inspected paths, not executed tests. This document must be updated when implementation changes or observed evidence warrants a new status.
