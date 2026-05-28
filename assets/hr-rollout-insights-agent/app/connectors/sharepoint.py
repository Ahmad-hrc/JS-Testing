"""SharePoint connector — reads documents via Microsoft Graph API (read-only)."""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class SharePointConnector:
    """Read-only connector for SharePoint document libraries via Microsoft Graph API.

    Requires environment variables:
        SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET
    or connection dict with the same keys.
    """

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self, connection: dict[str, Any]) -> None:
        self.tenant_id = connection.get("tenant_id") or os.environ.get("SHAREPOINT_TENANT_ID", "")
        self.client_id = connection.get("client_id") or os.environ.get("SHAREPOINT_CLIENT_ID", "")
        self.client_secret = connection.get("client_secret") or os.environ.get("SHAREPOINT_CLIENT_SECRET", "")
        self.site_url = connection.get("site_url", "")
        self.folder_path = connection.get("folder_path", "")
        self._token: str | None = None

    def _get_token(self) -> str:
        """Obtain OAuth2 client-credentials token from Azure AD."""
        import urllib.parse
        import urllib.request
        import json

        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
        return result["access_token"]

    def _ensure_token(self) -> str:
        if not self._token:
            self._token = self._get_token()
        return self._token

    def _graph_get(self, path: str) -> Any:
        import urllib.request
        import json
        token = self._ensure_token()
        url = f"{self.GRAPH_BASE}{path}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def _get_site_id(self) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(self.site_url)
        hostname = parsed.netloc
        site_path = parsed.path.rstrip("/")
        result = self._graph_get(f"/sites/{hostname}:{site_path}")
        return result["id"]

    def fetch_all(self) -> list[tuple[str, str]]:
        """Return list of (filename, content) tuples for all documents in the configured folder.

        NOTE: This is a real implementation stub. In production it fetches file content
        via Microsoft Graph /drives/{drive-id}/items/{item-id}/content.
        In test environments, inject a mock via dependency inversion.
        """
        if not all([self.tenant_id, self.client_id, self.client_secret, self.site_url]):
            logger.warning("SharePointConnector: missing credentials — returning empty document list")
            return []
        try:
            site_id = self._get_site_id()
            drives = self._graph_get(f"/sites/{site_id}/drives")
            if not drives.get("value"):
                return []
            drive_id = drives["value"][0]["id"]
            folder = self.folder_path.strip("/")
            items = self._graph_get(f"/drives/{drive_id}/root:/{folder}:/children") if folder else self._graph_get(f"/drives/{drive_id}/root/children")
            results = []
            for item in items.get("value", []):
                if item.get("file") and item["name"].endswith((".txt", ".md", ".docx", ".pdf")):
                    # Fetch content (text files only for now)
                    import urllib.request
                    token = self._ensure_token()
                    content_url = item.get("@microsoft.graph.downloadUrl") or f"{self.GRAPH_BASE}/drives/{drive_id}/items/{item['id']}/content"
                    req = urllib.request.Request(content_url, headers={"Authorization": f"Bearer {token}"})
                    with urllib.request.urlopen(req) as resp:
                        content = resp.read().decode("utf-8", errors="replace")
                    if content:
                        results.append((item["name"], content))
            return results
        except Exception as exc:
            logger.error("SharePointConnector fetch failed: %s", exc)
            return []
