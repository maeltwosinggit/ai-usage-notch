"""
Antigravity Quota Provider for Codenotch Local.

Communicates with Antigravity's local language server RPC over loopback (127.0.0.1)
using the session CSRF token. No external credentials or .env files needed.
"""

import subprocess
import re
import urllib.request
import ssl
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple


def format_countdown(reset_time_str: str) -> str:
    """Calculates human-readable time remaining until reset time (ISO-8601)."""
    try:
        # e.g., '2026-09-30T06:23:07Z'
        clean_time = reset_time_str.replace("Z", "+00:00")
        target_dt = datetime.fromisoformat(clean_time)
        now_dt = datetime.now(timezone.utc)
        diff = target_dt - now_dt
        total_seconds = int(diff.total_seconds())

        if total_seconds <= 0:
            return "ready to refresh"

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except Exception:
        return "unknown"


class AntigravityProvider:
    def __init__(self):
        self._cached_pid: Optional[str] = None
        self._cached_csrf: Optional[str] = None
        self._cached_ports: List[int] = []
        self._last_snapshot: Optional[Dict[str, Any]] = None
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def discover(self) -> Tuple[Optional[str], Optional[str], List[int]]:
        """
        Discovers the running Antigravity language_server process, extracts
        the --csrf_token and finds its active listening loopback ports.
        """
        ps_cmd = (
            'Get-CimInstance Win32_Process -Filter "Name LIKE \'%language_server%\'" | '
            'ForEach-Object { "$($_.ProcessId)`t$($_.CommandLine)" }'
        )
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                startupinfo=startupinfo,
                timeout=5,
            )

            pid = None
            csrf_token = None

            for line in res.stdout.strip().splitlines():
                if not line.strip() or "\t" not in line:
                    continue
                pid_str, cmdline = line.split("\t", 1)
                token_match = re.search(r"--csrf_token\s+([^\s]+)", cmdline)
                if token_match:
                    pid = pid_str.strip()
                    csrf_token = token_match.group(1).strip("\"'")
                    break

            if not pid or not csrf_token:
                return None, None, []

            # Query netstat to find TCP listening ports bound to this PID
            ns_res = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                startupinfo=startupinfo,
                timeout=5,
            )

            ports = []
            for ns_line in ns_res.stdout.splitlines():
                if "LISTENING" in ns_line and pid in ns_line:
                    parts = ns_line.split()
                    if len(parts) >= 5 and parts[4] == pid:
                        ip_port = parts[1]
                        port = int(ip_port.rsplit(":", 1)[-1])
                        if port not in ports:
                            ports.append(port)

            self._cached_pid = pid
            self._cached_csrf = csrf_token
            self._cached_ports = ports
            return pid, csrf_token, ports
        except Exception as e:
            return None, None, []

    def fetch_quotas(self) -> Dict[str, Any]:
        """
        Queries the language server RPC for live quota summaries.
        Returns parsed model group dictionaries with remaining fractions and countdowns.
        """
        # Attempt using cached ports/token first, or rediscover
        pid, token, ports = self._cached_pid, self._cached_csrf, self._cached_ports
        if not token or not ports:
            pid, token, ports = self.discover()

        if not token or not ports:
            return {
                "status": "disconnected",
                "message": "Antigravity language server not running",
                "groups": self._last_snapshot.get("groups", []) if self._last_snapshot else [],
            }

        data = None
        for port in ports:
            url = f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary"
            req = urllib.request.Request(
                url,
                data=b'{"forceRefresh":true}',
                headers={
                    "Content-Type": "application/json",
                    "x-codeium-csrf-token": token,
                },
            )
            try:
                with urllib.request.urlopen(req, context=self._ssl_ctx, timeout=3) as resp:
                    raw = json.loads(resp.read().decode())
                    data = raw.get("response", {})
                    break
            except Exception:
                continue

        # If call failed with cached credentials, force rediscovery once
        if data is None:
            pid, token, ports = self.discover()
            if token and ports:
                for port in ports:
                    url = f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary"
                    req = urllib.request.Request(
                        url,
                        data=b'{"forceRefresh":true}',
                        headers={
                            "Content-Type": "application/json",
                            "x-codeium-csrf-token": token,
                        },
                    )
                    try:
                        with urllib.request.urlopen(req, context=self._ssl_ctx, timeout=3) as resp:
                            raw = json.loads(resp.read().decode())
                            data = raw.get("response", {})
                            break
                    except Exception:
                        continue

        if data is None:
            return {
                "status": "stale",
                "message": "Unable to connect to Antigravity RPC",
                "groups": self._last_snapshot.get("groups", []) if self._last_snapshot else [],
            }

        parsed_groups = []
        raw_groups = data.get("groups", [])
        for g in raw_groups:
            display_name = g.get("displayName", "AI Models")
            buckets = []
            for b in g.get("buckets", []):
                remaining_frac = float(b.get("remainingFraction", 1.0))
                remaining_pct = round(remaining_frac * 100, 1)
                used_pct = round((1.0 - remaining_frac) * 100, 1)
                reset_time = b.get("resetTime", "")
                countdown = format_countdown(reset_time)

                buckets.append({
                    "id": b.get("bucketId", ""),
                    "displayName": b.get("displayName", ""),
                    "window": b.get("window", ""),  # '5h' or 'weekly'
                    "remainingFraction": remaining_frac,
                    "remainingPct": remaining_pct,
                    "usedPct": used_pct,
                    "resetTime": reset_time,
                    "countdown": countdown,
                })

            parsed_groups.append({
                "displayName": display_name,
                "buckets": buckets,
            })

        snapshot = {
            "status": "connected",
            "message": "Active",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "groups": parsed_groups,
        }
        self._last_snapshot = snapshot
        return snapshot


if __name__ == "__main__":
    provider = AntigravityProvider()
    result = provider.fetch_quotas()
    print("Fetched Quotas Snapshot:")
    print(json.dumps(result, indent=2))
