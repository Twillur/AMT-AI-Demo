"""
AMT LLC — SAP-aligned database seed
Real brands, real product catalog, realistic MENA business data.
Run once: python db/seed.py
"""
import sqlite3, os
from datetime import datetime, timedelta

DB_PATH   = os.path.join(os.path.dirname(__file__), "amt.db")
SCHEMA    = os.path.join(os.path.dirname(__file__), "schema.sql")

def d(days_ago=0):
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
def f(days_ahead=0):
    return (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur  = conn.cursor()
cur.execute("PRAGMA foreign_keys = OFF")

with open(SCHEMA) as fh:
    conn.executescript(fh.read())

# ── BRANCHES ─────────────────────────────────────────────────────────────────
branches = [
    ("DXB-HQ",  "Dubai Showroom HQ",          "Dubai",  "UAE",          "Mezzanine, Galadari Automobiles Bldg, Sheikh Zayed Road",   "+971 4 352 9977", "AED", 5.0, 0, 0),
    ("DXB-WH",  "Dubai Al Quoz Warehouse & Service", "Dubai", "UAE",    "Al Quoz Industrial Area, Dubai",                            "+971 4 352 9977", "AED", 5.0, 1, 1),
    ("RUH-KSA", "Riyadh Showroom",             "Riyadh", "Saudi Arabia", "Showroom #5, Coral Center, Exit 7, Uthman Ibn Affan Road",  "+966 55 490 9911","SAR", 15.0,0, 1),
    ("CAI-EGY", "Cairo Office",                "Cairo",  "Egypt",        "Bldg P5, Office 207, Cairo Festival Business District",     "+20 2 2345 6789", "EGP", 14.0,0, 0),
]
cur.executemany("INSERT INTO branches (branch_code,name,city,country,address,phone,currency,vat_rate_pct,is_warehouse,is_service_ctr) VALUES (?,?,?,?,?,?,?,?,?,?)", branches)
bids = {r[0]: cur.execute("SELECT id FROM branches WHERE branch_code=?", (r[0],)).fetchone()[0] for r in branches}

# ── WAREHOUSES ────────────────────────────────────────────────────────────────
warehouses = [
    ("WH-DXB-MAIN", "Al Quoz Main Store",       bids["DXB-WH"],  "Al Quoz Industrial Area, Dubai"),
    ("WH-DXB-SVC",  "Service Parts Store",      bids["DXB-WH"],  "Al Quoz Service Centre"),
    ("WH-RUH",      "Riyadh Stock Room",         bids["RUH-KSA"], "Coral Center, Riyadh"),
    ("WH-CAI",      "Cairo Stock Room",          bids["CAI-EGY"], "Cairo Festival Business District"),
]
cur.executemany("INSERT INTO warehouses (warehouse_code,name,branch_id,address) VALUES (?,?,?,?)", warehouses)
wids = {r[0]: cur.execute("SELECT id FROM warehouses WHERE warehouse_code=?", (r[0],)).fetchone()[0] for r in warehouses}

# ── EMPLOYEES ─────────────────────────────────────────────────────────────────
employees = [
    ("EMP-001","Kaveh Farnam",      "Managing Director",          "management", bids["DXB-HQ"],  "kaveh@amt.tv",       "+971 50 100 0001","2002-01-01"),
    ("EMP-002","Alaa Al Rantisi",   "Co-founder & Managing Director","management",bids["DXB-HQ"],"alaa@amt.tv",        "+971 50 100 0002","2002-01-01"),
    ("EMP-003","Pooyan Farnam",     "Director",                   "management", bids["DXB-HQ"],  "pooyan@amt.tv",      "+971 50 100 0003","2010-03-15"),
    ("EMP-004","Ragheed Al Rantisi","Director",                   "management", bids["DXB-HQ"],  "ragheed@amt.tv",     "+971 50 100 0004","2012-06-01"),
    ("EMP-005","Tariq Mansoor",     "Senior Sales Manager",       "sales",      bids["DXB-HQ"],  "tariq@amt.tv",       "+971 50 200 0005","2015-09-01"),
    ("EMP-006","Dina Al Amin",      "Sales Executive",            "sales",      bids["DXB-HQ"],  "dina@amt.tv",        "+971 55 200 0006","2018-04-15"),
    ("EMP-007","Reem Sadiq",        "Sales Executive",            "sales",      bids["DXB-HQ"],  "reem@amt.tv",        "+971 56 200 0007","2020-01-10"),
    ("EMP-008","Hassan Al-Masri",   "KSA Sales Manager",          "sales",      bids["RUH-KSA"], "hassan.ksa@amt.tv",  "+966 55 300 0008","2019-07-01"),
    ("EMP-009","Layla Nasser",      "Egypt Sales Executive",      "sales",      bids["CAI-EGY"], "layla.eg@amt.tv",    "+20 10 400 0009", "2022-03-01"),
    ("EMP-010","Karim Nour",        "Senior Service Technician",  "service",    bids["DXB-WH"],  "karim@amt.tv",       "+971 50 500 0010","2016-02-01"),
    ("EMP-011","Hassan Bilal",      "Service Technician",         "service",    bids["DXB-WH"],  "h.bilal@amt.tv",     "+971 55 500 0011","2019-11-01"),
    ("EMP-012","Ahmed Mansour",     "Service Technician",         "service",    bids["DXB-WH"],  "a.mansour@amt.tv",   "+971 56 500 0012","2021-05-15"),
    ("EMP-013","Mohammed Al-Zahrani","Finance Manager",           "finance",    bids["DXB-HQ"],  "m.zahrani@amt.tv",   "+971 50 600 0013","2014-08-01"),
    ("EMP-014","Sarah Kamal",       "Finance Executive",          "finance",    bids["DXB-HQ"],  "s.kamal@amt.tv",     "+971 55 600 0014","2020-09-01"),
    ("EMP-015","Ali Hassan",        "Logistics Coordinator",      "logistics",  bids["DXB-WH"],  "ali.h@amt.tv",       "+971 50 700 0015","2017-03-01"),
    ("EMP-016","Omar Khalil",       "Customs & Shipping Exec",    "logistics",  bids["DXB-WH"],  "omar.k@amt.tv",      "+971 55 700 0016","2018-10-01"),
    ("EMP-017","Waleed Ibrahim",    "Training Manager",           "training",   bids["DXB-HQ"],  "waleed@amt.tv",      "+971 50 800 0017","2016-06-01"),
    ("EMP-018","Nour Al-Rashid",    "KSA Service Technician",     "service",    bids["RUH-KSA"], "nour.ksa@amt.tv",    "+966 55 500 0018","2021-01-01"),
]
cur.executemany("INSERT INTO employees (employee_id,name,role,department,branch_id,email,phone,hire_date) VALUES (?,?,?,?,?,?,?,?)", employees)

def eid(code): return cur.execute("SELECT id FROM employees WHERE employee_id=?", (code,)).fetchone()[0]

# ── SUPPLIERS ─────────────────────────────────────────────────────────────────
suppliers = [
    ("SUP-DJI",  "DJI Innovations",          "China",       "Shenzhen","MENA Partner Team",  "mena@dji.com",          60, 21,"USD","DJI drones, gimbals, stabilizers, accessories"),
    ("SUP-SON",  "Sony Professional Solutions","Japan",      "Tokyo",   "MENA Dist. Mgr",     "proav-mena@sony.com",   60, 28,"USD","Sony cameras, camcorders, audio, memory"),
    ("SUP-RED",  "RED Digital Cinema",        "USA",         "Irvine",  "MENA Distributor",   "sales@red.com",         45, 35,"USD","RED cinema cameras, accessories"),
    ("SUP-ZEI",  "Carl Zeiss AG",             "Germany",     "Oberkochen","International Sales","cinema@zeiss.com",    60, 42,"EUR","Zeiss cinema lenses, Supreme Primes"),
    ("SUP-PRO",  "Profoto AB",                "Sweden",      "Stockholm","MENA Distributor",  "info@profoto.com",      60, 35,"EUR","Profoto studio lighting, battery flashes"),
    ("SUP-SEN",  "Sennheiser Electronic",     "Germany",     "Wedemark", "Middle East Sales", "proav@sennheiser.com",  60, 28,"EUR","Sennheiser microphones, wireless audio"),
    ("SUP-MAN",  "Manfrotto / Vitec Group",   "Italy",       "Cassola",  "MENA Dist.",        "sales@manfrotto.com",   60, 28,"EUR","Manfrotto tripods, supports, bags"),
    ("SUP-ATO",  "Atomos Global",             "Australia",   "Melbourne","MENA Sales",        "sales@atomos.com",      60, 21,"USD","Atomos recorders, monitors"),
    ("SUP-TER",  "Teradek LLC",               "USA",         "Irvine",   "International Sales","info@teradek.com",     45, 35,"USD","Teradek wireless video systems"),
    ("SUP-APU",  "Aputure Imaging",           "China",       "Shenzhen", "Intl Sales",        "info@aputure.com",      45, 21,"USD","Aputure LED lights, accessories"),
    ("SUP-NAN",  "Nanlite",                   "China",       "Guangzhou","Intl Sales",        "info@nanlite.com",      45, 21,"USD","Nanlite LED lights, Forza series"),
    ("SUP-HAS",  "Hasselblad",                "Sweden",      "Gothenburg","MENA Distributor", "info@hasselblad.com",   60, 42,"USD","Hasselblad medium format cameras"),
    ("SUP-ARR",  "ARRI AG",                   "Germany",     "Munich",   "MENA Sales",        "mena@arri.com",         60, 45,"EUR","ARRI cameras, lenses, lighting"),
    ("SUP-ROD",  "Rode Microphones",          "Australia",   "Sydney",   "MENA Dist.",        "sales@rode.com",        60, 21,"USD","Rode microphones, accessories"),
    ("SUP-SAC",  "Sachtler / Vitec Group",    "Germany",     "Munich",   "MENA Sales",        "sachtler@vitecgroup.com",60,35,"EUR","Sachtler broadcast tripods, heads"),
    ("SUP-BLK",  "Blackmagic Design",         "Australia",   "Melbourne","MENA Dist.",        "sales@blackmagic.com",  45, 21,"USD","Blackmagic cameras, recorders, switchers"),
    ("SUP-SMR",  "SmallRig",                  "China",       "Shenzhen", "Intl Sales",        "info@smallrig.com",     45, 14,"USD","SmallRig cages, accessories, rigging"),
    ("SUP-HOL",  "Hollyland Technology",      "China",       "Shenzhen", "Intl Sales",        "info@hollyland.cn",     45, 21,"USD","Hollyland wireless video, intercom"),
    ("SUP-TIL",  "Tilta Technology",          "China",       "Shenzhen", "Intl Sales",        "info@tiltaing.com",     45, 14,"USD","Tilta camera accessories, follow focus"),
    ("SUP-AST",  "Astera LED Technology",     "Germany",     "Munich",   "MENA Dist.",        "info@astera-led.com",   60, 35,"EUR","Astera wireless LED tubes"),
]
cur.executemany("INSERT INTO suppliers (supplier_code,name,country,city,contact_name,contact_email,payment_terms_days,lead_time_days,currency,authorized_brands) VALUES (?,?,?,?,?,?,?,?,?,?)", suppliers)
def sid(code): return cur.execute("SELECT id FROM suppliers WHERE supplier_code=?", (code,)).fetchone()[0]

# ── PRODUCT CATEGORIES ────────────────────────────────────────────────────────
cats = [
    ("CAM",  "Cameras",        None),
    ("CAM-C","Cinema Cameras", "CAM"),
    ("CAM-B","Broadcast Cameras","CAM"),
    ("CAM-M","Mirrorless/DSLR","CAM"),
    ("CAM-MF","Medium Format", "CAM"),
    ("DRN",  "Drones & Aerial",None),
    ("DRN-P","Prosumer Drones","DRN"),
    ("DRN-C","Cinema Drones",  "DRN"),
    ("DRN-E","Enterprise Drones","DRN"),
    ("LNS",  "Lenses",         None),
    ("LNS-C","Cinema Lenses",  "LNS"),
    ("LNS-P","Photo Lenses",   "LNS"),
    ("AUD",  "Audio",          None),
    ("AUD-M","Microphones",    "AUD"),
    ("AUD-W","Wireless Systems","AUD"),
    ("LGT",  "Lighting",       None),
    ("LGT-S","Studio Flash",   "LGT"),
    ("LGT-L","LED Continuous", "LGT"),
    ("SUP",  "Support & Rigging",None),
    ("SUP-T","Tripods & Heads","SUP"),
    ("SUP-G","Gimbals",        "SUP"),
    ("REC",  "Recording & Monitoring",None),
    ("REC-R","Field Recorders","REC"),
    ("REC-W","Wireless Video", "REC"),
    ("STR",  "Storage & Media",None),
    ("ACC",  "Accessories",    None),
]
for code, name, parent in cats:
    pid = cur.execute("SELECT id FROM product_categories WHERE code=?", (parent,)).fetchone()[0] if parent else None
    cur.execute("INSERT INTO product_categories (code,name,parent_id) VALUES (?,?,?)", (code, name, pid))
def cid(code): return cur.execute("SELECT id FROM product_categories WHERE code=?", (code,)).fetchone()[0]

# ── PRODUCTS ──────────────────────────────────────────────────────────────────
# (sku, brand, model, category, category_code, description, supplier_code,
#  price_aed, price_usd, cost_usd, hs_code, weight_kg, warranty_months, is_serialized)
products_raw = [
    # ── Cinema Cameras
    ("CAM-001","Sony","FX3 Full-Frame Cinema Camera","camera","CAM-C","4K full-frame, dual ISO 800/12800, 12.1MP","SUP-SON",14900,4060,2850,"8525.8900",0.72,12,1),
    ("CAM-002","Sony","FX6 Full-Frame Cinema Camera","camera","CAM-C","4K 120fps, 15+ stops DR, dual base ISO","SUP-SON",22000,5990,4190,"8525.8900",0.89,12,1),
    ("CAM-003","Sony","FX9 Full-Frame Cinema Camera","camera","CAM-C","6K full-frame, Fast Hybrid AF, 15+ stops","SUP-SON",38000,10350,7240,"8525.8900",1.17,12,1),
    ("CAM-004","Sony","Venice 2 8.6K Large Format","camera","CAM-C","8.6K, dual base ISO 800/3200, anamorphic","SUP-SON",112000,30500,21350,"8525.8900",2.60,12,1),
    ("CAM-005","RED","V-RAPTOR 8K VV","camera","CAM-C","8K large format DSMC3, 120fps","SUP-RED",89000,24250,16975,"8525.8900",1.46,12,1),
    ("CAM-006","RED","Komodo 6K Cinema Camera","camera","CAM-C","6K global shutter, REDCODE RAW, compact","SUP-RED",18500,5040,3528,"8525.8900",0.59,12,1),
    ("CAM-007","Blackmagic","URSA Mini Pro 12K","camera","CAM-C","12K Super 35, BRAW, PL/EF/B4 mounts","SUP-BLK",14200,3870,2709,"8525.8900",2.42,12,1),
    ("CAM-008","Sony","PXW-Z280 4K Camcorder","camera","CAM-B","3-chip 4K HDR, XAVC, built-in ND","SUP-SON",18500,5040,3528,"8525.8900",1.65,12,1),
    ("CAM-009","Sony","HXR-NX80 Palm Camcorder","camera","CAM-B","4K HDR, 1-inch sensor, palm-sized ENG","SUP-SON",8900,2430,1701,"8525.8900",0.56,12,1),
    ("CAM-010","Sony","Alpha 7 IV Mirrorless","camera","CAM-M","33MP FF hybrid, 4K 60fps, Eye AF","SUP-SON",9200,2510,1757,"8525.8900",0.66,24,1),
    ("CAM-011","Hasselblad","X2D 100C Medium Format","camera","CAM-MF","100MP CMOS, 16 stops DR, 8fps burst","SUP-HAS",55000,14980,10486,"9006.5300",0.74,24,1),
    # ── Drones
    ("DRN-001","DJI","Mavic 3 Pro","drone","DRN-P","Triple Hasselblad cameras, 5.1K, 43min flight","SUP-DJI",7299,1990,1393,"8806.2190",0.89,12,1),
    ("DRN-002","DJI","Mini 4 Pro","drone","DRN-P","<249g, 4K 100fps, 34min flight, no registration","SUP-DJI",2799,762,533,"8806.2190",0.29,12,1),
    ("DRN-003","DJI","Inspire 3","drone","DRN-C","FF 8K cinema, Zenmuse X9-8K, dual operator","SUP-DJI",55000,15000,10500,"8806.2190",4.25,12,1),
    ("DRN-004","DJI","Phantom 4 Pro V2.0","drone","DRN-P","20MP 1-inch, 4K 60fps, 30min flight","SUP-DJI",5500,1500,1050,"8806.2190",1.37,12,1),
    ("DRN-005","DJI","Matrice 350 RTK","drone","DRN-E","Enterprise survey/inspection, 55min, IP55","SUP-DJI",32000,8720,6104,"8806.2990",6.47,12,1),
    ("DRN-006","DJI","Agras T50","drone","DRN-E","Agricultural spraying, 40kg payload, 16L tank","SUP-DJI",55000,15000,10500,"8806.2990",47.50,12,1),
    # ── Lenses
    ("LNS-001","Zeiss","Supreme Prime 35mm T1.5","lens","LNS-C","FF cinema prime, LPL/PL, Supreme coating","SUP-ZEI",28500,7770,5439,"9002.1100",1.00,24,1),
    ("LNS-002","Zeiss","Supreme Prime 50mm T1.5","lens","LNS-C","FF cinema prime, 50mm, LPL/PL mount","SUP-ZEI",28500,7770,5439,"9002.1100",1.00,24,1),
    ("LNS-003","Zeiss","Supreme Prime 85mm T1.5","lens","LNS-C","FF cinema prime, 85mm, portrait/drama","SUP-ZEI",28500,7770,5439,"9002.1100",1.00,24,1),
    ("LNS-004","Sony","FE 24-70mm f/2.8 GM II","lens","LNS-P","Pro E-mount zoom, 1670g, fast AF","SUP-SON",8900,2430,1701,"9002.1100",0.53,24,1),
    ("LNS-005","Sony","FE 70-200mm f/2.8 GM OSS II","lens","LNS-P","Telephoto zoom, 1045g, OSS stabilisation","SUP-SON",12500,3410,2387,"9002.1100",1.05,24,1),
    # ── Audio
    ("AUD-001","Sennheiser","MKH 416 Shotgun Mic","audio","AUD-M","Industry-standard boom mic, super-cardioid","SUP-SEN",2800,763,534,"8518.1000",0.17,24,1),
    ("AUD-002","Sennheiser","EW-DP ENG Set","audio","AUD-W","Digital wireless ENG, 6GHz, ME 2-II lav","SUP-SEN",4600,1254,878,"8518.1000",0.35,24,1),
    ("AUD-003","Sennheiser","AMBEO VR Mic","audio","AUD-M","4-capsule ambisonics, 360-degree spatial","SUP-SEN",3900,1063,744,"8518.1000",0.29,24,1),
    ("AUD-004","Rode","NTG5 Lightweight Shotgun","audio","AUD-M","Ultra-compact broadcast shotgun, 76dB SNR","SUP-ROD",1600,436,305,"8518.1000",0.08,24,1),
    # ── Lighting
    ("LGT-001","Profoto","B10X Plus 500Ws","lighting","LGT-S","500Ws TTL/HSS battery strobe, 70cm","SUP-PRO",5500,1500,1050,"9405.4000",0.99,24,1),
    ("LGT-002","Profoto","A2 Studio Flash 76Ws","lighting","LGT-S","Compact TTL flash, GN60, HSS","SUP-PRO",2100,572,400,"9405.4000",0.35,24,1),
    ("LGT-003","Profoto","Pro-B4 1000Ws Kit","lighting","LGT-S","1000Ws location battery kit, HSS","SUP-PRO",14500,3951,2766,"9405.4000",8.20,24,1),
    ("LGT-004","Aputure","600d Pro LED","lighting","LGT-L","600W daylight LED, Bowens, CRI 96+","SUP-APU",6500,1771,1240,"9405.4000",6.80,12,1),
    ("LGT-005","Nanlite","Forza 500 LED","lighting","LGT-L","500W daylight, Bowens, App control","SUP-NAN",3200,872,610,"9405.4000",5.10,12,1),
    ("LGT-006","Astera","Titan Tube LED (Set of 8)","lighting","LGT-L","RGB+W wireless tubes, battery, flight case","SUP-AST",14400,3924,2747,"9405.4000",6.40,12,1),
    # ── Gimbals
    ("GMB-001","DJI","RS 4 Pro","gimbal","SUP-G","3-axis, 4.5kg payload, OLED, LiDAR focus","SUP-DJI",1899,517,362,"8479.8990",0.86,12,1),
    ("GMB-002","DJI","RS 3 Mini","gimbal","SUP-G","Lightweight, 2kg payload, mirrorless","SUP-DJI",1099,299,209,"8479.8990",0.80,12,1),
    # ── Recording & Wireless Video
    ("REC-001","Atomos","Shogun Ultra 8K","recording","REC-R","8K HDMI/SDI recorder-monitor, ProRes RAW","SUP-ATO",9500,2590,1813,"8528.5990",0.55,12,1),
    ("REC-002","Atomos","Ninja V+ Monitor Recorder","recording","REC-R","5-inch 8K RAW monitor-recorder","SUP-ATO",4200,1145,802,"8528.5990",0.32,12,1),
    ("REC-003","Teradek","Bolt 6 XT 750 TX/RX","recording","REC-W","Zero-delay wireless video, 4K 60fps, 750ft","SUP-TER",19500,5314,3720,"8525.6000",0.28,12,1),
    ("REC-004","Hollyland","Mars 4K HDMI Wireless","recording","REC-W","4K wireless video TX/RX, 100m range","SUP-HOL",2200,600,420,"8525.6000",0.18,12,1),
    # ── Support & Tripods
    ("SUP-001","Manfrotto","504X Fluid Video Head","support","SUP-T","12kg payload, 2 drag positions, flat base","SUP-MAN",1800,491,344,"9620.0000",1.64,24,1),
    ("SUP-002","Sachtler","Aktiv8 Fluid Head + CF Legs","support","SUP-T","8kg payload, carbon fibre, SpeedLevel","SUP-SAC",9500,2590,1813,"9620.0000",4.80,24,1),
    # ── Storage
    ("STR-001","Sony","CFexpress Type A 160GB","storage","STR","Read 800MB/s, Write 700MB/s, FX3/FX6/FX9","SUP-SON",1650,450,315,"8523.5190",0.02,12,0),
    ("STR-002","Sony","CFexpress Type A 80GB","storage","STR","Read 800MB/s, compact, FX3/Alpha series","SUP-SON",990,270,189,"8523.5190",0.02,12,0),
]

for row in products_raw:
    sku,brand,model,cat,cat_code,desc,sup_code,price_aed,price_usd,cost_usd,hs,weight,warranty,serial = row
    cat_id  = cid(cat_code)
    sup_id  = sid(sup_code)
    cur.execute("""
        INSERT INTO products (sku,brand,model,category,category_id,description,supplier_id,
                              price_aed,price_usd,cost_usd,hs_code,weight_kg,warranty_months,is_serialized)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (sku,brand,model,cat,cat_id,desc,sup_id,price_aed,price_usd,cost_usd,hs,weight,warranty,serial))

def pid(sku): return cur.execute("SELECT id FROM products WHERE sku=?", (sku,)).fetchone()[0]

# ── INVENTORY ─────────────────────────────────────────────────────────────────
# (sku, warehouse_code, qty_on_hand, qty_reserved, qty_on_order, reorder_point)
inventory = [
    ("CAM-001","WH-DXB-MAIN",5,1,0,2), ("CAM-001","WH-RUH",2,0,2,1),
    ("CAM-002","WH-DXB-MAIN",3,0,0,2), ("CAM-002","WH-RUH",1,1,0,1),
    ("CAM-003","WH-DXB-MAIN",2,1,0,1),
    ("CAM-004","WH-DXB-MAIN",1,1,0,1),
    ("CAM-005","WH-DXB-MAIN",2,1,0,1),
    ("CAM-006","WH-DXB-MAIN",4,0,0,2), ("CAM-006","WH-RUH",1,0,0,1),
    ("CAM-007","WH-DXB-MAIN",3,0,2,2),
    ("CAM-008","WH-DXB-MAIN",6,2,0,2), ("CAM-008","WH-RUH",2,0,0,1),
    ("CAM-009","WH-DXB-MAIN",8,1,0,3),
    ("CAM-010","WH-DXB-MAIN",12,3,0,4), ("CAM-010","WH-RUH",3,0,0,2),
    ("CAM-011","WH-DXB-MAIN",2,0,0,1),
    ("DRN-001","WH-DXB-MAIN",15,4,0,5), ("DRN-001","WH-RUH",4,1,0,2),
    ("DRN-002","WH-DXB-MAIN",22,5,10,8),("DRN-002","WH-RUH",6,0,0,3),
    ("DRN-003","WH-DXB-MAIN",2,0,0,1),
    ("DRN-004","WH-DXB-MAIN",5,1,0,2),
    ("DRN-005","WH-DXB-MAIN",4,1,0,2), ("DRN-005","WH-RUH",2,0,0,1),
    ("DRN-006","WH-DXB-MAIN",1,0,2,1),
    ("LNS-001","WH-DXB-MAIN",2,0,0,1),
    ("LNS-002","WH-DXB-MAIN",3,1,0,1),
    ("LNS-003","WH-DXB-MAIN",2,0,0,1),
    ("LNS-004","WH-DXB-MAIN",7,2,0,3), ("LNS-004","WH-RUH",2,0,0,1),
    ("LNS-005","WH-DXB-MAIN",4,1,0,2),
    ("AUD-001","WH-DXB-MAIN",10,2,0,4), ("AUD-001","WH-RUH",3,0,0,2),
    ("AUD-002","WH-DXB-MAIN",6,1,0,3),
    ("AUD-003","WH-DXB-MAIN",3,0,0,2),
    ("AUD-004","WH-DXB-MAIN",12,2,0,4),
    ("LGT-001","WH-DXB-MAIN",8,2,0,3),
    ("LGT-002","WH-DXB-MAIN",14,3,0,5),
    ("LGT-003","WH-DXB-MAIN",3,0,0,1),
    ("LGT-004","WH-DXB-MAIN",5,1,0,2),
    ("LGT-005","WH-DXB-MAIN",7,2,0,3),
    ("LGT-006","WH-DXB-MAIN",4,0,0,2),
    ("GMB-001","WH-DXB-MAIN",18,4,0,6), ("GMB-001","WH-RUH",5,1,0,2),
    ("GMB-002","WH-DXB-MAIN",25,6,0,8),
    ("REC-001","WH-DXB-MAIN",4,1,0,2),
    ("REC-002","WH-DXB-MAIN",8,2,0,3),
    ("REC-003","WH-DXB-MAIN",3,0,0,1),
    ("REC-004","WH-DXB-MAIN",10,2,0,4),
    ("SUP-001","WH-DXB-MAIN",9,2,0,3), ("SUP-001","WH-RUH",3,0,0,1),
    ("SUP-002","WH-DXB-MAIN",4,1,0,2),
    ("STR-001","WH-DXB-MAIN",30,8,0,10),("STR-001","WH-RUH",10,2,0,5),
    ("STR-002","WH-DXB-MAIN",40,10,0,15),
]
for sku, wh_code, qoh, qres, qord, rop in inventory:
    cur.execute("""INSERT OR IGNORE INTO inventory (product_id,warehouse_id,qty_on_hand,qty_reserved,qty_on_order,reorder_point)
                   VALUES (?,?,?,?,?,?)""", (pid(sku), wids[wh_code], qoh, qres, qord, rop))

# ── CUSTOMERS ─────────────────────────────────────────────────────────────────
# (code, name, company, country, city, address, email, phone, type, credit_aed, terms, vat_reg, branch_code, sales_rep_id)
customers_raw = [
    ("CUS-001","Mohammed Al Rashidi","Al Rashidi Productions LLC","UAE","Dubai","DIFC, Gate Village","m.rashidi@arproductions.ae","+971 50 123 4567","corporate",150000,30,"100-123456-7",bids["DXB-HQ"],eid("EMP-005")),
    ("CUS-002","Ahmed Bin Khalid","MBC Group","UAE","Dubai","MBC HQ, Media City","ahmed.bk@mbc.net","+971 4 456 7890","broadcast",500000,45,"100-987654-3",bids["DXB-HQ"],eid("EMP-005")),
    ("CUS-003","Sara Al Mansoori",None,"UAE","Abu Dhabi","Al Reem Island","sara.mansoori@gmail.com","+971 55 987 6543","retail",10000,0,None,bids["DXB-HQ"],eid("EMP-007")),
    ("CUS-004","Faisal Al Otaibi","Saudi Broadcasting Authority","Saudi Arabia","Riyadh","SBA HQ, Riyadh","f.otaibi@sba.sa","+966 11 234 5678","broadcast",800000,60,"300-456789-1",bids["RUH-KSA"],eid("EMP-008")),
    ("CUS-005","Omar Nasser","Nasser Media Group","Egypt","Cairo","Zamalek, Cairo","omar@nassermedia.eg","+20 10 1234 5678","reseller",120000,45,None,bids["CAI-EGY"],eid("EMP-009")),
    ("CUS-006","Layla Hassan","Dubai Film Commission","UAE","Dubai","Dubai Design District","layla.h@dfc.gov.ae","+971 4 333 2222","government",250000,60,"100-111222-3",bids["DXB-HQ"],eid("EMP-006")),
    ("CUS-007","Khalid Al Shammari","KSA Drone Solutions","Saudi Arabia","Riyadh","Al Olaya, Riyadh","khalid@ksadrone.sa","+966 55 111 2222","reseller",200000,30,"300-777888-9",bids["RUH-KSA"],eid("EMP-008")),
    ("CUS-008","Rami Yousef",None,"UAE","Dubai","JLT, Dubai","ramiyousef92@hotmail.com","+971 52 444 5555","retail",15000,0,None,bids["DXB-HQ"],eid("EMP-007")),
    ("CUS-009","Nour Chehab","Laha Magazine / ITP Media","UAE","Dubai","ITP HQ, Media City","nour.c@laha.ae","+971 4 222 9999","corporate",80000,30,"100-334455-6",bids["DXB-HQ"],eid("EMP-006")),
    ("CUS-010","Hassan Al Zaabi","ADNOC Corporate Films","UAE","Abu Dhabi","ADNOC HQ, Corniche","h.alzaabi@adnoc.ae","+971 2 600 1234","government",400000,45,"100-556677-8",bids["DXB-HQ"],eid("EMP-005")),
    ("CUS-011","Yousuf Al Hamdan","OSN Networks","UAE","Dubai","OSN HQ, Media City","y.hamdan@osn.com","+971 4 550 0011","broadcast",350000,45,"100-998877-6",bids["DXB-HQ"],eid("EMP-005")),
    ("CUS-012","Ahmad Al Jaber","Abu Dhabi Media","UAE","Abu Dhabi","ADM HQ, Al Bateen","a.jaber@adm.ae","+971 2 414 0012","broadcast",600000,60,"100-112233-4",bids["DXB-HQ"],eid("EMP-006")),
    ("CUS-013","Tariq Al-Rasheed","Rotana Media Group","Saudi Arabia","Riyadh","Rotana City, Riyadh","t.rasheed@rotana.net","+966 11 200 0013","broadcast",450000,45,"300-223344-5",bids["RUH-KSA"],eid("EMP-008")),
    ("CUS-014","Dina Mansour","Creative Media House","UAE","Dubai","Al Quoz, Dubai","dina@creativemediahouse.ae","+971 50 600 0014","corporate",100000,30,"100-445566-7",bids["DXB-HQ"],eid("EMP-007")),
    ("CUS-015","Waleed Farouk","ON TV Egypt","Egypt","Cairo","Smart Village, Cairo","w.farouk@ontv.eg","+20 10 700 0015","broadcast",200000,45,None,bids["CAI-EGY"],eid("EMP-009")),
]
cur.executemany("""INSERT INTO customers (customer_code,name,company,country,city,address,email,phone,account_type,
    credit_limit_aed,payment_terms_days,vat_reg_number,assigned_branch_id,assigned_sales_rep_id,created_date)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
    [(r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9],r[10],r[11],r[12],r[13],d(365)) for r in customers_raw])
