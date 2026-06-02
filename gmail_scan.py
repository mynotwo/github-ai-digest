"""Weekly Gmail scan — find bulk/promotional mail (List-Unsubscribe header),
group by sender domain, and DM the candidate list to Lark for confirmation.

Read-only: uses the local gmail.readonly OAuth token. Does NOT delete anything.
Deletion happens on demand via the GitHub `gmail-delete` workflow, triggered
after you reply with which senders to drop (see gmail_del.py).
"""
from __future__ import annotations

import json
import os
import subprocess
from collections import defaultdict
from pathlib import Path

import requests

TOKEN_FILE = Path.home() / ".config" / "gmail_claude_token.json"
STATE_DIR = Path.home() / ".config" / "gmail-cleanup"
CANDIDATES_FILE = STATE_DIR / "candidates.json"

LARK_OPEN_ID = "ou_694f6600030c2fa33db21cf0ba87b7b1"  # Audrey, lark-cli app namespace
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
SCAN_QUERY = "in:inbox newer_than:30d"
MAX_SENDERS_IN_DM = 25


def access_token() -> str:
    """Refresh and return a Gmail access token from the stored refresh token."""
    tok = json.loads(TOKEN_FILE.read_text())
    resp = requests.post(
        tok["token_uri"],
        data={
            "grant_type": "refresh_token",
            "refresh_token": tok["refresh_token"],
            "client_id": tok["client_id"],
            "client_secret": tok["client_secret"],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _headers_map(payload_headers: list[dict]) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in payload_headers}


def scan(token: str) -> dict[str, dict]:
    """Return {domain: {count, sample_subject}} for inbox mail that carries a
    List-Unsubscribe header (i.e. bulk/promotional)."""
    auth = {"Authorization": f"Bearer {token}"}
    ids: list[str] = []
    page_token = None
    while True:
        params = {"q": SCAN_QUERY, "maxResults": 500}
        if page_token:
            params["pageToken"] = page_token
        r = requests.get(f"{GMAIL_API}/messages", headers=auth, params=params, timeout=30)
        r.raise_for_status()
        body = r.json()
        ids.extend(m["id"] for m in body.get("messages", []))
        page_token = body.get("nextPageToken")
        if not page_token:
            break

    groups: dict[str, dict] = defaultdict(lambda: {"count": 0, "sample_subject": ""})
    for mid in ids:
        r = requests.get(
            f"{GMAIL_API}/messages/{mid}",
            headers=auth,
            params={
                "format": "metadata",
                "metadataHeaders": ["From", "List-Unsubscribe", "Subject"],
            },
            timeout=30,
        )
        r.raise_for_status()
        hdrs = _headers_map(r.json().get("payload", {}).get("headers", []))
        if "list-unsubscribe" not in hdrs:
            continue
        sender = hdrs.get("from", "")
        if "@" not in sender:
            continue
        domain = sender.split("@")[-1].strip().strip(">").lower()
        g = groups[domain]
        g["count"] += 1
        if not g["sample_subject"]:
            g["sample_subject"] = hdrs.get("subject", "")[:60]
    return groups


def build_dm(senders: list[dict]) -> str:
    """Numbered sender list + reply instructions."""
    total = sum(s["count"] for s in senders)
    lines = [f"📬 本周批量邮件候选（{total} 封，{len(senders)} 个发件人）："]
    for i, s in enumerate(senders[:MAX_SENDERS_IN_DM], 1):
        lines.append(f"{i}. {s['domain']} — {s['count']} 封")
    if len(senders) > MAX_SENDERS_IN_DM:
        lines.append(f"…还有 {len(senders) - MAX_SENDERS_IN_DM} 个（见 candidates.json）")
    lines.append("")
    lines.append("要删的回复我：gmail-del 1 3 5（编号），或 gmail-del all 全删")
    return "\n".join(lines)


def send_lark(text: str) -> None:
    subprocess.run(
        ["lark-cli", "im", "+messages-send", "--as", "bot",
         "--user-id", LARK_OPEN_ID, "--text", text],
        check=True, capture_output=True, text=True,
    )


def main() -> None:
    groups = scan(access_token())
    senders = sorted(
        ({"domain": d, **v} for d, v in groups.items()),
        key=lambda s: s["count"],
        reverse=True,
    )
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATES_FILE.write_text(json.dumps(senders, ensure_ascii=False, indent=2))

    if not senders:
        send_lark("📬 本周扫描：收件箱没有批量/广告邮件，干净。")
        print("0 candidates")
        return

    send_lark(build_dm(senders))
    print(f"{len(senders)} senders, {sum(s['count'] for s in senders)} emails → DM sent")


if __name__ == "__main__":
    main()
