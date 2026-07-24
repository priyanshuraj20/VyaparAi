# VyaparAI
### AI Business Manager for Kirana Stores — Complete Product Design Suite

**Vision:** Build an AI-powered Business Manager for small kirana stores that runs entirely through WhatsApp. It should feel like hiring a digital employee — not installing another software. The shopkeeper should never need to learn dashboards, ERP systems, or complicated interfaces. They chat in natural language; the AI understands requests, performs business operations, maintains records, and assists with day-to-day store management.

**Guiding rules for every decision in this document:**
- ✅ Real-world first — if papa won't actually use a feature, it's rejected
- ✅ No feature for resume only
- ✅ AI only where needed — regex/SQL where deterministic logic works, LLM only for reasoning
- ✅ Production quality — logging, error handling, validation, retries, config, testing
- ✅ Human approval — AI never silently takes a business action (ledger write, reminder send, bill save)

---

# Document 1 — Product Requirements Document (PRD)

## 1.1 Problem Statement
Small kirana stores in India run entirely on manual, memory-based credit (udhaar) tracking. This causes forgotten entries, disputes over balances, delayed payment recovery, and hours lost on manual reporting. Store owners are unwilling to adopt POS/ERP software because of learning curve and workflow disruption — but they already use WhatsApp daily.

## 1.2 Target Users
- **Primary:** Kirana store owner (papa) — non-technical, WhatsApp-comfortable, time-constrained during business hours
- **Secondary:** Regular customers (25-40) — passive recipients of reminders, only if opted in

## 1.3 Why WhatsApp?
- Already installed, already used daily by the target user
- Zero onboarding — no app to download, no account to create
- Voice notes and photos are native, low-friction input methods
- Meta Cloud API makes it programmatically accessible

## 1.4 Goals
- Replace the physical khata with an AI-managed digital ledger, without changing how papa naturally communicates
- Provide instant visibility into outstanding balances and daily/monthly business performance
- Automate the mechanical parts (transcription, extraction, calculation) while keeping papa in control of every financial decision

## 1.5 Non-Goals (Explicitly Out of Scope for MVP)
- Inventory prediction or tracking
- Product recommendations
- Shelf photo–based stock counting
- Demand forecasting
- Automatic reordering
- Full POS replacement (billing/checkout hardware)
- Multi-store / multi-tenant support (deferred to post-MVP)

## 1.6 MVP Features
1. Smart Ledger (credit entry via text/voice)
2. Payment Update
3. OCR Bill/List Extraction
4. Customer History Query
5. Outstanding Report
6. Reminder Workflow (owner-approved, channel-aware)
7. Business Reports (daily/monthly)

## 1.7 User Stories
- *As papa, I want to say "Ram ko 650 udhaar diya" and have it recorded correctly, so I don't have to write it down manually.*
- *As papa, I want to send a photo of a customer's handwritten list and have the AI create the bill, so I don't have to type it out.*
- *As papa, I want to ask "kis kis ka paisa baaki hai" and get an instant answer, so I don't have to flip through a notebook.*
- *As papa, I want to approve every reminder before it's sent to a customer, so I stay in control of customer relationships.*
- *As a customer, I want to receive respectful, infrequent reminders only if I've agreed to it, so I'm not spammed.*

## 1.8 Success Metrics
- Papa uses VyaparAI daily for 4+ consecutive weeks without reverting to the physical khata
- <5% of transactions require manual correction
- At least one reminder successfully completes the full approve → send → payment loop during pilot

## 1.9 Constraints
- WhatsApp Business Cloud API's 24-hour customer service window — outbound messages outside this window require Meta-approved templates
- Customers must explicitly opt in before receiving any WhatsApp message from the store number
- Financial actions carry a high error cost — every low-confidence extraction must be confirmed by papa before saving
- Small scale (25-40 customers) — system should not be prematurely over-engineered for scale it doesn't need yet

## 1.10 Future Roadmap (Post-MVP)
- Multi-store SaaS version for other kirana stores
- Optional web dashboard for owners who want one
- Inventory and reorder features
- Analytics: customer purchase patterns, seasonal trends

---

# Document 2 — User Journeys

## 2.1 Journey: Voice Ledger Entry
```
Customer buys goods on credit
      ↓
Papa sends voice note: "Ram ko 650 ka udhaar diya"
      ↓
Whisper transcribes audio to text
      ↓
Planner Agent interprets: transaction intent detected
      ↓
resolve_customer("Ram") → match found (or clarification asked)
      ↓
extract_amount() → ₹650, high confidence
      ↓
add_transaction() → saved as 'confirmed' with undo window
      ↓
Reply: "Ram ka udhaar ab ₹1150. Galat ho to 'undo' bolo."
```

