const el = function (id) { return document.getElementById(id); };
const PER = { daily: "day", weekly: "week", monthly: "mo", yearly: "yr" };
let subs = [], invoices = [], plans = [], products = [], addons = [];

const planOf = function (sub) { return plans.find(function (p) { return p.id === sub.plan_id; }) || {}; };
const lineName = function (l) { const p = products.find(function (x) { return x.id === l.product_id; }); return p ? p.name : "Item"; };

function actions(sub) {
  const p = planOf(sub);
  const b = [];
  const add = function (action, text, style) {
    b.push('<button class="btn ' + (style || "btn-ghost") + ' btn-sm" data-sub="' + BL.esc(sub.id) + '" data-action="' + action + '">' + text + "</button>");
  };
  if (sub.status === "active" && p.can_pause) add("pause", "Pause subscription");
  if (sub.status === "paused") add("resume", "Resume subscription");
  if ((sub.status === "active" || sub.status === "paused") && p.can_close_early) add("close", "Cancel", "btn-danger-ghost");
  if (sub.status === "closed" && p.can_renew) add("renew", "Renew subscription");
  return b.join("");
}

function addonControls(sub) {
  if (sub.status === "closed") return "";
  const on = sub.lines.filter(function (l) { return addons.some(function (a) { return a.id === l.product_id; }); });
  const free = addons.filter(function (a) { return !sub.lines.some(function (l) { return l.product_id === a.id; }); });
  if (!on.length && !free.length) return "";
  return '<div class="panel-title" style="margin:18px 0 8px;">Add-ons</div>' +
    on.map(function (l) {
      return '<div class="summary-line"><span class="l">' + BL.esc(lineName(l)) + "</span>" +
        '<button class="btn btn-ghost btn-sm" data-sub="' + BL.esc(sub.id) + '" data-off="' + BL.esc(l.id) + '">Switch off</button></div>';
    }).join("") +
    free.map(function (a) {
      return '<div class="summary-line"><span class="l">' + BL.esc(a.name) + " — " + BL.money(a.sales_price) + "</span>" +
        '<button class="btn btn-ghost btn-sm" data-sub="' + BL.esc(sub.id) + '" data-on="' + BL.esc(a.id) + '">Switch on</button></div>';
    }).join("");
}

function renderSubs() {
  el("subscriptions").innerHTML = subs.map(function (sub) {
    const p = planOf(sub);
    const total = sub.lines.reduce(function (t, l) { return t + Number(l.line_total); }, 0);
    const next = sub.status === "active" && sub.next_billing_date ? " · next bill " + BL.date(sub.next_billing_date) : "";
    const end = sub.expiry_date ? " · ends " + BL.date(sub.expiry_date) : "";
    return '<div class="sub-block"><div class="plan-card"><div class="left"><div class="plan-name">' + BL.esc(sub.plan_name) + "</div>" +
      '<div class="plan-meta">' + BL.esc(sub.subscription_number) + " · billed " + BL.esc(p.billing_interval || "") + next + end + "</div></div>" +
      '<div class="right"><div class="amt">' + BL.money(total) + '<span style="font-size:12px;color:var(--text-secondary);font-weight:500;"> /' + (PER[p.billing_interval] || "") + "</span></div>" +
      '<div style="margin-top:6px;">' + BL.subBadge(sub.status) + "</div></div></div>" +
      '<div class="toolbar" style="margin-top:14px;">' + actions(sub) + "</div>" + addonControls(sub) + "</div>";
  }).join("") || '<p class="empty-state">You have no subscriptions yet.</p>';
}

function invoiceStatus(inv) {
  if (inv.is_overdue) return BL.badge("Overdue", "danger");
  if (inv.status === "confirmed") return BL.badge("Due " + BL.date(inv.due_date), "warn");
  return BL.invoiceBadge(inv);
}

