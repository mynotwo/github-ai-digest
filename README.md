# github-ai-digest

Daily email: top 5 AI/LLM GitHub repos by stars gained today.

Runs via GitHub Actions at 09:00 CST. Zero infrastructure.

## Setup

1. Fork or create this repo on GitHub.

2. Add three repository secrets (**Settings → Secrets → Actions**):

   | Secret | Value |
   |---|---|
   | `GMAIL_USER` | Your Gmail address (sender) |
   | `GMAIL_APP_PASSWORD` | Gmail App Password (not your login password) |
   | `NOTIFY_EMAIL` | Recipient email |

   Get a Gmail App Password: Google Account → Security → 2-Step Verification → App passwords.

3. Push — first email arrives at the next 09:00 CST, or trigger manually via **Actions → Daily AI Digest → Run workflow**.

## Local test

```bash
pip install -r requirements.txt
GMAIL_USER=you@gmail.com GMAIL_APP_PASSWORD=xxxx NOTIFY_EMAIL=you@gmail.com python digest.py
```

## What counts as "AI/LLM"

Repos whose name or description contains any of (whole-word match):
`llm`, `agent`, `mcp`, `claude`, `openai`, `gpt`, `copilot`, `langchain`, `rag`, `embedding`, `transformer`, `diffusion`, `ai`, `model`
