import logging
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()  # load .env BEFORE anything reads environment variables

from flask import Flask, jsonify, request, send_from_directory  # noqa: E402
from flask.json.provider import DefaultJSONProvider  # noqa: E402
from psycopg.errors import UniqueViolation  # noqa: E402
from werkzeug.exceptions import HTTPException  # noqa: E402

import ai  # noqa: E402
import db  # noqa: E402

logging.basicConfig(level=logging.INFO)
ALLOWED_STATUS = ("lead", "active", "inactive")


class JSONProvider(DefaultJSONProvider):
    """PostgreSQL returns real datetime objects; send them to the browser as ISO-8601 strings."""
    @staticmethod
    def default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        return DefaultJSONProvider.default(o)


app = Flask(__name__, static_folder="static", static_url_path="/static")
app.json = JSONProvider(app)
db.init_db()


def error(message, status, **extra):
    return jsonify({"error": message, **extra}), status


def get_customer(conn, customer_id):
    # %s is psycopg's parameter placeholder (the value is sent separately -> no SQL injection)
    return conn.execute("SELECT * FROM customers WHERE id = %s", (customer_id,)).fetchone()


def validate_customer(data, existing=None):
    """Create: name + phone required. Update: unsent fields keep their old value."""
    if not isinstance(data, dict):
        return None, ["request body must be a JSON object"]
    errors = []
    values = {k: existing[k] for k in ("name", "phone", "status")} if existing else {"status": "lead"}

    for field in ("name", "phone"):
        if existing is None or field in data:
            value = data.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{field} is required and must not be empty")
            else:
                values[field] = value.strip()

    if "status" in data:
        if data["status"] not in ALLOWED_STATUS:
            errors.append("status must be one of: " + ", ".join(ALLOWED_STATUS))
        else:
            values["status"] = data["status"]
    return values, errors


# ---------------------------------------------------------------- Task 2: CRUD

@app.post("/customers")
def create_customer():
    values, errors = validate_customer(request.get_json(silent=True))
    if errors:
        return error("Validation failed", 400, details=errors)
    try:
        with db.connect() as conn:
            customer = conn.execute(
                "INSERT INTO customers (name, phone, status) VALUES (%s, %s, %s) RETURNING *",
                (values["name"], values["phone"], values["status"])).fetchone()
    except UniqueViolation:  # UNIQUE(phone) fired
        return error("Phone number already exists", 409)
    return jsonify(customer), 201


@app.get("/customers")
def list_customers():
    status = request.args.get("status")
    if status is not None and status not in ALLOWED_STATUS:
        return error("status filter must be one of: " + ", ".join(ALLOWED_STATUS), 400)
    sql, params = "SELECT * FROM customers", []
    if status:
        sql += " WHERE status = %s"
        params.append(status)
    with db.connect() as conn:
        rows = conn.execute(sql + " ORDER BY id DESC", params).fetchall()
    return jsonify(rows), 200


@app.get("/customers/<int:customer_id>")
def read_customer(customer_id):
    with db.connect() as conn:
        customer = get_customer(conn, customer_id)
        if not customer:
            return error("Customer not found", 404)
        customer["messages"] = conn.execute(
            "SELECT id, direction, content, created_at FROM messages "
            "WHERE customer_id = %s ORDER BY id", (customer_id,)).fetchall()
    return jsonify(customer), 200


@app.put("/customers/<int:customer_id>")
def update_customer(customer_id):
    try:
        with db.connect() as conn:
            existing = get_customer(conn, customer_id)
            if not existing:
                return error("Customer not found", 404)
            values, errors = validate_customer(request.get_json(silent=True), existing)
            if errors:
                return error("Validation failed", 400, details=errors)
            customer = conn.execute(
                "UPDATE customers SET name = %s, phone = %s, status = %s WHERE id = %s RETURNING *",
                (values["name"], values["phone"], values["status"], customer_id)).fetchone()
    except UniqueViolation:
        return error("Phone number already exists", 409)
    return jsonify(customer), 200


@app.delete("/customers/<int:customer_id>")
def delete_customer(customer_id):
    with db.connect() as conn:
        if not get_customer(conn, customer_id):
            return error("Customer not found", 404)
        conn.execute("DELETE FROM customers WHERE id = %s", (customer_id,))  # messages deleted by CASCADE
    return jsonify({"message": "Customer deleted", "id": customer_id}), 200


# ---------------------------------------------------------------- Task 3: webhook

@app.post("/webhook/incoming-message")
def incoming_message():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("Request body must be a JSON object", 400)

    errors = []
    phone, message, name = data.get("phone"), data.get("message"), data.get("name")
    if not isinstance(phone, str) or not phone.strip():
        errors.append("phone is required")
    if not isinstance(message, str) or not message.strip():
        errors.append("message is required")
    if errors:
        return error("Incomplete data", 400, details=errors)
    phone, message = phone.strip(), message.strip()

    # 1 + 2: find or create the customer, save the incoming message (committed before the AI is called)
    with db.connect() as conn:
        row = conn.execute("SELECT id FROM customers WHERE phone = %s", (phone,)).fetchone()
        if row:
            customer_id = row["id"]
        else:
            display_name = name.strip() if isinstance(name, str) and name.strip() else phone
            customer_id = conn.execute(
                "INSERT INTO customers (name, phone, status) VALUES (%s, %s, 'lead') RETURNING id",
                (display_name, phone)).fetchone()["id"]
        conn.execute("INSERT INTO messages (customer_id, direction, content) VALUES (%s, 'incoming', %s)",
                     (customer_id, message))

    # 3: AI reply (never raises; falls back to a canned reply)
    result = ai.generate_reply(message)

    # 4: save the outgoing reply
    with db.connect() as conn:
        conn.execute("INSERT INTO messages (customer_id, direction, content) VALUES (%s, 'outgoing', %s)",
                     (customer_id, result["text"]))

    # 5: respond 200 with the reply
    return jsonify({"customer_id": customer_id, "reply": result["text"],
                    "reply_source": result["source"]}), 200


# ---------------------------------------------------------------- Task 5: page + JSON errors

@app.get("/")
def dashboard():
    return send_from_directory(app.static_folder, "index.html")


@app.errorhandler(HTTPException)
def http_error(exc):  # 404 / 405 as JSON instead of HTML
    return error(exc.description, exc.code)


@app.errorhandler(Exception)
def unexpected_error(exc):
    logging.exception("Unhandled error")
    return error("Internal server error", 500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
