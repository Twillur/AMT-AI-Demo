-- ============================================================
-- AMT LLC — SAP-aligned SQLite Schema
-- Mirrors: SAP SD (Sales & Distribution), MM (Materials Mgmt),
--          FI (Finance), CS (Customer Service), WM (Warehouse)
-- Branches: Dubai HQ, Al Quoz Warehouse+Service, Riyadh, Cairo
-- ============================================================

PRAGMA foreign_keys = ON;

-- ── MASTER DATA ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS branches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_code     TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    city            TEXT NOT NULL,
    country         TEXT NOT NULL,
    address         TEXT,
    phone           TEXT,
    currency        TEXT NOT NULL DEFAULT 'AED',
    vat_rate_pct    REAL NOT NULL DEFAULT 5.0,
    is_warehouse    INTEGER NOT NULL DEFAULT 0,
    is_service_ctr  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS employees (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    role            TEXT NOT NULL,
    department      TEXT NOT NULL,
    branch_id       INTEGER REFERENCES branches(id),
    email           TEXT,
    phone           TEXT,
    hire_date       TEXT
);

CREATE TABLE IF NOT EXISTS suppliers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_code   TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    country         TEXT NOT NULL,
    city            TEXT,
    contact_name    TEXT,
    contact_email   TEXT,
    payment_terms_days INTEGER DEFAULT 60,
    lead_time_days  INTEGER DEFAULT 30,
    currency        TEXT NOT NULL DEFAULT 'USD',
    authorized_brands TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS product_categories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    parent_id       INTEGER REFERENCES product_categories(id)
);

CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sku             TEXT UNIQUE NOT NULL,
    brand           TEXT NOT NULL,
    model           TEXT NOT NULL,
    category        TEXT NOT NULL,
    category_id     INTEGER REFERENCES product_categories(id),
    description     TEXT,
    supplier_id     INTEGER REFERENCES suppliers(id),
    price_aed       REAL NOT NULL,
    price_usd       REAL,
    cost_usd        REAL,
    hs_code         TEXT,
    weight_kg       REAL,
    warranty_months INTEGER DEFAULT 12,
    is_serialized   INTEGER DEFAULT 1,
    is_active       INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS warehouses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_code  TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    branch_id       INTEGER REFERENCES branches(id),
    address         TEXT
);

CREATE TABLE IF NOT EXISTS inventory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(id),
    warehouse_id    INTEGER NOT NULL REFERENCES warehouses(id),
    qty_on_hand     INTEGER NOT NULL DEFAULT 0,
    qty_reserved    INTEGER NOT NULL DEFAULT 0,
    qty_on_order    INTEGER NOT NULL DEFAULT 0,
    reorder_point   INTEGER DEFAULT 2,
    UNIQUE(product_id, warehouse_id)
);

CREATE TABLE IF NOT EXISTS price_lists (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_type   TEXT NOT NULL,
    product_id      INTEGER NOT NULL REFERENCES products(id),
    price_aed       REAL NOT NULL,
    discount_pct    REAL DEFAULT 0,
    valid_from      TEXT,
    valid_to        TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_code   TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    company         TEXT,
    country         TEXT NOT NULL DEFAULT 'UAE',
    city            TEXT,
    address         TEXT,
    email           TEXT,
    phone           TEXT,
    account_type    TEXT NOT NULL DEFAULT 'corporate',
    credit_limit_aed REAL DEFAULT 50000,
    payment_terms_days INTEGER DEFAULT 30,
    vat_reg_number  TEXT,
    assigned_branch_id INTEGER REFERENCES branches(id),
    assigned_sales_rep_id INTEGER REFERENCES employees(id),
    created_date    TEXT
);

-- ── PROCUREMENT — SAP MM ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS purchase_orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    po_ref          TEXT UNIQUE NOT NULL,
    supplier_id     INTEGER NOT NULL REFERENCES suppliers(id),
    branch_id       INTEGER REFERENCES branches(id),
    created_by      INTEGER REFERENCES employees(id),
    order_date      TEXT NOT NULL,
    expected_delivery TEXT,
    status          TEXT NOT NULL DEFAULT 'open',
    total_usd       REAL,
    currency        TEXT DEFAULT 'USD',
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS purchase_order_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id           INTEGER NOT NULL REFERENCES purchase_orders(id),
    product_id      INTEGER NOT NULL REFERENCES products(id),
    qty_ordered     INTEGER NOT NULL,
    unit_cost_usd   REAL NOT NULL,
    qty_received    INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS inbound_shipments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_ref    TEXT UNIQUE NOT NULL,
    po_id           INTEGER REFERENCES purchase_orders(id),
    supplier_id     INTEGER REFERENCES suppliers(id),
    origin_country  TEXT,
    dest_warehouse_id INTEGER REFERENCES warehouses(id),
    shipped_date    TEXT,
    eta             TEXT,
    status          TEXT NOT NULL DEFAULT 'ordered',
    carrier         TEXT,
    tracking_number TEXT,
    customs_hold    INTEGER DEFAULT 0,
    notes           TEXT
);

