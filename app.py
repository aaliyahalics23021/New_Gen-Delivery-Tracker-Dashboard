from flask import Flask, render_template, request, redirect, flash
import sqlite3
import os
from datetime import datetime, timedelta
import random
import string

app = Flask(__name__)
app.secret_key = "secret123"
DATABASE = "tracker.db"

# ---------------- Database connection ----------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- Initialize database ----------------
def init_db():
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        conn.execute('''CREATE TABLE deliveries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER,
                        tracking_id TEXT,
                        customer TEXT,
                        product TEXT,
                        amount_paid REAL,
                        status TEXT DEFAULT 'Pending',
                        driver_name TEXT,
                        order_date TEXT,
                        estimated_delivery TEXT
                        )''')
        conn.execute('''CREATE TABLE drivers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        phone TEXT
                        )''')
        # Add predefined drivers
        predefined_drivers = [
            ("Vinay", "9876543210"),
            ("Aman", "9123456780"),
            ("Akshad", "9988776655"),
            ("Amrit", "9012345678"),
            ("Soham", "9234567890")
        ]
        conn.executemany("INSERT INTO drivers (name, phone) VALUES (?,?)", predefined_drivers)
        conn.commit()
        conn.close()

# ---------------- Routes ----------------
@app.route("/")
def index():
    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    conn = get_db_connection()
    deliveries = conn.execute("SELECT * FROM deliveries ORDER BY id DESC").fetchall()
    drivers = conn.execute("SELECT * FROM drivers").fetchall()
    notifications = conn.execute("SELECT * FROM deliveries ORDER BY id DESC LIMIT 5").fetchall()
    conn.close()
    return render_template("dashboard.html", deliveries=deliveries, drivers=drivers, notifications=notifications)

@app.route("/add_delivery", methods=["GET", "POST"])
def add_delivery():
    conn = get_db_connection()
    drivers = conn.execute("SELECT * FROM drivers").fetchall()
    if request.method == "POST":
        customer = request.form.get("customer")
        product = request.form.get("product")
        amount = float(request.form.get("amount"))
        driver = request.form.get("driver")

        order_id = random.randint(100000, 999999)
        tracking_id = "TRK" + "".join(random.choices(string.digits, k=6))
        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        estimated_delivery = (datetime.now() + timedelta(days=random.randint(2,10))).strftime("%Y-%m-%d %H:%M:%S")
        status = "Pending"

        conn.execute(
            "INSERT INTO deliveries (order_id, tracking_id, customer, product, amount_paid, status, driver_name, order_date, estimated_delivery) VALUES (?,?,?,?,?,?,?,?,?)",
            (order_id, tracking_id, customer, product, amount, status, driver, order_date, estimated_delivery)
        )
        conn.commit()
        conn.close()
        flash(f"New delivery created: {order_id}")
        return redirect("/dashboard")
    conn.close()
    return render_template("add_delivery.html", drivers=drivers)

@app.route("/add_driver", methods=["GET","POST"])
def add_driver():
    if request.method=="POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        conn = get_db_connection()
        conn.execute("INSERT INTO drivers (name, phone) VALUES (?,?)", (name, phone))
        conn.commit()
        conn.close()
        flash(f"New driver added: {name}")
        return redirect("/dashboard")
    return render_template("add_driver.html")

@app.route("/update_status/<int:id>", methods=["POST"])
def update_status(id):
    new_status = request.form.get("status")
    conn = get_db_connection()
    old = conn.execute("SELECT customer, status FROM deliveries WHERE id=?", (id,)).fetchone()
    conn.execute("UPDATE deliveries SET status=? WHERE id=?", (new_status, id))
    conn.commit()
    conn.close()
    flash(f"Order #{id} ({old['customer']}) status updated from {old['status']} → {new_status} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return redirect("/dashboard")

@app.route("/delete/<int:id>", methods=["POST"])
def delete_delivery(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM deliveries WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash(f"Delivery #{id} deleted")
    return redirect("/dashboard")

@app.route("/delete_driver/<int:id>", methods=["POST"])
def delete_driver(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM drivers WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash(f"Driver deleted")
    return redirect("/dashboard")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
