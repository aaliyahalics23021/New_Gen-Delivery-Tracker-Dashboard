from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "deliveries.db")

app = Flask(__name__)
app.config['DATABASE'] = DB_PATH

# --- DB helpers ---
def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(app.config['DATABASE']):
        open(app.config['DATABASE'], 'a').close()
    conn = get_db()
    sql_path = os.path.join(BASE_DIR, 'schema.sql')
    if os.path.exists(sql_path):
        with open(sql_path, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
    conn.commit()
    conn.close()

# --- Notification utility ---
def log_notification(evt_type, entity, entity_id, message, from_status=None, to_status=None):
    ts = datetime.utcnow().isoformat() + "Z"
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notifications (evt_type, entity, entity_id, message, from_status, to_status, ts) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (evt_type, entity, entity_id, message, from_status, to_status, ts)
    )
    conn.commit()
    conn.close()

# --- Routes ---
@app.route('/')
def index():
    conn = get_db()
    cur = conn.cursor()
    deliveries = cur.execute("""
        SELECT d.*, drv.name as driver_name
        FROM deliveries d
        LEFT JOIN drivers drv ON d.driver_id = drv.id
        ORDER BY d.updated_at DESC, d.created_at DESC
    """).fetchall()
    drivers = cur.execute("SELECT * FROM drivers ORDER BY created_at DESC").fetchall()
    notifications = cur.execute("SELECT * FROM notifications ORDER BY ts DESC LIMIT 50").fetchall()
    conn.close()
    return render_template('index.html', deliveries=deliveries, drivers=drivers, notifications=notifications)

# API endpoints used by JS (and form actions)
@app.route('/api/drivers', methods=['POST'])
def api_add_driver():
    data = request.form
    name = data.get('name','').strip()
    contact = data.get('contact','').strip()
    if not name:
        return jsonify({'success': False, 'error': 'Driver name required'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO drivers (name, contact) VALUES (?, ?)", (name, contact))
    driver_id = cur.lastrowid
    conn.commit()
    conn.close()
    log_notification('driver_added','driver', driver_id, f"Driver added: {name}")
    return jsonify({'success': True, 'driver': {'id': driver_id, 'name': name, 'contact': contact}})

@app.route('/api/deliveries', methods=['POST'])
def api_add_delivery():
    data = request.form
    customer_name = data.get('customer_name','').strip()
    customer_contact = data.get('customer_contact','').strip()
    product = data.get('product','').strip()
    price = data.get('price','0').strip()
    driver_id = data.get('driver_id') or None
    try:
        price_val = float(price)
    except:
        price_val = 0.0
    if not customer_name or not product:
        return jsonify({'success':False, 'error':'Missing fields'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO deliveries (customer_name, customer_contact, product, price, driver_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
        (customer_name, customer_contact, product, price_val, driver_id, 'Pending')
    )
    delivery_id = cur.lastrowid
    conn.commit()
    conn.close()
    log_notification('delivery_added','delivery', delivery_id, f"Delivery added: {customer_name} — {product}")
    return jsonify({'success': True, 'delivery_id': delivery_id})

@app.route('/api/delete_driver', methods=['POST'])
def api_delete_driver():
    driver_id = request.form.get('id')
    if not driver_id:
        return jsonify({'success': False, 'error':'id required'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM drivers WHERE id = ?", (driver_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Driver not found'}), 404
    name = row['name']
    cur.execute("DELETE FROM drivers WHERE id = ?", (driver_id,))
    conn.commit()
    conn.close()
    log_notification('driver_deleted','driver', driver_id, f"Driver removed: {name}")
    return jsonify({'success': True, 'removed': name})

@app.route('/api/delete_delivery', methods=['POST'])
def api_delete_delivery():
    delivery_id = request.form.get('id')
    if not delivery_id:
        return jsonify({'success': False, 'error':'id required'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT customer_name, product FROM deliveries WHERE id = ?", (delivery_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Delivery not found'}), 404
    customer_name = row['customer_name']
    product = row['product']
    cur.execute("DELETE FROM deliveries WHERE id = ?", (delivery_id,))
    conn.commit()
    conn.close()
    log_notification('delivery_deleted','delivery', delivery_id, f"Delivery removed: {customer_name} — {product}")
    return jsonify({'success': True, 'removed': customer_name})

@app.route('/api/update_status', methods=['POST'])
def api_update_status():
    data = request.get_json() or {}
    delivery_id = data.get('id')
    new_status = data.get('status')
    if not delivery_id or new_status is None:
        return jsonify({'success': False, 'error': 'missing'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT status, customer_name FROM deliveries WHERE id = ?", (delivery_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'delivery not found'}), 404
    old_status = row['status']
    customer_name = row['customer_name']
    cur.execute("UPDATE deliveries SET status = ?, updated_at = datetime('now') WHERE id = ?", (new_status, delivery_id))
    conn.commit()
    conn.close()
    log_notification('status_changed','delivery', delivery_id, f"Status for {customer_name}: {old_status} → {new_status}", from_status=old_status, to_status=new_status)
    return jsonify({'success': True, 'from': old_status, 'to': new_status, 'customer_name': customer_name, 'when': datetime.utcnow().isoformat() + "Z"})

# Read endpoints for JS
@app.route('/api/get_deliveries')
def api_get_deliveries():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT d.*, drv.name as driver_name
        FROM deliveries d
        LEFT JOIN drivers drv ON d.driver_id = drv.id
        ORDER BY d.updated_at DESC, d.created_at DESC
    """).fetchall()
    out = [dict(r) for r in rows]
    conn.close()
    return jsonify(out)

@app.route('/api/get_notifications')
def api_get_notifications():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM notifications ORDER BY ts DESC LIMIT 100").fetchall()
    out = [dict(r) for r in rows]
    conn.close()
    return jsonify(out)

@app.route('/api/get_drivers')
def api_get_drivers():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM drivers ORDER BY created_at DESC").fetchall()
    out = [dict(r) for r in rows]
    conn.close()
    return jsonify(out)

# Simple pages that use the modern UI but the forms use JS calls
@app.route('/add_driver')
def add_driver_page():
    return render_template('add_driver.html')

@app.route('/add_delivery')
def add_delivery_page():
    return render_template('add_delivery.html')

# --- Start ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