def cuid(code): return cur.execute("SELECT id FROM customers WHERE customer_code=?", (code,)).fetchone()[0]

# ── PURCHASE ORDERS ───────────────────────────────────────────────────────────
pos = [
    ("PO-2026-001", sid("SUP-DJI"),  bids["DXB-WH"], eid("EMP-015"), d(65), d(44), "received",   62000, "USD"),
    ("PO-2026-002", sid("SUP-SON"),  bids["DXB-WH"], eid("EMP-015"), d(50), d(22), "received",   48500, "USD"),
    ("PO-2026-003", sid("SUP-RED"),  bids["DXB-WH"], eid("EMP-015"), d(40), d(5),  "in_transit", 24250, "USD"),
    ("PO-2026-004", sid("SUP-PRO"),  bids["DXB-WH"], eid("EMP-015"), d(30), f(5),  "open",       12800, "EUR"),
    ("PO-2026-005", sid("SUP-ZEI"),  bids["DXB-WH"], eid("EMP-015"), d(20), f(22), "open",       31110, "EUR"),
]
cur.executemany("INSERT INTO purchase_orders (po_ref,supplier_id,branch_id,created_by,order_date,expected_delivery,status,total_usd,currency) VALUES (?,?,?,?,?,?,?,?,?)", pos)
def poid(ref): return cur.execute("SELECT id FROM purchase_orders WHERE po_ref=?", (ref,)).fetchone()[0]