## 2.2 Journey: OCR Bill from Handwritten List
```
Customer enters shop, hands over shopping list
      ↓
Papa photographs the list, sends via WhatsApp
      ↓
Vision-LLM extracts items + handwritten amounts
      ↓
Customer detection (from context or papa specifies)
      ↓
Confidence check on extracted amounts
      ↓
   ┌────┴────┐
  High       Low
   │           │
   ▼           ▼
Bill generated   Agent asks: "₹120 ya ₹170 — 
+ ledger updated   yeh amount clear nahi hai"
                    │
                    ▼
              Papa confirms/corrects
                    │
                    ▼
              Bill + ledger updated
                    ↓
              Reply sent to papa
```

## 2.3 Journey: Customer History Check
```
Papa: "Ram ka account dikhao"
      ↓
get_customer_history() tool call
      ↓
SQL query: all transactions + running balance for Ram
      ↓
LLM formats into natural language
      ↓
Reply: transaction list, total outstanding, last payment date
```

## 2.4 Journey: Reminder Workflow
```
Daily scheduled job checks overdue balances (30+ days)
      ↓
Agent drafts reminder, sends proposal to papa
      ↓
Papa: "Haan, bhejo" / "Nahi"
      ↓
   ┌────┴────┐
  Haan       Nahi
   │           │
   ▼           ▼
Check opt-in +   Mark reviewed,
24hr window       skip
   │
   ├─ Opted-in + within window → conversational message sent
   ├─ Opted-in + outside window → Meta utility template sent
   └─ Not opted-in → papa notified only: "Ram ko phone karo, ₹650 pending"
```

## 2.5 Journey: Business Report
```
Papa: "Aaj kitna udhaar hua?"
      ↓
get_daily_report() tool call → SQL aggregation
      ↓
LLM formats: "Aaj ₹2,340 ka udhaar diya gaya, 6 customers ko."
```

---

# Document 3 — Agent Architecture

## 3.1 Component Overview
```
                    Incoming WhatsApp Message
                              │
                              ▼
                    ┌───────────────────┐
                    │  Planner Agent    │  ← LLM with tool-calling
                    │  (reasons about   │     schema, decides what
                    │   what to do)     │     to do this turn
                    └─────────┬─────────┘
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
      ┌──────────────┐ ┌──────────────┐ ┌─────────────────┐
      │    Memory    │ │ Decision     │ │  Tool Router     │
      │  (session +  │ │ Engine       │ │ (dispatches to   │
      │   pending    │ │ (confidence  │ │  the right tool  │
      │   actions)   │ │  thresholds) │ │  based on agent's│
      └──────────────┘ └──────────────┘ │  tool call)      │
                                         └────────┬─────────┘
                    ┌────────────┬───────────────┼────────────┬────────────┐
                    ▼            ▼               ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐   ┌──────────┐ ┌───────────┐ ┌──────────┐
              │  Ledger  │ │   OCR    │   │ Customer │ │ Reminder  │ │  Report  │
              │   Tool   │ │   Tool   │   │   Tool   │ │   Tool    │ │   Tool   │
              └──────────┘ └──────────┘   └──────────┘ └───────────┘ └──────────┘
```

## 3.2 Component Responsibilities

**Planner Agent**
- Receives the incoming message (transcribed if voice) + conversation context
- Has access to a tool-calling schema describing every available tool
- Reasons: what is the user's intent, which tool(s) to call, in what order, whether to ask a clarifying question instead of acting
- This is a single LLM reasoning step, not a hardcoded router

**Memory**
- Session state: what confirmation is pending, what was the last ambiguous entity, recent conversation turns
- Not a long-term "personality" memory — purely operational state needed to resolve multi-turn exchanges (e.g., "which Sharma ji?")

**Decision Engine**
- Applies confidence thresholds to extraction results (customer match score, amount clarity, OCR confidence)
- Decides: auto-proceed with undo window, or block and ask for confirmation
- This logic can be simple rules on top of LLM-provided confidence scores — doesn't need to be an LLM call itself

**Tool Router**
- Dispatches the Planner's chosen tool call(s) to the actual tool implementation
- Handles retries, error catching, and returns structured results back to the Planner for the next reasoning step