function renderInvoices() {
  const term = el("invoiceSearch").value.trim().toLowerCase();
  const rows = invoices.filter(function (inv) { return !term || inv.invoice_number.toLowerCase().includes(term); });
  el("invoiceRows").innerHTML = rows.map(function (inv) {
    return '<tr><td class="cell-strong">' + BL.esc(inv.invoice_number) + '</td><td class="cell-muted">' + BL.date(inv.issued_at || inv.created_at) + "</td>" +
      "<td>" + BL.money(inv.grand_total) + "</td><td>" + invoiceStatus(inv) + "</td>" +
      '<td><button class="btn btn-ghost btn-sm" data-pdf="' + BL.esc(inv.id) + '" data-number="' + BL.esc(inv.invoice_number) + '">Download</button></td></tr>';
  }).join("") || '<tr><td colspan="5" class="empty-state">No invoices yet.</td></tr>';
}

async function loadSubs() {
  subs = await BL.api("/portal/subscriptions");
  renderSubs();
}

async function loadInvoices() {
  invoices = await BL.api("/portal/invoices");
  renderInvoices();
}

function fillProfile(me) {
  el("welcome").textContent = "Welcome back, " + (me.company_name || me.full_name || me.email);
  el("profileName").value = me.full_name || "";
  el("profileCompany").value = me.company_name || "";
  el("profileEmail").value = me.email;
  el("profilePhone").value = me.phone || "";
  el("profileAddress").value = me.address || "";
}

(async function () {
  const me = await BL.boot(["customer"]);
  fillProfile(me);
  const data = await Promise.all([BL.api("/plans"), BL.api("/products"), BL.api("/portal/addons")]);
  plans = data[0]; products = data[1]; addons = data[2];
  await Promise.all([loadSubs(), loadInvoices()]);
})().catch(function (e) { BL.toast(e.message); });

BL.onSearch(el("invoiceSearch"), renderInvoices);

el("subscriptions").addEventListener("click", function (e) {
  const b = e.target.closest("button[data-sub]");
  if (!b) return;
  const path = "/portal/subscriptions/" + b.dataset.sub;
  const confirmFirst = b.dataset.action === "close"
    ? BL.ask("Cancel this subscription? Billing stops, and you can renew it later if your plan allows.", "Cancel subscription")
    : Promise.resolve(true);
  confirmFirst.then(function (yes) {
    if (!yes) return;
    BL.run(async function () {
      if (b.dataset.action) await BL.post(path + "/" + b.dataset.action);
      else if (b.dataset.on) await BL.post(path + "/addons", { product_id: b.dataset.on, quantity: 1 });
      else await BL.del(path + "/addons/" + b.dataset.off);
      await loadSubs();
    }, b);
  });
});

el("invoiceRows").addEventListener("click", function (e) {
  const b = e.target.closest("[data-pdf]");
  if (b) BL.run(function () { return BL.download("/portal/invoices/" + b.dataset.pdf + "/pdf", b.dataset.number + ".pdf"); }, b);
});

el("statementBtn").addEventListener("click", function () {
  BL.saveCsv(
    [["Invoice", "Date", "Due", "Total", "Paid", "Balance", "Status"]].concat(invoices.map(function (i) {
      return [i.invoice_number, (i.issued_at || i.created_at).slice(0, 10), i.due_date, i.grand_total, i.amount_paid, i.balance_due, i.status];
    })),
    "brightloop-statement-" + BL.iso(new Date()) + ".csv"
  );
});

el("profileForm").addEventListener("submit", function (e) {
  e.preventDefault();
  const body = {
    full_name: el("profileName").value,
    company_name: el("profileCompany").value,
    phone: el("profilePhone").value,
    address: el("profileAddress").value
  };
  if (el("profilePassword").value) body.password = el("profilePassword").value;
  BL.run(async function () {
    fillProfile(await BL.patch("/portal/profile", body));
    el("profilePassword").value = "";
    BL.toast("Details updated", "ok");
  }, e.target.querySelector('button[type="submit"]'));
});
