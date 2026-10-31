const COLUMNS = ["draft", "quotation", "confirmed", "active", "paused", "closed"];
const PER_COLUMN = 30;
const SUFFIX = { daily: " / day", weekly: " / wk", monthly: " / mo", yearly: " / yr" };
const ACTIONS = {
  draft: [["quotation", "Send quotation", "btn-primary"]],
  quotation: [["confirm", "Confirm", "btn-primary"]],
  confirmed: [["activate", "Activate", "btn-primary"]],
  active: [["invoice", "Generate invoice", "btn-primary"], ["pause", "Pause", "btn-ghost"], ["close", "Close", "btn-danger-ghost"]],
  paused: [["resume", "Resume", "btn-primary"], ["close", "Close", "btn-danger-ghost"]],
  closed: [["renew", "Renew", "btn-primary"]]
};
const el = function (id) { return document.getElementById(id); };
let plans = [], products = [], templates = [], selected = null, createMode = "plan";

const plan = function (id) { return plans.find(function (p) { return p.id === id; }) || {}; };
const product = function (id) { return products.find(function (p) { return p.id === id; }) || {}; };

function subTotal(sub) {
  return sub.lines.reduce(function (sum, l) { return sum + Number(l.line_total); }, 0);
}

function card(sub) {
  const closed = sub.status === "closed";
  const meta = closed ? "Ended " + BL.date(sub.expiry_date) : BL.money(subTotal(sub)) + (SUFFIX[plan(sub.plan_id).billing_interval] || "");
  return '<div class="kanban-card' + (closed ? " closed" : "") + (selected && selected.id === sub.id ? " selected" : "") + '" data-id="' + BL.esc(sub.id) + '">' +
    '<div class="id">' + BL.esc(sub.subscription_number) + '</div><div class="name">' + BL.esc(sub.customer_name) + "</div>" +
    '<div class="meta"><span>' + BL.esc(sub.plan_name) + "</span><span>" + BL.esc(meta) + "</span></div></div>";
}

async function loadBoard() {
  const shared = { plan_id: el("planFilter").value, search: el("subSearch").value.trim(), limit: PER_COLUMN };
  const results = await Promise.all(COLUMNS.map(function (status) {
    return BL.list("/subscriptions", Object.assign({ status: status }, shared));
  }));
  let total = 0;
  el("board").innerHTML = COLUMNS.map(function (status, i) {
    const r = results[i];
    total += r.total;
    const more = r.total > r.items.length ? '<p class="hint" style="font-size:11px;color:var(--text-muted);">Showing newest ' + r.items.length + ". Search to find others.</p>" : "";
    return '<div class="kanban-col"><h4>' + BL.label(status) + " <span>" + r.total + "</span></h4>" + r.items.map(card).join("") + more + "</div>";
  }).join("");
  el("subCount").textContent = total + (total === 1 ? " subscription" : " subscriptions");
}

function lineRow(sub, line, editable) {
  const p = product(line.product_id);
  const variant = (p.variants || []).find(function (v) { return v.id === line.variant_id; });
  const name = (p.name || "Product") + (variant ? " — " + variant.label : "");
  const removable = editable && line.product_id !== plan(sub.plan_id).product_id;
  const rate = Number(line.line_total) - Number(line.tax_amount);
  return "<tr><td>" + BL.esc(name) + "</td>" +
    "<td>" + (editable ? '<input class="qty-input" type="number" min="1" value="' + line.quantity + '" data-line="' + BL.esc(line.id) + '">' : line.quantity) + "</td>" +
    "<td>" + BL.money(line.unit_price) + "</td><td>" + (rate ? (Number(line.tax_amount) / rate * 100).toFixed(1).replace(/\.0$/, "") : "0") + "%</td>" +
    '<td class="cell-strong">' + BL.money(line.line_total) + "</td>" +
    "<td>" + (removable ? '<button class="btn btn-ghost btn-sm" data-remove="' + BL.esc(line.id) + '">Remove</button>' : "") + "</td></tr>";
}

function addableProducts(sub) {
  const used = sub.lines.map(function (l) { return l.product_id; });
  const rows = [];
  products.filter(function (p) { return p.is_active && !used.includes(p.id); }).forEach(function (p) {
    rows.push({ value: p.id + "|", text: p.name + " — " + BL.money(p.sales_price) });
    (p.variants || []).filter(function (v) { return v.is_active; }).forEach(function (v) {
      rows.push({ value: p.id + "|" + v.id, text: p.name + " — " + v.label + " — " + BL.money(Number(p.sales_price) + Number(v.price_delta)) });
    });
  });
  return rows;
}