**Tools** (deterministic code, not LLM):
- **Ledger Tool** — `add_transaction()`, `update_payment()`, `undo_last()`
- **OCR Tool** — `extract_from_image()`, returns structured items + confidence
- **Customer Tool** — `resolve_customer()`, `get_customer_history()`
- **Reminder Tool** — `get_overdue_customers()`, `propose_reminder()`, `send_reminder()` (channel-aware)
- **Report Tool** — `get_daily_report()`, `get_monthly_report()`, `get_outstanding_report()`

## 3.3 Why This Is Agentic, Not a Pipeline
The Planner doesn't follow a fixed sequence of steps for every message. It decides per-message which tools are relevant, whether to chain multiple tool calls, and whether the confidence of any step is low enough to require human input before proceeding. A fixed pipeline (classify → extract → save) cannot represent this branching, context-dependent behavior.

## 3.4 Tool Interface Specification
Every tool exposed to the Planner follows the same contract — this consistency is what makes the Tool Router simple and what makes each tool independently testable.

```
Tool: resolve_customer()
─────────────────────────
Input:
  name_raw: str              -- as extracted from the message
  context_hint: str | None    -- e.g. area/alias mentioned alongside the name

Output:
  customer_id: UUID | None
  match_confidence: float
  ambiguous_candidates: list[str]   -- populated only if confidence is low

Errors:
  NoMatchFound          -- zero candidates in DB
  DatabaseError         -- connection/query failure (retried by Tool Router)
```

```
Tool: add_transaction()
─────────────────────────
Input:
  customer_id: UUID
  type: 'credit_given' | 'payment_received'
  amount: float
  item_description: str | None
  source: 'text' | 'voice' | 'ocr'
  confidence: float

Output:
  transaction_id: UUID
  new_balance: float
  status: 'confirmed' | 'pending_confirmation'

Errors:
  InvalidAmount         -- negative or zero
  CustomerNotFound
  DatabaseError
```

```
Tool: extract_from_image()
─────────────────────────
Input:
  media_url: str

Output:
  items: list[{description, amount, confidence}]
  overall_confidence: float

Errors:
  UnreadableImage
  VisionAPIError        -- retried by Tool Router, falls back to 
                            "photo samajh nahi aayi, dobara bhejo"
```

```
Tool: propose_reminder()
─────────────────────────
Input:
  customer_id: UUID
  outstanding_amount: float
  days_overdue: int

Output:
  reminder_id: UUID
  draft_message: str
  requires_approval: bool     -- always true, never auto-sent

Errors:
  CustomerNotFound
```

```
Tool: get_outstanding_report()
─────────────────────────
Input:
  (none — always scoped to the single shop)

Output:
  customers: list[{name, outstanding_balance}]
  total_outstanding: float

Errors:
  DatabaseError
```

The same shape — **Input → Output → Errors** — applies to every remaining tool (`update_payment`, `undo_last`, `get_customer_history`, `send_reminder`, `get_daily_report`, `get_monthly_report`). Defining this contract up front means each tool can be unit-tested in isolation, without needing the LLM in the loop at all.

## 3.5 Sequence Diagram — End-to-End Message Flow
```
Papa          WhatsApp        Webhook         Planner          Tool          DB
 │               │               │               │               │            │
 │─ voice note ─▶│               │               │               │            │
 │               │─ POST /webhook▶               │               │            │
 │               │               │─ transcribe ─▶│               │            │
 │               │               │               │─ resolve_     │            │
 │               │               │               │  customer() ─▶│            │
 │               │               │               │               │─ SELECT ──▶│
 │               │               │               │               │◀─ result ──│
 │               │               │               │◀── result ────│            │
 │               │               │               │                            │
 │               │               │               │─ add_                     │
 │               │               │               │  transaction()───────────▶│
 │               │               │               │               │─ INSERT ──▶│
 │               │               │               │◀── new_balance ───────────│
 │               │               │               │                            │
 │               │               │◀─ response ────│                            │
 │               │◀─ send msg ────│               │                            │
 │◀─ "Ram ka udhaar│               │               │                            │
 │   ab ₹1150"    │               │               │                            │
```

This is the same shape for every feature (OCR, reminders, reports) — only the tool(s) called in the middle changes. The Planner is always the single decision-making point between the Webhook and the Tools.

---

# Document 4 — Database Design

## 4.1 Entities

Single-shop MVP — no `Shop` or `User` entity needed right now. The owner's WhatsApp number is verified against a single config value (`OWNER_PHONE_NUMBER` env var), not a database row. Add these back only when a second store or second staff member is actually onboarded — not before.

