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
            "description": "AI-powered semantic search over AMT's full product catalog. Use this for conceptual queries like 'best camera for broadcast', 'lightweight drone options', 'professional audio kit'. Returns ranked products with descriptions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language product search query"},
                    "top_k": {"type": "integer", "description": "Number of results (default 5, max 10)"}
                },
                "required": ["query"]
            }
        }
    },
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
            "description": "Look up order history for a specific customer by name or company.",
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
            "name": "get_active_orders",
            "description": "Get all active sales orders across all customers. Use when asked for 'active orders', 'confirmed orders', 'pending orders', 'open orders', or any broad order status overview with no specific customer mentioned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string",
                        "description": "Optional status filter: 'pending', 'confirmed', 'shipped', or 'all' (default: 'all' active statuses)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_level",
            "description": "Check current stock levels. Accepts a product SKU, model name, brand name, or category (camera/drone/lens/audio/lighting). Use for questions like 'stock on Sony FX cameras' or 'DJI drone inventory'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {"type": "string", "description": "Product SKU, model name, brand, or category keyword"}
                },
                "required": ["product"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_out_of_stock",
            "description": "Returns all products that are currently out of stock (zero available units). Use for questions like 'which products are out of stock?' or 'what do we not have available?'",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_low_stock",
            "description": "Returns products with stock below a given threshold. Use for 'low stock', 'running low', 'under X units', 'nearly out of stock' questions. Default threshold is 5 units.",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold": {"type": "integer", "description": "Max available units to include (default: 5)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_orders",
            "description": "Get ALL sales orders including delivered and historical ones. Use this for aggregate questions, historical analysis, or filtering by country. Pass status_filter='delivered' to see completed orders only. Pass country to filter by country (e.g. 'Saudi Arabia', 'UAE', 'Egypt').",
            "parameters": {
                "type": "object",
                "properties": {
                    "status_filter": {"type": "string", "description": "Optional: 'pending','confirmed','shipped','delivered','all' (default: all statuses)"},
                    "country": {"type": "string", "description": "Optional: filter orders by customer country, e.g. 'Saudi Arabia', 'UAE', 'Egypt'"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_analytics",
            "description": "Aggregated sales analytics. Use for: 'which customer ordered most', 'which brand sells most', 'average order value', 'top products by sales', 'inactive customers', 'which sales rep has most orders'. Set metric to: 'customers', 'brands', 'products', 'avg_value', 'inactive_customers', 'sales_reps'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "description": "One of: customers, brands, products, avg_value, inactive_customers, sales_reps"},
                    "limit": {"type": "integer", "description": "Number of results (default 10)"}
                },
                "required": ["metric"]
            }
        }
    }
]


def search_products(keyword: str, max_price_aed: float = None) -> list:
    trace.log("search_products", "SQLite", f"Keyword search: '{keyword}'")
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
    trace.log("get_customer_orders", "SQLite", f"Orders for: '{customer_name}'")
    return query("""
        SELECT o.order_ref, c.name, c.company, o.order_date, o.status, o.total_aed, o.sales_rep
        FROM orders o JOIN customers c ON c.id = o.customer_id
        WHERE c.name LIKE ? OR c.company LIKE ?
        ORDER BY o.order_date DESC
    """, (f"%{customer_name}%", f"%{customer_name}%"))


def get_active_orders(status_filter: str = "all") -> list:
    trace.log("get_active_orders", "SQLite", f"Active orders — filter: '{status_filter}'")
    if status_filter in ("pending", "confirmed", "shipped"):
        statuses = (status_filter,)
        placeholders = "?"
    else:
        statuses = ("pending", "confirmed", "shipped")
        placeholders = "?,?,?"
    return query(f"""
        SELECT o.order_ref, c.name AS customer, c.company, c.country,
               o.order_date, o.status, o.total_aed, o.sales_rep
        FROM orders o JOIN customers c ON c.id = o.customer_id
        WHERE o.status IN ({placeholders})
        ORDER BY o.order_date DESC
    """, statuses)


def get_stock_level(product: str) -> list:
    trace.log("get_stock_level", "SQLite", f"Stock check: '{product}'")
    # Search compound phrase AND each individual word (handles "Sony FX", "DJI drone", etc.)
    words = [w for w in product.split() if len(w) > 2]
    all_terms = [product] + words
    seen = set()
    unique_terms = [t for t in all_terms if not (t in seen or seen.add(t))]
    conditions, params = [], []
    for term in unique_terms:
        kw = f"%{term}%"
        conditions.append("(p.sku LIKE ? OR p.model LIKE ? OR p.brand LIKE ? OR p.category LIKE ?)")
        params.extend([kw, kw, kw, kw])
    where = " OR ".join(conditions)
    return query(f"""
        SELECT p.sku, p.brand, p.model, p.category,
               SUM(i.qty_on_hand) AS qty_on_hand,
               SUM(i.qty_reserved) AS qty_reserved,
               SUM(i.qty_on_hand - i.qty_reserved) AS qty_available,
               MAX(i.reorder_point) AS reorder_point
        FROM products p JOIN inventory i ON i.product_id = p.id
        WHERE {where}
        GROUP BY p.id, p.sku, p.brand, p.model, p.category
        ORDER BY p.brand, p.model
    """, tuple(params))