po_items = [
    (poid("PO-2026-001"), pid("DRN-001"), 10, 1393),
    (poid("PO-2026-001"), pid("GMB-001"), 8,  362),
    (poid("PO-2026-001"), pid("DRN-002"), 15, 533),
    (poid("PO-2026-002"), pid("CAM-001"), 4,  2850),
    (poid("PO-2026-002"), pid("CAM-002"), 2,  4190),
    (poid("PO-2026-002"), pid("STR-001"), 20, 315),
    (poid("PO-2026-003"), pid("CAM-005"), 1,  16975),
    (poid("PO-2026-004"), pid("LGT-001"), 5,  1050),
    (poid("PO-2026-004"), pid("LGT-002"), 8,  400),
    (poid("PO-2026-005"), pid("LNS-001"), 2,  5439),
    (poid("PO-2026-005"), pid("LNS-002"), 2,  5439),
    (poid("PO-2026-005"), pid("LNS-003"), 1,  5439),
]
cur.executemany("INSERT INTO purchase_order_items (po_id,product_id,qty_ordered,unit_cost_usd) VALUES (?,?,?,?)", po_items)

# ── INBOUND SHIPMENTS ─────────────────────────────────────────────────────────
inbound = [
    ("SHP-IN-001", poid("PO-2026-001"), sid("SUP-DJI"),  "China",       wids["WH-DXB-MAIN"], d(55), d(44), "delivered",  "Emirates SkyCargo","EK-CARGO-71234",0,None),
    ("SHP-IN-002", poid("PO-2026-002"), sid("SUP-SON"),  "Japan",       wids["WH-DXB-MAIN"], d(40), d(28), "delivered",  "DHL Express",       "DHL-AE-88301",  0,None),
    ("SHP-IN-003", poid("PO-2026-003"), sid("SUP-RED"),  "USA",         wids["WH-DXB-MAIN"], d(22), d(5),  "customs",    "FedEx International","FX-INT-99012", 1,"Customs hold — awaiting HS code clarification for 8K camera system"),
    ("SHP-IN-004", poid("PO-2026-004"), sid("SUP-PRO"),  "Sweden",      wids["WH-DXB-MAIN"], d(10), f(5),  "in_transit", "DHL Express",       "DHL-AE-91020",  0,None),
    ("SHP-IN-005", poid("PO-2026-005"), sid("SUP-ZEI"),  "Germany",     wids["WH-DXB-MAIN"], d(5),  f(22), "in_transit", "Lufthansa Cargo",   "LH-CARGO-45901",0,None),
]
cur.executemany("""INSERT INTO inbound_shipments (shipment_ref,po_id,supplier_id,origin_country,dest_warehouse_id,
    shipped_date,eta,status,carrier,tracking_number,customs_hold,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", inbound)

# ── SALES QUOTATIONS ──────────────────────────────────────────────────────────
quotes = [
    ("QT-2026-001", cuid("CUS-002"), eid("EMP-005"), d(30), d(15), "accepted", 176000),
    ("QT-2026-002", cuid("CUS-004"), eid("EMP-008"), d(20), f(10), "sent",     280000),
    ("QT-2026-003", cuid("CUS-006"), eid("EMP-006"), d(15), f(15), "sent",      96000),
    ("QT-2026-004", cuid("CUS-010"), eid("EMP-005"), d(10), f(20), "draft",    145000),
    ("QT-2026-005", cuid("CUS-007"), eid("EMP-008"), d(5),  f(25), "sent",      64000),
]
cur.executemany("INSERT INTO sales_quotations (quote_ref,customer_id,sales_rep_id,quote_date,valid_until,status,total_aed) VALUES (?,?,?,?,?,?,?)", quotes)
def qid(ref): return cur.execute("SELECT id FROM sales_quotations WHERE quote_ref=?", (ref,)).fetchone()[0]

# ── ORDERS ────────────────────────────────────────────────────────────────────
orders_data = [
    ("ORD-2026-001", cuid("CUS-001"), None,          eid("EMP-005"), bids["DXB-HQ"], d(120),"delivered", 67400, "AED","Tariq Mansoor"),
    ("ORD-2026-002", cuid("CUS-002"), qid("QT-2026-001"), eid("EMP-005"), bids["DXB-HQ"], d(90), "delivered", 176000,"AED","Tariq Mansoor"),
    ("ORD-2026-003", cuid("CUS-004"), None,          eid("EMP-008"), bids["RUH-KSA"], d(80), "shipped",  55000, "AED","Hassan Al-Masri"),
    ("ORD-2026-004", cuid("CUS-006"), None,          eid("EMP-006"), bids["DXB-HQ"], d(75), "delivered", 14900,"AED","Dina Al Amin"),
    ("ORD-2026-005", cuid("CUS-007"), None,          eid("EMP-008"), bids["RUH-KSA"], d(70), "confirmed", 93580,"AED","Hassan Al-Masri"),
    ("ORD-2026-006", cuid("CUS-010"), None,          eid("EMP-005"), bids["DXB-HQ"], d(55), "delivered", 44700,"AED","Tariq Mansoor"),
    ("ORD-2026-007", cuid("CUS-003"), None,          eid("EMP-007"), bids["DXB-HQ"], d(50), "delivered",  9200,"AED","Reem Sadiq"),
    ("ORD-2026-008", cuid("CUS-005"), None,          eid("EMP-009"), bids["CAI-EGY"],d(40), "shipped",  22000, "AED","Layla Nasser"),
    ("ORD-2026-009", cuid("CUS-008"), None,          eid("EMP-007"), bids["DXB-HQ"], d(20), "confirmed",  7299,"AED","Reem Sadiq"),
    ("ORD-2026-010", cuid("CUS-009"), None,          eid("EMP-006"), bids["DXB-HQ"], d(12), "pending",  36700, "AED","Dina Al Amin"),
    ("ORD-2026-011", cuid("CUS-011"), None,          eid("EMP-005"), bids["DXB-HQ"], d(8),  "confirmed",112000,"AED","Tariq Mansoor"),
    ("ORD-2026-012", cuid("CUS-013"), None,          eid("EMP-008"), bids["RUH-KSA"],d(5),  "pending",  85500, "AED","Hassan Al-Masri"),
]
cur.executemany("""INSERT INTO orders (order_ref,customer_id,quotation_id,sales_rep_id,branch_id,
    order_date,status,total_aed,currency,sales_rep) VALUES (?,?,?,?,?,?,?,?,?,?)""", orders_data)
def oid(ref): return cur.execute("SELECT id FROM orders WHERE order_ref=?", (ref,)).fetchone()[0]

order_items_data = [
    (oid("ORD-2026-001"), pid("CAM-002"), 2, 22000, 0),
    (oid("ORD-2026-001"), pid("LNS-001"), 1, 28500, 0),
    (oid("ORD-2026-001"), pid("GMB-001"), 1,  1899, 0),
    (oid("ORD-2026-002"), pid("CAM-008"), 2, 18500, 5),
    (oid("ORD-2026-002"), pid("AUD-002"), 4,  4600, 5),
    (oid("ORD-2026-002"), pid("REC-001"), 2,  9500, 5),
    (oid("ORD-2026-002"), pid("SUP-002"), 2,  9500, 5),
    (oid("ORD-2026-003"), pid("DRN-003"), 1, 55000, 0),
    (oid("ORD-2026-004"), pid("CAM-001"), 1, 14900, 0),
    (oid("ORD-2026-005"), pid("CAM-005"), 1, 89000, 5),
    (oid("ORD-2026-006"), pid("LGT-001"), 4,  5500, 0),
    (oid("ORD-2026-006"), pid("LGT-002"), 6,  2100, 0),
    (oid("ORD-2026-007"), pid("CAM-010"), 1,  9200, 0),
    (oid("ORD-2026-008"), pid("CAM-002"), 1, 22000, 0),
    (oid("ORD-2026-009"), pid("DRN-001"), 1,  7299, 0),
    (oid("ORD-2026-010"), pid("REC-003"), 1, 19500, 0),
    (oid("ORD-2026-010"), pid("AUD-002"), 1,  4600, 0),
    (oid("ORD-2026-010"), pid("REC-001"), 1,  9500, 0),
    (oid("ORD-2026-011"), pid("CAM-004"), 1,112000, 0),
    (oid("ORD-2026-012"), pid("CAM-003"), 2, 38000, 5),
    (oid("ORD-2026-012"), pid("LNS-004"), 1,  8900, 0),
]
cur.executemany("INSERT INTO order_items (order_id,product_id,qty,unit_price_aed,discount_pct) VALUES (?,?,?,?,?)", order_items_data)

# ── DELIVERIES ────────────────────────────────────────────────────────────────
deliveries = [
    ("DEL-2026-001", oid("ORD-2026-001"), wids["WH-DXB-MAIN"], d(118),"AMT Own Vehicle", None,           "delivered"),
    ("DEL-2026-002", oid("ORD-2026-002"), wids["WH-DXB-MAIN"], d(88), "DHL Express",    "DHL-OUT-71022", "delivered"),
    ("DEL-2026-004", oid("ORD-2026-004"), wids["WH-DXB-MAIN"], d(73), "AMT Own Vehicle", None,           "delivered"),
    ("DEL-2026-006", oid("ORD-2026-006"), wids["WH-DXB-MAIN"], d(53), "AMT Own Vehicle", None,           "delivered"),
    ("DEL-2026-007", oid("ORD-2026-007"), wids["WH-DXB-MAIN"], d(48), "AMT Own Vehicle", None,           "delivered"),
]
cur.executemany("INSERT INTO deliveries (delivery_ref,order_id,warehouse_id,delivery_date,carrier,tracking_number,status) VALUES (?,?,?,?,?,?,?)", deliveries)

# ── INVOICES (AR — Customer) ──────────────────────────────────────────────────
invoices = [
    ("INV-2026-001", oid("ORD-2026-001"), cuid("CUS-001"), bids["DXB-HQ"],  d(119),d(89), 67400, 3370, 5,"AED","paid",   d(95), "Bank Transfer"),
    ("INV-2026-002", oid("ORD-2026-002"), cuid("CUS-002"), bids["DXB-HQ"],  d(88), d(43),176000, 8800, 5,"AED","paid",   d(50), "Bank Transfer"),
    ("INV-2026-003", oid("ORD-2026-003"), cuid("CUS-004"), bids["RUH-KSA"], d(79), d(19), 55000, 8250,15,"SAR","overdue",None,  None),
    ("INV-2026-004", oid("ORD-2026-004"), cuid("CUS-006"), bids["DXB-HQ"],  d(74), d(44), 14900,  745, 5,"AED","paid",   d(48), "Bank Transfer"),
    ("INV-2026-005", oid("ORD-2026-005"), cuid("CUS-007"), bids["RUH-KSA"], d(69), d(39), 93580,14037,15,"SAR","overdue",None,  None),
    ("INV-2026-006", oid("ORD-2026-006"), cuid("CUS-010"), bids["DXB-HQ"],  d(54), d(24), 44700, 2235, 5,"AED","paid",   d(28), "Cheque"),
    ("INV-2026-007", oid("ORD-2026-007"), cuid("CUS-003"), bids["DXB-HQ"],  d(49), d(19),  9200,  460, 5,"AED","unpaid", None,  None),
    ("INV-2026-008", oid("ORD-2026-008"), cuid("CUS-005"), bids["CAI-EGY"], d(39), d(9),  22000, 3080,14,"EGP","overdue",None,  None),
    ("INV-2026-009", oid("ORD-2026-009"), cuid("CUS-008"), bids["DXB-HQ"],  d(19), f(11),  7299,  365, 5,"AED","unpaid", None,  None),
    ("INV-2026-010", oid("ORD-2026-010"), cuid("CUS-009"), bids["DXB-HQ"],  d(11), f(19), 36700, 1835, 5,"AED","unpaid", None,  None),
    ("INV-2026-011", oid("ORD-2026-011"), cuid("CUS-011"), bids["DXB-HQ"],  d(7),  f(38),112000, 5600, 5,"AED","unpaid", None,  None),
    ("INV-2026-012", oid("ORD-2026-012"), cuid("CUS-013"), bids["RUH-KSA"], d(4),  f(56), 85500,12825,15,"SAR","unpaid", None,  None),
]
cur.executemany("""INSERT INTO invoices (invoice_ref,order_id,customer_id,branch_id,issue_date,due_date,
    amount_aed,vat_aed,vat_rate_pct,currency,status,paid_date,payment_method) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", invoices)

# ── SUPPLIER INVOICES (AP) ────────────────────────────────────────────────────
sup_invoices = [
    ("SINV-2026-001", poid("PO-2026-001"), sid("SUP-DJI"), d(60), d(30), 62000, 62000*3.67,"paid", d(35)),
    ("SINV-2026-002", poid("PO-2026-002"), sid("SUP-SON"), d(45), d(15), 48500, 48500*3.67,"paid", d(18)),
    ("SINV-2026-003", poid("PO-2026-003"), sid("SUP-RED"), d(30), f(15), 24250, 24250*3.67,"unpaid",None),
]
cur.executemany("INSERT INTO supplier_invoices (inv_ref,po_id,supplier_id,issue_date,due_date,amount_usd,amount_aed,status,paid_date) VALUES (?,?,?,?,?,?,?,?,?)", sup_invoices)

# ── SERVICE TICKETS ───────────────────────────────────────────────────────────
tickets = [
    ("SVC-2026-001", cuid("CUS-001"), pid("DRN-001"),"MAV3P-AX1923",bids["DXB-WH"],eid("EMP-010"),"Drone lost GPS signal mid-flight, erratic return-to-home","Flight log reviewed — GPS module fault",         "in_repair",   "in_warranty", "high",   d(42),f(3), None, 0,   0,   "Karim Nour",None),
    ("SVC-2026-002", cuid("CUS-003"), pid("CAM-010"),"A7IV-DX8812", bids["DXB-WH"],eid("EMP-011"),"LCD screen flickering at shutter speeds above 1/500","Shutter assembly fault confirmed",                  "diagnosed",   "in_warranty", "normal", d(30),f(8), None, 0,   0,   "Hassan Bilal",None),
    ("SVC-2026-003", cuid("CUS-008"), pid("GMB-001"),"RS4P-GX3301", bids["DXB-WH"],eid("EMP-010"),"Motor overheating on axis 2, unresponsive at full load","IMU calibration failed — motor replacement needed", "awaiting_parts","out_of_warranty","normal",d(21),f(12),None,650,200, "Karim Nour",None),
    ("SVC-2026-004", cuid("CUS-002"), pid("AUD-002"),"EWDP-YZ0045", bids["DXB-WH"],None,         "Receiver drops wireless signal beyond 30m range",None,                                                   "open",        "in_warranty", "normal", d(10),f(18),None, 0,   0,   None,  None),
    ("SVC-2026-005", cuid("CUS-010"), pid("CAM-001"),"FX3-ZZ7734",  bids["DXB-WH"],eid("EMP-011"),"Overexposure in S-Log3 regardless of settings, sensor issue","Sensor calibration needed — Sony parts ordered",   "ready",       "in_warranty", "high",   d(24),d(2), d(2), 0,   0,   "Hassan Bilal",None),
    ("SVC-2026-006", cuid("CUS-006"), pid("LGT-001"),"B10X-PP2290", bids["DXB-WH"],eid("EMP-010"),"Flash not recycling at full power — battery fault suspected","Battery cell failure confirmed. Replaced.",         "closed",      "out_of_warranty","low",d(68),d(38),d(40),980,350, "Karim Nour",None),
    ("SVC-2026-007", cuid("CUS-007"), pid("DRN-005"),"M350-KK8821", bids["RUH-KSA"],eid("EMP-018"),"RTK module not acquiring GPS fix on site","Firmware update resolved partial fix. RTK antenna check in progress","in_repair","in_warranty","urgent",d(7), f(5),None, 0,   0,   "Nour Al-Rashid",None),
    ("SVC-2026-008", cuid("CUS-004"), pid("CAM-008"),"Z280-SA1122", bids["RUH-KSA"],eid("EMP-018"),"4K recording drops to HD unexpectedly on XQD media","Media card format mismatch — Sony XQD firmware issue",  "diagnosed",   "in_warranty", "normal", d(5), f(10),None, 0,   0,   "Nour Al-Rashid",None),
]
cur.executemany("""INSERT INTO service_tickets (ticket_ref,customer_id,product_id,serial_number,branch_id,technician_id,
    issue_description,diagnosis_notes,status,warranty_status,priority,received_date,estimated_completion,
    closed_date,repair_cost_aed,parts_cost_aed,technician,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", tickets)

# ── WARRANTY REGISTRATIONS ────────────────────────────────────────────────────
warranties = [
    (pid("CAM-001"),"FX3-ZZ7734", cuid("CUS-010"),d(90), d(-275),d(80), bids["DXB-WH"]),
    (pid("DRN-001"),"MAV3P-AX1923",cuid("CUS-001"),d(130),d(-235),d(120),bids["DXB-WH"]),
    (pid("CAM-010"),"A7IV-DX8812",cuid("CUS-003"),d(200),d(-165),d(190),bids["DXB-WH"]),
    (pid("GMB-001"),"RS4P-GX3301",cuid("CUS-008"),d(400),d(35),  d(390),bids["DXB-WH"]),
    (pid("AUD-002"),"EWDP-YZ0045",cuid("CUS-002"),d(25), d(340), d(20), bids["DXB-WH"]),
]
cur.executemany("""INSERT INTO warranty_registrations (product_id,serial_number,customer_id,
    purchase_date,warranty_expiry,registered_date,branch_id) VALUES (?,?,?,?,?,?,?)""", warranties)

conn.commit()
conn.close()

print(f"Database rebuilt at {DB_PATH}")
rows = lambda t: sqlite3.connect(DB_PATH).execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
for table in ["branches","warehouses","employees","suppliers","product_categories","products",
              "inventory","customers","purchase_orders","orders","invoices","service_tickets","warranty_registrations"]:
    print(f"  {table:<28} {rows(table)} rows")
