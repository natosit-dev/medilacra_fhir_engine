"""Requirements page stays last in both standalone and integrated Workbench."""
from pathlib import Path

from unified.page_catalog import PAGES


ROOT = Path(__file__).resolve().parents[1]


def test_shn_requirements_are_last_navigation_page():
    page = PAGES[-1]
    assert page.slug == "shn-testing-requirements"
    assert page.source == "apps/workbench/pages/6_SHN_Testing_Requirements.py"
    assert (ROOT / page.source).is_file()


def test_shn_requirements_markdown_is_dated_and_provisional():
    document = ROOT / "apps/workbench/docs/SHN_TESTING_REQUIREMENTS_2026-10-31.md"
    content = document.read_text(encoding="utf-8")
    assert "2026-10-31" in content
    assert "Provisional" in content
    assert "SHN-TST-001" in content
    assert "SHN-TST-017" in content