-- Keep legacy 'shipments' as alias view for agent compatibility
CREATE VIEW IF NOT EXISTS shipments AS
    SELECT
        s.id, s.shipment_ref, s.po_id AS order_id,
        sup.name AS supplier, sup.country AS origin_country,
        'Dubai, UAE' AS destination,
        s.shipped_date, s.eta, s.status,
        s.carrier, s.tracking_number, s.notes
    FROM inbound_shipments s
    JOIN suppliers sup ON sup.id = s.supplier_id;

-- ── SALES — SAP SD ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sales_quotations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_ref       TEXT UNIQUE NOT NULL,
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    sales_rep_id    INTEGER REFERENCES employees(id),
    quote_date      TEXT NOT NULL,
    valid_until     TEXT,
    status          TEXT NOT NULL DEFAULT 'sent',
    total_aed       REAL,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS quotation_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_id        INTEGER NOT NULL REFERENCES sales_quotations(id),
    product_id      INTEGER NOT NULL REFERENCES products(id),
    qty             INTEGER NOT NULL,
    unit_price_aed  REAL NOT NULL,
    discount_pct    REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_ref       TEXT UNIQUE NOT NULL,
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    quotation_id    INTEGER REFERENCES sales_quotations(id),
    sales_rep_id    INTEGER REFERENCES employees(id),
    branch_id       INTEGER REFERENCES branches(id),
    order_date      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'confirmed',
    total_aed       REAL NOT NULL,
    currency        TEXT DEFAULT 'AED',
    delivery_address TEXT,
    sales_rep       TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    product_id      INTEGER NOT NULL REFERENCES products(id),
    qty             INTEGER NOT NULL,
    unit_price_aed  REAL NOT NULL,
    discount_pct    REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS deliveries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    delivery_ref    TEXT UNIQUE NOT NULL,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    warehouse_id    INTEGER REFERENCES warehouses(id),
    delivery_date   TEXT,
    carrier         TEXT,
    tracking_number TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    notes           TEXT
);

-- ── FINANCE — SAP FI ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS invoices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_ref     TEXT UNIQUE NOT NULL,
    order_id        INTEGER REFERENCES orders(id),
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    branch_id       INTEGER REFERENCES branches(id),
    issue_date      TEXT NOT NULL,
    due_date        TEXT NOT NULL,
    amount_aed      REAL NOT NULL,
    vat_aed         REAL NOT NULL DEFAULT 0,
    vat_rate_pct    REAL NOT NULL DEFAULT 5,
    currency        TEXT DEFAULT 'AED',
    status          TEXT NOT NULL DEFAULT 'unpaid',
    paid_date       TEXT,
    payment_method  TEXT
);

CREATE TABLE IF NOT EXISTS supplier_invoices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    inv_ref         TEXT UNIQUE NOT NULL,
    po_id           INTEGER REFERENCES purchase_orders(id),
    supplier_id     INTEGER NOT NULL REFERENCES suppliers(id),
    issue_date      TEXT NOT NULL,
    due_date        TEXT NOT NULL,
    amount_usd      REAL NOT NULL,
    amount_aed      REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'unpaid',
    paid_date       TEXT
);

-- ── SERVICE — SAP CS ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS service_tickets (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_ref          TEXT UNIQUE NOT NULL,
    customer_id         INTEGER NOT NULL REFERENCES customers(id),
    product_id          INTEGER NOT NULL REFERENCES products(id),
    serial_number       TEXT,
    branch_id           INTEGER REFERENCES branches(id),
    technician_id       INTEGER REFERENCES employees(id),
    issue_description   TEXT NOT NULL,
    diagnosis_notes     TEXT,
    status              TEXT NOT NULL DEFAULT 'open',
    warranty_status     TEXT NOT NULL DEFAULT 'in_warranty',
    priority            TEXT DEFAULT 'normal',
    received_date       TEXT NOT NULL,
    estimated_completion TEXT,
    closed_date         TEXT,
    repair_cost_aed     REAL DEFAULT 0,
    parts_cost_aed      REAL DEFAULT 0,
    technician          TEXT,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS warranty_registrations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(id),
    serial_number   TEXT UNIQUE NOT NULL,
    customer_id     INTEGER REFERENCES customers(id),
    purchase_date   TEXT NOT NULL,
    warranty_expiry TEXT NOT NULL,
    registered_date TEXT,
    branch_id       INTEGER REFERENCES branches(id)
);
