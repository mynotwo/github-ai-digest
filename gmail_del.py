"""Trigger the GitHub gmail-delete workflow for chosen senders.

Usage:
    gmail-del 1 3 5      # delete senders #1 #3 #5 from the last scan
    gmail-del all        # delete every candidate

Maps the numbers against ~/.config/gmail-cleanup/candidates.json (written by
gmail_scan.py), then dispatches the GitHub workflow which does the actual IMAP
trashing with the credential that lives in GitHub secrets.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CANDIDATES_FILE = Path.home() / ".config" / "gmail-cleanup" / "candidates.json"
REPO_DIR = Path.home() / "Documents" / "projects" / "github-ai-digest"
WORKFLOW = "gmail-delete.yml"
LARK_OPEN_ID = "ou_694f6600030c2fa33db21cf0ba87b7b1"


def send_lark(text: str) -> None:
    subprocess.run(
        ["lark-cli", "im", "+messages-send", "--as", "bot",
         "--user-id", LARK_OPEN_ID, "--text", text],
        check=False, capture_output=True, text=True,
    )


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: gmail-del <numbers...|all>", file=sys.stderr)
        return 2
    senders = json.loads(CANDIDATES_FILE.read_text())
    if not senders:
        print("no candidates on file; run a scan first", file=sys.stderr)
        return 1

    if argv == ["all"]:
        chosen = senders
    else:
        try:
            idx = [int(a) for a in argv]
        except ValueError:
            print("args must be numbers or 'all'", file=sys.stderr)
            return 2
        bad = [n for n in idx if n < 1 or n > len(senders)]
        if bad:
            print(f"out of range: {bad} (have 1..{len(senders)})", file=sys.stderr)
            return 2
        chosen = [senders[n - 1] for n in idx]

    domains = [s["domain"] for s in chosen]
    csv = ",".join(domains)
    subprocess.run(
        ["gh", "workflow", "run", WORKFLOW, "-f", f"senders={csv}"],
        cwd=REPO_DIR, check=True, capture_output=True, text=True,
    )
    msg = f"🗑️ 已触发删除 {len(domains)} 个发件人：{', '.join(domains)}（GitHub 执行中，移到 Trash 可恢复）"
    print(msg)
    send_lark(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
