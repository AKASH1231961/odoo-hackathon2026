const PAGE_SIZE = 20;
const el = function (id) { return document.getElementById(id); };
let page = 0, total = 0, selected = null;

function filters() {
  const status = el("statusFilter").value;
  const params = { search: el("invoiceSearch").value.trim(), skip: page * PAGE_SIZE, limit: PAGE_SIZE };
  if (status === "overdue") params.overdue = true;
  else params.status = status;
  const now = new Date();
  if (el("periodFilter").value === "this") {
    params.date_from = BL.iso(new Date(now.getFullYear(), now.getMonth(), 1));
    params.date_to = BL.iso(now);
  } else if (el("periodFilter").value === "last") {
    params.date_from = BL.iso(new Date(now.getFullYear(), now.getMonth() - 1, 1));
    params.date_to = BL.iso(new Date(now.getFullYear(), now.getMonth(), 0));
  }
  return params;
}

async function loadList() {
  const r = await BL.list("/invoices", filters());
  total = r.total;
  el("invoiceCount").textContent = total + (total === 1 ? " invoice" : " invoices");
  el("invoiceRows").innerHTML = r.items.map(function (inv) {
    return '<tr class="clickable' + (selected && selected.id === inv.id ? " selected" : "") + '" data-id="' + BL.esc(inv.id) + '">' +
      '<td class="cell-strong">' + BL.esc(inv.invoice_number) + "</td><td>" + BL.esc(inv.customer_name || inv.customer_email) + "</td>" +
      "<td>" + BL.money(inv.grand_total) + '</td><td class="cell-muted">' + BL.date(inv.due_date) + "</td><td>" + BL.invoiceBadge(inv) + "</td></tr>";
  }).join("") || '<tr><td colspan="5" class="empty-state">No invoices match. Billing creates them automatically on the billing date.</td></tr>';
  el("pageLabel").textContent = "Page " + (page + 1) + " of " + Math.max(1, Math.ceil(total / PAGE_SIZE));
  el("prevPage").disabled = page === 0;
  el("nextPage").disabled = (page + 1) * PAGE_SIZE >= total;
}

function renderActions(inv) {
  const b = [];
  const button = function (action, text, style) {
    b.push('<button class="btn btn-block ' + style + '" style="margin-top:8px;" data-action="' + action + '">' + text + "</button>");
  };
  if (inv.status === "draft") button("confirm", "Confirm invoice", "btn-primary");
  if (inv.status === "confirmed") button("pay", "Record payment", "btn-primary");
  if (inv.status === "confirmed" || inv.status === "paid") button("send", inv.sent_at ? "Send again" : "Send to customer", "btn-ghost");
  if (inv.status !== "cancelled") button("pdf", "Download PDF", "btn-ghost");
  if (inv.status === "draft" || inv.status === "confirmed") button("cancel", "Cancel invoice", "btn-danger-ghost");
  if (inv.status === "cancelled") button("reissue", "Reissue invoice", "btn-primary");
  return b.join("");
}

function line(text, value, style) {
  return '<div class="summary-line' + (style === "total" ? " total" : "") + '"><span class="l">' + text + "</span><span" +
    (style === "ok" ? ' style="color:var(--ok);"' : "") + ">" + value + "</span></div>";
}

async function showInvoice(id) {
  const data = await Promise.all([BL.api("/invoices/" + id), BL.api("/invoices/" + id + "/payments")]);
  const inv = data[0], payments = data[1];
  selected = inv;
  document.querySelectorAll("#invoiceRows tr").forEach(function (r) { r.classList.toggle("selected", r.dataset.id === id); });

  el("invoiceLines").hidden = false;
  el("invoiceLines").innerHTML =
    '<div class="panel-title"><span>' + BL.esc(inv.invoice_number) + " — " + BL.esc(inv.customer_name || inv.customer_email) + " &nbsp;" + BL.invoiceBadge(inv) + "</span>" +
    '<span class="cell-muted" style="font-size:11.5px;font-weight:500;">' + BL.esc(inv.subscription_number) + " · " + BL.date(inv.period_start) + " – " + BL.date(inv.period_end) + "</span></div>" +
    "<table><thead><tr><th>Product</th><th>Qty</th><th>Unit price</th><th>Discount</th><th>Tax</th><th>Amount</th></tr></thead><tbody>" +
    inv.lines.map(function (l) {
      return "<tr><td>" + BL.esc(l.description) + "</td><td>" + l.quantity + "</td><td>" + BL.money(l.unit_price) + "</td>" +
        '<td style="color:var(--ok);">' + (Number(l.discount) ? "− " + BL.money(l.discount) : "—") + "</td><td>" + BL.money(l.tax_amount) + "</td><td>" + BL.money(l.line_total) + "</td></tr>";
    }).join("") + "</tbody></table>";

  el("invoicePayments").hidden = !payments.length;
  el("invoicePayments").innerHTML = '<div class="panel-title">Payments</div><table><tbody>' + payments.map(function (p) {
    return "<tr><td>" + BL.date(p.payment_date) + "</td><td>" + BL.esc(BL.label(p.method)) + '</td><td class="cell-muted">' + BL.esc(p.reference || p.note || "") + '</td><td style="text-align:right;">' + BL.money(p.amount) + "</td></tr>";
  }).join("") + "</tbody></table>";

  el("invoiceSummary").hidden = false;
  el("summaryTotals").innerHTML = '<div class="panel-title">Invoice summary</div>' +
    line("Subtotal", BL.money(inv.subtotal)) +
    line("Discount", "− " + BL.money(inv.discount_total), "ok") +
    line("Tax", BL.money(inv.tax_total)) +
    line("Total", BL.money(inv.grand_total), "total") +
    line("Paid", BL.money(inv.amount_paid)) +
    line("Balance due", BL.money(inv.balance_due), "total") +
    renderActions(inv);
  el("summaryStatus").innerHTML = '<div class="panel-title">Status</div>' +
    line("Issued", inv.issued_at ? BL.date(inv.issued_at) : "Draft") +
    line("Due", BL.date(inv.due_date)) +
    line("Sent", inv.sent_at ? BL.date(inv.sent_at) : "Not yet") +
    line("Paid", inv.paid_at ? BL.date(inv.paid_at) : '<span class="cell-muted">Pending</span>');
}

