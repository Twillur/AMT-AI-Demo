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


def get_stock_level(product: str) -> list:
    trace.log("get_stock_level", "SQLite", f"Stock check: '{product}'")
    return query("""
        SELECT p.sku, p.brand, p.model, i.qty_on_hand, i.qty_reserved,
               (i.qty_on_hand - i.qty_reserved) AS qty_available
        FROM products p JOIN inventory i ON i.product_id = p.id
        WHERE p.sku LIKE ? OR p.model LIKE ?
    """, (f"%{product}%", f"%{product}%"))


TOOL_MAP = {
    "semantic_catalog_search": lambda query, top_k=5: lc_semantic_search(query, top_k),
    "search_products": search_products,
    "get_customer_orders": get_customer_orders,
    "get_stock_level": get_stock_level,
}

SYSTEM = """You are an AI sales assistant for Advanced Media Trading (AMT), the largest professional AV equipment distributor in MENA. AMT represents 100+ brands including DJI, Sony Professional, RED, ARRI, Zeiss, Sennheiser, Profoto, Atomos, and Teradek.

You have access to AMT's live product catalog, inventory, and customer order history. Use semantic_catalog_search for broad product discovery, search_products for specific keyword/brand lookups, and get_stock_level to confirm availability.

Your job:
- Build detailed quotes and BOMs for client projects
- Check stock availability before quoting
- Recommend the right products based on budget and use case
- Pull up customer history on request

When building quotes, format as a clean markdown table: | Product | Brand | Model | Unit Price (AED) | Qty | Total (AED) |
Always include a subtotal and 5% VAT line at the bottom. Be concise and professional."""

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
    <span style="color:#888;font-size:12px">Advanced Media Trading LLC &nbsp;|&nbsp; sales@amt.tv &nbsp;|&nbsp; +971 4 XXX XXXX</span></p>
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
