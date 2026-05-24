import os, json
from openai import OpenAI
from .db_utils import query
from . import trace
from .vector_store import lc_semantic_search

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "semantic_catalog_search",
            "description": "AI-powered semantic search over AMT's product catalog. Use to find products by type or use case when checking what's in transit or low stock.",
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
            "name": "get_shipments",
            "description": "Get inbound shipment status from suppliers. Filter by status, supplier name, or overdue. Use overdue_only=true for delayed/late delivery questions. Use supplier to find shipments from a specific supplier like 'DJI', 'Sony', 'Zeiss'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by: ordered/in_transit/customs/delivered/delayed. Leave empty for all."},
                    "supplier": {"type": "string", "description": "Filter by supplier name, e.g. 'DJI', 'Sony', 'Profoto', 'Zeiss'"},
                    "overdue_only": {"type": "boolean", "description": "If true, return only shipments where ETA has passed but not yet delivered — catches late deliveries even if not marked 'delayed'"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_purchase_orders",
            "description": "Get open or recent purchase orders sent to suppliers. Shows PO status, supplier, total value, and expected delivery.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by: open/partial/received/cancelled. Leave empty for all."},
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
            "description": "Get sales orders that are confirmed but not yet shipped or delivered.",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]


def get_shipments(status: str = None, supplier: str = None, overdue_only: bool = False) -> list:
    label = f"Shipments query — status: {status or 'all'}" + (f", supplier: {supplier}" if supplier else "") + (" [overdue]" if overdue_only else "")
    trace.log("get_shipments", "SQLite", label)
    sql = """
        SELECT s.shipment_ref, s.supplier, s.origin_country,
               s.shipped_date, s.eta, s.status,
               s.carrier, s.tracking_number, s.notes,
               po.po_ref, po.total_usd,
               CASE WHEN s.eta < date('now') AND s.status NOT IN ('delivered','cancelled')
                    THEN 'YES' ELSE 'NO' END AS is_overdue
        FROM shipments s
        LEFT JOIN purchase_orders po ON po.id = s.order_id
        WHERE 1=1
    """
    params = []
    if overdue_only:
        sql += " AND s.eta < date('now') AND s.status NOT IN ('delivered','cancelled')"
    elif status:
        sql += " AND s.status = ?"
        params.append(status)
    if supplier:
        sql += " AND s.supplier LIKE ?"
        params.append(f"%{supplier}%")
    sql += " ORDER BY s.eta"
    return query(sql, tuple(params))


def get_purchase_orders(status: str = None, supplier: str = None) -> list:
    trace.log("get_purchase_orders", "SQLite", f"PO query — status: {status or 'all'}")
    sql = """
        SELECT po.po_ref, sup.name AS supplier, sup.country,
               po.order_date, po.expected_delivery, po.status,
               po.total_usd, po.currency, po.notes,
               COUNT(poi.id) AS line_items,
               SUM(poi.qty_ordered) AS total_units
        FROM purchase_orders po
        JOIN suppliers sup ON sup.id = po.supplier_id
        LEFT JOIN purchase_order_items poi ON poi.po_id = po.id
        WHERE 1=1
    """
    params = []
    if status:
        sql += " AND po.status = ?"
        params.append(status)
    if supplier:
        sql += " AND sup.name LIKE ?"
        params.append(f"%{supplier}%")
    sql += " GROUP BY po.id ORDER BY po.order_date DESC"
    return query(sql, tuple(params))


def get_inventory_levels(category: str = None, low_stock_only: bool = False) -> list:
    trace.log("get_inventory_levels", "SQLite", f"Inventory — category: {category or 'all'}, low_stock: {low_stock_only}")
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
    trace.log("get_pending_orders", "SQLite", "Pending & confirmed orders")
    return query("""
        SELECT o.order_ref, c.name, c.company, c.country,
               o.order_date, o.status, o.total_aed, o.sales_rep
        FROM orders o JOIN customers c ON c.id = o.customer_id
        WHERE o.status IN ('pending','confirmed')
        ORDER BY o.order_date
    """)


TOOL_MAP = {
    "semantic_catalog_search": lambda query, top_k=5: lc_semantic_search(query, top_k),
    "get_shipments": get_shipments,
    "get_purchase_orders": get_purchase_orders,
    "get_inventory_levels": get_inventory_levels,
    "get_pending_orders": get_pending_orders,
}

SYSTEM = """You are an AI assistant for AMT's distribution and logistics team. AMT ships professional AV equipment across UAE, Saudi Arabia, Egypt, and the wider MENA region from its Jebel Ali warehouse in Dubai.

You have live access to AMT's inventory, shipment tracking, and purchase order status.

TOOL SELECTION RULES:
- "purchase orders" / "open POs" / "supplier orders" → get_purchase_orders (these are supplier POs, NOT customer orders)
- "reorder" / "stock low" / "restock" / "need to order" → get_inventory_levels(low_stock_only=True), then draft a professional reorder email using the supplier name from the product brand
- "delayed" / "late" / "overdue" → get_shipments(overdue_only=True)
- "shipments from [supplier]" → get_shipments(supplier="[supplier]")
- "lighting inventory" / "camera inventory" / "[category] stock" → get_inventory_levels(category="[category]")

When drafting reorder emails: address the actual supplier by name (e.g. "RED Digital Cinema" for RED products), include the specific product SKU and model, and fill in AMT's details. Never use placeholder text like [Supplier Name].

Present shipment and PO data as tables. Flag urgent issues (delays, customs holds, low stock) clearly. Be action-oriented."""


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
                "content": json.dumps(result)
            })
