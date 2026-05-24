import os, json
import pandas as pd
from io import StringIO
from openai import OpenAI
from .db_utils import query
from . import trace

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
    },
    {
        "type": "function",
        "function": {
            "name": "pandas_financial_report",
            "description": "Run a Pandas analysis on AMT's invoice data. Use for: aging reports, payment rate stats, top debtors, monthly revenue trends, VAT summaries. Returns a formatted markdown table built by Pandas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_type": {
                        "type": "string",
                        "description": "One of: aging_report | payment_rate | top_debtors | monthly_trend | vat_summary | full_overview"
                    }
                },
                "required": ["report_type"]
            }
        }
    }
]


def get_invoices(status: str = None, min_amount_aed: float = None) -> list:
    trace.log("get_invoices", "SQLite", f"Invoice query — status: {status or 'all'}")
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
    trace.log("get_revenue_summary", "SQLite", f"Revenue {from_date} → {to_date}")
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
    trace.log("get_customer_balance", "SQLite", f"Balance for: '{customer_name}'")
    return query("""
        SELECT c.name, c.company,
               i.invoice_ref, i.issue_date, i.due_date,
               i.amount_aed, i.vat_aed, i.status, i.paid_date
        FROM invoices i JOIN customers c ON c.id = i.customer_id
        WHERE c.name LIKE ? OR c.company LIKE ?
        ORDER BY i.due_date
    """, (f"%{customer_name}%", f"%{customer_name}%"))


