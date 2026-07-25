from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Landing Page"])

LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>VyaparAI — Agentic AI WhatsApp Ledger Assistant</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <script>
    document.addEventListener("DOMContentLoaded", function() {
      mermaid.initialize({
        startOnLoad: true,
        theme: 'dark',
        themeVariables: {
          darkMode: true,
          background: '#0d1322',
          primaryColor: '#8b5cf6',
          primaryTextColor: '#ffffff',
          primaryBorderColor: '#a7f3d0',
          lineColor: '#38bdf8',
          secondaryColor: '#06b6d4',
          tertiaryColor: '#10b981'
        }
      });
    });
  </script>
  <style>
    :root {
      --bg: #090d16;
      --card-bg: rgba(18, 26, 43, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent-purple: #8b5cf6;
      --accent-cyan: #06b6d4;
      --accent-green: #10b981;
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
    }
    
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Plus Jakarta Sans', sans-serif;
      background-color: var(--bg);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 2rem 1rem;
      background-image: 
        radial-gradient(circle at 15% 20%, rgba(139, 92, 246, 0.15) 0%, transparent 40%),
        radial-gradient(circle at 85% 80%, rgba(6, 182, 212, 0.15) 0%, transparent 40%);
    }

    .container {
      max-width: 960px;
      width: 100%;
    }

    .header-card {
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      border: 1px solid var(--card-border);
      border-radius: 24px;
      padding: 3rem 2rem;
      text-align: center;
      box-shadow: 0 20px 50px rgba(0,0,0,0.5);
      margin-bottom: 2rem;
      position: relative;
      overflow: hidden;
    }

    .header-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: linear-gradient(90deg, var(--accent-purple), var(--accent-cyan), var(--accent-green));
    }

    .badge-live {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
      padding: 0.4rem 1rem;
      border-radius: 9999px;
      font-size: 0.875rem;
      font-weight: 600;
      margin-bottom: 1.5rem;
    }

    .badge-live .pulse {
      width: 8px;
      height: 8px;
      background-color: var(--accent-green);
      border-radius: 50%;
      box-shadow: 0 0 10px var(--accent-green);
      animation: pulse-anim 2s infinite;
    }

    @keyframes pulse-anim {
      0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
      70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
      100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    h1 {
      font-size: 2.75rem;
      font-weight: 800;
      letter-spacing: -0.025em;
      margin-bottom: 1rem;
      background: linear-gradient(135deg, #ffffff 30%, #a7f3d0 70%, #a5b4fc 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    p.subtitle {
      font-size: 1.125rem;
      color: var(--text-muted);
      max-width: 680px;
      margin: 0 auto 2rem auto;
      line-height: 1.6;
    }

    .btn-group {
      display: flex;
      gap: 1rem;
      justify-content: center;
      flex-wrap: wrap;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.85rem 1.75rem;
      border-radius: 14px;
      font-weight: 700;
      font-size: 0.95rem;
      text-decoration: none;
      transition: all 0.2s ease;
    }

    .btn-primary {
      background: linear-gradient(135deg, var(--accent-purple), #6366f1);
      color: #ffffff;
      box-shadow: 0 10px 25px rgba(139, 92, 246, 0.3);
    }

    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 15px 30px rgba(139, 92, 246, 0.45);
    }

    .btn-secondary {
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-main);
      border: 1px solid var(--card-border);
    }

    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.1);
      transform: translateY(-2px);
    }

    .grid-2 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .card {
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      border: 1px solid var(--card-border);
      border-radius: 20px;
      padding: 1.75rem;
      margin-bottom: 1.5rem;
    }

    .card h3 {
      font-size: 1.2rem;
      font-weight: 700;
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .mermaid-container {
      display: flex;
      justify-content: center;
      padding: 1rem 0;
      overflow-x: auto;
    }

    .cmd-list {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .cmd-item {
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 10px;
      padding: 0.75rem 1rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.875rem;
      color: #38bdf8;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .cmd-tag {
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 0.75rem;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.08);
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
    }

    .tech-stack {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 1rem;
    }

    .tech-pill {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.08);
      padding: 0.4rem 0.8rem;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
    }

    footer {
      text-align: center;
      font-size: 0.875rem;
      color: var(--text-muted);
      margin-top: 1rem;
    }

    footer a {
      color: var(--accent-cyan);
      text-decoration: none;
    }
  </style>
