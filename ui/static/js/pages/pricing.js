const el = function (id) { return document.getElementById(id); };
let products = [], plans = [], customers = [], templates = [], editingTemplate = null, isAdmin = false;

const productName = function (id) { const p = products.find(function (x) { return x.id === id; }); return p ? p.name : "Product"; };
const planName = function (id) { const p = plans.find(function (x) { return x.id === id; }); return p ? p.name : "Plan"; };

function customerName(id) {
  const c = customers.find(function (x) { return x.id === id; });
  return c ? c.company_name || c.full_name || c.email : "one customer";
}

const customerLabel = function (c) { return (c.company_name || c.full_name || c.email) + " — " + c.email; };

async function loadCustomers(term) {
  const r = await BL.list("/users/customers", { search: term, limit: 50 });
  if (!term) customers = r.items;
  el("discCustomer").innerHTML = BL.options(r.items, function (c) { return c.id; }, customerLabel, "Every customer");
  await loadCustomerSubs();
}

async function loadCustomerSubs() {
  const customer = el("discCustomer").value;
  el("discSubField").hidden = !customer;
  if (!customer) return;
  const r = await BL.list("/subscriptions", { customer_id: customer, limit: 50 });
  el("discSub").innerHTML = BL.options(r.items, function (s) { return s.id; }, function (s) {
    return s.subscription_number + " — " + s.plan_name;
  }, "All of them");
}

async function loadTaxes() {
  const rows = await BL.api("/tax-rules");
  el("taxRows").innerHTML = rows.map(function (t) {
    const target = t.applies_to === "product" ? productName(t.product_id) : t.applies_to === "plan" ? planName(t.plan_id) : "Everything";
    return '<tr><td class="cell-strong">' + BL.esc(t.name) + "</td><td>" + (Number(t.rate) * 100).toFixed(2).replace(/\.?0+$/, "") + "%</td><td>" + BL.esc(target) + "</td>" +
      "<td>" + (t.is_active ? BL.badge("Active", "ok") : BL.badge("Off", "neutral")) + "</td>" +
      "<td>" + (isAdmin ? '<button class="btn btn-ghost btn-sm" data-del="tax-rules/' + BL.esc(t.id) + '">Delete</button>' : "") + "</td></tr>";
  }).join("") || '<tr><td colspan="5" class="empty-state">No tax rules yet.</td></tr>';
}

async function loadDiscounts() {
  const rows = await BL.api("/discounts");
  el("discountRows").innerHTML = rows.map(function (d) {
    const value = d.type === "percentage" ? Number(d.value) + "%" : BL.money(d.value);
    const what = d.scope === "subscription" ? "Whole subscription" : (d.product_ids || []).map(productName).join(", ") || "Products";
    const target = what + (d.subscription_id ? " · one subscription" : d.customer_id ? " · " + customerName(d.customer_id) + " only" : "");
    const toggle = d.is_active ? ["false", "Switch off"] : ["true", "Switch on"];
    return '<tr><td class="cell-strong">' + BL.esc(d.name) + "</td><td>" + BL.esc(value) + "</td><td>" + BL.esc(target) + "</td>" +
      '<td class="cell-muted">' + BL.date(d.start_date) + " – " + (d.end_date ? BL.date(d.end_date) : "ongoing") + "</td>" +
      "<td>" + d.used_count + (d.max_uses ? " / " + d.max_uses : "") + "</td>" +
      "<td>" + (d.is_active ? BL.badge("Active", "ok") : BL.badge("Off", "neutral")) + "</td>" +
      '<td><span class="toolbar"><button class="btn btn-ghost btn-sm" data-toggle="' + BL.esc(d.id) + '" data-to="' + toggle[0] + '">' + toggle[1] + "</button>" +
      '<button class="btn btn-ghost btn-sm" data-del="discounts/' + BL.esc(d.id) + '">Delete</button></span></td></tr>';
  }).join("") || '<tr><td colspan="7" class="empty-state">No discounts yet.</td></tr>';
}

