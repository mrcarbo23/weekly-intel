# Weekly Intel

An AI-powered weekly intelligence digest generator. Ingests Substack RSS feeds, Gmail newsletters, and YouTube video transcripts, then uses Claude to synthesize a weekly digest with deduplication, semantic clustering, and HTML/Markdown output.

## Overview

The pipeline runs in three stages:

1. **Ingest** — Fetch content from configured sources (Substack RSS, Gmail, YouTube). Two-layer deduplication using SHA-256 exact hashing and MinHash near-duplicate detection prevents redundant content from entering the pipeline.
2. **Process** — Claude analyzes each article to extract key facts, themes, hot takes, and named entities. Semantic embeddings (OpenAI or local sentence-transformers) are computed for clustering.
3. **Digest** — Items are clustered by semantic similarity. Claude synthesizes a unified summary per cluster, generates an executive summary, and renders the digest as both HTML email and Markdown.

## Prerequisites

- Python 3.11+
- Node.js 18+
- An Anthropic API key (required)
- Optional: OpenAI API key for embeddings (falls back to local `sentence-transformers` if not set)
- Optional: Gmail OAuth credentials (for Gmail ingestion)
- Optional: Resend, SendGrid, or AWS SES credentials (for email delivery)

## Local Setup

### 1. Clone and configure environment

```bash
cp .env.example .env
# Edit .env and fill in your ANTHROPIC_API_KEY at minimum
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize the database

```bash
python scripts/setup_db.py
```

This creates a local SQLite database (`weekly_intel.db`) by default. Set `DATABASE_URL` in `.env` to use PostgreSQL instead.

### 4. Install Node.js dependencies

```bash
npm install
```

### 5. Add your first source

```bash
# Add a Substack RSS feed
python scripts/run_pipeline.py add-source \
  --name "Stratechery" \
  --type substack \
  --url "https://stratechery.com/feed"

# Add a YouTube channel
python scripts/run_pipeline.py add-source \
  --name "Lex Fridman" \
  --type youtube \
  --url "https://www.youtube.com/@lexfridman"

# Add a Gmail newsletter source (requires OAuth setup below)
python scripts/run_pipeline.py add-source \
  --name "Morning Brew" \
  --type gmail \
  --url ""
```

### 6. Run the full pipeline

```bash
# Run all steps: ingest → process → cluster → digest
python scripts/run_pipeline.py full
```

Or run individual steps:

```bash
python scripts/run_pipeline.py ingest
python scripts/run_pipeline.py process
python scripts/run_pipeline.py cluster --week-start 2024-01-01
python scripts/run_pipeline.py digest --week-start 2024-01-01
```

### 7. Send the digest

```bash
python scripts/send_digest.py --recipients you@example.com,colleague@example.com
```

### 8. Start the web dashboard

```bash
npm run dev
# Open http://localhost:3000
```

## Gmail Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2. Enable the Gmail API.
3. Create OAuth 2.0 credentials (Desktop app type).
4. Download the credentials JSON and save it as `gmail_credentials.json` in the project root.
5. Set `GMAIL_CREDENTIALS_PATH=gmail_credentials.json` in `.env`.
6. On first run, a browser window will open asking you to authorize access. The token is saved to `gmail_token.json`.

Gmail ingestion reads from the "Newsletters" label by default. You can configure a different label or filter by sender in the source config:

```python
# In scripts/run_pipeline.py, you can add a gmail source with custom config:
add_source(db, "My Newsletters", "gmail", "", config={
    "label": "Newsletters",          # Gmail label to read
    "senders": ["news@morning.brew"], # Optional: filter by sender
    "days_back": 7,                  # How many days to look back
})
```

## Vercel Deployment

1. Push your code to a GitHub repository.
2. Import the project in [Vercel](https://vercel.com).
3. Set the following environment variables in the Vercel dashboard:
   - `ANTHROPIC_API_KEY`
   - `DATABASE_URL` (use a Postgres URL from [Neon](https://neon.tech) or similar)
   - `OPENAI_API_KEY` (optional)
   - `RESEND_API_KEY` (or `SENDGRID_API_KEY`)
   - `FROM_EMAIL`
4. Deploy. The Next.js frontend and Python serverless functions deploy automatically.

Note: The Vercel Python functions in `api/` use the `python3.11` runtime with a 300-second timeout for long-running pipeline steps.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend                      │
│   app/page.tsx (landing)  app/dashboard/page.tsx (UI)   │
│   app/api/* (route handlers proxy to Python API)        │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────┐
│              Python Serverless Functions                 │
│   api/ingest.py  api/process.py  api/digest.py          │
│   api/sources.py                                        │
└──────────────────────────┬──────────────────────────────┘
                           │ imports
┌──────────────────────────▼──────────────────────────────┐
│                    src/ Python Library                   │
│                                                         │
│  ingestion/          processing/        digest/         │
│  ├── substack.py     ├── fingerprint.py ├── generator.py│
│  ├── gmail.py        ├── embeddings.py  ├── markdown_   │
│  └── youtube.py      ├── clustering.py  │   renderer.py │
│                      └── llm.py         └── html_       │
│  storage/                                   renderer.py │
│  ├── models.py       delivery/                          │
│  └── database.py     └── email.py                      │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│              Database (SQLite / PostgreSQL)              │
│   sources → content_items → content_summaries           │
│   story_clusters → cluster_memberships                  │
│   weekly_digests → delivery_logs                        │
└─────────────────────────────────────────────────────────┘
```

### Deduplication Strategy

- **Layer 1 (exact)**: SHA-256 hash of normalized content — prevents storing identical articles.
- **Layer 1 (fuzzy)**: MinHash with 128 permutations — catches near-duplicates (same story, minor edits) with Jaccard similarity threshold of 0.80.
- **Layer 2 (semantic)**: Cosine similarity on embeddings — clusters related but non-duplicate stories for unified synthesis.
- **Layer 3 (historical)**: Novelty scoring against 4 weeks of history — flags "ongoing" vs "new" stories.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for LLM processing |
| `DATABASE_URL` | No | Database connection URL (defaults to SQLite) |
| `OPENAI_API_KEY` | No | OpenAI key for embeddings (falls back to local model) |
| `GMAIL_CREDENTIALS_PATH` | Gmail only | Path to Gmail OAuth credentials JSON |
| `GMAIL_TOKEN_PATH` | Gmail only | Path to Gmail OAuth token JSON |
| `EMAIL_PROVIDER` | No | Email provider: `resend`, `sendgrid`, or `ses` (default: `resend`) |
| `FROM_EMAIL` | No | Sender email address |
| `FROM_NAME` | No | Sender display name |
| `RESEND_API_KEY` | If using Resend | Resend API key |
| `SENDGRID_API_KEY` | If using SendGrid | SendGrid API key |
| `AWS_ACCESS_KEY_ID` | If using SES | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | If using SES | AWS secret key |
| `AWS_REGION` | If using SES | AWS region (default: `us-east-1`) |
| `OUTPUT_DIR` | No | Directory for digest output files (default: `output/digests`) |
| `INTERNAL_API_URL` | No | Python API base URL for Next.js proxy (default: `http://localhost:8000`) |

## Running Tests

```bash
# Install test dependencies (included in requirements.txt)
pip install pytest

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_fingerprint.py -v
```
