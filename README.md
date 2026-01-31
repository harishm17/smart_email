# Smart Email Assistant — Privacy-First Email Drafting

> Multi-agent system for drafting emails and scheduling actions with PII-aware guardrails

[Overview](#-overview) • [Privacy Model](#-privacy-model) • [Architecture](#-architecture) • [Evaluation](#-evaluation--tests) • [Setup](#-quick-start)

---

## 🎯 Overview

Smart Email Assistant orchestrates **three specialized AI agents** to handle email communication and calendar tasks:
- **Planner Agent:** Analyzes incoming requests and determines required actions
- **Retriever Agent:** Searches email history and contacts for context
- **Drafting Agent:** Generates context-aware responses with appropriate tone

**Safety Layer:** PII detection + redaction runs before drafts are sent, with a final validation gate.

### The Problem
- 📧 Email management is time-consuming (5-10 minutes per response)
- 📅 Calendar scheduling requires multiple back-and-forth exchanges
- 🔒 Risk of accidentally leaking sensitive information (SSNs, API keys, credentials)
- 🤝 Need to search through past conversations for context

### The Solution
An intelligent multi-agent system that:
- Automatically drafts context-aware email responses
- Manages calendar events through natural language
- Validates outputs and redacts detected PII
- Integrates seamlessly with Google Workspace

---

## ✅ Proof

- OAuth 2.0 Gmail/Calendar integration with token refresh
- PII validator + redaction pipeline (`validators/pii_validator.py`)
- Structured outputs with Pydantic to reduce malformed actions

## ✨ Features

- 🤖 **Multi-Agent Orchestration:** LangChain-powered agent collaboration with ReAct pattern
- 🔒 **PII Protection:** Automated redaction of SSNs, credit cards, API keys, phone numbers
- 📧 **Smart Email Drafting:** Context-aware response generation from email threads
- 📅 **Calendar Integration:** Google Calendar event creation and updates
- 👥 **Contact Management:** Workspace directory search and retrieval
- ✅ **Structured Outputs:** Validated JSON responses via Pydantic models
- 🔗 **OAuth 2.0 Authentication:** Secure token management for Google Workspace

---

## 🔐 Privacy Model

- **Pre-LLM scrub:** Inputs are sanitized before they reach the model (configurable).
- **Post-LLM guard:** Drafts are validated; detected PII is redacted and flagged.
- **Data boundaries:** OAuth tokens stay local; only the minimum context needed is sent to the model.

## 🏗️ Architecture

```
┌─────────────┐
│    User     │
│   Request   │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  PII Scrub (pre-LLM)│
└──────┬──────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│           Planner Agent (LangChain)             │
│  "What actions needed? Search, draft, schedule?" │
└──────┬──────────────────────────────────────────┘
       │
   ┌───┴────┬──────────┬────────────┐
   │        │          │            │
   ▼        ▼          ▼            ▼
┌──────┐ ┌──────┐ ┌────────┐ ┌──────────┐
│Gmail │ │Calendar│ │Contacts│ │Retriever │
│ API  │ │  API   │ │  API   │ │  Agent   │
└──┬───┘ └───┬────┘ └───┬────┘ └────┬─────┘
   │         │          │          │
   └─────────┴──────────┴──────────┘
              │
              ▼
    ┌──────────────────┐
    │  Drafting Agent  │
    │   (Gemini 1.5)   │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  PII Validator   │
    │ (redaction gate) │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   Send Email     │
    │  (Gmail API)     │
    └──────────────────┘
```

**Tech Stack:**
- **AI Framework:** LangChain 0.1.x for agent orchestration
- **LLM:** Google Gemini 1.5 Pro for reasoning and generation
- **Safety Layer:** PII detection + redaction with a send/no‑send gate
- **APIs:** Google Workspace (Gmail, Calendar, Contacts via REST)
- **Authentication:** OAuth 2.0 with refresh token flow

**Data Flow:**
1. User inputs natural language request (e.g., "Schedule meeting with John Tuesday 2pm")
2. Planner Agent determines actions needed (search contact, create calendar event, draft email)
3. Retriever Agent fetches relevant context (John's email from contacts)
4. Calendar Agent creates event via Google Calendar API
5. Drafting Agent generates invitation email
6. PII validator checks drafts before sending
7. Email sent via Gmail API

---

## 🚧 Technical Challenges & Solutions

### Challenge 1: Context Window Management
**Problem:** Email threads can exceed LLM context limits (200K+ tokens for long conversations).

**Solution:**
- Implemented semantic chunking of email history with relevance scoring
- Only top-5 most relevant messages sent to drafting agent based on cosine similarity
- Reduced context usage while maintaining drafting accuracy

**Technical Details:**
```python
# Semantic search for relevant emails
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(email_history, embeddings)
relevant_emails = vectorstore.similarity_search(query, k=5)
```

---

### Challenge 2: PII Protection at Scale
**Problem:** LLMs can inadvertently leak sensitive information or hallucinate contact details.

**Solution:**
- Pre-LLM scrubbing of user input and context to limit exposure
- Guardrails-based validation of drafts for PII patterns (SSN, credit card, API keys)
- Detected PII is redacted before sending

**Technical Details:**
```python
from validators.pii_validator import get_pii_validator

validator = get_pii_validator()
safe_request = validator.sanitize(user_request)

draft = drafter.draft(safe_request, plan, context)
pii_check = validator.validate(draft.body)
```

---

### Challenge 3: Multi-Step Orchestration Reliability
**Problem:** Complex tasks require sequential API calls (search → create → draft). Failure at any step breaks workflow.

**Solution:**
- LangChain's ReAct agent pattern allows "thinking" and retry logic
- State management via LangGraph ensures proper execution order
- Exponential backoff for API rate limits

**Technical Details:**
```python
from langchain.agents import create_react_agent
from langchain.tools import Tool

tools = [
    Tool(name="search_contacts", func=search_contacts_func),
    Tool(name="create_calendar_event", func=create_event_func),
    Tool(name="draft_email", func=draft_email_func)
]

agent = create_react_agent(llm=gemini_llm, tools=tools)
result = agent.invoke({"input": user_request})
```

---

### Challenge 4: Natural Language to API Parameter Mapping
**Problem:** User says "next Tuesday at 3pm" but API needs ISO 8601 datetime.

**Solution:**
- Built structured output extraction using Pydantic models
- Gemini 1.5 Pro with function calling to parse dates/times
- Timezone handling with pytz library

**Example:**
```python
from pydantic import BaseModel
from datetime import datetime

class CalendarEvent(BaseModel):
    summary: str
    start_datetime: datetime
    end_datetime: datetime
    attendees: list[str]

# LLM extracts structured data
event = gemini_llm.with_structured_output(CalendarEvent).invoke(user_request)
```

---

## 🎬 Demo

### 📹 Video Walkthrough

> **Coming Soon**: 60-second demo showing email drafting, PII redaction, and calendar scheduling

### 📸 Screenshots

**Email Drafting with Context**
![Email Draft](./docs/screenshots/email-draft.png)
*AI-generated email draft with context from previous conversations*

**PII Detection & Redaction**
![PII Redaction](./docs/screenshots/pii-redaction.png)
*Automatic detection and redaction of sensitive information*

**Calendar Event Creation**
![Calendar](./docs/screenshots/calendar-event.png)
*Natural language calendar scheduling*

### 🚀 Try It Locally

Follow the [Quick Start](#-quick-start) guide to run locally with your own Google Workspace account.

---

## ✅ Evaluation & Tests

**Automated checks**
- `tests/test_pii_validator.py` validates detection + redaction behavior

**Manual eval checklist**
- Draft quality (tone, clarity, task completion)
- PII safety (no leakage in output)
- Calendar accuracy (timezones, intent handling)

> Keep a small fixed set of test emails to compare outputs across model/prompt changes.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Google Cloud Project with Gmail + Calendar + Contacts APIs enabled
- Gemini API key

### Installation

```bash
git clone https://github.com/harishm17/smart_email.git
cd smart_email
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
GOOGLE_OAUTH_CLIENT_ID=your_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
GEMINI_API_KEY=your_gemini_key
GUARDRAILS_API_KEY=your_guardrails_key
```

### Google Cloud Setup

1. Enable APIs in Google Cloud Console:
   - Gmail API
   - Google Calendar API
   - People API (Contacts)

2. Create OAuth 2.0 credentials:
   - Application type: Desktop app
   - Download `credentials.json`
   - Place in `credentials/` directory

3. First run will open browser for OAuth consent

### Run

**Interactive Mode:**
```bash
python main.py --interactive
```

**Single Request:**
```bash
python main.py --request "Reply to John's email about the project deadline"
```

**Auto-send (use with caution):**
```bash
python main.py --request "Schedule a meeting with team" --auto-send
```

### Example Usage

```python
from main import SmartEmailAssistant

assistant = SmartEmailAssistant()

# Example 1: Draft an email
result = assistant.process_request("Reply to John about the project meeting")
# Output: Displays draft email with subject and body

# Example 2: Search emails
context = assistant.retriever.retrieve_context("from:john@example.com subject:project")
# Output: Returns relevant email context

# Example 2: Draft reply
result = assistant.process("Reply to John's email about project deadline")
# Output: Context-aware email draft based on previous conversation

# Example 3: Search and respond
result = assistant.process("Send a follow-up to Sarah about the proposal")
# Output: Searches email history, drafts appropriate follow-up
```

---

## 🔮 Future Enhancements

- [ ] Microsoft Outlook support via Graph API
- [ ] Sentiment analysis for tone matching
- [ ] Multi-language support (Spanish, French, German)
- [ ] Slack integration for notifications
- [ ] Email template library
- [ ] Meeting notes summarization
- [ ] Automated follow-up reminders
- [ ] Email classification and prioritization

---

## 📂 Project Structure

```
smart_email/
├── main.py                    # Application entry point
├── agents/
│   ├── planner.py            # Planner agent (action determination)
│   ├── retriever.py          # Retriever agent (context search)
│   └── drafter.py            # Drafting agent (email generation)
├── tools/
│   ├── gmail_tools.py        # Gmail API wrapper
│   ├── calendar_tools.py     # Calendar API wrapper
│   └── contacts_tools.py     # Contacts API wrapper
├── validators/
│   └── pii_validator.py      # PII detection + redaction
├── tests/
│   └── test_pii_validator.py # Unit tests for PII guard
├── utils/
│   ├── auth.py               # OAuth 2.0 management
│   └── datetime_parser.py    # Natural language date parsing
├── requirements.txt
└── README.md
```

---

## 🧪 Testing

```bash
# Run unit tests
pytest tests/ -v
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Harish Manoharan**
MS Computer Science @ UT Dallas | Software Engineer @ Purgo AI

- Portfolio: [harishm17.github.io](https://harishm17.github.io)
- LinkedIn: [linkedin.com/in/harishm17](https://linkedin.com/in/harishm17)
- Email: harish.manoharan@utdallas.edu

---

## 🙏 Acknowledgments

Built with:
- [LangChain](https://langchain.com) - Agent orchestration framework
- PII validator - regex-based detection + redaction
- [Google Gemini](https://ai.google.dev/) - Large language model
- [Google Workspace APIs](https://developers.google.com/workspace) - Email and calendar integration

---

*Building intelligent systems that respect privacy while enhancing productivity*
