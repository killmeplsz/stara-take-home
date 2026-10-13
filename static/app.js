// Dashboard logic. Plain JavaScript, no framework.
// Security note: user-supplied text is always inserted with textContent (never innerHTML),
// so a customer named "<script>..." cannot run code in the dashboard (XSS).

let selectedId = null;

const $ = (id) => document.getElementById(id);

// Small wrapper around fetch(): sends/receives JSON and turns API errors into thrown Errors.
async function api(path, options = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const details = data.details ? ": " + data.details.join("; ") : "";
    throw new Error((data.error || "Request failed") + details);
  }
  return data;
}

// ---------- customer list ----------
async function loadCustomers() {
  $("list-error").textContent = "";
  try {
    const status = $("filter").value;
    const customers = await api("/customers" + (status ? "?status=" + status : ""));
    renderList(customers);
  } catch (err) {
    $("list-error").textContent = err.message;
  }
}

function renderList(customers) {
  const ul = $("customer-list");
  ul.replaceChildren();
  if (customers.length === 0) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "No customers yet.";
    ul.appendChild(li);
    return;
  }
  for (const c of customers) {
    const li = document.createElement("li");
    if (c.id === selectedId) li.classList.add("selected");

    const name = document.createElement("strong");
    name.textContent = c.name;
    const badge = document.createElement("span");
    badge.className = "badge " + c.status;
    badge.textContent = c.status;
    const phone = document.createElement("span");
    phone.className = "phone";
    phone.textContent = c.phone;

    li.append(name, badge, phone);
    li.addEventListener("click", () => selectCustomer(c.id));
    ul.appendChild(li);
  }
}

// ---------- conversation ----------
async function selectCustomer(id) {
  selectedId = id;
  $("detail-error").textContent = "";
  try {
    const c = await api("/customers/" + id);
    $("placeholder").hidden = true;
    $("detail").hidden = false;
    $("detail-name").textContent = c.name;
    $("detail-phone").textContent = c.phone;
    $("detail-status").textContent = c.status;
    $("detail-status").className = "badge " + c.status;
    renderMessages(c.messages);
    loadCustomers(); // refresh the highlight
  } catch (err) {
    $("detail-error").textContent = err.message;
  }
}

function renderMessages(messages) {
  const box = $("messages");
  box.replaceChildren();
  if (messages.length === 0) {
    const p = document.createElement("p");
    p.className = "empty";
    p.textContent = "No messages yet.";
    box.appendChild(p);
    return;
  }
  for (const m of messages) {
    const div = document.createElement("div");
    div.className = "msg " + m.direction;
    div.textContent = m.content;
    const time = document.createElement("small");
    time.textContent = m.direction + " · " + new Date(m.created_at).toLocaleString();
    div.appendChild(time);
    box.appendChild(div);
  }
  box.scrollTop = box.scrollHeight;
}

// ---------- forms ----------
$("add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("list-error").textContent = "";
  try {
    await api("/customers", {
      method: "POST",
      body: JSON.stringify({
        name: $("add-name").value,
        phone: $("add-phone").value,
        status: $("add-status").value,
      }),
    });
    e.target.reset();
    loadCustomers();
  } catch (err) {
    $("list-error").textContent = err.message;
  }
});

$("test-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("detail-error").textContent = "";
  try {
    // Reuse the selected customer's data, exactly like WhatsApp would send it to the webhook.
    const c = await api("/customers/" + selectedId);
    await api("/webhook/incoming-message", {
      method: "POST",
      body: JSON.stringify({ phone: c.phone, name: c.name, message: $("test-message").value }),
    });
    $("test-message").value = "";
    selectCustomer(selectedId);
  } catch (err) {
    $("detail-error").textContent = err.message;
  }
});

$("delete-btn").addEventListener("click", async () => {
  if (!confirm("Delete this customer and all their messages?")) return;
  try {
    await api("/customers/" + selectedId, { method: "DELETE" });
    selectedId = null;
    $("detail").hidden = true;
    $("placeholder").hidden = false;
    loadCustomers();
  } catch (err) {
    $("detail-error").textContent = err.message;
  }
});

$("filter").addEventListener("change", loadCustomers);

loadCustomers();
