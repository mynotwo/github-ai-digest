"""Gmail cleanup — trash mail from given sender domains.

Domains come from --senders (comma-separated), as dispatched by the
gmail-delete GitHub workflow after you confirm a scan. Falls back to the
built-in DELETE_DOMAINS list when --senders is omitted.
"""
from __future__ import annotations

import argparse
import imaplib
import os
import sys

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# Sender domains confirmed as pure advertising (no transactional value)
DELETE_DOMAINS: set[str] = {
    "discover.pinterest.com",
    "explore.pinterest.com",
    "ideas.pinterest.com",
    "inspire.pinterest.com",
    "mail.artbasel.com",
    "spinneys.com",
    "choose.etihadguest.com",
    "email.etihadguest.com",
    "sayweee.com",
    "hello.scribd.com",
    "scholarshipdb.net",
    "glassdoor.com",
    "hey.simplify.jobs",
    "people.nokia.com",
    "e.saje.com",
    "dubaiculture.ae",
    "mp1.tripadvisor.com",
    "newsletter.trip.com",
    "vio.com",
    "squaremktg.com",
    "deepnote.com",
    "anytimemailbox.com",
    "mail.notion.so",
    "connect.readdle.com",
    "pagepeek.ai",
    "m.learn.coursera.org",
    "coursera.org",
    "mail.skinceuticals.com",
    "recreation.gov",
}


def _search_from_domain(mail: imaplib.IMAP4_SSL, domain: str) -> list[bytes]:
    _, data = mail.uid("SEARCH", None, f'FROM "@{domain}"')
    uids = data[0].split() if data and data[0] else []
    return uids


def trash_uid(mail: imaplib.IMAP4_SSL, uid: bytes) -> None:
    mail.uid("COPY", uid, "[Gmail]/Trash")
    mail.uid("STORE", uid, "+FLAGS", "\\Deleted")


def run_cleanup(gmail_user: str, gmail_app_password: str, domains: set[str]) -> int:
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(gmail_user, gmail_app_password)
    mail.select('"[Gmail]/All Mail"')

    total = 0
    for domain in domains:
        uids = _search_from_domain(mail, domain)
        for uid in uids:
            trash_uid(mail, uid)
            total += 1

    mail.expunge()
    mail.logout()
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Trash Gmail by sender domain.")
    parser.add_argument("--senders", default="",
                        help="comma-separated sender domains; defaults to DELETE_DOMAINS")
    args = parser.parse_args()

    if args.senders.strip():
        domains = {s.strip().lstrip("@").lower() for s in args.senders.split(",") if s.strip()}
    else:
        domains = DELETE_DOMAINS

    gmail_user = os.environ["GMAIL_USER"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    trashed = run_cleanup(gmail_user, gmail_app_password, domains)
    print(f"Trashed {trashed} emails from {len(domains)} sender domain(s).")


if __name__ == "__main__":
    main()
