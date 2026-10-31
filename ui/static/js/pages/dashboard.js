let byPlan = [];
const el = function (id) { return document.getElementById(id); };

function shift(d, months) {
  const last = new Date(d.getFullYear(), d.getMonth() + months + 1, 0).getDate();
  return new Date(d.getFullYear(), d.getMonth() + months, Math.min(d.getDate(), last));
}

function range() {
  const months = Number(el("period").value);
  const today = new Date();
  const from = months === 1 ? new Date(today.getFullYear(), today.getMonth(), 1)
    : months === 3 ? new Date(today.getFullYear(), Math.floor(today.getMonth() / 3) * 3, 1)
    : new Date(today.getFullYear(), 0, 1);
  return { from: from, to: today, months: months };
}

function note(id, text, kind) {
  el(id).textContent = text;
  el(id).className = "delta" + (kind ? " " + kind : "");
}

function change(id, current, previous) {
  if (!previous) return note(id, "No payments in the previous period");
  const pct = (current - previous) / previous * 100;
  note(id, (pct >= 0 ? "▲ " : "▼ ") + Math.abs(pct).toFixed(1) + "% vs previous period", pct >= 0 ? "up" : "down");
}

function renderBars(rows) {
  const today = new Date();
  const months = [];
  for (let i = 5; i >= 0; i--) {
    const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
    const key = BL.iso(d).slice(0, 7);
    const row = rows.find(function (r) { return r.month === key; });
    months.push({ name: d.toLocaleDateString("en-GB", { month: "short" }), value: row ? row.revenue : 0 });
  }
  const top = Math.max.apply(null, months.map(function (m) { return m.value; })) || 1;
  el("revenueBars").innerHTML = months.map(function (m, i) {
    const height = Math.max(m.value / top * 100, 2);
    return '<div class="bar' + (i === 5 ? " now" : "") + '" style="height:' + height + '%;" title="' + BL.esc(BL.money(m.value)) + '">' +
      '<span class="lbl">' + BL.esc(m.name) + "</span></div>";
  }).join("");
}

function renderOverdue(rows) {
  el("overdueRows").innerHTML = rows.map(function (r) {
    return '<tr><td><span class="cell-strong">' + BL.esc(r.customer_name || r.customer_email) + '</span><br>' +
      '<span class="cell-muted" style="font-size:11.5px;">' + BL.esc(r.invoice_number) + " · " + r.days_overdue + (r.days_overdue === 1 ? " day" : " days") + ' late</span></td>' +
      '<td style="text-align:right;">' + BL.money(r.balance_due) + "</td></tr>";
  }).join("") || '<tr><td class="empty-state">Nothing is overdue.</td></tr>';
}

function renderPlans(rows) {
  const plan = el("planFilter").value;
  byPlan = rows.filter(function (r) { return !plan || r.plan_id === plan; });
  el("planRows").innerHTML = byPlan.map(function (r) {
    return '<tr><td class="cell-strong">' + BL.esc(r.name) + "</td><td>" + BL.esc(BL.label(r.billing_interval)) + "</td>" +
      "<td>" + r.active + "</td><td>" + r.paused + "</td><td>" + r.closed + "</td><td>" + BL.money(r.mrr) + "</td><td>" + BL.money(r.received) + "</td></tr>";
  }).join("") || '<tr><td colspan="7" class="empty-state">No plans yet.</td></tr>';
}

function renderPayments(rows, count) {
  el("paymentCount").textContent = count + (count === 1 ? " payment" : " payments");
  el("paymentRows").innerHTML = rows.map(function (r) {
    return "<tr><td>" + BL.esc(BL.label(r.method)) + '</td><td class="cell-muted">' + r.count + '</td><td style="text-align:right;">' + BL.money(r.total) + "</td></tr>";
  }).join("") || '<tr><td class="empty-state">No payments in this period.</td></tr>';
}

function renderRenewals(rows) {
  el("renewalRows").innerHTML = rows.map(function (r) {
    const days = function (n) { return n + (n === 1 ? " day" : " days"); };
    const left = r.days_left < 0 ? days(-r.days_left) + " past end" : r.days_left === 0 ? "ends today" : days(r.days_left) + " left";
    return '<tr><td><a class="cell-strong" href="pipeline.html?q=' + encodeURIComponent(r.subscription_number) + '">' + BL.esc(r.customer_name) + "</a><br>" +
      '<span class="cell-muted" style="font-size:11.5px;">' + BL.esc(r.subscription_number) + " · " + BL.esc(r.plan_name) + "</span></td>" +
      '<td style="text-align:right;">' + BL.badge(left, r.days_left <= 7 ? "warn" : "neutral") + "</td></tr>";
  }).join("") || '<tr><td class="empty-state">Nothing ends in the next 30 days.</td></tr>';
}

