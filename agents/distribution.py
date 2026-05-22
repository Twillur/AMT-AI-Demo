import os, json
from openai import OpenAI
from .db_utils import query

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_shipments",
            "description": "Get current shipment status. Filter by status or supplier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by: ordered/in_transit/customs/delivered/delayed. Leave empty for all."},
                    "supplier": {"type": "string", "description": "Filter by supplier name. Leave empty for all."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory_levels",
            "description": "Get current stock levels across all products or filtered by category/brand.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by: camera/drone/audio/lighting/gimbal/storage/lens"},
                    "low_stock_only": {"type": "boolean", "description": "If true, only show items with qty_available <= 3"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pending_orders",
            "description": "Get orders that are pending or confirmed but not yet shipped.",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

def get_shipments(status: str = None, supplier: str = None) -> list:
    sql = """
        SELECT s.shipment_ref, s.supplier, s.origin_country, s.eta, s.status,
               s.carrier, s.tracking_number, s.notes,
               o.order_ref, c.name AS customer, c.company
        FROM shipments s
        JOIN orders o ON o.id = s.order_id
        JOIN customers c ON c.id = o.customer_id
        WHERE 1=1
    """
    params = []
    if status:
        sql += " AND s.status = ?"
        params.append(status)
    if supplier:
        sql += " AND s.supplier LIKE ?"
        params.append(f"%{supplier}%")
    sql += " ORDER BY s.eta"
    return query(sql, tuple(params))

def get_inventory_levels(category: str = None, low_stock_only: bool = False) -> list:
    sql = """
        SELECT p.sku, p.brand, p.model, p.category,
               i.qty_on_hand, i.qty_reserved,
               (i.qty_on_hand - i.qty_reserved) AS qty_available
        FROM products p JOIN inventory i ON i.product_id = p.id
        WHERE 1=1
    """
    params = []
    if category:
        sql += " AND p.category = ?"
        params.append(category)
    if low_stock_only:
        sql += " AND (i.qty_on_hand - i.qty_reserved) <= 3"
    sql += " ORDER BY qty_available ASC"
    return query(sql, tuple(params))

def get_pending_orders() -> list:
    return query("""
        SELECT o.order_ref, c.name, c.company, c.country,
               o.order_date, o.status, o.total_aed, o.sales_rep
        FROM orders o JOIN customers c ON c.id = o.customer_id
        WHERE o.status IN ('pending','confirmed')
        ORDER BY o.order_date
    """)

TOOL_MAP = {
    "get_shipments": get_shipments,
    "get_inventory_levels": get_inventory_levels,
    "get_pending_orders": get_pending_orders,
}

SYSTEM = """You are an AI assistant for AMT's distribution and logistics team. AMT ships professional AV equipment across UAE, Saudi Arabia, Egypt, and the wider MENA region from its Al Quoz warehouse in Dubai.

You have live access to AMT's inventory, shipment tracking, and order status.

Your job:
- Track inbound shipments and flag delays or customs holds
- Monitor stock levels and highlight low inventory
- Show which pending orders need follow-up
- Summarize logistics status clearly for the team

Present shipment data as tables. Flag urgent issues (delays, customs holds, low stock) clearly. Be action-oriented."""


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
