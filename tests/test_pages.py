"""Integration tests verifying Streamlit pages render cleanly."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_main_app_renders() -> None:
    """Verify main landing page renders with zero uncaught exceptions."""
    entrypoint = REPO_ROOT / "app.py"
    at = AppTest.from_file(str(entrypoint))
    at.run()
    assert not at.exception


@pytest.mark.parametrize(
    "relative_page_path",
    [
        "pages/1_Market_Dashboard.py",
        "pages/2_Backtest_Lab.py",
        "pages/3_Paper_Trading.py",
        "pages/4_Trade_History.py",
        "pages/5_Settings_About.py",
    ],
)
def test_all_subpages_render(relative_page_path: str) -> None:
    """Verify each page renders cleanly in Streamlit."""
    page_file = REPO_ROOT / relative_page_path
    at = AppTest.from_file(str(page_file))
    at.run()
    assert not at.exception