async function loadTemplates() {
  templates = await BL.api("/quotation-templates");
  el("templateRows").innerHTML = templates.map(function (t) {
    return '<tr><td class="cell-strong">' + BL.esc(t.name) + "</td><td>" + BL.esc(planName(t.plan_id)) + "</td><td>" + t.lines.length + "</td>" +
      "<td>" + t.validity_days + " days</td><td>" + t.payment_terms + " days</td>" +
      '<td><span class="toolbar"><button class="btn btn-ghost btn-sm" data-edit="' + BL.esc(t.id) + '">Edit</button>' +
      '<button class="btn btn-ghost btn-sm" data-del="quotation-templates/' + BL.esc(t.id) + '">Delete</button></span></td></tr>';
  }).join("") || '<tr><td colspan="6" class="empty-state">No templates yet.</td></tr>';
}

function loadAll() {
  const jobs = [loadTaxes(), loadTemplates()];
  if (isAdmin) jobs.push(loadDiscounts());
  return Promise.all(jobs);
}

function lineChoices() {
  const rows = [];
  products.forEach(function (p) {
    rows.push({ value: p.id + "|", text: p.name });
    (p.variants || []).filter(function (v) { return v.is_active; }).forEach(function (v) {
      rows.push({ value: p.id + "|" + v.id, text: p.name + " — " + v.label });
    });
  });
  return rows;
}

function addTemplateLine(line) {
  const row = document.createElement("div");
  row.className = "toolbar";
  row.style.marginBottom = "8px";
  row.dataset.price = line && line.unit_price !== null && line.unit_price !== undefined ? line.unit_price : "";
  row.innerHTML = '<select class="pill-select" style="flex:1;min-width:0;" data-tpl-product>' + BL.options(lineChoices(), function (c) { return c.value; }, function (c) { return c.text; }) + "</select>" +
    '<input class="qty-input" type="number" min="1" value="1" data-tpl-qty>' +
    '<button type="button" class="btn btn-ghost btn-sm" data-tpl-remove>Remove</button>';
  el("tplLines").appendChild(row);
  if (line) {
    row.querySelector("[data-tpl-product]").value = line.product_id + "|" + (line.variant_id || "");
    row.querySelector("[data-tpl-qty]").value = line.quantity;
  }
}

function openTemplate(template) {
  editingTemplate = template || null;
  el("tplTitle").textContent = template ? "Edit quotation template" : "Add quotation template";
  el("tplPlan").disabled = !!template;
  el("tplName").value = template ? template.name : "";
  el("tplValidity").value = template ? template.validity_days : 30;
  el("tplTerms").value = template ? template.payment_terms : 15;
  el("tplNotes").value = template ? template.notes || "" : "";
  if (template) el("tplPlan").value = template.plan_id;
  el("tplLines").innerHTML = "";
  if (template) template.lines.forEach(addTemplateLine);
  else addTemplateLine();
  BL.modal("templateModal", true);
}

function submit(formId, modalId, action, reload) {
  const form = el(formId);
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    BL.run(async function () {
      await action();
      form.reset();
      BL.modal(modalId, false);
      BL.toast("Saved", "ok");
      await reload();
    }, form.querySelector('button[type="submit"]'));
  });
}

(async function () {
  const me = await BL.boot(["admin", "staff"]);
  isAdmin = me.role === "admin";
  document.querySelectorAll(".admin-only").forEach(function (n) { n.hidden = !isAdmin; });
  const data = await Promise.all([BL.api("/products"), BL.api("/plans")]);
  products = data[0]; plans = data[1];
  const live = plans.filter(function (p) { return p.is_active; });
  const planOptions = BL.options(live, function (p) { return p.id; }, function (p) { return p.name; });
  const productOptions = BL.options(products, function (p) { return p.id; }, function (p) { return p.name; });
  el("taxPlan").innerHTML = planOptions;
  el("tplPlan").innerHTML = planOptions;
  el("taxProduct").innerHTML = productOptions;
  el("discProducts").innerHTML = productOptions;
  if (isAdmin) await loadCustomers("");
  await loadAll();
})().catch(function (e) { BL.toast(e.message); });

