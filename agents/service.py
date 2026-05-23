import os, json, threading
import requests
from openai import OpenAI
from datetime import datetime
from .db_utils import query, execute
from . import trace
from .vector_store import lc_semantic_search

N8N_TICKET_WEBHOOK  = "http://localhost:5678/webhook/DhKyDc1sZdnNTasL/webhook/amt-new-ticket"
N8N_UPDATE_WEBHOOK  = "http://localhost:5678/webhook/e959LqnzZkMIUy7X/webhook/amt-ticket-update"


def _build_email_html(p: dict) -> str:
    warranty_label = "In Warranty" if p["warranty_status"] == "in_warranty" else "Out of Warranty"
    warranty_color = "#155724" if p["warranty_status"] == "in_warranty" else "#721c24"
    warranty_bg    = "#d4edda"  if p["warranty_status"] == "in_warranty" else "#f8d7da"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;background:#f0f2f5;color:#333}}
.wrap{{max-width:600px;margin:30px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.1)}}
.hdr{{background:#0d1b2a;padding:22px 28px}}
.hdr-title{{color:#e8b94f;font-size:13px;font-weight:700;letter-spacing:2px;text-transform:uppercase}}
.body{{padding:28px}}
.heading{{font-size:20px;font-weight:700;color:#0d1b2a;margin-bottom:6px}}
.sub{{color:#666;font-size:14px;margin-top:6px}}
table{{width:100%;border-collapse:collapse;margin-top:18px;font-size:14px}}
td{{padding:11px 14px;border-bottom:1px solid #f0f0f0}}
td:first-child{{color:#888;font-weight:600;width:140px}}
.badge{{display:inline-block;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:700}}
.ftr{{background:#f8f9fa;padding:16px 28px;font-size:12px;color:#aaa;border-top:3px solid #e8b94f;text-align:center}}
</style></head>
<body><div class="wrap">
  <div class="hdr"><div class="hdr-title">Advanced Media Trading &mdash; Service Center</div></div>
  <div class="body">
    <div class="heading">New Repair Ticket Created</div>
    <div class="sub">A repair request has been logged and is now open for processing.</div>
    <table>
      <tr><td>Ticket Ref</td><td><strong>{p['ticket_ref']}</strong></td></tr>
      <tr><td>Customer</td><td>{p['customer']}</td></tr>
      <tr><td>Product</td><td>{p['product']}</td></tr>
      <tr><td>Serial No.</td><td>{p['serial_number']}</td></tr>
      <tr><td>Issue</td><td>{p['issue']}</td></tr>
      <tr><td>Warranty</td><td><span class="badge" style="background:{warranty_bg};color:{warranty_color}">{warranty_label}</span></td></tr>
      <tr><td>Received</td><td>{p['received_date']}</td></tr>
      <tr><td>Status</td><td><span class="badge" style="background:#d4edda;color:#155724">Open</span></td></tr>
    </table>
  </div>
  <div class="ftr">AMT Service Center &mdash; Al Quoz Industrial 4, Dubai &nbsp;|&nbsp; service@amt.tv</div>
</div></body></html>"""


def _fire_n8n_notification(payload: dict):
    try:
        payload["subject"] = f"[AMT Service] New Repair Ticket — {payload['ticket_ref']} | {payload['product']}"
        payload["html_body"] = _build_email_html(payload)
        requests.post(N8N_TICKET_WEBHOOK, json=payload, timeout=10)
    except Exception:
        pass

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "semantic_catalog_search",
            "description": "AI-powered semantic search over AMT's product catalog. Use to identify products when customer describes a device without the exact model name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_service_tickets",
            "description": "Get open or recent service/repair tickets, optionally filtered by status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by: open/diagnosed/in_repair/awaiting_parts/ready/closed. Leave empty for all open tickets."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticket_by_customer",
            "description": "Look up service tickets for a specific customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer name or company"}
                },
                "required": ["customer_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_service_ticket",
            "description": "Create a new service/repair ticket for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "product_model": {"type": "string", "description": "Product model name e.g. 'Mavic 3 Pro'"},
                    "serial_number": {"type": "string"},
                    "issue_description": {"type": "string"},
                    "warranty_status": {"type": "string", "description": "in_warranty or out_of_warranty"}
                },
                "required": ["customer_name", "product_model", "issue_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_ticket_status",
            "description": "Update the status of an existing service ticket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_ref": {"type": "string", "description": "e.g. SVC-2026-001"},
                    "new_status": {"type": "string", "description": "open/diagnosed/in_repair/awaiting_parts/ready/closed"},
                    "notes": {"type": "string"}
                },
                "required": ["ticket_ref", "new_status"]
            }
        }
    }
]


def get_service_tickets(status: str = None) -> list:
    trace.log("get_service_tickets", "SQLite", f"Tickets — status: {status or 'all open'}")
    sql = """
        SELECT t.ticket_ref, c.name, c.company, p.brand, p.model,
               t.serial_number, t.issue_description, t.status,
               t.warranty_status, t.received_date, t.estimated_completion,
               t.technician, t.repair_cost_aed
        FROM service_tickets t
        JOIN customers c ON c.id = t.customer_id
        JOIN products p ON p.id = t.product_id
        WHERE 1=1
    """
    params = []
    if status:
        sql += " AND t.status = ?"
        params.append(status)
    else:
        sql += " AND t.status != 'closed'"
    sql += " ORDER BY t.received_date"
    return query(sql, tuple(params))


def get_ticket_by_customer(customer_name: str) -> list:
    trace.log("get_ticket_by_customer", "SQLite", f"Tickets for: '{customer_name}'")
    return query("""
        SELECT t.ticket_ref, c.name, c.company, p.brand, p.model,
               t.issue_description, t.status, t.warranty_status,
               t.received_date, t.estimated_completion, t.repair_cost_aed
        FROM service_tickets t
        JOIN customers c ON c.id = t.customer_id
        JOIN products p ON p.id = t.product_id
        WHERE c.name LIKE ? OR c.company LIKE ?
        ORDER BY t.received_date DESC
    """, (f"%{customer_name}%", f"%{customer_name}%"))


def create_service_ticket(customer_name: str, product_model: str,
                          issue_description: str, serial_number: str = None,
                          warranty_status: str = "in_warranty") -> dict:
    trace.log("create_service_ticket", "SQLite", f"New ticket: {customer_name} — {product_model}")
    customer = query("SELECT id FROM customers WHERE name LIKE ? LIMIT 1", (f"%{customer_name}%",))
    product = None
    for kw in product_model.split():
        if len(kw) >= 3:
            product = query("SELECT id FROM products WHERE model LIKE ? LIMIT 1", (f"%{kw}%",))
            if product:
                break

    if not customer:
        cust_count = query("SELECT COUNT(*) AS cnt FROM customers")[0]["cnt"] + 1
        cust_code = f"CUST-WALK-{cust_count:03d}"
        cust_id = execute(
            "INSERT INTO customers (customer_code, name, account_type, country) VALUES (?, ?, 'retail', 'UAE')",
            (cust_code, customer_name)
        )
    else:
        cust_id = customer[0]["id"]

    if not product:
        return {"error": f"Product '{product_model}' not found in catalog"}

    prod_id = product[0]["id"]
    existing = query("SELECT COUNT(*) AS cnt FROM service_tickets", ())
    count = existing[0]["cnt"] + 1
    ticket_ref = f"SVC-2026-{count:03d}"
    today = datetime.now().strftime("%Y-%m-%d")

    execute("""
        INSERT INTO service_tickets
        (ticket_ref, customer_id, product_id, serial_number, issue_description,
         status, warranty_status, received_date)
        VALUES (?,?,?,?,?,'open',?,?)
    """, (ticket_ref, cust_id, prod_id, serial_number, issue_description, warranty_status, today))

    payload = {
        "ticket_ref": ticket_ref,
        "customer": customer_name,
        "product": product_model,
        "serial_number": serial_number or "Not provided",
        "issue": issue_description,
        "warranty_status": warranty_status,
        "received_date": today,
    }
    threading.Thread(target=_fire_n8n_notification, args=(payload,), daemon=True).start()
    trace.log("n8n_webhook", "n8n", f"Ticket notification fired → n8n workflow")

    return {"ticket_ref": ticket_ref, "status": "created", "customer": customer_name,
            "product": product_model, "received_date": today}


def update_ticket_status(ticket_ref: str, new_status: str, notes: str = None) -> dict:
    trace.log("update_ticket_status", "SQLite", f"Update {ticket_ref} → {new_status}")
    sql = "UPDATE service_tickets SET status = ?"
    params = [new_status]
    if notes:
        sql += ", notes = ?"
        params.append(notes)
    sql += " WHERE ticket_ref = ?"
    params.append(ticket_ref)
    execute(sql, tuple(params))

    if new_status in ("diagnosed", "in_repair", "awaiting_parts", "ready", "closed"):
        ticket = query("""
            SELECT t.ticket_ref, c.name AS customer, p.brand, p.model
            FROM service_tickets t
            JOIN customers c ON c.id = t.customer_id
            JOIN products p ON p.id = t.product_id
            WHERE t.ticket_ref = ?
        """, (ticket_ref,))
        if ticket:
            from .reports import ticket_update_html
            t = ticket[0]
            subject, html = ticket_update_html(
                ticket_ref, t["customer"],
                f"{t['brand']} {t['model']}", new_status, notes or ""
            )
            payload = {"subject": subject, "html_body": html, "ticket_ref": ticket_ref, "new_status": new_status}
            threading.Thread(target=lambda: requests.post(N8N_UPDATE_WEBHOOK, json=payload, timeout=10), daemon=True).start()
            trace.log("n8n_update_webhook", "n8n", f"Customer update email fired → {new_status}")

    return {"ticket_ref": ticket_ref, "new_status": new_status, "updated": True}


TOOL_MAP = {
    "semantic_catalog_search": lambda query, top_k=5: lc_semantic_search(query, top_k),
    "get_service_tickets": get_service_tickets,
    "get_ticket_by_customer": get_ticket_by_customer,
    "create_service_ticket": create_service_ticket,
    "update_ticket_status": update_ticket_status,
}

SYSTEM = """You are an AI assistant for AMT's service and after-sales department. AMT is an authorized service center for DJI, Sony Professional, Profoto, Manfrotto, Hasselblad, Atomos, and other brands.

You have live access to the service ticketing system. You can view, create, and update repair tickets.

Your job:
- Show open service tickets and their status
- Log new repair requests
- Update ticket statuses as work progresses
- Draft professional, empathetic customer update emails

For customer emails always include: issue summary, current status, next steps, estimated completion. Sign off as "AMT Service Team"."""


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
