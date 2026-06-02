# Implementation Notes — Gmail scan + confirm + delete

Replaces the old fully-automatic weekly trash (fixed 32-domain list) with a
scan → Lark confirm → on-demand delete loop. Built 2026-06-01.

## Flow
1. **Local Mac, weekly Mon 10:00** (`com.user.gmail-scan` launchd agent) runs
   `gmail_scan.py`.
2. Scan reads Gmail via the **local `gmail.readonly` OAuth token**
   (`~/.config/gmail_claude_token.json`), finds bulk mail, DMs the candidate
   list to Lark.
3. You reply to the **Rimemosa bridge**: `gmail-del 1 3 5` (or `all`).
4. `gmail_del.py` maps numbers → domains via `candidates.json`, dispatches the
   GitHub **`gmail-delete`** workflow.
5. GitHub runs `gmail_cleaner.py --senders ...` and trashes them over IMAP using
   the **app password already in GitHub secrets**.

Net: local side only ever READS; the write credential never leaves GitHub.
**No new secrets added anywhere.**

## Decisions (not in any spec — chosen here)
- **Detection = presence of `List-Unsubscribe` header** (not a domain list, not
  Gmail's promo category). Catches every new bulk sender automatically — the
  root cause of "没怎么删" was the old fixed list + exact-domain match missing
  subdomains.
- **Scan scope: `in:inbox newer_than:30d`.** Inbox = the clutter you actually
  see; 30d bounds the per-message metadata fetches (one GET per message).
- **Group by full From-domain.** `email.openai.com` and `openai.com` stay
  separate on purpose — you may want to drop marketing subdomains but keep the
  root. Deletion matches the exact domain you pick.
- **Deletion scope stays `[Gmail]/All Mail`** (unchanged from before) and trashes
  (recoverable, Gmail purges Trash after 30d).
- **Two bots, bridged by `candidates.json`.** Notifications go out via the
  lark-cli app (`cli_aa85cc4d8061dbcf`); your reply/command goes to the Rimemosa
  bridge (`cli_aa853ff652f8dccd`). They are different Lark apps; the shared local
  `~/.config/gmail-cleanup/candidates.json` is what links the pushed list to the
  delete command. open_id `ou_694f6600...` is Audrey in the lark-cli namespace.
- **`gmail_cleaner.py` keeps `DELETE_DOMAINS` as a fallback** when `--senders` is
  omitted (back-compat), but the workflow always passes `--senders`.

## Removed
- `.github/workflows/weekly-clean.yml` (the auto fixed-list trash). Its weekly
  job is replaced by the local scan; its delete capability is now
  `gmail-delete.yml` (manual / dispatched only).

## Tradeoffs / gotchas
- DM arrives from one bot, you reply to another (the bridge). Minor UX seam.
- `newer_than:30d` + inbox-only scan can miss older archived bulk; but once you
  confirm a domain, deletion sweeps **all** mail from it in All Mail.
- `gmail_del.py` needs `gh` authed locally (it is — account `mynotwo`).
- launchd agent runs in the Aqua (gui) domain so it can read `~/.config` and use
  the lark-cli token — same reason the other local claude agents were migrated
  off crontab. If you log out of the GUI session it won't fire.

## Files
- `gmail_scan.py` — read-only scan + Lark DM (new)
- `gmail_del.py` — map numbers → trigger GitHub delete (new); wrapper at
  `~/.local/bin/gmail-del`
- `gmail_cleaner.py` — now takes `--senders` (modified)
- `.github/workflows/gmail-delete.yml` — on-demand delete (new)
- `~/Library/LaunchAgents/com.user.gmail-scan.plist` — weekly timer (new, local)