def get_out_of_stock() -> list:
    trace.log("get_out_of_stock", "SQLite", "Products with zero available stock")
    return query("""
        SELECT p.sku, p.brand, p.model, p.category, p.price_aed,
               COALESCE(SUM(i.qty_on_hand - i.qty_reserved), 0) AS qty_available
        FROM products p
        LEFT JOIN inventory i ON i.product_id = p.id
        WHERE p.is_active = 1
        GROUP BY p.id
        HAVING qty_available <= 0
        ORDER BY p.brand, p.model
    """)


def get_low_stock(threshold: int = 5) -> list:
    trace.log("get_low_stock", "SQLite", f"Products with stock <= {threshold} units")
    return query("""
        SELECT p.sku, p.brand, p.model, p.category, p.price_aed,
               COALESCE(SUM(i.qty_on_hand - i.qty_reserved), 0) AS qty_available
        FROM products p
        LEFT JOIN inventory i ON i.product_id = p.id
        WHERE p.is_active = 1
        GROUP BY p.id
        HAVING qty_available > 0 AND qty_available <= ?
        ORDER BY qty_available ASC
    """, (threshold,))


def get_all_orders(status_filter: str = "all", country: str = None) -> list:
    trace.log("get_all_orders", "SQLite", f"All orders — filter: '{status_filter}'" + (f", country: '{country}'" if country else ""))
    conditions, params = [], []
    if status_filter in ("pending", "confirmed", "shipped", "delivered", "cancelled"):
        conditions.append("o.status = ?")
        params.append(status_filter)
    if country:
        conditions.append("c.country LIKE ?")
        params.append(f"%{country}%")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return query(f"""
        SELECT o.order_ref, c.name AS customer, c.company, c.country,
               o.order_date, o.status, o.total_aed, o.sales_rep
        FROM orders o JOIN customers c ON c.id = o.customer_id
        {where}
        ORDER BY o.order_date DESC
    """, tuple(params))


def get_order_analytics(metric: str, limit: int = 10) -> list:
    trace.log("get_order_analytics", "SQLite", f"Analytics: {metric}")
    if metric == "customers":
        return query("""
            SELECT c.name, c.company, c.country,
                   COUNT(o.id) AS total_orders,
                   ROUND(SUM(o.total_aed), 0) AS total_value_aed,
                   ROUND(AVG(o.total_aed), 0) AS avg_order_aed,
                   MAX(o.order_date) AS last_order_date
            FROM orders o JOIN customers c ON c.id = o.customer_id
            GROUP BY c.id ORDER BY total_value_aed DESC LIMIT ?
        """, (limit,))
    if metric == "brands":
        return query("""
            SELECT p.brand,
                   COUNT(oi.id) AS line_items,
                   SUM(oi.qty) AS total_units_sold,
                   ROUND(SUM(oi.qty * oi.unit_price_aed), 0) AS total_value_aed
            FROM order_items oi JOIN products p ON p.id = oi.product_id
            GROUP BY p.brand ORDER BY total_units_sold DESC LIMIT ?
        """, (limit,))
    if metric == "products":
        return query("""
            SELECT p.brand, p.model, p.category,
                   COUNT(oi.id) AS times_ordered,
                   SUM(oi.qty) AS total_units_sold,
                   ROUND(SUM(oi.qty * oi.unit_price_aed), 0) AS total_value_aed
            FROM order_items oi JOIN products p ON p.id = oi.product_id
            GROUP BY p.id ORDER BY total_units_sold DESC LIMIT ?
        """, (limit,))
    if metric == "avg_value":
        return query("""
            SELECT COUNT(*) AS total_orders,
                   ROUND(AVG(total_aed), 0) AS avg_order_value_aed,
                   ROUND(MIN(total_aed), 0) AS min_aed,
                   ROUND(MAX(total_aed), 0) AS max_aed,
                   ROUND(SUM(total_aed), 0) AS total_revenue_aed
            FROM orders
        """)
    if metric == "inactive_customers":
        return query("""
            SELECT c.name, c.company, c.country,
                   MAX(o.order_date) AS last_order_date,
                   COUNT(o.id) AS total_orders_ever
            FROM customers c
            LEFT JOIN orders o ON o.customer_id = c.id
            GROUP BY c.id
            HAVING last_order_date < date('now', '-90 days') OR last_order_date IS NULL
            ORDER BY last_order_date ASC
        """)
    if metric == "sales_reps":
        return query("""
            SELECT o.sales_rep,
                   COUNT(o.id) AS total_orders,
                   ROUND(SUM(o.total_aed), 0) AS total_value_aed,
                   ROUND(AVG(o.total_aed), 0) AS avg_order_aed
            FROM orders o
            WHERE o.sales_rep IS NOT NULL
            GROUP BY o.sales_rep ORDER BY total_orders DESC LIMIT ?
        """, (limit,))
    return []