function allowed(sub, action) {
  const p = plan(sub.plan_id);
  if (action === "pause") return p.can_pause;
  if (action === "close") return p.can_close_early;
  if (action === "renew") return p.can_renew;
  return true;
}

async function showDetail(id) {
  const data = await Promise.all([BL.api("/subscriptions/" + id), BL.api("/subscriptions/" + id + "/history")]);
  const sub = data[0], history = data[1];
  selected = sub;
  document.querySelectorAll(".kanban-card").forEach(function (c) { c.classList.toggle("selected", c.dataset.id === id); });
  const editable = sub.status !== "closed";
  const p = plan(sub.plan_id);
  const buttons = (ACTIONS[sub.status] || []).filter(function (a) { return allowed(sub, a[0]); }).map(function (a) {
    return '<button class="btn btn-sm ' + a[2] + '" data-action="' + a[0] + '">' + a[1] + "</button>";
  }).join("");
  const lock = editable ? "" : " disabled";
  const adds = addableProducts(sub);

  el("detail").hidden = false;
  el("detail").innerHTML =
    '<div class="panel-title"><span>' + BL.esc(sub.subscription_number) + " — " + BL.esc(sub.customer_name) + " &nbsp;" + BL.subBadge(sub.status) + '</span><span class="toolbar">' + buttons + "</span></div>" +
    '<div class="field-row"><div class="field"><label>Plan</label><input disabled value="' + BL.esc(sub.plan_name + " · " + BL.label(p.billing_interval)) + '"></div>' +
    '<div class="field"><label>Payment terms (days)</label><input type="number" min="0" id="editTerms" value="' + sub.payment_terms + '"' + lock + "></div></div>" +
    '<div class="field-row"><div class="field"><label>Start date</label><input type="date" id="editStart" value="' + BL.esc(sub.start_date || "") + '"' + lock + "></div>" +
    '<div class="field"><label>Expiry date</label><input type="date" id="editExpiry" value="' + BL.esc(sub.expiry_date || "") + '"' + lock + "></div></div>" +
    '<div class="toolbar"><span class="cell-muted" style="font-size:12.5px;">Next billing: ' + BL.date(sub.next_billing_date) +
    (sub.quotation_valid_until ? " · Quotation valid until " + BL.date(sub.quotation_valid_until) : "") + '</span><div class="spacer"></div>' +
    (editable ? '<button class="btn btn-ghost btn-sm" data-action="save">Save changes</button>' : "") + "</div>" +
    '<table style="margin-top:8px;"><thead><tr><th>Product</th><th>Qty</th><th>Unit price</th><th>Tax</th><th>Amount</th><th></th></tr></thead><tbody>' +
    sub.lines.map(function (l) { return lineRow(sub, l, editable); }).join("") +
    '<tr><td colspan="4" class="cell-strong">Total per period</td><td class="cell-strong">' + BL.money(subTotal(sub)) + "</td><td></td></tr></tbody></table>" +
    (editable && adds.length ? '<div class="inline-add"><div class="field"><label>Add product</label><select id="addProduct">' +
      BL.options(adds, function (a) { return a.value; }, function (a) { return a.text; }) + '</select></div>' +
      '<div class="field" style="flex:0 0 90px;min-width:90px;"><label>Qty</label><input type="number" min="1" value="1" id="addQty"></div>' +
      '<button class="btn btn-ghost" data-action="addLine">+ Add</button></div>' : "") +
    '<div class="panel-title" style="margin-top:20px;">Status history</div><table><tbody>' +
    history.map(function (h) {
      return '<tr><td>' + (h.from_status ? BL.esc(BL.label(h.from_status)) + " → " : "") + BL.esc(BL.label(h.to_status)) + '</td><td class="cell-muted" style="text-align:right;">' + BL.date(h.changed_at) + "</td></tr>";
    }).join("") + "</tbody></table>";
}

async function refreshAll() {
  await loadBoard();
  if (selected) await showDetail(selected.id);
}

async function act(action, button) {
  const id = selected.id;
  const path = "/subscriptions/" + id;
  if (action === "close" && !(await BL.ask("Close " + selected.subscription_number + "? Billing stops for this subscription.", "Close subscription"))) return;
  await BL.run(async function () {
    if (action === "save") {
      await BL.patch(path, {
        start_date: el("editStart").value || null,
        expiry_date: el("editExpiry").value || null,
        payment_terms: Number(el("editTerms").value)
      });
      BL.toast("Changes saved", "ok");
    } else if (action === "addLine") {
      const pick = el("addProduct").value.split("|");
      await BL.post(path + "/lines", { product_id: pick[0], variant_id: pick[1] || null, quantity: Number(el("addQty").value) });
    } else if (action === "invoice") {
      const inv = await BL.post("/invoices/generate/" + id);
      BL.toast("Draft invoice " + inv.invoice_number + " created", "ok");
    } else {
      await BL.post(path + "/" + action);
    }
    await refreshAll();
  }, button);
}