**Customer**
```
id                  UUID PK
name                TEXT
alias_notes         TEXT        -- "Gandhi road wale Sharma ji" for disambiguation
phone               TEXT NULL
whatsapp_opted_in   BOOLEAN DEFAULT FALSE
opted_in_at         TIMESTAMP NULL
created_at          TIMESTAMP
```
*No cached `running_balance` field — see §4.1a below for why.*

**Transaction**
```
id                  UUID PK
customer_id         UUID FK -> Customer
type                ENUM('credit_given','payment_received')
amount              NUMERIC
item_description    TEXT NULL
status              ENUM('pending_confirmation','confirmed','rejected','undone')
source              ENUM('text','voice','ocr')
confidence_score    FLOAT
raw_input           TEXT        -- original transcription/OCR text, for audit
created_at          TIMESTAMP
confirmed_at        TIMESTAMP NULL
```

## 4.1a Single Source of Truth: No Ledger Table, No Cached Balance
Earlier drafts had both a `running_balance` field on `Customer` *and* a separate `Ledger` table — two places holding the same derived number. That's a real risk: any bug or missed update path lets them drift apart, and a wrong balance is the worst possible failure mode for a financial system.

**Decision: outstanding balance is always computed live from `Transaction`, never stored.**

```sql
SELECT
  COALESCE(SUM(CASE WHEN type = 'credit_given' THEN amount ELSE 0 END), 0)
  - COALESCE(SUM(CASE WHEN type = 'payment_received' THEN amount ELSE 0 END), 0)
  AS outstanding_balance
FROM transactions
WHERE customer_id = :customer_id
  AND status = 'confirmed';
```

At 25-40 customers and a handful of transactions a day, this aggregate query costs milliseconds — there is no performance reason to cache it. An index on `transactions(customer_id, status)` is enough. If the store ever scales to a point where this genuinely matters, a proper caching layer (materialized view with explicit refresh, or Redis) can be added later — that's a scale problem to solve when it actually shows up, not now.

**Reminder**
```
id                  UUID PK
customer_id         UUID FK -> Customer
amount_at_time      NUMERIC
proposed_at         TIMESTAMP
approved_by_owner   BOOLEAN NULL
channel_used        ENUM('conversational','template','owner_only') NULL
sent_at             TIMESTAMP NULL
```

**Conversation**
```
id                  UUID PK
started_at          TIMESTAMP
last_message_at     TIMESTAMP
```

**Message**
```
id                  UUID PK
conversation_id     UUID FK -> Conversation
direction           ENUM('inbound','outbound')
type                ENUM('text','voice','image')
content             TEXT
media_url           TEXT NULL
created_at          TIMESTAMP
```

**OCRDocument**
```
id                  UUID PK
message_id          UUID FK -> Message
extracted_json      JSONB       -- raw structured extraction
confidence_score    FLOAT
reviewed            BOOLEAN DEFAULT FALSE
created_at          TIMESTAMP
```

## 4.2 Relationships
- Customer 1───N Transaction
- Customer 1───N Reminder
- Conversation 1───N Message
- Message 1───1 OCRDocument (when type = image)

**Lean by design:** five entities total — Customer, Transaction, Reminder, Conversation, Message, OCRDocument. Nothing here exists "for later" — every table earns its place by being needed for an MVP feature, and outstanding balance is a computed value, not a stored one.

---

# Document 5 — API Design

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/webhook` | Receives incoming WhatsApp messages/media from Meta Cloud API |
| POST | `/ledger` | Manually create a transaction (fallback/admin use) |
| GET | `/customer/{id}` | Get a customer's profile + transaction history |
| GET | `/customer/{id}/balance` | Get current outstanding balance only |
| POST | `/ocr` | Submit an image for extraction (internal, called by webhook flow) |
| GET | `/reports/daily` | Daily summary report |
| GET | `/reports/monthly` | Monthly summary report |
| GET | `/reports/outstanding` | Full outstanding balances across all customers |
| POST | `/reminder` | Trigger/propose a reminder for a specific customer |
| POST | `/reminder/{id}/approve` | Owner approves a pending reminder |
| POST | `/transaction/{id}/undo` | Reverse a transaction within the undo window |

All endpoints beyond `/webhook` are for internal use and debugging only — no auth layer needed since there's no external caller for MVP. Papa never touches these directly; all real interaction happens through WhatsApp.

---

# Document 6 — AI Design

## 6.1 Planner Reasoning Flow (Example)
```
Input: "Ram ko ₹650 ka udhaar diya"
      ↓
