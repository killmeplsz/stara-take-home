
"""Workflow tests using an in-memory fake database."""
import db

# Prevent app.py from initializing the real database during import.
db.init_db = lambda: None

import app as stara


class FakeCursor:
    def __init__(self, one=None, many=None):
        self.one = one
        self.many = many or []

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.many


class FakeDatabase:
    def __init__(self):
        self.customers = {}
        self.messages = []
        self.next_customer_id = 1
        self.next_message_id = 1

    def connect(self):
        return FakeConnection(self)


class FakeConnection:
    def __init__(self, database):
        self.db = database

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        params = params or ()
        sql = " ".join(sql.split())

        if sql.startswith("INSERT INTO customers"):
            if "RETURNING *" in sql:
                name, phone, status = params
                customer = {
                    "id": self.db.next_customer_id,
                    "name": name,
                    "phone": phone,
                    "status": status,
                    "created_at": None,
                }
                self.db.customers[customer["id"]] = customer
                self.db.next_customer_id += 1
                return FakeCursor(one=customer.copy())

            name, phone = params
            customer = {
                "id": self.db.next_customer_id,
                "name": name,
                "phone": phone,
                "status": "lead",
                "created_at": None,
            }
            self.db.customers[customer["id"]] = customer
            self.db.next_customer_id += 1
            return FakeCursor(one={"id": customer["id"]})

        if sql.startswith("SELECT id FROM customers WHERE phone"):
            phone = params[0]
            for customer in self.db.customers.values():
                if customer["phone"] == phone:
                    return FakeCursor(one={"id": customer["id"]})
            return FakeCursor()

        if sql.startswith("SELECT * FROM customers WHERE id"):
            customer = self.db.customers.get(params[0])
            return FakeCursor(one=customer.copy() if customer else None)

        if sql.startswith("SELECT * FROM customers"):
            rows = list(self.db.customers.values())
            if "WHERE status = %s" in sql:
                rows = [c for c in rows if c["status"] == params[0]]
            rows.sort(key=lambda c: c["id"], reverse=True)
            return FakeCursor(many=[c.copy() for c in rows])

        if sql.startswith("SELECT id, direction, content, created_at FROM messages"):
            customer_id = params[0]
            rows = [
                {
                    "id": m["id"],
                    "direction": m["direction"],
                    "content": m["content"],
                    "created_at": None,
                }
                for m in self.db.messages
                if m["customer_id"] == customer_id
            ]
            return FakeCursor(many=rows)

        if sql.startswith("INSERT INTO messages"):
            customer_id, content = params
            direction = "incoming" if "'incoming'" in sql else "outgoing"
            self.db.messages.append({
                "id": self.db.next_message_id,
                "customer_id": customer_id,
                "direction": direction,
                "content": content,
            })
            self.db.next_message_id += 1
            return FakeCursor()

        if sql.startswith("UPDATE customers"):
            name, phone, status, customer_id = params
            customer = self.db.customers.get(customer_id)
            if customer:
                customer.update(name=name, phone=phone, status=status)
                return FakeCursor(one=customer.copy())
            return FakeCursor()

        if sql.startswith("DELETE FROM customers"):
            customer_id = params[0]
            self.db.customers.pop(customer_id, None)
            self.db.messages = [
                m for m in self.db.messages
                if m["customer_id"] != customer_id
            ]
            return FakeCursor()

        raise AssertionError(f"SQL query not mocked: {sql}")


def setup_client(monkeypatch):
    fake_db = FakeDatabase()
    monkeypatch.setattr(stara.db, "connect", fake_db.connect)
    stara.app.config.update(TESTING=True)
    return stara.app.test_client(), fake_db


def test_create_and_read_customer(monkeypatch):
    client, fake_db = setup_client(monkeypatch)

    created = client.post(
        "/customers",
        json={"name": "Budi", "phone": "081234567890"},
    )
    assert created.status_code == 201
    assert created.json["name"] == "Budi"
    assert created.json["status"] == "lead"

    customer_id = created.json["id"]
    fetched = client.get(f"/customers/{customer_id}")

    assert fetched.status_code == 200
    assert fetched.json["phone"] == "081234567890"
    assert fetched.json["messages"] == []
    assert len(fake_db.customers) == 1


def test_update_customer(monkeypatch):
    client, _ = setup_client(monkeypatch)

    created = client.post(
        "/customers",
        json={"name": "Budi", "phone": "081234567890"},
    )
    customer_id = created.json["id"]

    updated = client.put(
        f"/customers/{customer_id}",
        json={"name": "Budi Santoso", "status": "active"},
    )

    assert updated.status_code == 200
    assert updated.json["name"] == "Budi Santoso"
    assert updated.json["status"] == "active"
    assert updated.json["phone"] == "081234567890"


def test_delete_customer(monkeypatch):
    client, fake_db = setup_client(monkeypatch)

    created = client.post(
        "/customers",
        json={"name": "Budi", "phone": "081234567890"},
    )
    customer_id = created.json["id"]

    deleted = client.delete(f"/customers/{customer_id}")

    assert deleted.status_code == 200
    assert deleted.json["id"] == customer_id
    assert client.get(f"/customers/{customer_id}").status_code == 404
    assert customer_id not in fake_db.customers


def test_webhook_saves_incoming_and_outgoing_messages(monkeypatch):
    client, fake_db = setup_client(monkeypatch)

    monkeypatch.setattr(
        stara.ai,
        "generate_reply",
        lambda message: {
            "text": "Halo, ada yang bisa kami bantu?",
            "source": "mock",
        },
    )

    response = client.post(
        "/webhook/incoming-message",
        json={
            "name": "Siti",
            "phone": "081234567891",
            "message": "Halo, saya ingin bertanya",
        },
    )

    assert response.status_code == 200
    assert response.json["reply"] == "Halo, ada yang bisa kami bantu?"
    assert response.json["reply_source"] == "mock"
    assert len(fake_db.customers) == 1
    assert len(fake_db.messages) == 2
    assert fake_db.messages[0]["direction"] == "incoming"
    assert fake_db.messages[1]["direction"] == "outgoing"


def test_webhook_reuses_existing_customer(monkeypatch):
    client, fake_db = setup_client(monkeypatch)

    first = client.post(
        "/customers",
        json={"name": "Siti", "phone": "081234567891"},
    )
    customer_id = first.json["id"]

    monkeypatch.setattr(
        stara.ai,
        "generate_reply",
        lambda message: {"text": "Baik, kami bantu.", "source": "mock"},
    )

    response = client.post(
        "/webhook/incoming-message",
        json={
            "phone": "081234567891",
            "message": "Saya ingin bertanya lagi",
        },
    )

    assert response.status_code == 200
    assert response.json["customer_id"] == customer_id
    assert len(fake_db.customers) == 1
    assert len(fake_db.messages) == 2
