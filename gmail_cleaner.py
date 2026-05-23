"""Weekly Gmail cleanup — trash promotional emails matching known ad sender domains."""
from __future__ import annotations

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


def run_cleanup(gmail_user: str, gmail_app_password: str) -> int:
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(gmail_user, gmail_app_password)
    mail.select('"[Gmail]/All Mail"')

    total = 0
    for domain in DELETE_DOMAINS:
        uids = _search_from_domain(mail, domain)
        for uid in uids:
            trash_uid(mail, uid)
            total += 1

    mail.expunge()
    mail.logout()
    return total


def main() -> None:
    gmail_user = os.environ["GMAIL_USER"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    trashed = run_cleanup(gmail_user, gmail_app_password)
    print(f"Trashed {trashed} promotional emails.")


if __name__ == "__main__":
    main()
