from types import SimpleNamespace

from support_agent.browser import ApprovedBrowser


def test_browser_rejects_non_allowlisted_navigation() -> None:
    browser = ApprovedBrowser(region="us-east-1")
    result = browser.navigate(SimpleNamespace(url="https://example.com/login"))
    assert "error" in result


def test_browser_disables_interactive_actions() -> None:
    browser = ApprovedBrowser(region="us-east-1")
    assert "error" in browser.click(object())
    assert "error" in browser.type(object())
