"""Original application entry points preserved as registered Streamlit pages.

Keep these pointers stable during the first integration. A page's existing
working directory, imports, and business logic remain owned by its subtree.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExistingPage:
    section: str
    slug: str
    title: str
    source: str
    icon: str


PAGES: tuple[ExistingPage, ...] = (
    # Synthetic clinical reality: patient/context generation and modification.
    ExistingPage("Clinical Reality", "hl7-generator", "HL7 Message Generator", "apps/mvp0/medi_lacra_app.py", "🧬"),
    ExistingPage("Clinical Reality", "generate-persist", "Generate & Persist", "apps/mvp0/pages/2_Generate_and_Persist.py", "🗂️"),
    ExistingPage("Clinical Reality", "message-config", "Message Configuration", "apps/mvp0/pages/3_Message_Config.py", "📝"),
    ExistingPage("Clinical Reality", "site-scenario", "Site & Scenario Setup", "apps/mvp0/pages/5_Site_and_Scenario_Setup.py", "🏥"),

    # Operational reality: configuration, connections and test execution.
    ExistingPage("Operational Reality", "test-systems", "Test Systems", "apps/workbench/pages/1_Test_Systems.py", "🧭"),
    ExistingPage("Operational Reality", "connection-lab", "Connection Lab", "apps/workbench/pages/2_Connection_Lab.py", "🌐"),
    ExistingPage("Operational Reality", "authentication", "Authentication", "apps/workbench/pages/3_Auth_Workbench.py", "🔑"),
    ExistingPage("Operational Reality", "testscript-runner", "FHIR TestScript Runner", "apps/workbench/pages/4_TestScript_Runner.py", "🧪"),
    ExistingPage("Operational Reality", "mvp0-connectivity", "MVP-0 Connectivity", "apps/mvp0/pages/1_medi_lacra_connectivity.py", "📡"),

    # Existing full workflows and research/demo experiments.
    ExistingPage("Workflows & Experiments", "x12-eligibility", "X12 Eligibility (270/271)", "apps/mvp0/pages/8_X12_Eligibility.py", "📨"),
    ExistingPage("Workflows & Experiments", "shn-provider-epa", "SHN Provider ePA", "apps/mvp0/pages/10_SHN_Provider_ePA.py", "🔁"),
    ExistingPage("Workflows & Experiments", "piqi-connectathon", "PIQI Connectathon 43", "apps/mvp0/pages/9_PIQI_Connectathon_43.py", "🔬"),
    ExistingPage("Workflows & Experiments", "disco-inferno", "DiScO Inferno", "apps/mvp0/pages/8_Disco_Inferno.py", "🔥"),

    # Evidence and other previously working experimental tools.
    ExistingPage("Inspection & Tools", "evidence", "Evidence", "apps/workbench/pages/5_Evidence.py", "🔎"),
)