LLM call with tool schema + conversation context
      ↓
LLM reasons: "This is a credit-given transaction. 
              Need to resolve customer 'Ram' first."
      ↓
Tool call: resolve_customer("Ram")
      ↓
Tool result: {customer_id: "...", match_confidence: 0.92}
      ↓
LLM reasons: "High confidence match. Extract amount and save."
      ↓
Tool call: add_transaction(customer_id, type='credit_given', 
                            amount=650, source='text')
      ↓
Tool result: {new_balance: 1150, status: 'confirmed'}
      ↓
LLM generates final response to papa
      ↓
Memory updated with last transaction (for undo reference)
```

## 6.2 Structured Output Design
All extraction steps use structured (Pydantic-validated) outputs, not free-form text, so results can be programmatically checked before any DB write:

```python
class TransactionExtraction(BaseModel):
    customer_name_raw: str
    transaction_type: Literal["credit_given", "payment_received"]
    amount: float
    item_description: Optional[str]
    confidence: float  # 0.0 - 1.0
```

```python
class CustomerResolution(BaseModel):
    customer_id: Optional[str]
    match_confidence: float
    ambiguous_candidates: list[str] = []
```

## 6.3 Confidence Thresholds (initial, tunable during pilot)
| Signal | High confidence (auto-proceed + undo window) | Low confidence (ask first) |
|---|---|---|
| Customer match | ≥ 0.85 | < 0.85 |
| Amount extraction (voice) | Clear digit match, no ambiguity | Homophone risk (e.g. paanch/pachaas) |
| OCR handwriting | Legible, single interpretation | Multiple possible readings |

## 6.4 Design Principle: LLM for Language, Code for Math
The LLM is never asked to compute totals, balances, or aggregates directly. It only extracts structured entities and formats final responses. All arithmetic happens in SQL or Python against the database, eliminating hallucination risk in financial figures.

## 6.5 Human Approval Gates
Every one of these requires explicit owner confirmation before it takes effect:
- Any transaction below the confidence threshold
- Every OCR-derived transaction below threshold
- Every reminder, before it's sent to any customer
- Undo/reversal of a transaction

---

# Document 7 — Deployment

## 7.1 Infrastructure
- **Containerization:** Docker + Docker Compose (FastAPI app + PostgreSQL as services)
- **Hosting:** Railway or Render for MVP (simple, cheap, sufficient for single-store scale); VPS as a fallback if more control is needed
- **Database:** Managed PostgreSQL (Railway/Render add-on, or self-hosted on VPS)

## 7.2 Environment Variables (illustrative)
```
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=
ANTHROPIC_API_KEY=          # or OPENAI_API_KEY
DATABASE_URL=
WHISPER_API_KEY=
ENVIRONMENT=production
LOG_LEVEL=info
```

## 7.3 Operational Concerns
- **Logging:** structured logs for every tool call, every LLM decision, every DB write (needed for debugging real-world errors and for the audit trail on financial actions)
- **Error handling:** every external call (WhatsApp API, LLM API, Whisper) wrapped with retries + graceful fallback message to papa if something fails ("Samajh nahi aaya, dobara bhejo")
- **Secrets management:** environment variables only, never committed to source control
- **Backups:** scheduled PostgreSQL backups, since this holds real financial data for a real business

## 7.4 Rollout Plan
- Deploy to production environment before pilot begins
- Run parallel with physical khata during initial weeks
- Monitor logs daily during pilot for extraction errors or confidence miscalibration

## 7.5 Folder Structure
```
app/
├── api/                  # FastAPI route definitions
│   ├── webhook.py         # POST /webhook — WhatsApp entry point
│   └── reports.py         # /reports/* endpoints
│
├── agents/
│   └── planner.py         # Planner Agent — LLM tool-calling loop
│
├── tools/
│   ├── ledger_tool.py      # add_transaction, update_payment, undo_last
│   ├── customer_tool.py    # resolve_customer, get_customer_history
│   ├── ocr_tool.py         # extract_from_image
│   ├── reminder_tool.py    # get_overdue_customers, propose_reminder, send_reminder
│   └── report_tool.py      # get_daily_report, get_monthly_report, get_outstanding_report
│
├── memory/
│   └── session_store.py   # pending confirmations, conversation context
│
├── services/
│   ├── whatsapp_service.py # send/receive via Meta Cloud API
│   ├── whisper_service.py  # voice transcription
│   └── vision_service.py   # OCR/vision-LLM calls
│
├── db/
│   ├── models/             # SQLAlchemy models (one file per entity)
│   └── session.py          # DB session/connection management
│
├── schemas/                # Pydantic models — structured LLM outputs,
│                           #   request/response validation
│
├── prompts/                # Planner system prompt + tool-calling schemas,
│                           #   kept separate from code for easy iteration
│
├── core/
│   ├── config.py           # env var loading (OWNER_PHONE_NUMBER, API keys)
│   └── logging.py          # structured logging setup
│
├── tests/
│   ├── test_tools/          # unit tests per tool, no LLM required
│   └── test_agents/         # planner reasoning tests with mocked tools
│
├── alembic/                # DB migrations
├── main.py                 # FastAPI app entrypoint
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

