from . import sales, distribution, finance, service

DOMAINS = [
    {
        "id": "sales",
        "name": "Sales",
        "color": "#3b7eff",
        "icon": "📊",
        "description": (
            "Revenue, quotes, product catalog, and customer order history. "
            "Use for questions about building equipment quotes, checking stock availability, "
            "pulling customer order history, comparing products, and semantic product discovery "
            "across AMT's full brand portfolio."
        ),
        "tools": sales.TOOLS,
        "tables": [
            {"name": "products",   "type": "Table", "description": "42 products — brand, model, SKU, price, HS code, warranty period"},
            {"name": "inventory",  "type": "Table", "description": "Stock levels per product per warehouse — qty on hand, reserved, reorder point"},
            {"name": "orders",     "type": "Table", "description": "Sales orders — status, total AED, sales rep, customer"},
            {"name": "customers",  "type": "Table", "description": "15 customers — MBC, ADNOC, SBA, Dubai Film Commission, OSN and more"},
            {"name": "ChromaDB",   "type": "Vector Store", "description": "39-product semantic embeddings — LlamaIndex + OpenAI text-embedding-3-small"},
        ],
    },
    {
        "id": "distribution",
        "name": "Distribution",
        "color": "#10d97a",
        "icon": "🚚",
        "description": (
            "Inbound logistics, warehouse stock, and procurement tracking. "
            "Use for questions about shipment status and delays, customs-held cargo, "
            "purchase order fulfilment, low stock alerts, and supplier delivery timelines."
        ),
        "tools": distribution.TOOLS,
        "tables": [
            {"name": "shipments",             "type": "Table", "description": "Inbound shipments — ETA, carrier, tracking, customs status"},
            {"name": "purchase_orders",        "type": "Table", "description": "POs raised with suppliers — status, value USD, expected delivery"},
            {"name": "purchase_order_items",   "type": "Table", "description": "Line items per PO — product, qty ordered, qty received"},
            {"name": "suppliers",              "type": "Table", "description": "20 suppliers — DJI, Sony, RED, Profoto, Sennheiser and more"},
            {"name": "inventory",              "type": "Table", "description": "Live stock levels — available qty, reorder thresholds"},
        ],
    },
    {
        "id": "finance",
        "name": "Finance",
        "color": "#9d5eff",
        "icon": "💰",
        "description": (
            "Invoices, receivables, VAT, and revenue analytics. "
            "Use for questions about overdue invoices, customer outstanding balances, "
            "aging reports, collection rates, branch revenue comparison, and "
            "VAT calculations across UAE (5%), KSA (15%), and Egypt (14%)."
        ),
        "tools": finance.TOOLS,
        "tables": [
            {"name": "invoices",   "type": "Table",  "description": "12 invoices — amount AED, VAT, status (paid/unpaid/overdue), due date"},
            {"name": "customers",  "type": "Table",  "description": "Customer master — country, account type, credit terms"},
            {"name": "orders",     "type": "Table",  "description": "Sales orders linked to invoices for revenue aggregation"},
            {"name": "Pandas",     "type": "Engine", "description": "In-memory DataFrame analysis — aging buckets, top debtors, collection rate, monthly trends"},
        ],
    },
    {
        "id": "service",
        "name": "Service",
        "color": "#ff7a2f",
        "icon": "🔧",
        "description": (
            "After-sales repair ticketing, warranty management, and customer communications. "
            "Use for questions about open repair tickets, logging new service requests, "
            "updating ticket status, drafting customer update emails, and warranty eligibility checks."
        ),
        "tools": service.TOOLS,
        "tables": [
            {"name": "service_tickets", "type": "Table",      "description": "8 repair tickets — status, warranty, technician, received date, repair cost"},
            {"name": "customers",       "type": "Table",      "description": "Customer records linked to tickets"},
            {"name": "products",        "type": "Table",      "description": "Product catalog for device identification"},
            {"name": "ChromaDB",        "type": "Vector Store","description": "Semantic product search for identifying devices from natural language descriptions"},
            {"name": "n8n Webhooks",    "type": "Automation", "description": "Fires branded email notifications on ticket create and status update via Gmail SMTP"},
        ],
    },
]


def get_domains_payload() -> list:
    result = []
    for d in DOMAINS:
        tools_out = []
        for t in d["tools"]:
            fn = t["function"]
            tools_out.append({
                "name": fn["name"],
                "description": fn["description"],
                "params": list(fn.get("parameters", {}).get("properties", {}).keys()),
                "required": fn.get("parameters", {}).get("required", []),
            })
        result.append({
            "id":          d["id"],
            "name":        d["name"],
            "color":       d["color"],
            "icon":        d["icon"],
            "description": d["description"],
            "tools":       tools_out,
            "tables":      d["tables"],
        })
    return result
