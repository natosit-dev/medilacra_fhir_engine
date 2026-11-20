# Lucifer ADT/DFT — Raw Prompt History and Provenance

- **Captured:** 2026-11-20
- **Scope:** The user-authored turns in the **current Lucifer ADT/DFT design thread**, reproduced verbatim from the visible conversation, in order.
- **Companion:** [Lucifer ADT/DFT MVP plan](LUCIFER_ADT_DFT_MVP_PLAN_2026-11-20.md)
- **Status:** User instructions / research hypotheses, **not** a record of software execution.
- **Attribution rule:** Some user turns begin by quoting **earlier assistant language** before correcting it. The quoted language is preserved as part of the raw *user message*, **not attributed as an original user assertion**.
- **Exclusion rule:** Assistant replies, generated intermediate drafts, tool outputs, and unrelated conversation turns are not presented as user prompts. September historical prompts are clearly separated from November direct transcript.

## Historical origin (separate source, September 11)

The September 11 sanitized provenance document preserves this user-originated later reinterpretation of a reserved name:

**2026-09-11 — historical user-origin prompt, quoted from `Disco_Inferno_Name_Design_Lineage_Current_Meaning_v1.2_SANITIZED.docx`:**

```text
Lol Lucifer should be for betrayal- synthetic fake HIPAA violations                  🤣🤣🤣🤣
```

This historical wording establishes **Lucifer = betrayal** as a preexisting direction, not an idea invented after the November MythBusters discussion. It refers to simulated evidence, not a real HIPAA legal finding. The original Disco Inferno MVP, Beatrice naming, 42/666 seeds, and operator-selection lineage are documented in that provenance file and `Disco_Inferno_Story_v1.1_2026-09-14.docx`. The full earlier 17-prompt Disco Inferno corpus is **not reproduced here**; this appendix is scoped to the Lucifer ADT/DFT design thread.

## November 20 — verbatim user prompts

### RAW-N01 — revive Lucifer following the safety discussion

```text
The worst outcome isn't necessarily that the system stops working. It might be that it continues working while producing believable falsehoods.

Yoooooo we should build Lucifer! 
```

**Attribution note:** The first two sentences quote an earlier assistant response. The user's proposed action is the second paragraph.

### RAW-N02 — DFT total, missing discharge, default zero, persistence

```text
I'm thinking a DFT message that has a charge field that defaults null to 0. Something like claim total. If visit has no value in PV1:45, the visit is considered still in progress so no total claim field is populated. That changes to null, which defaults to 0 with a unique id and timestamp. It stays that way no matter how many claims are added
```

### RAW-N03 — contract as object of betrayal; PV1-45 ambiguity

```text
 one distinction: HL7 doesn't inherently say that an empty PV1-45 means an encounter must be active, or that PV1-47 must remain empty until discharge. We would establish that behavior in our synthetic sender's contract.

The contract is what is betrayed. PV1:45 is NOTORIOUSLY ambiguous, and requires  explicit specs and mapping 
```

**Attribution note:** First paragraph quotes an assistant caveat. The second paragraph is the user's correction. Preserve the distinction; the normative object is the explicit interface contract.

### RAW-N04 — composite first; reproduce; isolate then recombine

```text
test those separately before combining them, because otherwise we wouldn't know which defect actually produced the persistent falsehood.

No, better to test them together. Define and record the variables. See if it is reproducible. If it fails, then isolate the failure, then recombine. 
```

**Attribution note:** First paragraph quotes an earlier assistant proposal; second is the user's methodological correction.

### RAW-N05 — message scope; gap analysis and MVP request

```text
So this will be DFT messages, ADT messages only at this point. Let's see a gap analysis and high level build to MVP 
```

### RAW-N06 — target repository, branch and documentation request

```text
Let's create a new branch off Medilacra FHIR Engine for Lucifer. Add this to docs, full trim, raw prompt history.
```

## Interpretation boundaries (not raw prompts)

The following are **editorial observations from the sequence**, not quotations from the user:

1. The user distinguished a betrayed *specified contract* from an interpretation that merely differs from general HL7 expectations.
2. The user preferred **whole-system composite testing first** with fixed variables, reproducibility checks, and decomposition/recombination only for diagnosis.
3. The user explicitly bounded the first implementation to ADT/DFT messages.
4. The user chose **Medilacra FHIR Engine** as the branch target; its bundled MVP-0 code already contains the relevant Disco Inferno and HL7 builders.
5. The proposed $400/$0 sequence, specific A01/P03/A03 ordering, fidelity policy, output file names, and acceptance criteria are **assistant-authored plan elaborations** based on the user's design direction. They are not raw user prompts or observed test results.
6. The MythBusters safety observation occurred earlier in the conversation, but the exact original user turn has **not** been verified from a direct raw transcript in this appendix. No reconstructed wording is passed off as a verbatim prompt.

## Source identity and change rules

- Current thread: directly visible user messages, captured as `RAW-N01` through `RAW-N06`.
- Historical provenance: `Disco_Inferno_Name_Design_Lineage_Current_Meaning_v1.2_SANITIZED.docx` (2026-09-11), plus `Disco_Inferno_Story_v1.1_2026-09-14.docx`. Historical quotations are explicitly separated.
- **Do not silently edit the RAW blocks.** Append corrections or later turns as a new section with a capture date and provenance note; preserve earlier wording even when technical decisions change.
- Avoid back-projecting the November ADT/DFT scenario into August/September original design intent.

**Purpose:** preserve the chain from user instruction through design decision and implementation planning without manufacturing an origin story or confusing a plan with executed evidence.