TOOL_MAP = {
    "semantic_catalog_search": lambda query, top_k=5: lc_semantic_search(query, top_k),
    "search_products": search_products,
    "get_customer_orders": get_customer_orders,
    "get_active_orders": get_active_orders,
    "get_stock_level": get_stock_level,
    "get_out_of_stock": get_out_of_stock,
    "get_low_stock": get_low_stock,
    "get_all_orders": get_all_orders,
    "get_order_analytics": get_order_analytics,
}

SYSTEM = """You are an AI sales assistant for Advanced Media Trading (AMT), the largest professional AV equipment distributor in MENA. AMT represents brands including DJI, Sony, RED, Zeiss, Sennheiser, Profoto, Atomos, and Blackmagic.

BRAND NAMES IN DATABASE: Use the short form — "Sony" (not "Sony Professional"), "DJI" (not "DJI Technologies"), "RED" (not "RED Digital Cinema"), "Blackmagic" (not "Blackmagic Design"). Always search with the short brand name.

TOOL SELECTION RULES:
- "out of stock" / "not available" / "zero stock" → get_out_of_stock
- "low stock" / "running low" / "under X units" / "nearly out" → get_low_stock(threshold=X)
- "which customer ordered most" / "top customers" / "order count" → get_order_analytics(metric="customers")
- "which brand sells most" / "best-selling brand" / "top brand by sales" → get_order_analytics(metric="brands")
- "top selling products" / "best selling products" / "most ordered products" → get_order_analytics(metric="products")
- "average order value" / "avg order" → get_order_analytics(metric="avg_value")
- "haven't ordered" / "inactive customers" / "no orders recently" → get_order_analytics(metric="inactive_customers")
- "which sales rep" / "top sales rep" / "rep performance" → get_order_analytics(metric="sales_reps")
- "orders from [country]" / "orders in UAE/Saudi/Egypt" → get_all_orders(country="[country]")
- "all orders" / "order history" / "total orders" including delivered → get_all_orders
- Active/current orders (pending/confirmed/shipped) → get_active_orders
- Specific customer's order history → get_customer_orders
- Stock levels by brand/model/category → get_stock_level

QUOTE RULES — CRITICAL:
- When building a quote or BOM, ONLY include products returned by semantic_catalog_search. Never invent, suggest, or mention products not found in the search results.
- If the catalog search does not return enough items to complete a kit, say which products were found and tell the customer AMT does not currently carry the remaining items.
- Run semantic_catalog_search multiple times with different terms (e.g. "cinema camera", "studio lighting", "audio recorder") to find all relevant products before writing the quote.
- Format as a clean markdown table: | Product | Brand | Model | Unit Price (AED) | Qty | Total (AED) |
- Always include a subtotal and 5% VAT line at the bottom. Be concise and professional."""

RFQ_SYSTEM = """You are an AI sales assistant for Advanced Media Trading (AMT), the largest professional AV equipment distributor in MENA.

A customer has sent an email requesting a quote. Read their requirements carefully, then:
1. Use semantic_catalog_search to find matching products for each requirement
2. Use get_stock_level to verify availability
3. Select the best-fit products staying within any stated budget
4. Build a complete itemized quote

Return ONLY a JSON object with exactly these fields:
{
  "greeting": "Dear [customer name or Sir/Madam],",
  "intro": "one sentence thanking them and summarising what you're quoting",
  "line_items": [
    {"product": "...", "brand": "...", "model": "...", "qty": 1, "unit_price_aed": 0.0, "in_stock": true}
  ],
  "notes": "optional short note on lead times, alternatives, or stock status",
  "sales_rep": "AMT Sales Team"
}
Do not include any text outside the JSON."""


