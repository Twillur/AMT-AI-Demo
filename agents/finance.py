import os, json
from openai import OpenAI
from .db_utils import query

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_invoices",
            "description": "Get invoices filtered by status and/or minimum amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by: unpaid/paid/overdue/disputed. Leave empty for all."},
                    "min_amount_aed": {"type": "number", "description": "Only show invoices above this amount in AED"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_revenue_summary",
            "description": "Get total revenue, VAT collected, and payment stats for a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                    "to_date": {"type": "string", "description": "End date YYYY-MM-DD"}
                },
                "required": ["from_date", "to_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_balance",
            "description": "Get outstanding balance and payment history for a specific customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer name or company name"}
                },
                "required": ["customer_name"]
            }
        }
    }
]

def get_invoices(status: str = None, min_amount_aed: float = None) -> list:
    sql = """
        SELECT i.invoice_ref, c.name, c.company, i.issue_date, i.due_date,
               i.amount_aed, i.vat_aed, (i.amount_aed + i.vat_aed) AS total_aed,
               i.status, i.paid_date
        FROM invoices i JOIN customers c ON c.id = i.customer_id
        WHERE 1=1
    """
    params = []
    if status:
        sql += " AND i.status = ?"
        params.append(status)
    if min_amount_aed:
        sql += " AND i.amount_aed >= ?"
        params.append(min_amount_aed)
    sql += " ORDER BY i.due_date"
    return query(sql, tuple(params))

def get_revenue_summary(from_date: str, to_date: str) -> dict:
    rows = query("""
        SELECT
            COUNT(*) AS invoice_count,
            SUM(amount_aed) AS revenue_aed,
            SUM(vat_aed) AS vat_collected,
            SUM(CASE WHEN status='paid' THEN amount_aed ELSE 0 END) AS collected_aed,
            SUM(CASE WHEN status IN ('unpaid','overdue') THEN amount_aed ELSE 0 END) AS outstanding_aed
        FROM invoices
        WHERE issue_date BETWEEN ? AND ?
    """, (from_date, to_date))
    return rows[0] if rows else {}

def get_customer_balance(customer_name: str) -> list:
    return query("""
        SELECT c.name, c.company,
               i.invoice_ref, i.issue_date, i.due_date,
               i.amount_aed, i.vat_aed, i.status, i.paid_date
        FROM invoices i JOIN customers c ON c.id = i.customer_id
        WHERE c.name LIKE ? OR c.company LIKE ?
        ORDER BY i.due_date
    """, (f"%{customer_name}%", f"%{customer_name}%"))

TOOL_MAP = {
    "get_invoices": get_invoices,
    "get_revenue_summary": get_revenue_summary,
    "get_customer_balance": get_customer_balance,
}

SYSTEM = """You are an AI assistant for AMT's finance team. AMT operates across multiple jurisdictions:
- UAE: 5% VAT | Saudi Arabia: 15% VAT | Egypt: separate regime
- Purchases in USD/EUR/JPY, sells in AED/SAR/EGP

You have live access to AMT's invoicing and payment data.

Your job:
- Report on overdue invoices and outstanding balances
- Summarize revenue for any period
- Show customer payment history
- Flag high-value unpaid invoices

Always present financials in clean tables. Show totals including VAT. Highlight overdue items clearly."""


def run(user_message: str, history: list) -> str:
    messages = [{"role": "system", "content": SYSTEM}] + history + [{"role": "user", "content": user_message}]

    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=1500
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content

        messages.append(msg)
        for tc in msg.tool_calls:
            fn = TOOL_MAP[tc.function.name]
            result = fn(**json.loads(tc.function.arguments))
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result)
            })