async function refreshAll() {
  await loadList();
  if (selected) await showInvoice(selected.id);
}

async function act(action, button) {
  const inv = selected;
  if (action === "pay") {
    el("paymentTitle").textContent = "Record payment — " + inv.invoice_number;
    el("payAmount").value = inv.balance_due;
    el("payAmount").max = inv.balance_due;
    el("payDate").value = BL.iso(new Date());
    return BL.modal("paymentModal", true);
  }
  if (action === "cancel" && !(await BL.ask("Cancel " + inv.invoice_number + "? It can be reissued afterwards.", "Cancel invoice"))) return;
  await BL.run(async function () {
    const path = "/invoices/" + inv.id;
    if (action === "pdf") return BL.download(path + "/pdf", inv.invoice_number + ".pdf");
    if (action === "send") {
      await BL.post(path + "/send");
      BL.toast("Invoice sent to " + inv.customer_email, "ok");
    } else if (action === "reissue") {
      selected = await BL.post("/invoices/generate/" + inv.subscription_id);
      BL.toast("Reissued as " + selected.invoice_number, "ok");
    } else {
      await BL.post(path + "/" + action);
    }
    await refreshAll();
  }, button);
}

function reload() {
  page = 0;
  BL.run(loadList);
}

(async function () {
  const me = await BL.boot(["admin", "staff"]);
  el("runBillingBtn").hidden = me.role !== "admin";
  const params = new URLSearchParams(location.search);
  if (params.get("overdue")) el("statusFilter").value = "overdue";
  if (params.get("q")) el("invoiceSearch").value = params.get("q");
  await loadList();
})().catch(function (e) { BL.toast(e.message); });

["statusFilter", "periodFilter"].forEach(function (id) { el(id).addEventListener("change", reload); });
BL.onSearch(el("invoiceSearch"), reload);
el("prevPage").addEventListener("click", function () { page--; BL.run(loadList); });
el("nextPage").addEventListener("click", function () { page++; BL.run(loadList); });

el("invoiceRows").addEventListener("click", function (e) {
  const row = e.target.closest("tr[data-id]");
  if (row) BL.run(function () { return showInvoice(row.dataset.id); });
});
el("summaryTotals").addEventListener("click", function (e) {
  const b = e.target.closest("[data-action]");
  if (b) act(b.dataset.action, b);
});

el("paymentForm").addEventListener("submit", function (e) {
  e.preventDefault();
  BL.run(async function () {
    await BL.post("/payments", {
      invoice_id: selected.id,
      amount: el("payAmount").value,
      method: el("payMethod").value,
      payment_date: el("payDate").value,
      reference: el("payReference").value || null,
      note: el("payNote").value || null
    });
    e.target.reset();
    BL.modal("paymentModal", false);
    BL.toast("Payment saved", "ok");
    await refreshAll();
  }, e.target.querySelector('button[type="submit"]'));
});

el("runBillingBtn").addEventListener("click", function (e) {
  const button = e.currentTarget;
  BL.run(async function () {
    await BL.post("/invoices/run-billing");
    BL.toast("Billing started. New invoices appear here shortly.", "ok");
    setTimeout(function () { BL.run(loadList); }, 3000);
  }, button);
});

el("newInvoiceBtn").addEventListener("click", function () {
  BL.run(async function () {
    const r = await BL.list("/subscriptions", { status: "active", limit: 200 });
    el("invoiceSubPick").innerHTML = BL.options(r.items, function (s) { return s.id; }, function (s) {
      return s.subscription_number + " — " + s.customer_name + " — " + s.plan_name;
    });
    BL.modal("newInvoiceModal", true);
  });
});

el("newInvoiceForm").addEventListener("submit", function (e) {
  e.preventDefault();
  BL.run(async function () {
    const inv = await BL.post("/invoices/generate/" + el("invoiceSubPick").value);
    BL.modal("newInvoiceModal", false);
    BL.toast("Draft invoice " + inv.invoice_number + " created", "ok");
    selected = inv;
    await refreshAll();
  }, e.target.querySelector('button[type="submit"]'));
});