def _build_quote_html(from_name: str, data: dict) -> str:
    rows = ""
    subtotal = 0.0
    for item in data.get("line_items", []):
        total = item["qty"] * item["unit_price_aed"]
        subtotal += total
        stock_badge = (
            '<span style="color:#155724;font-weight:700">In Stock</span>'
            if item.get("in_stock") else
            '<span style="color:#721c24;font-weight:700">Check Lead Time</span>'
        )
        rows += f"""<tr>
          <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0">{item['brand']} {item['model']}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0;text-align:center">{item['qty']}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0;text-align:right">AED {item['unit_price_aed']:,.0f}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0;text-align:right">AED {total:,.0f}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0;text-align:center">{stock_badge}</td>
        </tr>"""
    vat = subtotal * 0.05
    grand_total = subtotal + vat
    notes_html = f'<p style="margin:20px 0 0;font-size:14px;color:#555"><strong>Note:</strong> {data["notes"]}</p>' if data.get("notes") else ""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;max-width:700px;margin:0 auto;padding:20px">
  <div style="background:#0d1b2a;padding:20px 28px;border-radius:8px 8px 0 0">
    <div style="color:#e8b94f;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase">Advanced Media Trading LLC</div>
    <div style="color:#fff;font-size:18px;font-weight:700;margin-top:4px">Sales Quotation</div>
  </div>
  <div style="background:#fff;border:1px solid #e0e0e0;border-top:none;padding:28px;border-radius:0 0 8px 8px">
    <p style="margin:0 0 16px;font-size:15px">{data.get('greeting', f'Dear {from_name},')}</p>
    <p style="margin:0 0 20px;font-size:14px;color:#555">{data.get('intro', 'Please find your quotation below.')}</p>
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <thead>
        <tr style="background:#f8f9fa">
          <th style="padding:10px 14px;text-align:left;font-weight:700;color:#555;border-bottom:2px solid #e8b94f">Product</th>
          <th style="padding:10px 14px;text-align:center;font-weight:700;color:#555;border-bottom:2px solid #e8b94f">Qty</th>
          <th style="padding:10px 14px;text-align:right;font-weight:700;color:#555;border-bottom:2px solid #e8b94f">Unit Price</th>
          <th style="padding:10px 14px;text-align:right;font-weight:700;color:#555;border-bottom:2px solid #e8b94f">Total</th>
          <th style="padding:10px 14px;text-align:center;font-weight:700;color:#555;border-bottom:2px solid #e8b94f">Availability</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
      <tfoot>
        <tr><td colspan="3" style="padding:10px 14px;text-align:right;font-weight:600">Subtotal</td>
            <td style="padding:10px 14px;text-align:right">AED {subtotal:,.0f}</td><td></td></tr>
        <tr><td colspan="3" style="padding:10px 14px;text-align:right;font-weight:600;color:#888">VAT (5%)</td>
            <td style="padding:10px 14px;text-align:right;color:#888">AED {vat:,.0f}</td><td></td></tr>
        <tr style="background:#0d1b2a">
          <td colspan="3" style="padding:12px 14px;text-align:right;font-weight:700;color:#e8b94f">TOTAL</td>
          <td style="padding:12px 14px;text-align:right;font-weight:700;color:#fff">AED {grand_total:,.0f}</td><td></td>
        </tr>
      </tfoot>
    </table>
    {notes_html}
    <p style="margin:28px 0 0;font-size:14px">Kind regards,<br><strong>{data.get('sales_rep', 'AMT Sales Team')}</strong><br>
    <span style="color:#888;font-size:12px">Advanced Media Trading LLC &nbsp;|&nbsp; sales@amt.tv &nbsp;|&nbsp; +971 4 447 6000</span></p>
  </div>
  <div style="text-align:center;padding:12px;font-size:11px;color:#aaa">
    This quotation is valid for 14 days. Prices are in AED and subject to VAT.
  </div>
</body></html>"""


def run_rfq(from_email: str, from_name: str, subject: str, body: str) -> dict:
    """Process an inbound RFQ email and return a structured quote + HTML."""
    trace.log("rfq_received", "n8n", f"Inbound RFQ from {from_name} <{from_email}>")
    prompt = f"Subject: {subject}\n\n{body}"
    messages = [{"role": "system", "content": RFQ_SYSTEM}, {"role": "user", "content": prompt}]

    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=2000
        )
        msg = response.choices[0].message
        if not msg.tool_calls:
            break
        messages.append(msg)
        for tc in msg.tool_calls:
            fn = TOOL_MAP[tc.function.name]
            result = fn(**json.loads(tc.function.arguments))
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result)
            })

    raw = msg.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    quote_data = json.loads(raw)
    html = _build_quote_html(from_name, quote_data)
    trace.log("rfq_quote_built", "GPT-4o", f"{len(quote_data.get('line_items', []))} line items | AED {sum(i['qty']*i['unit_price_aed'] for i in quote_data.get('line_items',[])):.0f}")
    return {"quote": quote_data, "html_quote": html}


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
