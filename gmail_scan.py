"""Weekly Gmail scan — find bulk/promotional mail (List-Unsubscribe header),
group by sender domain, and DM the candidate list to Lark for confirmation.

Read-only: uses the local gmail.readonly OAuth token. Does NOT delete anything.
Deletion happens on demand via the GitHub `gmail-delete` workflow, triggered
after you reply with which senders to drop (see gmail_del.py).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import requests

TOKEN_FILE = Path.home() / ".config" / "gmail_claude_token.json"
STATE_DIR = Path.home() / ".config" / "gmail-cleanup"
CANDIDATES_FILE = STATE_DIR / "candidates.json"
ALL_SENDERS_FILE = STATE_DIR / "all_senders.json"

LARK_OPEN_ID = "ou_694f6600030c2fa33db21cf0ba87b7b1"  # Audrey, lark-cli app namespace
HERMES_URL = "http://127.0.0.1:8766/v1/messages"  # local Claude (subscription) proxy
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
# This account has no Gmail category labels, so category:promotions is empty.
# Fall back to List-Unsubscribe (= bulk/list mail, not personal); the DM shows
# a sample subject per sender so you can tell ads from receipts at a glance.
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


def classify_ads(senders: list[dict]) -> tuple[list[dict], bool]:
    """Ask local Claude (hermes proxy) which senders are pure advertising.
    Returns (ad_senders, classified_ok). On any failure, returns all senders so
    the feature degrades to a plain list rather than dropping silently."""
    listing = "\n".join(
        f"{i}. {s['domain']} | {s.get('sample_subject', '')}"
        for i, s in enumerate(senders, 1)
    )
    prompt = (
        "下面是邮件发件人和样本标题。判断每个是不是【纯广告/营销推广】"
        "（促销、打折、新品、newsletter、welcome 营销、购物推荐）。\n"
        "【不是广告】= 收据、账单、对账单、安全告警、账号验证、订单确认、银行/退休金通知。\n"
        "只输出一个 JSON 数组，列出是广告的编号，例如 [1,3,5]。不要解释。\n\n"
        + listing
    )
    try:
        r = requests.post(
            HERMES_URL,
            json={"model": "claude-haiku-4-5", "stream": False,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=180,
        )
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json().get("content", []))
        m = re.search(r"\[[\d,\s]*\]", text)
        if not m:
            return senders, False
        idx = {int(n) for n in re.findall(r"\d+", m.group(0))}
        ads = [s for i, s in enumerate(senders, 1) if i in idx]
        return ads, True
    except Exception:
        return senders, False


def build_dm(senders: list[dict], classified: bool, total_scanned: int) -> str:
    """Numbered sender list + reply instructions."""
    total = sum(s["count"] for s in senders)
    if classified:
        head = f"📬 本周扫了 {total_scanned} 个批量发件人，我判断这些是广告（{len(senders)} 个 / {total} 封）："
    else:
        head = f"📬 本周批量邮件（{len(senders)} 个发件人 / {total} 封，自动分类没成功，列全部）："
    lines = [head]
    for i, s in enumerate(senders[:MAX_SENDERS_IN_DM], 1):
        subj = s.get("sample_subject", "")
        tail = f"「{subj}」" if subj else ""
        lines.append(f"{i}. {s['domain']} — {s['count']} 封 {tail}")
    if len(senders) > MAX_SENDERS_IN_DM:
        lines.append(f"…还有 {len(senders) - MAX_SENDERS_IN_DM} 个（见 candidates.json）")
    lines.append("")
    lines.append("确认删：给 Rimemosa 发「gmail-del all」（全删）或「gmail-del 1 3 5」（只删这几个）")
    lines.append("（本号只推送、不收消息，命令请发 Rimemosa）")
    return "\n".join(lines)


def send_lark(text: str) -> None:
    subprocess.run(
        ["lark-cli", "im", "+messages-send", "--as", "bot",
         "--user-id", LARK_OPEN_ID, "--text", text],
        check=True, capture_output=True, text=True,
    )


def main() -> None:
    groups = scan(access_token())
    all_senders = sorted(
        ({"domain": d, **v} for d, v in groups.items()),
        key=lambda s: s["count"],
        reverse=True,
    )
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ALL_SENDERS_FILE.write_text(json.dumps(all_senders, ensure_ascii=False, indent=2))

    if not all_senders:
        CANDIDATES_FILE.write_text("[]")
        send_lark("📬 本周扫描：收件箱没有批量/广告邮件，干净。")
        print("0 candidates")
        return

    ads, classified = classify_ads(all_senders)
    # candidates.json = exactly the numbered list shown in the DM (gmail-del indexes it)
    CANDIDATES_FILE.write_text(json.dumps(ads, ensure_ascii=False, indent=2))

    if classified and not ads:
        send_lark(f"📬 本周扫了 {len(all_senders)} 个批量发件人，没有明显广告，都像交易邮件。")
        print("classified: 0 ads")
        return

    send_lark(build_dm(ads, classified, len(all_senders)))
    print(f"scanned={len(all_senders)} ads={len(ads)} classified={classified} → DM sent")


if __name__ == "__main__":
    main()
