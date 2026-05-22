"""
Run this once to create and populate amt.db with realistic sample data.
Usage: python db/seed.py
"""
import sqlite3, os, random
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "amt.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

def random_date(start_days_ago=180, end_days_ago=0):
    delta = random.randint(end_days_ago, start_days_ago)
    return (datetime.now() - timedelta(days=delta)).strftime("%Y-%m-%d")

def future_date(days_ahead):
    return (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

with open(SCHEMA_PATH) as f:
    conn.executescript(f.read())

# ── Products ─────────────────────────────────────────────────────────────────
products = [
    # Cameras
    ("CAM-001", "Sony", "FX3 Full-Frame Cinema Camera", "camera", "4K full-frame cinema camera, dual base ISO", 14900, 4060),
    ("CAM-002", "Sony", "FX6 Full-Frame Cinema Camera", "camera", "4K full-frame, 15+ stops dynamic range", 22000, 5990),
    ("CAM-003", "Sony", "PXW-Z280 4K Camcorder", "camera", "3-chip 4K HDR camcorder, broadcast-grade", 18500, 5040),
    ("CAM-004", "RED", "V-RAPTOR 8K VV Camera", "camera", "8K large format cinema, DSMC3 system", 89000, 24250),
    ("CAM-005", "Sony", "Alpha 7 IV Mirrorless", "camera", "33MP full-frame hybrid camera", 9200, 2510),
    # Lenses
    ("LNS-001", "Zeiss", "Supreme Prime 35mm T1.5", "lens", "Full-frame cinema prime, LPL mount", 28500, 7770),
    ("LNS-002", "Zeiss", "Supreme Prime 50mm T1.5", "lens", "Full-frame cinema prime, LPL mount", 28500, 7770),
    ("LNS-003", "Sony", "FE 24-70mm f/2.8 GM II", "lens", "Professional zoom lens, E-mount", 8900, 2430),
    # Drones
    ("DRN-001", "DJI", "Mavic 3 Pro", "drone", "Triple-camera drone, Hasselblad main sensor", 7299, 1990),
    ("DRN-002", "DJI", "Inspire 3", "drone", "8K cinema drone, full-frame sensor", 55000, 15000),
    ("DRN-003", "DJI", "Mini 4 Pro", "drone", "Compact 4K drone, under 249g", 2799, 762),
    ("DRN-004", "DJI", "Matrice 350 RTK", "drone", "Enterprise drone for surveying & inspection", 32000, 8720),
    # Audio
    ("AUD-001", "Sennheiser", "MKH 416 Shotgun Mic", "audio", "Industry-standard boom microphone", 2800, 763),
    ("AUD-002", "Sennheiser", "EW-DP ENG Set", "audio", "Digital wireless microphone system", 4600, 1254),
    ("AUD-003", "Sennheiser", "AMBEO VR Mic", "audio", "360 spatial audio microphone", 3900, 1063),
    # Lighting
    ("LGT-001", "Profoto", "B10X Plus", "lighting", "500Ws battery strobe, TTL/HSS", 5500, 1500),
    ("LGT-002", "Profoto", "A2 Studio Flash", "lighting", "Compact TTL flash, 76Ws", 2100, 572),
    ("LGT-003", "Profoto", "Pro-B4 1000 Air Kit", "lighting", "1000Ws location battery kit", 14500, 3951),
    # Gimbals
    ("GMB-001", "DJI", "RS 4 Pro", "gimbal", "Handheld gimbal stabilizer, 4.5kg payload", 1899, 517),
    ("GMB-002", "DJI", "RS 3 Mini", "gimbal", "Lightweight gimbal, mirrorless cameras", 1099, 299),
    # Storage & Recording
    ("STR-001", "Atomos", "Shogun Ultra", "storage", "8K HDMI/SDI recorder-monitor", 9500, 2590),
    ("STR-002", "Sony", "CEA-G160T CFexpress Type A 160GB", "storage", "High-speed media for FX3/FX6", 1650, 450),
    ("STR-003", "Teradek", "Bolt 6 XT 750 TX/RX", "storage", "Wireless video transmission system", 19500, 5314),
]

cur.executemany(
    "INSERT OR IGNORE INTO products (sku,brand,model,category,description,price_aed,price_usd) VALUES (?,?,?,?,?,?,?)",
    products
)

# ── Inventory ────────────────────────────────────────────────────────────────
cur.execute("SELECT id, sku FROM products")
product_rows = cur.fetchall()
product_ids = {row[1]: row[0] for row in product_rows}

inventory = [
    (product_ids["CAM-001"], 5, 1),
    (product_ids["CAM-002"], 3, 0),
    (product_ids["CAM-003"], 8, 2),
    (product_ids["CAM-004"], 1, 1),
    (product_ids["CAM-005"], 12, 3),
    (product_ids["LNS-001"], 2, 0),
    (product_ids["LNS-002"], 3, 1),
    (product_ids["LNS-003"], 7, 2),
    (product_ids["DRN-001"], 15, 4),
    (product_ids["DRN-002"], 2, 0),
    (product_ids["DRN-003"], 22, 5),
    (product_ids["DRN-004"], 4, 1),
    (product_ids["AUD-001"], 10, 2),
    (product_ids["AUD-002"], 6, 1),
    (product_ids["AUD-003"], 3, 0),
    (product_ids["LGT-001"], 8, 2),
    (product_ids["LGT-002"], 14, 3),
    (product_ids["LGT-003"], 3, 0),
    (product_ids["GMB-001"], 18, 4),
    (product_ids["GMB-002"], 25, 6),
    (product_ids["STR-001"], 4, 1),
    (product_ids["STR-002"], 30, 8),
    (product_ids["STR-003"], 3, 0),
]
cur.executemany(
    "INSERT INTO inventory (product_id, qty_on_hand, qty_reserved) VALUES (?,?,?)",
    inventory
)

# ── Customers ────────────────────────────────────────────────────────────────
customers = [
    ("Mohammed Al Rashidi", "Al Rashidi Productions", "UAE", "m.rashidi@alrashidiproductions.ae", "+971 50 123 4567", "corporate"),
    ("Ahmed Bin Khalid", "MBC Group", "UAE", "ahmed.bk@mbc.net", "+971 4 456 7890", "corporate"),
    ("Sara Al Mansoori", None, "UAE", "sara.mansoori@gmail.com", "+971 55 987 6543", "retail"),
    ("Faisal Al Otaibi", "Saudi Broadcasting Corp", "Saudi Arabia", "f.otaibi@sbc.sa", "+966 11 234 5678", "corporate"),
    ("Omar Nasser", "Nasser Media Group", "Egypt", "omar@nassermedia.eg", "+20 10 1234 5678", "reseller"),
    ("Layla Hassan", "Dubai Film Commission", "UAE", "layla.h@dfc.gov.ae", "+971 4 333 2222", "corporate"),
    ("Khalid Al Shammari", "KSA Drone Solutions", "Saudi Arabia", "khalid@ksadrone.sa", "+966 55 111 2222", "reseller"),
    ("Rami Yousef", None, "UAE", "ramiyousef92@hotmail.com", "+971 52 444 5555", "retail"),
    ("Nour Chehab", "Laha Magazine", "UAE", "nour.c@laha.ae", "+971 4 222 9999", "corporate"),
    ("Hassan Al Zaabi", "ADNOC Corporate Films", "UAE", "h.alzaabi@adnoc.ae", "+971 2 600 1234", "corporate"),
]
cur.executemany(
    "INSERT INTO customers (name,company,country,email,phone,account_type) VALUES (?,?,?,?,?,?)",
    customers
)

# ── Orders ───────────────────────────────────────────────────────────────────
cur.execute("SELECT id FROM customers")
customer_ids = [row[0] for row in cur.fetchall()]

orders_data = [
    ("ORD-2026-001", customer_ids[0], "2026-01-15", "delivered", 67400, "Tariq Mansoor"),
    ("ORD-2026-002", customer_ids[1], "2026-02-03", "delivered", 29800, "Dina Al Amin"),
    ("ORD-2026-003", customer_ids[3], "2026-02-18", "shipped", 55000, "Tariq Mansoor"),
    ("ORD-2026-004", customer_ids[5], "2026-03-05", "delivered", 14900, "Dina Al Amin"),
    ("ORD-2026-005", customer_ids[6], "2026-03-12", "confirmed", 93580, "Tariq Mansoor"),
    ("ORD-2026-006", customer_ids[9], "2026-03-28", "delivered", 44700, "Dina Al Amin"),
    ("ORD-2026-007", customer_ids[2], "2026-04-02", "delivered", 9300, "Reem Sadiq"),
    ("ORD-2026-008", customer_ids[4], "2026-04-15", "shipped", 22000, "Tariq Mansoor"),
    ("ORD-2026-009", customer_ids[7], "2026-05-01", "confirmed", 7299, "Reem Sadiq"),
    ("ORD-2026-010", customer_ids[8], "2026-05-10", "pending", 36700, "Dina Al Amin"),
]
cur.executemany(
    "INSERT INTO orders (order_ref,customer_id,order_date,status,total_aed,sales_rep) VALUES (?,?,?,?,?,?)",
    orders_data
)

# ── Order Items ──────────────────────────────────────────────────────────────
cur.execute("SELECT id, order_ref FROM orders")
order_map = {row[1]: row[0] for row in cur.fetchall()}

order_items = [
    (order_map["ORD-2026-001"], product_ids["CAM-002"], 2, 22000),
    (order_map["ORD-2026-001"], product_ids["LNS-001"], 1, 28500),
    (order_map["ORD-2026-001"], product_ids["GMB-001"], 1, 1899),
    (order_map["ORD-2026-002"], product_ids["DRN-001"], 2, 7299),
    (order_map["ORD-2026-002"], product_ids["AUD-002"], 1, 4600),
    (order_map["ORD-2026-003"], product_ids["DRN-002"], 1, 55000),
    (order_map["ORD-2026-004"], product_ids["CAM-001"], 1, 14900),
    (order_map["ORD-2026-005"], product_ids["CAM-004"], 1, 89000),
    (order_map["ORD-2026-006"], product_ids["LGT-001"], 4, 5500),
    (order_map["ORD-2026-006"], product_ids["LGT-002"], 6, 2100),
    (order_map["ORD-2026-007"], product_ids["CAM-005"], 1, 9200),
    (order_map["ORD-2026-008"], product_ids["CAM-002"], 1, 22000),
    (order_map["ORD-2026-009"], product_ids["DRN-001"], 1, 7299),
    (order_map["ORD-2026-010"], product_ids["STR-003"], 1, 19500),
    (order_map["ORD-2026-010"], product_ids["AUD-002"], 1, 4600),
    (order_map["ORD-2026-010"], product_ids["STR-001"], 1, 9500),
]
cur.executemany(
    "INSERT INTO order_items (order_id,product_id,qty,unit_price_aed) VALUES (?,?,?,?)",
    order_items
)

# ── Invoices ─────────────────────────────────────────────────────────────────
invoices = [
    ("INV-2026-001", order_map["ORD-2026-001"], customer_ids[0], "2026-01-16", "2026-02-15", 67400, 3370, "paid", "2026-02-10"),
    ("INV-2026-002", order_map["ORD-2026-002"], customer_ids[1], "2026-02-04", "2026-03-06", 29800, 1490, "paid", "2026-03-01"),
    ("INV-2026-003", order_map["ORD-2026-003"], customer_ids[3], "2026-02-19", "2026-03-21", 55000, 2750, "overdue", None),
    ("INV-2026-004", order_map["ORD-2026-004"], customer_ids[5], "2026-03-06", "2026-04-05", 14900, 745, "paid", "2026-03-30"),
    ("INV-2026-005", order_map["ORD-2026-005"], customer_ids[6], "2026-03-13", "2026-04-12", 93580, 4679, "overdue", None),
    ("INV-2026-006", order_map["ORD-2026-006"], customer_ids[9], "2026-03-29", "2026-04-28", 44700, 2235, "paid", "2026-04-20"),
    ("INV-2026-007", order_map["ORD-2026-007"], customer_ids[2], "2026-04-03", "2026-05-03", 9300, 465, "unpaid", None),
    ("INV-2026-008", order_map["ORD-2026-008"], customer_ids[4], "2026-04-16", "2026-05-16", 22000, 1100, "unpaid", None),
    ("INV-2026-009", order_map["ORD-2026-009"], customer_ids[7], "2026-05-02", "2026-06-01", 7299, 365, "unpaid", None),
    ("INV-2026-010", order_map["ORD-2026-010"], customer_ids[8], "2026-05-11", "2026-06-10", 36700, 1835, "unpaid", None),
]
cur.executemany(
    "INSERT INTO invoices (invoice_ref,order_id,customer_id,issue_date,due_date,amount_aed,vat_aed,status,paid_date) VALUES (?,?,?,?,?,?,?,?,?)",
    invoices
)

# ── Shipments ────────────────────────────────────────────────────────────────
shipments = [
    ("SHP-2026-001", order_map["ORD-2026-003"], "DJI Enterprise", "China", "Dubai, UAE", "2026-02-25", "2026-03-10", "delivered", "Emirates SkyCargo", "EK-CARGO-88234", None),
    ("SHP-2026-002", order_map["ORD-2026-005"], "RED Digital Cinema", "USA", "Dubai, UAE", "2026-03-20", "2026-04-05", "delayed", "FedEx International", "FX-INT-99012", "Customs hold — awaiting HS code clarification"),
    ("SHP-2026-003", order_map["ORD-2026-008"], "Sony Professional", "Japan", "Dubai, UAE", "2026-04-20", "2026-05-08", "in_transit", "DHL Express", "DHL-77891", None),
    ("SHP-2026-004", order_map["ORD-2026-010"], "Teradek", "USA", "Dubai, UAE", "2026-05-15", "2026-05-30", "ordered", "FedEx International", None, None),
    ("SHP-2026-005", order_map["ORD-2026-009"], "DJI Authorized", "Hong Kong", "Dubai, UAE", "2026-05-05", "2026-05-20", "delivered", "Emirates SkyCargo", "EK-CARGO-91122", None),
]
cur.executemany(
    "INSERT INTO shipments (shipment_ref,order_id,supplier,origin_country,destination,shipped_date,eta,status,carrier,tracking_number,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
    shipments
)

# ── Service Tickets ──────────────────────────────────────────────────────────
service_tickets = [
    ("SVC-2026-001", customer_ids[0], product_ids["DRN-001"], "MAV3P-AX1923", "Drone lost GPS signal mid-flight, returned home erratically", "in_repair", "in_warranty", "2026-04-10", "2026-05-01", "Karim Nour", 0),
    ("SVC-2026-002", customer_ids[2], product_ids["CAM-005"], "A7IV-DX8812", "LCD screen flickering at certain shutter speeds", "diagnosed", "in_warranty", "2026-04-22", "2026-05-10", "Hassan Bilal", 0),
    ("SVC-2026-003", customer_ids[7], product_ids["GMB-001"], "RS4P-GX3301", "Motor overheating warning, axis 2 unresponsive", "awaiting_parts", "out_of_warranty", "2026-05-01", "2026-05-25", "Karim Nour", 650),
    ("SVC-2026-004", customer_ids[1], product_ids["AUD-002"], "EWDP-YZ0045", "Receiver drops signal beyond 30m range", "open", "in_warranty", "2026-05-12", "2026-05-28", None, 0),
    ("SVC-2026-005", customer_ids[9], product_ids["CAM-001"], "FX3-ZZ7734", "Overexposure issues in S-Log3, sensor calibration needed", "ready", "in_warranty", "2026-04-28", "2026-05-20", "Hassan Bilal", 0),
    ("SVC-2026-006", customer_ids[5], product_ids["LGT-001"], "B10X-PP2290", "Flash not recycling at full power, battery fault suspected", "closed", "out_of_warranty", "2026-03-15", "2026-03-30", "Karim Nour", 980),
]
cur.executemany(
    "INSERT INTO service_tickets (ticket_ref,customer_id,product_id,serial_number,issue_description,status,warranty_status,received_date,estimated_completion,technician,repair_cost_aed) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
    service_tickets
)

conn.commit()
conn.close()
print(f"Database seeded successfully at {DB_PATH}")
print(f"  Products:        {len(products)}")
print(f"  Customers:       {len(customers)}")
print(f"  Orders:          {len(orders_data)}")
print(f"  Invoices:        {len(invoices)}")
print(f"  Shipments:       {len(shipments)}")
print(f"  Service tickets: {len(service_tickets)}")
