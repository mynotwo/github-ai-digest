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
