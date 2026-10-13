"""Manual end-to-end test. Start the server first (python app.py), then in a 2nd terminal:  python test_manual.py

Each case prints PASS or FAIL with the status code we got. Phone numbers are random, so you can run it again and again.
"""
import random
import sys

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
passed = failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}   {detail}")


def phone():
    return "0899" + "".join(random.choice("0123456789") for _ in range(8))


def send(method, path, **kwargs):
    return requests.request(method, BASE + path, timeout=15, **kwargs)


print("\n== Customers: create (POST /customers)")
p1, p2 = phone(), phone()
r = send("POST", "/customers", json={"name": "Budi", "phone": p1})
check("valid customer -> 201", r.status_code == 201, r.text)
cid = r.json().get("id")
check("default status is 'lead'", r.json().get("status") == "lead", r.text)
r = send("POST", "/customers", json={"name": "Siti", "phone": p2, "status": "active"})
check("valid customer with status active -> 201", r.status_code == 201, r.text)
cid2 = r.json().get("id")
r = send("POST", "/customers", json={"phone": phone()})
check("missing name -> 400", r.status_code == 400, r.text)
r = send("POST", "/customers", json={"name": "   ", "phone": phone()})
check("blank name -> 400", r.status_code == 400, r.text)
r = send("POST", "/customers", json={"name": "X", "phone": ""})
check("empty phone -> 400", r.status_code == 400, r.text)
r = send("POST", "/customers", json={"name": "X", "phone": phone(), "status": "vip"})
check("invalid status -> 400", r.status_code == 400, r.text)
r = send("POST", "/customers", data="ini bukan json", headers={"Content-Type": "application/json"})
check("invalid JSON body -> 400", r.status_code == 400, r.text)
r = send("POST", "/customers", json={"name": "Dobel", "phone": p1})
check("duplicate phone -> 409", r.status_code == 409, r.text)

print("\n== Customers: read")
r = send("GET", "/customers")
check("list -> 200 and is a list", r.status_code == 200 and isinstance(r.json(), list), r.text)
r = send("GET", "/customers", params={"status": "active"})
check("filter ?status=active only returns active",
      r.status_code == 200 and all(c["status"] == "active" for c in r.json()) and any(c["id"] == cid2 for c in r.json()), r.text)
r = send("GET", "/customers", params={"status": "vip"})
check("filter with unknown status -> 400", r.status_code == 400, r.text)
r = send("GET", f"/customers/{cid}")
check("detail -> 200 with 'messages' list", r.status_code == 200 and r.json().get("messages") == [], r.text)
r = send("GET", "/customers/999999999")
check("unknown id -> 404", r.status_code == 404, r.text)

print("\n== Customers: update (PUT)")
r = send("PUT", f"/customers/{cid}", json={"status": "active"})
check("change status -> 200", r.status_code == 200 and r.json().get("status") == "active", r.text)
check("fields not sent keep their value", r.json().get("name") == "Budi" and r.json().get("phone") == p1, r.text)
r = send("PUT", f"/customers/{cid}", json={"status": "vip"})
check("update with invalid status -> 400", r.status_code == 400, r.text)
r = send("PUT", f"/customers/{cid}", json={"phone": p2})
check("update to a phone that already exists -> 409", r.status_code == 409, r.text)
r = send("PUT", "/customers/999999999", json={"status": "active"})
check("update unknown id -> 404", r.status_code == 404, r.text)

print("\n== Webhook (POST /webhook/incoming-message)")
p3 = phone()
r = send("POST", "/webhook/incoming-message", json={"phone": p3, "name": "Andi", "message": "Halo, saya mau tanya harga paket layanan"})
check("new number -> 200", r.status_code == 200, r.text)
body = r.json()
check("reply is not empty", bool(body.get("reply")), r.text)
wid = body.get("customer_id")
r = send("GET", f"/customers/{wid}")
msgs = r.json().get("messages", [])
check("customer was auto-created as 'lead' with name 'Andi'", r.json().get("status") == "lead" and r.json().get("name") == "Andi", r.text)
check("2 messages saved: incoming then outgoing", [m["direction"] for m in msgs] == ["incoming", "outgoing"], r.text)
r = send("POST", "/webhook/incoming-message", json={"phone": p3, "message": "Terima kasih"})
check("same number again -> same customer, no duplicate", r.status_code == 200 and r.json().get("customer_id") == wid, r.text)
r = send("GET", f"/customers/{wid}")
check("conversation now has 4 messages", len(r.json().get("messages", [])) == 4, r.text)
r = send("POST", "/webhook/incoming-message", json={"phone": phone()})
check("missing message -> 400", r.status_code == 400, r.text)
r = send("POST", "/webhook/incoming-message", json={"message": "halo"})
check("missing phone -> 400", r.status_code == 400, r.text)
r = send("POST", "/webhook/incoming-message", data="bukan json", headers={"Content-Type": "application/json"})
check("invalid JSON -> 400", r.status_code == 400, r.text)

print("\n== Delete")
r = send("DELETE", f"/customers/{wid}")
check("delete customer with messages -> 200", r.status_code == 200, r.text)
r = send("GET", f"/customers/{wid}")
check("deleted customer -> 404", r.status_code == 404, r.text)
r = send("DELETE", f"/customers/{wid}")
check("delete again -> 404", r.status_code == 404, r.text)
send("DELETE", f"/customers/{cid}")
send("DELETE", f"/customers/{cid2}")

print("\n== Other")
r = send("GET", "/nope")
check("unknown URL -> 404 as JSON", r.status_code == 404 and "error" in r.json(), r.text)
r = send("PATCH", "/customers")
check("wrong method -> 405 as JSON", r.status_code == 405 and "error" in r.json(), r.text)
r = send("GET", "/")
check("dashboard page -> 200", r.status_code == 200 and "<html" in r.text.lower(), r.status_code)

print(f"\nResult: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)