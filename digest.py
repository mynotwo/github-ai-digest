"""Daily AI/LLM GitHub Trending digest — scrape, filter, email."""
from __future__ import annotations

import os
import re
import smtplib
import sys
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

import requests
from bs4 import BeautifulSoup


AI_KEYWORDS = {
    "llm", "agent", "mcp", "claude", "openai", "gpt", "copilot",
    "langchain", "rag", "embedding", "transformer", "diffusion", "ai", "model",
}
_AI_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(kw) for kw in AI_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def parse_stars(text: str) -> int:
    """Extract integer star count from strings like '2,345 stars today'."""
    m = re.search(r"([\d,]+)", text)
    if not m:
        return 0
    return int(m.group(1).replace(",", ""))


def parse_trending(html: str) -> list[dict]:
    """Parse GitHub Trending page HTML into a list of repo dicts."""
    soup = BeautifulSoup(html, "html.parser")
    repos: list[dict] = []
    for article in soup.select("article.Box-row"):
        link = article.select_one("h2 a")
        if not link:
            continue
        full_name = link.get("href", "").lstrip("/")
        desc_el = article.select_one("p")
        description = desc_el.get_text(strip=True) if desc_el else ""
        star_el = article.select_one("span.d-inline-block.float-sm-right")
        stars_today = parse_stars(star_el.get_text(strip=True) if star_el else "")
        repos.append({
            "name": full_name,
            "description": description,
            "stars_today": stars_today,
            "url": f"https://github.com/{full_name}",
        })
    return repos


def is_ai_repo(repo: dict) -> bool:
    """Return True if repo name or description contains any AI keyword (whole word)."""
    text = repo["name"] + " " + (repo.get("description") or "")
    return bool(_AI_PATTERN.search(text))


def filter_ai_repos(repos: list[dict]) -> list[dict]:
    """Keep only repos that match AI_KEYWORDS."""
    return [r for r in repos if is_ai_repo(r)]


def build_subject(today: date) -> str:
    return f"🤖 AI/LLM GitHub Top 5 · {today.isoformat()}"


def build_html(repos: list[dict]) -> str:
    """Build HTML email body for the given repo list (≤5 expected)."""
    today = date.today().isoformat()
    if not repos:
        body = "<p>No AI/LLM repos in today's GitHub Trending.</p>"
    else:
        rows = ""
        for i, r in enumerate(repos, 1):
            desc = r["description"]
            if len(desc) > 120:
                desc = desc[:120] + "…"
            rows += (
                f'<tr><td style="padding:12px 0;border-bottom:1px solid #eee;">'
                f'<strong>{i}. <a href="{escape(r["url"])}">{escape(r["name"])}</a></strong><br>'
                f'<span style="color:#888;">+{r["stars_today"]:,} ⭐ today</span><br>'
                f'<span style="color:#444;">{escape(desc)}</span>'
                f"</td></tr>"
            )
        body = f'<table style="width:100%;border-collapse:collapse;">{rows}</table>'

    return (
        "<!DOCTYPE html><html>"
        '<body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;">'
        f"<h2>🤖 AI/LLM GitHub Top 5 · {today}</h2>"
        f"{body}"
        '<p style="color:#999;font-size:12px;">Source: github.com/trending?since=daily</p>'
        "</body></html>"
    )


def send_email(
    html: str,
    subject: str,
    gmail_user: str,
    gmail_app_password: str,
    notify_email: str,
) -> None:
    """Send HTML email via Gmail SMTP SSL."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = notify_email
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_user, gmail_app_password)
        smtp.sendmail(gmail_user, notify_email, msg.as_string())


def fetch_trending(since: str = "daily") -> list[dict]:
    """Fetch and parse GitHub Trending. Raises on HTTP error."""
    url = f"https://github.com/trending?since={since}"
    r = requests.get(url, headers={"User-Agent": "github-ai-digest/1.0"}, timeout=15)
    r.raise_for_status()
    return parse_trending(r.text)


def main() -> None:
    gmail_user = os.environ["GMAIL_USER"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    notify_email = os.environ["NOTIFY_EMAIL"]

    try:
        all_repos = fetch_trending()
    except Exception as exc:
        send_email(
            f"<p>Scrape failed: {exc}</p>",
            "⚠️ github-ai-digest scrape error",
            gmail_user,
            gmail_app_password,
            notify_email,
        )
        sys.exit(1)

    ai_repos = filter_ai_repos(all_repos)
    top5 = sorted(ai_repos, key=lambda r: r["stars_today"], reverse=True)[:5]
    today = date.today()
    html = build_html(top5)
    subject = build_subject(today)
    send_email(html, subject, gmail_user, gmail_app_password, notify_email)
    print(f"Sent: {len(top5)} repos · {subject}")


if __name__ == "__main__":
    main()
