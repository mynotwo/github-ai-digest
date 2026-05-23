"""Daily AI/LLM GitHub Trending digest — scrape, filter, email."""
from __future__ import annotations

import os
import re
import smtplib
import sys
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup


AI_KEYWORDS = {
    "llm", "agent", "mcp", "claude", "openai", "gpt", "copilot",
    "langchain", "rag", "embedding", "transformer", "diffusion", "ai", "model",
}


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
