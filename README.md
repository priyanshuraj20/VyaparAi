<div align="center">

# 🌐 VyaparAI

### AI-Powered WhatsApp Business Ledger Assistant

<p align="center">
Manage your entire business ledger directly from WhatsApp using Natural Language, AI Planning, OCR, and Voice Notes.
</p>

<p align="center">

[![Live Demo](https://img.shields.io/badge/Render-Live_Production-brightgreen?style=for-the-badge&logo=render)](https://vyaparai-jge7.onrender.com)
![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Production-green?style=for-the-badge&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue?style=for-the-badge&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker)
![Redis](https://img.shields.io/badge/Upstash-Redis-red?style=for-the-badge)
![OpenRouter](https://img.shields.io/badge/OpenRouter-LLM-orange?style=for-the-badge)
![Groq](https://img.shields.io/badge/Groq-Response%20Refiner-black?style=for-the-badge)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Business_API-25D366?style=for-the-badge&logo=whatsapp)

</p>

### 🔗 Live Production API URL
`https://vyaparai-jge7.onrender.com`

---

### 📱 Talk to your Business. Don't open another App.

Small business owners already use WhatsApp.

VyaparAI turns WhatsApp into an intelligent business assistant capable of understanding natural language, maintaining customer ledgers, recording payments, processing handwritten bills, understanding voice notes, creating payment reminders, and managing business state automatically.

</div>

---

# 🌟 Why VyaparAI?

Traditional accounting software requires users to open an app, search customers, fill forms, and save entries manually.

VyaparAI removes all friction. The shop owner simply sends a WhatsApp message:

```text
Ramesh ko 500 udhaar de do

Sharma ne 300 payment kar diya online

Kal subah 9 baje reminder bhej do

Ye bill scan kar do

Is voice note ko record kar lo
```

VyaparAI understands intent, executes business workflows safely, persists records in PostgreSQL, and replies with structured accounting software cards.

---

# ✨ Core Features

## 💬 Natural Language Business Assistant
- Understands Hindi, English, and Hinglish business conversations seamlessly.
- Handles casual greetings and assistant introduction prompts warm & conversationally.

## 📒 Smart Customer Ledger
- Customer Management & Fuzzy Name Resolution.
- Credit Entries (`credit_given`) & Payment Entries (`payment_received`).
- Live Outstanding Balance Computation (No cached balance drift).
- Duplicate Customer Detection & Auto Customer Creation Workflow.

## 🤖 AI Planner & Reasoning Engine
- Analyzes incoming text, voice notes, or photos using LLM function calling.
- Dynamically extracts customer name, transaction amount, payment mode (`Online`, `Cash`, `UPI`), and action intent.

## 📸 OCR Bill & Invoice Processing
- Vision LLM extracts line items, amounts, and customer details directly from handwritten bill or receipt photos.

## 🎤 Voice Note Understanding
- Transcribes incoming audio using OpenAI Whisper API and routes natural voice commands directly into the ledger workflow.

## ⏪ Reversal & Undo Transaction
- Reverses the most recent transaction instantly upon receiving `"undo"`.

## ⏳ Temporary Pending Confirmation (Upstash Redis)
- If a customer is missing or candidate match is ambiguous, temporary state is stored in Redis.
- Upon confirmation (`YES`/`NO`), original transaction context is retrieved and replayed seamlessly.

---

# 🏗 High Level Architecture

```mermaid
flowchart LR

A[User] --> B[WhatsApp]
B --> C[Meta Cloud API]
C --> D[FastAPI Backend]
D --> E[OpenRouter Planner]
E --> F[Business Services]
F --> G[(PostgreSQL)]
F --> H[(Upstash Redis)]
F --> I[Groq Response Refiner]
I --> J[WhatsApp Reply]
J --> A
```

---

# 🏛 Production Architecture

```mermaid
flowchart TD

A[User] --> B[WhatsApp]
B --> C[Meta Cloud API]
C --> D[FastAPI Backend]
D --> E[Planner Agent]
E --> F[Business Services]
F --> G[(PostgreSQL)]
F --> H[(Upstash Redis)]
F --> I[Groq Response Refiner]
I --> J[WhatsApp Reply]
```

---

# 🧩 AI Request Lifecycle

```mermaid
sequenceDiagram

participant U as User
participant W as WhatsApp
participant API as FastAPI
participant P as Planner
participant S as Service Layer
participant DB as PostgreSQL
participant R as Redis
participant F as Response Refiner

U->>W: Send Message
W->>API: Webhook
API->>P: Analyze User Intent
P->>S: Execute Business Tool
S->>DB: Read/Write Business Data
S->>R: Store Temporary State (Optional)
DB-->>S: Result
S->>F: Structured Response
F-->>API: Human Friendly Reply
API-->>W: Send Message
W-->>U: Response
```

---

# 📸 Screenshots & Live Deployment

## 1. WhatsApp Conversation Assistant

![WhatsApp Conversation](docs/images/01-whatsapp-chat.png)

---

## 2. Live Render Cloud Production Deployment

![Render Production Live Deployment](docs/images/03-render-live.png)

---

## 3. Docker Container & Environment Setup

![Docker Desktop Containers](docs/images/02-docker-containers.png)

---

# ⚙ Tech Stack

- **Backend**: Python 3.12, FastAPI, AsyncPG, SQLAlchemy, Alembic
- **AI Providers**: OpenRouter (DeepSeek Chat / GPT-4o-mini), Groq (Llama 3.1), Whisper STT
- **Database & Memory**: PostgreSQL 16 (Source of Truth), Upstash Redis (Temporary State & Idempotency)
- **Deployment**: Docker, Docker Compose, Render Cloud Platform

---

# 📂 Project Structure

```text
VyaparAI
├── app
│   ├── agents          # OpenRouter Planner & Reasoning Agent
│   ├── api             # FastAPI Webhook & REST Endpoints
│   ├── core            # Settings, Logging & Database Config
│   ├── db              # SQLAlchemy Models & Async Sessions
│   ├── memory          # Session Store & Upstash Redis Store
│   ├── prompts         # Domain-Aware Accounting Card Prompts
│   ├── services        # WhatsApp, Refiner, Whisper & Vision Services
│   └── tools           # Customer, Ledger, Report & Reminder Tools
├── alembic             # Database Migrations
├── docs/images         # Screenshots
├── tests               # Automated Pytest Suite
├── Dockerfile          # Render Compatible Production Dockerfile
├── docker-compose.yml  # Local Container Setup
├── render.yaml         # Render Blueprint Specification
└── README.md
```

---

# 💾 PostgreSQL & Upstash Redis Split

| Storage Layer | Data Stored | TTL |
|---------------|-------------|-----|
| **PostgreSQL** | Permanent Customers, Transactions, Ledgers, Reports, Reminders | Permanent |
| **Upstash Redis** | Pending Confirmation State, Candidates, Undo Reference, Message Deduplication | 5 min - 24 hr |

---

# 🚀 Quick Start (Local Development)

```bash
# 1. Clone Repository
git clone https://github.com/priyanshuraj20/VyaparAi.git
cd VyaparAi

# 2. Start Services via Docker Compose
docker compose up -d --build

# 3. Test Health Endpoint
curl http://localhost:8000/health
```

---

# 📄 License & Credits

This project is licensed under the **MIT License**.

Developed with ❤️ by **Priyanshu Raj**.
