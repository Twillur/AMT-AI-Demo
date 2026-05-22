# AMT AI Assistant — Internal Demo

> AI-powered department assistant for **Advanced Media Trading LLC** — the largest professional AV equipment distributor in MENA.

Built as a live internal demo to show non-technical department heads exactly how AI can simplify their daily work. No buzzwords. No slides. Just real data, real queries, real answers.

---

## What It Does

Four department-specific AI agents, each connected to a live database of realistic AMT data:

| Department | What the AI can do |
|---|---|
| **Sales** | Build equipment quotes, check stock, pull customer order history |
| **Distribution** | Track inbound shipments, flag delays & customs holds, monitor inventory |
| **Finance** | Show overdue invoices, summarize revenue, check customer balances |
| **Service** | View open repair tickets, log new ones, update status, draft customer emails |

Every response is grounded in real data — the AI queries the database, it doesn't hallucinate.

---

## Stack

- **Backend:** Python + Flask
- **AI:** GPT-4o with function calling (tool use)
- **Database:** SQLite with realistic AMT sample data
- **Frontend:** Custom HTML/CSS/JS chat interface with per-department theming

---

## Project Structure

```
AMT_Demo/
├── app.py                  # Flask server + session-based chat history
├── requirements.txt
├── .env                    # API keys (not committed)
│
├── agents/
│   ├── sales.py            # Product search, quote builder, order history
│   ├── distribution.py     # Shipment tracker, inventory monitor
│   ├── finance.py          # Invoice status, revenue summary, balances
│   └── service.py          # Ticket management, create/update tickets
│
├── db/
│   ├── schema.sql          # 7-table schema (products, inventory, customers,
│   │                       #   orders, invoices, shipments, service_tickets)
│   ├── seed.py             # Populates DB with realistic AMT sample data
│   └── amt.db              # Generated SQLite database (not committed)
│
├── templates/
│   └── index.html          # Chat UI with department switcher
│
└── static/
    └── amt_logo.webp
```

---

## Sample Data Included

- **23 products** — DJI, Sony Pro, RED, Zeiss, Sennheiser, Profoto, Atomos, Teradek
- **10 customers** — MBC Group, Dubai Film Commission, ADNOC, Saudi Broadcasting Corp, and more
- **10 orders** across delivered, shipped, confirmed, and pending states
- **10 invoices** — mix of paid, unpaid, and overdue
- **5 shipments** — from China, USA, Japan, Hong Kong — including a delayed customs hold
- **6 service tickets** — across all repair stages with real warranty status

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

**4. Set your API key**

Create a `.env` file in the root:
```
OPENAI_API_KEY=your_openai_key_here
FLASK_SECRET_KEY=any-random-string
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

**Distribution**
> "Show me all delayed or customs-held shipments"
> "What items are running low on stock?"

**Finance**
> "Show all overdue invoices"
> "What's our total revenue and outstanding balance for 2026?"

**Service**
> "Show me all open repair tickets"
> "Log a new repair for Rami Yousef — DJI RS 4 Pro, motor overheating"

---

## Design Philosophy

> *"Don't try to change the whole business. Make the individual person's daily tasks easier. Once daily tasks are easy, the convincing is done."*

This demo is intentionally personal and non-technical. Each department head sees a tool built for their exact workflow — not a generic AI chatbot.

---

Built by [William Kojumian](https://github.com/Twillur)