</head>
<body>

  <div class="container">
    <div class="header-card">
      <div class="badge-live">
        <span class="pulse"></span> Live Production Service Online
      </div>
      <h1>VyaparAI</h1>
      <p class="subtitle">
        Production-Grade Agentic AI WhatsApp Business Ledger Assistant.<br>
        Manage customer ledgers, credit entries, OCR bills, and voice notes in natural Hinglish directly on WhatsApp.
      </p>
      <div class="btn-group">
        <a href="/docs" class="btn btn-primary">
          🚀 Open Interactive Swagger API Docs (/docs)
        </a>
        <a href="/health" class="btn btn-secondary">
          🟢 Check Health Status (/health)
        </a>
        <a href="https://github.com/priyanshuraj20/VyaparAi" target="_blank" class="btn btn-secondary">
          ⭐ View GitHub Code
        </a>
      </div>
    </div>

    <!-- Detailed Mermaid System Architecture Flow -->
    <div class="card">
      <h3>🏛 Comprehensive System Architecture & Lifecycle</h3>
      <div class="mermaid-container">
        <div class="mermaid">
        flowchart TD
            User[WhatsApp User / Shopkeeper] -->|Sends Text / Voice / Photo| Meta[Meta Cloud API Webhook]
            Meta -->|JSON Webhook Payload| FastAPI[FastAPI Webhook Handler]
            
            subgraph Core Engine [VyaparAI Core Engine]
                FastAPI -->|Extract Message ID| Dedupe{Upstash Redis Deduplication}
                Dedupe -->|New Message| Agentic[OpenRouter Agentic AI Planner]
                
                Agentic -->|Intent & Parameters| Router{Business Tool Router}
                
                Router -->|Credit / Payment| Ledger[Ledger Tool & Fuzzy Resolution]
                Router -->|OCR Photo| Vision[Vision LLM Extraction]
                Router -->|Voice Note| Whisper[Whisper STT Service]
                Router -->|Reminders| Reminder[Reminder Tool]
                
                Ledger -->|Save Permanent Record| Postgres[(Supabase PostgreSQL 16)]
                Ledger -->|Temporary Confirmation / Undo| Redis[(Upstash Redis State)]
            end
            
            Ledger -->|Structured Ledger Card| Refiner[Groq Llama 3.1 Response Refiner]
            Refiner -->|Polished Hinglish Response| Reply[Meta Cloud API Send]
            Reply -->|WhatsApp Reply| User
        </div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <h3>🧪 How to Test API Endpoints</h3>
        <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1rem; line-height: 1.5;">
          You can test all endpoints, schemas, and AI planning flows directly using our interactive Swagger UI or curl commands:
        </p>
        <ul class="cmd-list">
          <li class="cmd-item">
            <span>GET /health</span>
            <span class="cmd-tag">System Health</span>
          </li>
          <li class="cmd-item">
            <span>POST /webhook</span>
            <span class="cmd-tag">WhatsApp Webhook</span>
          </li>
          <li class="cmd-item">
            <span>GET /customers</span>
            <span class="cmd-tag">Ledger Customers</span>
          </li>
          <li class="cmd-item">
            <span>GET /reports/daily</span>
            <span class="cmd-tag">Business Report</span>
          </li>
        </ul>
      </div>

      <div class="card">
        <h3>💬 Example Natural WhatsApp Inputs</h3>
        <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1rem; line-height: 1.5;">
          VyaparAI's Agentic Planner parses natural Hinglish messages and executes database ledger transactions:
        </p>
        <ul class="cmd-list">
          <li class="cmd-item">
            <span>"Ramesh ko 500 udhaar de do"</span>
            <span class="cmd-tag">Credit Given</span>
          </li>
          <li class="cmd-item">
            <span>"Sharma ne 300 online payment kar diya"</span>
            <span class="cmd-tag">Payment Received</span>
          </li>
          <li class="cmd-item">
            <span>"Harshit ka balance kitna hai"</span>
            <span class="cmd-tag">Balance Query</span>
          </li>
          <li class="cmd-item">
            <span>"undo"</span>
            <span class="cmd-tag">Revert Reversal</span>
          </li>
        </ul>
      </div>
    </div>

    <div class="card">
      <h3>⚡ System Architecture & Technology Stack</h3>
      <div class="tech-stack">
        <span class="tech-pill">Python 3.12</span>
        <span class="tech-pill">FastAPI</span>
        <span class="tech-pill">Agentic AI Planner</span>
        <span class="tech-pill">PostgreSQL 16 (Supabase)</span>
        <span class="tech-pill">Upstash Redis</span>
        <span class="tech-pill">OpenRouter (DeepSeek)</span>
        <span class="tech-pill">Groq (Llama 3.1)</span>
        <span class="tech-pill">OpenAI Whisper STT</span>
        <span class="tech-pill">Meta WhatsApp Cloud API</span>
        <span class="tech-pill">Docker & Render Cloud</span>
      </div>
    </div>

    <footer>
      VyaparAI Agentic Business Engine • Developed with ❤️ by <a href="https://github.com/priyanshuraj20" target="_blank">Priyanshu Raj</a>
    </footer>
  </div>

</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page():
    return HTMLResponse(content=LANDING_HTML)
