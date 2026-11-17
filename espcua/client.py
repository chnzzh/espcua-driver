"""Low-level HTTP REST client for communicating with ESP32-P4 IP-KVM endpoints."""

import json
import urllib.request
import urllib.error
from typing import Optional, Any


class ESPCUAClientError(Exception):
    """Exception raised for HTTP or communication errors with ESP32-P4."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class ESPCUAClient:
    """REST Client for ESP32-P4 IP-KVM endpoints."""

    def __init__(self, host: str = "192.168.1.100", port: int = 80, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> tuple[bytes, dict[str, str], int]:
        url = f"{self.base_url}{path}"
        req_headers = {"User-Agent": "ESPCUAClient/1.0"}
        if headers:
            req_headers.update(headers)

        payload = None
        if data is not None:
            payload = json.dumps(data).encode("utf-8")
            req_headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=payload, headers=req_headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
                resp_headers = {k: v for k, v in resp.headers.items()}
                return body, resp_headers, resp.status
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise ESPCUAClientError(
                f"HTTP {e.code} for {method} {url}: {err_body}",
                status_code=e.code,
                response_text=err_body,
            ) from e
        except urllib.error.URLError as e:
            raise ESPCUAClientError(f"Connection failed for {method} {url}: {e.reason}") from e

    def capture(self, quality: int = 80) -> tuple[bytes, dict[str, str]]:
        """Fetches a JPEG snapshot from /api/v1/capture.

        Returns (jpeg_bytes, headers_dict) containing 'X-Video-Width', 'X-Video-Height'.
        """
        body, headers, _ = self._request("GET", f"/api/v1/capture?quality={quality}")
        return body, headers

    def get_video_status(self) -> dict[str, Any]:
        """Queries /api/v1/video/status."""
        body, _, _ = self._request("GET", "/api/v1/video/status")
        return json.loads(body.decode("utf-8"))

    def set_video_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Sends EDID/HPD/USB reattach config to /api/v1/video/config."""
        body, _, _ = self._request("POST", "/api/v1/video/config", data=payload)
        return json.loads(body.decode("utf-8"))

    def send_keyboard(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Sends keyboard action to /api/v1/hid/keyboard."""
        body, _, _ = self._request("POST", "/api/v1/hid/keyboard", data=payload)
        return json.loads(body.decode("utf-8"))

    def send_mouse(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Sends mouse action to /api/v1/hid/mouse."""
        body, _, _ = self._request("POST", "/api/v1/hid/mouse", data=payload)
        return json.loads(body.decode("utf-8"))

    def send_power(self, action: str) -> dict[str, Any]:
        """Sends power action to /api/v1/atx/power (click, hold, on, off, cycle)."""
        body, _, _ = self._request("POST", "/api/v1/atx/power", data={"action": action})
        return json.loads(body.decode("utf-8"))

    def send_reset(self, duration_ms: int = 500) -> dict[str, Any]:
        """Sends reset action to /api/v1/atx/reset."""
        body, _, _ = self._request("POST", "/api/v1/atx/reset", data={"action": "pulse", "duration_ms": duration_ms})
        return json.loads(body.decode("utf-8"))

    def get_atx_status(self) -> dict[str, Any]:
        """Queries /api/v1/atx/status."""
        body, _, _ = self._request("GET", "/api/v1/atx/status")
        return json.loads(body.decode("utf-8"))

    def get_system_status(self) -> dict[str, Any]:
        """Queries /api/v1/system/status."""
        body, _, _ = self._request("GET", "/api/v1/system/status")
        return json.loads(body.decode("utf-8"))

    def get_logs(self, since: int = 0) -> dict[str, Any]:
        """Queries /api/v1/logs?since=<seq> for incremental firmware log entries."""
        seq = max(0, int(since))
        body, _, _ = self._request("GET", f"/api/v1/logs?since={seq}")
        return json.loads(body.decode("utf-8"))
