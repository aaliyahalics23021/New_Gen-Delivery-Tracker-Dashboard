-- Schema for Next Gen Delivery Dashboard
CREATE TABLE IF NOT EXISTS drivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    customer_contact TEXT,
    product TEXT NOT NULL,
    price REAL DEFAULT 0,
    driver_id INTEGER,
    status TEXT DEFAULT 'Pending',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(driver_id) REFERENCES drivers(id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evt_type TEXT NOT NULL,        -- e.g. delivery_added, driver_deleted, status_changed
    entity TEXT,                   -- 'delivery' or 'driver'
    entity_id INTEGER,             -- id of delivery/driver (if applicable)
    message TEXT NOT NULL,         -- human readable message
    from_status TEXT,              -- previous status (nullable)
    to_status TEXT,                -- new status (nullable)
    ts TEXT DEFAULT (datetime('now'))   -- timestamp
);
