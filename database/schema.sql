PRAGMA foreign_keys = ON;

CREATE TABLE locations (
    location TEXT PRIMARY KEY
);

CREATE TABLE sku_master (
    row_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    product_type TEXT NOT NULL,
    semiconductor_dependent INTEGER NOT NULL CHECK (semiconductor_dependent IN (0, 1)),
    unit_margin_aed REAL NOT NULL CHECK (unit_margin_aed >= 0),
    unit_value_aed REAL NOT NULL CHECK (unit_value_aed >= 0),
    timestamp TEXT NOT NULL,
    source_system TEXT NOT NULL
);

CREATE TABLE inventory (
    row_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL REFERENCES sku_master(sku),
    location TEXT NOT NULL REFERENCES locations(location),
    available INTEGER NOT NULL CHECK (available >= 0),
    reserved INTEGER NOT NULL CHECK (reserved >= 0),
    timestamp TEXT NOT NULL,
    source_system TEXT NOT NULL,
    UNIQUE (sku, location)
);

CREATE TABLE safety_stock (
    row_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL,
    location TEXT NOT NULL,
    safety_stock INTEGER NOT NULL CHECK (safety_stock >= 0),
    timestamp TEXT NOT NULL,
    source_system TEXT NOT NULL,
    UNIQUE (sku, location),
    FOREIGN KEY (sku, location) REFERENCES inventory(sku, location)
);

CREATE TABLE sales_history (
    row_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL,
    location TEXT NOT NULL,
    sale_date TEXT NOT NULL CHECK (sale_date GLOB '????-??-??'),
    units INTEGER NOT NULL CHECK (units >= 0),
    was_stockout INTEGER NOT NULL CHECK (was_stockout IN (0, 1)),
    order_type TEXT NOT NULL CHECK (order_type IN ('regular', 'bulk')),
    timestamp TEXT NOT NULL,
    source_system TEXT NOT NULL,
    UNIQUE (sku, location, sale_date),
    FOREIGN KEY (sku, location) REFERENCES inventory(sku, location)
);

CREATE TABLE stock_age (
    row_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL,
    location TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    units INTEGER NOT NULL CHECK (units >= 0),
    age_days INTEGER NOT NULL CHECK (age_days >= 0),
    timestamp TEXT NOT NULL,
    source_system TEXT NOT NULL,
    UNIQUE (sku, location, batch_id),
    FOREIGN KEY (sku, location) REFERENCES inventory(sku, location)
);

CREATE TABLE inbound_orders (
    row_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL,
    location TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    arrival_date TEXT NOT NULL CHECK (arrival_date GLOB '????-??-??'),
    supplier_lead_days INTEGER NOT NULL CHECK (supplier_lead_days >= 0),
    shipping_route TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    source_system TEXT NOT NULL,
    FOREIGN KEY (sku, location) REFERENCES inventory(sku, location)
);

CREATE TABLE transfer_costs (
    row_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL REFERENCES sku_master(sku),
    from_location TEXT NOT NULL REFERENCES locations(location),
    to_location TEXT NOT NULL REFERENCES locations(location),
    lead_days INTEGER NOT NULL CHECK (lead_days >= 1),
    variable_cost_aed REAL NOT NULL CHECK (variable_cost_aed >= 0),
    fixed_cost_aed REAL NOT NULL CHECK (fixed_cost_aed >= 0),
    timestamp TEXT NOT NULL,
    source_system TEXT NOT NULL,
    UNIQUE (sku, from_location, to_location),
    CHECK (from_location <> to_location)
);

CREATE TABLE holding_costs (
    row_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE REFERENCES sku_master(sku),
    per_unit_day_aed REAL NOT NULL CHECK (per_unit_day_aed >= 0),
    ageing_penalty_aed REAL NOT NULL CHECK (ageing_penalty_aed >= 0),
    timestamp TEXT NOT NULL,
    source_system TEXT NOT NULL
);

CREATE TABLE events (
    row_id TEXT PRIMARY KEY,
    scenario TEXT NOT NULL UNIQUE CHECK (scenario IN ('component_shortage', 'shipping_delay')),
    label TEXT NOT NULL CHECK (label LIKE '%FICTIONAL%'),
    affected_skus TEXT NOT NULL,
    shipping_route TEXT NOT NULL,
    demand_multiplier REAL NOT NULL CHECK (demand_multiplier > 0),
    delay_days INTEGER NOT NULL CHECK (delay_days >= 0),
    assumption TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    source_system TEXT NOT NULL
);

CREATE TABLE answer_key (
    row_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    sku TEXT,
    location TEXT,
    start_date TEXT,
    end_date TEXT,
    expected TEXT,
    note TEXT NOT NULL,
    version TEXT NOT NULL,
    timestamp TEXT,
    source_system TEXT
);

CREATE INDEX idx_sales_history_position_date ON sales_history (sku, location, sale_date);
CREATE INDEX idx_inbound_orders_position_eta ON inbound_orders (sku, location, arrival_date);
CREATE INDEX idx_stock_age_position ON stock_age (sku, location);
CREATE INDEX idx_transfer_costs_route ON transfer_costs (sku, from_location, to_location);
