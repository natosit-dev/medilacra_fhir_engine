# Understanding TestScript Runner Results

The unified app has an expandable **"What is this test checking? · Results guide"**
panel below the selected TestScript name. It is visible **before** you run a test.

The panel is generated from the selected TestScript: each operation and explicit
assertion receives a plain-language explanation. It defines every row state and
basic FHIR validation state, plus the event phases in the execution log. Each
individual result expander also repeats that step's explanation.

## Example — SHN Provider Connectivity

This is a deliberately limited smoke test, not a clinical or prior
authorization conformance test.

| Step | What it establishes |
|---|---|
| GET `/cds-services` | The request was executed and a response was captured. |
| HTTP 200 assertion | That the HTTP response status was exactly 200. |
| `services` path assertion | That the response JSON includes the `services` field. It does not check that the list is nonempty or that listed services function correctly. |

A typical successful run can show `EXECUTED`, HTTP `200`, validation
`SKIP`, and a whole-run `PASS` at the same time: all **configured**
assertions passed, while the automatic FHIR validator was inapplicable because
the CDS Hooks service-directory JSON is not a FHIR resource.

## How to read the columns

- **section**: FHIR TestScript `setup`, `test` or `teardown`.
- **test**: The name of the test grouping in the TestScript.
- **action**: Identifies one request or assertion.
- **kind**: `operation` sends an HTTP request; `assertion` compares
  observed behavior with an expectation.
- **state**: `EXECUTED` (operation completed without transport error),
  `PASS`, `FAIL`, `ERROR`, `UNSUPPORTED`, or `SKIP`
  (principally automatic validation, not normally an action state).
  `EXECUTED` is the UI name for an operation's internal `PASS`.
- **http**: Actual HTTP response status when one was received.
  It is **not** itself a verdict on business behavior.
- **validation**: The result of **basic** FHIR response parsing/checking:
  `PASS`, `FAIL`, `ERROR` or `SKIP`. `None` on an assertion row
  is normal. For operations, multiple results may be comma-separated.
- **error**: A runtime/processing error attached to the action, if any.
- **label**: Human-readable action name provided by the TestScript.
- **phase** (execution log): Category of event, not a pass/fail:
  `run`, `configuration`, `fixture`, `authentication`,
  `transport`, `operation`, `validation`, `assertion` or
  `persistence`. Each phase is defined in the panel.

## Boundaries of the implemented checker

- A successful HTTP request is not proof of a correct clinical or payer
  decision, even with HTTP 200.
- A TestScript assertion measures **only the exact property it checks**.
- Basic FHIR validation can parse FHIR JSON and optionally compare
  `resourceType` and declared `meta.profile`. It does **not** validate
  complete StructureDefinitions or certify US Core/Da Vinci conformance.
- `SKIP` does not fail the current overall run calculation.
- A whole-run `PASS` means no `FAIL`, `ERROR` or `UNSUPPORTED`
  was reported in executed assertions/basic validation, and no unsupported
  TestScript elements were declared. It does not imply that the test had
  strong or complete assertions.

## Source and maintenance

The app imports the dictionaries `ACTION_STATES`, `VALIDATION_STATES`,
`EVENT_PHASES` and per-action explanation functions from
`apps/workbench/toolbench/explain.py`. This is kept outside Streamlit and
unit tested against the real CDS listing and IRIS CapabilityStatement TestScripts.
It intentionally documents observed implemented behavior, not the full
FHIR TestScript specification.
