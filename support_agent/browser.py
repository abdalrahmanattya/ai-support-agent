"""AgentCore Browser with a code-enforced informational boundary."""

from __future__ import annotations

from urllib.parse import urlparse

from strands_tools.browser import AgentCoreBrowser

ALLOWED_HOSTS = {"docs.aws.amazon.com", "aws.amazon.com"}


class ApprovedBrowser(AgentCoreBrowser):
    def navigate(self, action):
        parsed = urlparse(action.url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            return {"error": "Browser navigation is limited to approved public documentation."}
        return super().navigate(action)

    def click(self, action):
        del action
        return {"error": "Interactive browser actions are disabled."}

    def type(self, action):
        del action
        return {"error": "Browser form entry is disabled."}

    def set_cookies(self, action):
        del action
        return {"error": "Browser cookies cannot be changed."}

    def evaluate(self, action):
        del action
        return {"error": "Browser script execution is disabled."}