el("addTaxBtn").addEventListener("click", function () { BL.modal("taxModal", true); });
el("addDiscountBtn").addEventListener("click", function () {
  el("discStart").value = BL.iso(new Date());
  BL.modal("discountModal", true);
});
el("addTemplateBtn").addEventListener("click", function () { openTemplate(); });
el("tplAddLine").addEventListener("click", function () { addTemplateLine(); });
el("discCustomer").addEventListener("change", function () { BL.run(loadCustomerSubs); });
BL.onSearch(el("discCustomerSearch"), function (term) { BL.run(function () { return loadCustomers(term); }); });
el("tplLines").addEventListener("click", function (e) {
  if (e.target.dataset.tplRemove !== undefined) e.target.parentNode.remove();
});
el("taxAppliesTo").addEventListener("change", function (e) {
  el("taxProductField").hidden = e.target.value !== "product";
  el("taxPlanField").hidden = e.target.value !== "plan";
});
el("discScope").addEventListener("change", function (e) {
  el("discProductsField").hidden = e.target.value !== "product";
});

submit("taxForm", "taxModal", function () {
  const applies = el("taxAppliesTo").value;
  return BL.post("/tax-rules", {
    name: el("taxName").value,
    rate: (Number(el("taxRate").value) / 100).toFixed(4),
    applies_to: applies,
    product_id: applies === "product" ? el("taxProduct").value : null,
    plan_id: applies === "plan" ? el("taxPlan").value : null
  });
}, loadTaxes);

submit("discountForm", "discountModal", function () {
  const scope = el("discScope").value;
  return BL.post("/discounts", {
    name: el("discName").value,
    type: el("discType").value,
    value: el("discValue").value,
    min_purchase: el("discMinPurchase").value || null,
    min_quantity: el("discMinQty").value ? Number(el("discMinQty").value) : null,
    start_date: el("discStart").value,
    end_date: el("discEnd").value || null,
    max_uses: el("discMaxUses").value ? Number(el("discMaxUses").value) : null,
    scope: scope,
    product_ids: scope === "product" ? Array.from(el("discProducts").selectedOptions).map(function (o) { return o.value; }) : [],
    customer_id: el("discCustomer").value || null,
    subscription_id: el("discCustomer").value ? el("discSub").value || null : null
  });
}, function () {
  el("discSubField").hidden = true;
  el("discProductsField").hidden = true;
  return loadDiscounts();
});

submit("templateForm", "templateModal", function () {
  const lines = Array.from(el("tplLines").children).map(function (row) {
    const pick = row.querySelector("[data-tpl-product]").value.split("|");
    return {
      product_id: pick[0],
      variant_id: pick[1] || null,
      quantity: Number(row.querySelector("[data-tpl-qty]").value),
      unit_price: row.dataset.price || null
    };
  });
  const body = {
    name: el("tplName").value,
    validity_days: Number(el("tplValidity").value),
    payment_terms: Number(el("tplTerms").value),
    notes: el("tplNotes").value || null,
    lines: lines
  };
  if (editingTemplate) return BL.patch("/quotation-templates/" + editingTemplate.id, body);
  return BL.post("/quotation-templates", Object.assign(body, { plan_id: el("tplPlan").value }));
}, loadTemplates);

document.querySelector(".main").addEventListener("click", function (e) {
  const del = e.target.closest("[data-del]");
  if (del) {
    return BL.ask("Delete this item?", "Delete").then(function (yes) {
      if (yes) BL.run(async function () { await BL.del("/" + del.dataset.del); await loadAll(); });
    });
  }
  const edit = e.target.closest("[data-edit]");
  if (edit) return openTemplate(templates.find(function (t) { return t.id === edit.dataset.edit; }));
  const toggle = e.target.closest("[data-toggle]");
  if (toggle) {
    BL.run(async function () {
      await BL.patch("/discounts/" + toggle.dataset.toggle, { is_active: toggle.dataset.to === "true" });
      await loadDiscounts();
    }, toggle);
  }
});