async function load() {
  const started = performance.now();
  const r = range();
  const plan = el("planFilter").value;
  const period = { from: BL.iso(r.from), to: BL.iso(r.to), plan_id: plan };
  const previous = { from: BL.iso(shift(r.from, -r.months)), to: BL.iso(shift(r.to, -r.months)), plan_id: plan };
  const sixMonths = new Date(r.to.getFullYear(), r.to.getMonth() - 5, 1);

  const data = await Promise.all([
    BL.api("/reports/summary", { params: period }),
    BL.api("/reports/summary", { params: previous }),
    BL.api("/reports/summary", { params: { plan_id: plan } }), // no dates: every overdue invoice
    BL.api("/reports/revenue", { params: { from: BL.iso(sixMonths), to: BL.iso(r.to), plan_id: plan } }),
    BL.api("/reports/overdue", { params: { limit: 5 } }),
    BL.api("/reports/by-plan", { params: { from: period.from, to: period.to } }),
    BL.api("/reports/payments", { params: period }),
    BL.api("/reports/renewals", { params: { days: 30, limit: 5 } })
  ]);
  const now = data[0], before = data[1], all = data[2];
  const revenue = now.total_revenue_this_month, earlier = before.total_revenue_this_month;
  const active = now.active_subscription_count;
  const total = Object.values(now.subscriptions_by_status).reduce(function (a, b) { return a + b; }, 0);

  el("kpiActive").textContent = active.toLocaleString("en-IN");
  note("kpiActiveNote", (now.subscriptions_by_status.quotation || 0) + " in quotation · " + (now.subscriptions_by_status.paused || 0) + " paused");
  el("kpiMrr").textContent = BL.money(now.monthly_recurring_revenue);
  note("kpiMrrNote", BL.money(now.monthly_recurring_revenue * 12) + " a year, before tax");
  el("kpiRevenue").textContent = BL.money(revenue);
  change("kpiRevenueNote", revenue, earlier);
  el("kpiOverdue").textContent = BL.money(all.overdue_amount);
  note("kpiOverdueNote", all.overdue_invoice_count + (all.overdue_invoice_count === 1 ? " invoice overdue" : " invoices overdue"), all.overdue_invoice_count ? "down" : "up");
  el("kpiAverage").textContent = BL.money(active ? revenue / active : 0);
  note("kpiAverageNote", BL.money(now.outstanding_amount) + " still to collect");

  renderBars(data[3]);
  renderOverdue(data[4]);
  renderPlans(data[5]);
  renderPayments(data[6], now.payment_count);
  renderRenewals(data[7]);
  const seconds = ((performance.now() - started) / 1000).toFixed(1);
  el("loadedIn").textContent = "Loaded in " + seconds + "s across " + total.toLocaleString("en-IN") + " subscriptions.";
}

(async function () {
  const me = await BL.boot(["admin", "staff"]);
  el("staffLink").hidden = me.role !== "admin";
  const plans = await BL.api("/plans");
  el("planFilter").innerHTML = BL.options(plans, function (p) { return p.id; }, function (p) { return p.name; }, "All plans");
  await load();
})().catch(function (e) { BL.toast(e.message); });

["period", "planFilter"].forEach(function (id) {
  el(id).addEventListener("change", function () { BL.run(load); });
});

el("globalSearch").addEventListener("keydown", function (e) {
  if (e.key === "Enter" && e.target.value.trim()) {
    location.href = "invoicing.html?q=" + encodeURIComponent(e.target.value.trim());
  }
});

el("exportBtn").addEventListener("click", function () {
  const r = range();
  BL.saveCsv(
    [["Plan", "Billing", "Active", "Paused", "Closed", "MRR", "Received from " + BL.iso(r.from) + " to " + BL.iso(r.to)]]
      .concat(byPlan.map(function (p) { return [p.name, p.billing_interval, p.active, p.paused, p.closed, p.mrr, p.received]; })),
    "brightloop-revenue-" + BL.iso(r.to) + ".csv"
  );
});