Keeping `tools/` fully decoupled from `agents/` is what makes the tool contracts in §3.4 independently unit-testable — the Planner is the only thing that needs an LLM in the loop.

---

# Document 8 — Roadmap (Sprints)

| Sprint | Focus | Key Deliverables |
|---|---|---|
| **Sprint 1** | Backend foundation | FastAPI skeleton, PostgreSQL schema, Docker Compose, Alembic migrations set up |
| **Sprint 2** | WhatsApp integration | Webhook receiving messages, sender verification (owner-only), basic echo/test reply |
| **Sprint 3** | Core Ledger (text) | Planner + tool-calling for credit/payment entries, resolve_customer, confirmation flow, undo |
| **Sprint 4** | Voice + Reports | Whisper integration, get_history/get_outstanding_report/daily-monthly reports |
| **Sprint 5** | OCR | Vision-LLM bill extraction, confidence-based confirmation, tested on real handwriting |
| **Sprint 6** | Reminders | Overdue detection job, owner-approval flow, opt-in tracking, Meta template approval, channel-aware sending |
| **Sprint 7** | Deployment & Pilot | Production deployment, logging/monitoring, parallel-khata pilot phase, real-world tuning |

*(This maps directly onto the Phase 0–7 breakdown from the earlier roadmap draft — Sprints 1-2 are Phase 0-1, Sprint 3 is Phase 1, Sprint 4 is Phase 2-3, Sprint 5 is Phase 4, Sprint 6 is Phase 5, Sprint 7 is Phase 6.)*

---

## Technology Stack (Confirmed)

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| AI | Claude / OpenAI (structured outputs, no framework in Phase 1) |
| OCR | TBD after evaluation (Vision-LLM first choice, PaddleOCR/Google Vision as alternatives) |
| WhatsApp | Meta Cloud API |
| Deployment | Docker |

*No auth layer for MVP — papa doesn't log in anywhere, and there's no admin panel to protect. The only "authentication" that matters is verifying the inbound WhatsApp sender number against `OWNER_PHONE_NUMBER` on every webhook call. Revisit if a dashboard or multi-user access is ever added.*

---

# Risk Analysis (One-Page Summary)

| Risk | Impact | Mitigation |
|---|---|---|
| Wrong OCR reading (unclear handwriting) | Wrong ledger entry, financial error | Human confirmation required below confidence threshold; raw image + extraction kept for audit |
| Wrong customer match (name ambiguity) | Money attributed to wrong person | Confidence threshold on `resolve_customer()`; agent asks "which one?" when ambiguous |
| Duplicate transactions (same voice note processed twice, or papa repeats himself) | Inflated/incorrect balance | Duplicate detector — flag same customer + same amount within a short time window before saving |
| WhatsApp 24-hour messaging window | Reminder can't be sent as free-form text outside the window | Meta-approved utility template as fallback; channel-aware Reminder Tool decides automatically |
| Customer never opted in | Can't message them via WhatsApp at all | Fallback to "notify owner only" — papa calls manually |
| External API failure (WhatsApp, LLM, Whisper, Vision) | Message goes unprocessed | Retry with backoff at the Tool Router level; graceful fallback reply to papa if all retries fail |
| Papa doesn't trust the system initially | Reverts to physical khata, pilot fails | Parallel khata maintained during pilot weeks; undo command always available |
| LLM asked to compute totals directly | Hallucinated numbers | Arithmetic always done in SQL/Python, never delegated to the LLM |

---

*This document is the frozen Phase 0 design output for VyaparAI. All subsequent code, README, and architecture decisions should stay consistent with this identity and structure.*