def pandas_financial_report(report_type: str) -> str:
    trace.log("pandas_financial_report", "Pandas", f"Generating: {report_type}")

    rows = query("""
        SELECT c.name, c.company, c.country,
               i.invoice_ref, i.issue_date, i.due_date,
               i.amount_aed, i.vat_aed, i.status, i.paid_date
        FROM invoices i JOIN customers c ON c.id = i.customer_id
    """)

    df = pd.DataFrame(rows)
    df["issue_date"] = pd.to_datetime(df["issue_date"])
    df["due_date"] = pd.to_datetime(df["due_date"])
    df["total_aed"] = df["amount_aed"] + df["vat_aed"]
    df["month"] = df["issue_date"].dt.to_period("M").astype(str)
    today = pd.Timestamp("2026-05-22")
    df["days_overdue"] = (today - df["due_date"]).dt.days.clip(lower=0)
    df["days_overdue"] = df["days_overdue"].where(df["status"] != "paid", 0)

    if report_type == "aging_report":
        unpaid = df[df["status"].isin(["unpaid", "overdue"])].copy()
        def bucket(d):
            if d <= 30: return "0–30 days"
            elif d <= 60: return "31–60 days"
            elif d <= 90: return "61–90 days"
            else: return "90+ days"
        unpaid["aging_bucket"] = unpaid["days_overdue"].apply(bucket)
        result = (unpaid.groupby("aging_bucket")
                        .agg(invoices=("invoice_ref", "count"),
                             total_aed=("amount_aed", "sum"))
                        .reindex(["0–30 days", "31–60 days", "61–90 days", "90+ days"])
                        .fillna(0))
        result["total_aed"] = result["total_aed"].map("AED {:,.0f}".format)
        result.index.name = "Aging Bucket"
        return result.reset_index().to_markdown(index=False)

    elif report_type == "payment_rate":
        total = len(df)
        paid = (df["status"] == "paid").sum()
        overdue = (df["status"] == "overdue").sum()
        unpaid = (df["status"] == "unpaid").sum()
        summary = pd.DataFrame([
            {"Status": "Paid", "Count": int(paid), "Amount (AED)": f"AED {df[df.status=='paid']['amount_aed'].sum():,.0f}", "Rate": f"{paid/total*100:.0f}%"},
            {"Status": "Unpaid", "Count": int(unpaid), "Amount (AED)": f"AED {df[df.status=='unpaid']['amount_aed'].sum():,.0f}", "Rate": f"{unpaid/total*100:.0f}%"},
            {"Status": "Overdue", "Count": int(overdue), "Amount (AED)": f"AED {df[df.status=='overdue']['amount_aed'].sum():,.0f}", "Rate": f"{overdue/total*100:.0f}%"},
        ])
        return summary.to_markdown(index=False)

    elif report_type == "top_debtors":
        debtors = (df[df["status"].isin(["unpaid", "overdue"])]
                   .groupby(["name", "company"])["amount_aed"].sum()
                   .sort_values(ascending=False)
                   .reset_index()
                   .head(5))
        debtors.columns = ["Customer", "Company", "Outstanding (AED)"]
        debtors["Outstanding (AED)"] = debtors["Outstanding (AED)"].map("AED {:,.0f}".format)
        return debtors.to_markdown(index=False)

    elif report_type == "monthly_trend":
        trend = (df.groupby("month")
                   .agg(invoices=("invoice_ref", "count"),
                        revenue_aed=("amount_aed", "sum"),
                        collected_aed=("amount_aed", lambda x: x[df.loc[x.index, "status"] == "paid"].sum()))
                   .reset_index())
        trend.columns = ["Month", "Invoices", "Revenue (AED)", "Collected (AED)"]
        trend["Revenue (AED)"] = trend["Revenue (AED)"].map("AED {:,.0f}".format)
        trend["Collected (AED)"] = trend["Collected (AED)"].map("AED {:,.0f}".format)
        return trend.to_markdown(index=False)

    elif report_type == "vat_summary":
        vat = (df.groupby("status")
                 .agg(vat_collected=("vat_aed", "sum"),
                      invoice_count=("invoice_ref", "count"))
                 .reset_index())
        vat.columns = ["Status", "VAT (AED)", "Invoices"]
        vat["VAT (AED)"] = vat["VAT (AED)"].map("AED {:,.0f}".format)
        total_vat = df["vat_aed"].sum()
        return vat.to_markdown(index=False) + f"\n\n**Total VAT across all invoices: AED {total_vat:,.0f}**"

    elif report_type == "full_overview":
        summary = {
            "total_revenue_aed": float(df["amount_aed"].sum()),
            "total_vat_aed": float(df["vat_aed"].sum()),
            "collected_aed": float(df[df["status"] == "paid"]["amount_aed"].sum()),
            "outstanding_aed": float(df[df["status"].isin(["unpaid", "overdue"])]["amount_aed"].sum()),
            "overdue_aed": float(df[df["status"] == "overdue"]["amount_aed"].sum()),
            "collection_rate_pct": round(df[df["status"] == "paid"]["amount_aed"].sum() / df["amount_aed"].sum() * 100, 1),
            "invoice_count": len(df),
        }
        overview = pd.DataFrame([
            {"Metric": "Total Revenue", "Value": f"AED {summary['total_revenue_aed']:,.0f}"},
            {"Metric": "VAT Collected", "Value": f"AED {summary['total_vat_aed']:,.0f}"},
            {"Metric": "Cash Collected", "Value": f"AED {summary['collected_aed']:,.0f}"},
            {"Metric": "Outstanding Balance", "Value": f"AED {summary['outstanding_aed']:,.0f}"},
            {"Metric": "Overdue (Action Needed)", "Value": f"AED {summary['overdue_aed']:,.0f}"},
            {"Metric": "Collection Rate", "Value": f"{summary['collection_rate_pct']}%"},
            {"Metric": "Total Invoices", "Value": str(summary["invoice_count"])},
        ])
        return overview.to_markdown(index=False)

    return json.dumps({"error": f"Unknown report_type: {report_type}"})


TOOL_MAP = {
    "get_invoices": get_invoices,
    "get_revenue_summary": get_revenue_summary,
    "get_customer_balance": get_customer_balance,
    "pandas_financial_report": pandas_financial_report,
}

SYSTEM = """You are an AI assistant for AMT's finance team. AMT operates across multiple jurisdictions:
- UAE: 5% VAT | Saudi Arabia: 15% VAT | Egypt: 14% VAT
- Purchases in USD/EUR/JPY, sells in AED/SAR/EGP
- TODAY'S DATE: 2026-05-24. Always use this as the reference for "this month", "this year", "current period".

You have live access to AMT's invoicing and payment data, and you can run Pandas-powered financial analysis.

TOOL SELECTION RULES:
- "this month" / "May 2026" / "revenue summary" → get_revenue_summary(from_date="2026-05-01", to_date="2026-05-31")
- "this year" / "2026 revenue" → get_revenue_summary(from_date="2026-01-01", to_date="2026-12-31")
- "collected vs outstanding" / "paid vs unpaid" → get_revenue_summary for the period, then also get_invoices(status="unpaid")
- aging / payment rate / trends / top debtors → pandas_financial_report
- specific invoice lookup → get_invoices
- specific customer → get_customer_balance

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

        trace.add_tokens(response.usage)
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
                "content": json.dumps(result) if not isinstance(result, str) else result
            })