async function loadCustomers(term) {
  const r = await BL.list("/users/customers", { search: term, limit: 50 });
  el("customerPick").innerHTML = BL.options(r.items, function (c) { return c.id; }, function (c) {
    return (c.company_name || c.full_name || c.email) + " — " + c.email;
  });
}

function pickVariants() {
  const p = plans.find(function (x) { return x.id === el("planPick").value; });
  const variants = p ? (product(p.product_id).variants || []).filter(function (v) { return v.is_active; }) : [];
  el("variantField").hidden = !variants.length || createMode !== "plan";
  el("variantPick").innerHTML = BL.options(variants, function (v) { return v.id; }, function (v) { return v.label + " (+" + BL.money(v.price_delta) + ")"; }, "Standard");
}

function openCreate(mode) {
  createMode = mode;
  el("subModalTitle").textContent = mode === "plan" ? "New subscription" : "Quote from template";
  el("planField").hidden = mode !== "plan";
  el("templateField").hidden = mode === "plan";
  pickVariants();
  BL.run(function () { return loadCustomers(""); });
  BL.modal("subModal", true);
}

(async function () {
  await BL.boot(["admin", "staff"]);
  const data = await Promise.all([BL.api("/plans"), BL.api("/products"), BL.api("/quotation-templates")]);
  plans = data[0]; products = data[1]; templates = data[2];
  el("planFilter").innerHTML = BL.options(plans, function (p) { return p.id; }, function (p) { return p.name; }, "All plans");
  el("planPick").innerHTML = BL.options(plans.filter(function (p) { return p.is_active; }), function (p) { return p.id; }, function (p) {
    return p.name + " — " + BL.money(p.price) + (SUFFIX[p.billing_interval] || "");
  });
  el("templatePick").innerHTML = BL.options(templates, function (t) { return t.id; }, function (t) { return t.name; });
  el("subSearch").value = new URLSearchParams(location.search).get("q") || "";
  await loadBoard();
})().catch(function (e) { BL.toast(e.message); });

el("planFilter").addEventListener("change", function () { BL.run(loadBoard); });
BL.onSearch(el("subSearch"), function () { BL.run(loadBoard); });
el("board").addEventListener("click", function (e) {
  const c = e.target.closest(".kanban-card");
  if (c) BL.run(function () { return showDetail(c.dataset.id); });
});
el("detail").addEventListener("click", function (e) {
  const action = e.target.closest("[data-action]");
  if (action) return act(action.dataset.action, action);
  const remove = e.target.closest("[data-remove]");
  if (remove) {
    BL.run(async function () {
      await BL.del("/subscriptions/" + selected.id + "/lines/" + remove.dataset.remove);
      await refreshAll();
    }, remove);
  }
});
el("detail").addEventListener("change", function (e) {
  if (!e.target.dataset.line) return;
  BL.run(async function () {
    await BL.patch("/subscriptions/" + selected.id + "/lines/" + e.target.dataset.line, { quantity: Number(e.target.value) });
  }).finally(function () { BL.run(refreshAll); });
});

el("newSubBtn").addEventListener("click", function () { openCreate("plan"); });
el("quoteBtn").addEventListener("click", function () { openCreate("template"); });
el("planPick").addEventListener("change", pickVariants);
BL.onSearch(el("customerSearch"), function (term) { BL.run(function () { return loadCustomers(term); }); });

el("subForm").addEventListener("submit", function (e) {
  e.preventDefault();
  const terms = el("termsPick").value;
  const body = {
    customer_id: el("customerPick").value,
    start_date: el("startPick").value || null,
    expiry_date: el("expiryPick").value || null,
    payment_terms: terms === "" ? null : Number(terms)
  };
  if (createMode === "plan") {
    body.plan_id = el("planPick").value;
    body.variant_id = el("variantPick").value || null;
  } else {
    body.template_id = el("templatePick").value;
  }
  BL.run(async function () {
    if (!body.customer_id) throw new Error("Choose a customer first");
    const sub = await BL.post("/subscriptions", body);
    e.target.reset();
    BL.modal("subModal", false);
    BL.toast(sub.subscription_number + " created", "ok");
    selected = sub;
    await refreshAll();
  }, e.target.querySelector('button[type="submit"]'));
});
