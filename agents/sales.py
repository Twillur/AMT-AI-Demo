import os, json
from openai import OpenAI
from .db_utils import query

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search AMT's product catalog by brand, category, or keyword. Returns matching products with price and stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Brand name, model name, or category (camera/lens/drone/audio/lighting/gimbal/storage)"},
                    "max_price_aed": {"type": "number", "description": "Optional maximum price filter in AED"}
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_orders",
            "description": "Look up order history for a customer by name or company.",
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
            "name": "get_stock_level",
            "description": "Check current stock level for a specific product by SKU or model name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {"type": "string", "description": "Product SKU or model name"}
                },
                "required": ["product"]
            }
        }
    }
]

def search_products(keyword: str, max_price_aed: float = None) -> list:
    sql = """
        SELECT p.sku, p.brand, p.model, p.category, p.price_aed, i.qty_on_hand
        FROM products p
        LEFT JOIN inventory i ON i.product_id = p.id
        WHERE (p.brand LIKE ? OR p.model LIKE ? OR p.category LIKE ? OR p.description LIKE ?)
    """
    kw = f"%{keyword}%"
    params = [kw, kw, kw, kw]
    if max_price_aed:
        sql += " AND p.price_aed <= ?"
        params.append(max_price_aed)
    return query(sql, tuple(params))

def get_customer_orders(customer_name: str) -> list:
    return query("""
        SELECT o.order_ref, c.name, c.company, o.order_date, o.status, o.total_aed, o.sales_rep
        FROM orders o JOIN customers c ON c.id = o.customer_id
        WHERE c.name LIKE ? OR c.company LIKE ?
        ORDER BY o.order_date DESC
    """, (f"%{customer_name}%", f"%{customer_name}%"))

def get_stock_level(product: str) -> list:
    return query("""
        SELECT p.sku, p.brand, p.model, i.qty_on_hand, i.qty_reserved,
               (i.qty_on_hand - i.qty_reserved) AS qty_available
        FROM products p JOIN inventory i ON i.product_id = p.id
        WHERE p.sku LIKE ? OR p.model LIKE ?
    """, (f"%{product}%", f"%{product}%"))

TOOL_MAP = {
    "search_products": search_products,
    "get_customer_orders": get_customer_orders,
    "get_stock_level": get_stock_level,
}

SYSTEM = """You are an AI sales assistant for Advanced Media Trading (AMT), the largest professional AV equipment distributor in MENA. AMT represents 100+ brands including DJI, Sony Professional, RED, ARRI, Zeiss, Sennheiser, Profoto, Atomos, and Teradek.

You have access to AMT's live product catalog, inventory, and customer order history.

Your job:
- Build detailed quotes and BOMs for client projects
- Check stock availability before quoting
- Recommend the right products based on budget and use case
- Pull up customer history on request

When building quotes, format as a clean markdown table: | Product | Brand | Model | Unit Price (AED) | Qty | Total (AED) |
Always include a subtotal and 5% VAT line at the bottom. Be concise and professional."""


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
