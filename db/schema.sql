-- AMT Demo Database Schema

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    category TEXT NOT NULL,   -- camera, lens, drone, audio, lighting, gimbal, storage, accessory
    description TEXT,
    price_aed REAL NOT NULL,
    price_usd REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER REFERENCES products(id),
    qty_on_hand INTEGER NOT NULL DEFAULT 0,
    qty_reserved INTEGER NOT NULL DEFAULT 0,
    warehouse TEXT DEFAULT 'Al Quoz, Dubai',
    last_updated TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company TEXT,
    country TEXT DEFAULT 'UAE',
    email TEXT,
    phone TEXT,
    account_type TEXT DEFAULT 'retail'  -- retail, corporate, reseller
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_ref TEXT UNIQUE NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    order_date TEXT NOT NULL,
    status TEXT DEFAULT 'pending',      -- pending, confirmed, shipped, delivered, cancelled
    total_aed REAL NOT NULL,
    sales_rep TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    qty INTEGER NOT NULL,
    unit_price_aed REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_ref TEXT UNIQUE NOT NULL,
    order_id INTEGER REFERENCES orders(id),
    customer_id INTEGER REFERENCES customers(id),
    issue_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    amount_aed REAL NOT NULL,
    vat_aed REAL NOT NULL,
    status TEXT DEFAULT 'unpaid',       -- unpaid, paid, overdue, disputed
    paid_date TEXT
);

CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_ref TEXT UNIQUE NOT NULL,
    order_id INTEGER REFERENCES orders(id),
    supplier TEXT,
    origin_country TEXT,
    destination TEXT DEFAULT 'Dubai, UAE',
    shipped_date TEXT,
    eta TEXT,
    status TEXT DEFAULT 'in_transit',   -- ordered, in_transit, customs, delivered, delayed
    carrier TEXT,
    tracking_number TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS service_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_ref TEXT UNIQUE NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    product_id INTEGER REFERENCES products(id),
    serial_number TEXT,
    issue_description TEXT NOT NULL,
    status TEXT DEFAULT 'open',         -- open, diagnosed, in_repair, awaiting_parts, ready, closed
    warranty_status TEXT DEFAULT 'in_warranty',  -- in_warranty, out_of_warranty, void
    received_date TEXT NOT NULL,
    estimated_completion TEXT,
    technician TEXT,
    repair_cost_aed REAL DEFAULT 0,
    notes TEXT
);
