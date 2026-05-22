# AMT AI Assistant — Internal Demo

> AI-powered department assistant for **Advanced Media Trading LLC** — the largest professional AV equipment distributor in MENA.

Built as a live internal demo to show non-technical department heads exactly how AI can simplify their daily work. No buzzwords. No slides. Just real data, real queries, real answers.

---

## What It Does

Four department-specific AI agents, each connected to a live SAP-aligned database of realistic AMT data:

| Department | What the AI can do |
|---|---|
| **Sales** | Build equipment quotes, check stock, pull customer order history, semantic product search |
| **Distribution** | Track inbound shipments, monitor purchase orders, flag delays & customs holds, inventory levels |
| **Finance** | Overdue invoices, revenue summaries, aging reports, customer balances, Pandas analytics |
| **Service** | View open repair tickets, log new ones, update status, draft customer emails |

Every response is grounded in real data — the AI queries the database, it doesn't hallucinate.

---

## Stack

| Layer | Technology |
|---|---|
| **Orchestration** | LangGraph (StateGraph routing to department agents) |
| **LLM** | GPT-4o via OpenAI function calling |
| **Semantic Search** | LlamaIndex + ChromaDB (40-product vector store) |
| **Tool Dispatch** | LangChain StructuredTool |
| **Financial Analysis** | Pandas (aging reports, payment rates, monthly trends) |
| **Observability** | LangSmith (full trace of every agent run) |
| **Database** | SQLite — SAP SD/MM/FI/CS aligned schema (20+ tables) |
| **Backend** | Python + Flask |
| **Frontend** | Custom HTML/CSS/JS with per-department theming + live tool trace |

---

## Project Structure

```
AMT_Demo/
├── app.py                      # Flask server, LangSmith init, session history
├── requirements.txt
├── .env                        # API keys (not committed)
│
├── agents/
│   ├── langgraph_flow.py       # LangGraph StateGraph router (entry point)
│   ├── trace.py                # Thread-local tool trace (fires per request)
│   ├── vector_store.py         # LlamaIndex + ChromaDB + LangChain StructuredTool
│   ├── sales.py                # Product search, quote builder, order history
│   ├── distribution.py         # Shipments, purchase orders, inventory
│   ├── finance.py              # Invoices, revenue, Pandas financial reports
│   └── service.py              # Ticket management, create/update, customer emails
│
├── db/
│   ├── schema.sql              # SAP-aligned schema: branches, employees, suppliers,
│   │                           #   products, inventory, customers, POs, orders,
│   │                           #   invoices, service_tickets, warranties + more
│   ├── seed.py                 # Full AMT data: 4 branches, 18 employees, 20 suppliers,
│   │                           #   42 products, 15 customers, 12 orders, 12 invoices,
│   │                           #   8 service tickets, 5 warranty registrations
│   └── amt.db                  # Generated SQLite database (not committed)
│
├── templates/
│   └── index.html              # Chat UI: department switcher, tech stack bar,
│                               #          per-message tool trace panel
└── static/
    └── amt_logo.webp
```

---

## Sample Data

- **4 branches** — Dubai HQ, Al Quoz Warehouse+Service, Riyadh, Cairo
- **18 employees** — real AMT leadership (Kaveh Farnam, Alaa Al Rantisi, Pooyan Farnam, etc.)
- **20 suppliers** — DJI, Sony Professional, RED, ARRI, Zeiss, Profoto, Sennheiser, Atomos, Teradek, and more
- **42 products** — with real HS codes, cost/sell prices, warranty periods
- **15 customers** — MBC Group, ADNOC, Saudi Broadcasting Authority, Dubai Film Commission, OSN, etc.
- **12 orders** across delivered, shipped, confirmed, and pending states
- **12 invoices** — UAE 5% VAT / KSA 15% VAT / Egypt 14% VAT applied correctly
- **5 inbound shipments** — including one on customs hold
- **8 service tickets** — Dubai + Riyadh, across all repair stages

---

## Getting Started

**1. Clone the repo**
```bash
git clone https://github.com/Twillur/AMT-AI-Demo.git
cd AMT-AI-Demo
```

**2. Create a virtual environment**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set your API keys**

Create a `.env` file in the root:
```
OPENAI_API_KEY=your_openai_key_here
FLASK_SECRET_KEY=any-random-string
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=AMT-Demo
LANGCHAIN_API_KEY=your_langsmith_key_here
```

**5. Seed the database**
```bash
python db/seed.py
```

**6. Run**
```bash
python app.py
```

Open `http://localhost:5000`

---

## Demo Queries to Try

**Sales**
> "Give me a quote for a 4K cinema shoot kit under AED 80,000"
> "What's the stock level on DJI Mavic 3 Pro?"
> "Show me all orders for MBC Group"

**Distribution**
> "Show me all delayed or customs-held shipments"
> "What purchase orders are currently open?"
> "What items are running low on stock?"

**Finance**
> "Show all overdue invoices"
> "Run an aging report"
> "What's our total revenue and collection rate for 2026?"

**Service**
> "Show me all open repair tickets"
> "Log a new repair for Rami Yousef — DJI RS 4 Pro, motor overheating"
> "Draft a customer update email for ticket SVC-2026-001"

---

## Design Philosophy

> *"Don't try to change the whole business. Make the individual person's daily tasks easier. Once daily tasks are easy, the convincing is done."*

This demo is intentionally personal and non-technical. Each department head sees a tool built for their exact workflow — not a generic AI chatbot.

---

Built by [William Kojumian](https://github.com/Twillur)
