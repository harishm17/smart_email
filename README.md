# Smart Email Assistant

A command-line tool that drafts emails from a natural-language request, using Gmail history for context and a regex-based PII scrub around the LLM calls. It is draft-only by default.

## How it works

The code is a sequential pipeline in `main.py` (`SmartEmailAssistant.process_request`), not a multi-agent system:

```
user request
    |
    v
Planner      one Gemini call (LangChain) -> EmailPlan (Pydantic)
    |
    v
Retriever    Gmail search using plan.context_query (no LLM call), only if the plan asks for context
    |
    v
Drafter      one Gemini call (LangChain) -> EmailDraft (Pydantic), then a PII check on the draft body
    |
    v
Display the draft; send via Gmail only if --auto-send is passed and the draft passed the PII check
```

- **Planner** (`agents/planner.py`): `prompt | ChatGoogleGenerativeAI | PydanticOutputParser` produces an `EmailPlan` (intent, tone, recipients, key points, optional context query). If the call fails, it falls back to a basic "compose" plan.
- **Retriever** (`agents/retriever.py`): runs a Gmail search through `tools/gmail_tools.py` and builds a short text summary (sender, subject, snippet) of the top results. It uses Gmail's own search syntax; there is no embedding or vector search.
- **Drafter** (`agents/drafter.py`): same chain pattern, producing an `EmailDraft` with subject, body, and tone. The PII validator is run on the draft body; if it finds PII, the body is redacted and the draft is marked not safe to send.
- **Sending**: `tools/gmail_tools.py` calls the Gmail API. `--auto-send` sends to the first recipient in the plan, without a confirmation prompt, and only when the draft is marked safe.
- **Model**: Gemini through `langchain-google-genai`. The model name comes from `LLM_MODEL` (default `gemini-1.5-pro` in `config.py`) and temperature from `LLM_TEMPERATURE` (default 0.7).

## Privacy model

- **Pre-LLM scrub**: the planner and drafter run regex redaction over the request, key points, and retrieved email context before building the prompt. This can be turned off with `ENABLE_PII_VALIDATION=false`.
- **Post-LLM check**: the draft body is checked with the same patterns. A draft with matches is redacted, flagged, and blocked from auto-send.
- **Patterns** (`validators/pii_validator.py`): email addresses, phone numbers, US SSNs, 16-digit card numbers, IPv4 addresses, and simple street addresses. This is pattern matching only; it does not detect API keys or other secrets.
- **Local state**: OAuth tokens are stored in `credentials/token.json` on your machine. Request text and retrieved email content (after the scrub) are sent to the Gemini API.
- **Draft-only by default**: without `--auto-send`, the draft is only printed to the terminal.

## Setup

Requirements: Python 3.11+, a Google Cloud project with the Gmail API enabled, and a Gemini API key.

```bash
git clone https://github.com/harishm17/smart_email.git
cd smart_email
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # see the note on pins below
cp .env.example .env
```

Fill in `.env` (variable names as in `.env.example`):

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GEMINI_API_KEY=...
```

Create an OAuth client (application type: Desktop app), download it as `credentials.json`, and place it in `credentials/`. The first run opens a browser for consent.

**Dependency pins**: the pins in `requirements.txt` do not currently resolve together. `langchain-openai==0.1.7` needs `openai>=1.24`, but `openai==1.12.0` is pinned, and `pytest==8.0.0` conflicts with `pytest-asyncio==0.23.4`. Several listed packages (`openai`, `langchain-openai`, `chromadb`, `tenacity`) are not imported by the code. To install, relax or drop those pins.

## Usage

```bash
# Interactive mode: type requests, or 'search <query>', 'recent', 'quit'
python main.py --interactive

# Single request, draft only
python main.py --request "Reply to John's email about the project deadline"

# Send the draft if it passes the PII check (no confirmation prompt)
python main.py --request "Send a follow-up to sarah@example.com about the proposal" --auto-send
```

## Tests

```bash
pytest tests/ -v
```

There are 60 tests in three files:
- `tests/test_pii_validator.py`: 3 tests for PII detection and redaction
- `tests/test_planner_agent.py`: 22 tests for the planner, with the LLM mocked
- `tests/test_datetime_parser.py`: 35 tests for `utils/datetime_parser.py`, a helper the application does not currently import

With the pins relaxed so the dependencies install (Python 3.11), a recent run gave 56 passed and 4 failed (phone sanitization, one planner fallback test with an incorrect mock, and two datetime parser tests). There are no tests for the drafter, retriever, Gmail tools, or `main.py`, and no evaluation of draft quality. CI (`.github/workflows/ci.yml`) installs from `requirements.txt`, so it cannot install until the pins are fixed.

## Status and known gaps

- **Calendar and contacts scopes are requested but unused.** `config.py` asks for the full Calendar and Contacts (read-only) scopes, and `utils/auth.py` can build those service objects, but no code calls them. Only Gmail is used. The scopes should be reduced to what is needed.
- **Redaction strips recipient emails before planning.** The scrub replaces addresses with `[EMAIL_REDACTED]@domain` before the planner sees the request, so `plan.recipients` can come back redacted or empty, which breaks `--auto-send`.
- **The phone regex misses some formats.** For example `(415) 555-1212` and international numbers are not matched, and the `phone` pattern can match digit groups like `123.456.7890`.
- **Errors fall back silently.** If an LLM call fails, the planner and drafter return a basic fallback and print the error. The drafter fallback is marked safe, and a Gmail API error in search returns no results.
- **Email content is untrusted input.** Retrieved snippets go into the prompt unfiltered, and there is no prompt-injection defense or recipient allow-list for `--auto-send`.

## Project structure

```
smart_email/
├── main.py                    # CLI entry point and pipeline
├── config.py                  # Environment settings
├── agents/
│   ├── planner.py             # Request -> EmailPlan (one LLM call)
│   ├── retriever.py           # Gmail search for context (no LLM call)
│   └── drafter.py             # Plan + context -> EmailDraft (one LLM call)
├── tools/
│   └── gmail_tools.py         # Gmail API wrapper
├── validators/
│   └── pii_validator.py       # Regex PII detection and redaction
├── utils/
│   ├── auth.py                # OAuth 2.0 flow and token refresh
│   └── datetime_parser.py     # Date parsing helper (not used by the app)
├── tests/
└── requirements.txt
```

## License

MIT License. See [LICENSE](LICENSE).

## Author

**Harish Manoharan**
MS Computer Science @ UT Dallas | Software Engineer @ Purgo AI

- Portfolio: [harishm17.github.io](https://harishm17.github.io)
- LinkedIn: [linkedin.com/in/harishm17](https://linkedin.com/in/harishm17)
- Email: harish_manoharan@outlook.com
