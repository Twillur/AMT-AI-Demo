import os, json
from openai import OpenAI
from datetime import datetime
from .db_utils import query, execute

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TOOLS = [
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
    customer = query("SELECT id FROM customers WHERE name LIKE ? LIMIT 1", (f"%{customer_name}%",))
    product = query("SELECT id FROM products WHERE model LIKE ? LIMIT 1", (f"%{product_model}%",))

    if not customer:
        cust_id = execute("INSERT INTO customers (name, account_type) VALUES (?, 'retail')", (customer_name,))
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

    return {"ticket_ref": ticket_ref, "status": "created", "customer": customer_name,
            "product": product_model, "received_date": today}

def update_ticket_status(ticket_ref: str, new_status: str, notes: str = None) -> dict:
    sql = "UPDATE service_tickets SET status = ?"
    params = [new_status]
    if notes:
        sql += ", notes = ?"
        params.append(notes)
    sql += " WHERE ticket_ref = ?"
    params.append(ticket_ref)
    execute(sql, tuple(params))
    return {"ticket_ref": ticket_ref, "new_status": new_status, "updated": True}

TOOL_MAP = {
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
