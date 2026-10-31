const el = function (id) { return document.getElementById(id); };
const SUFFIX = { daily: " / day", weekly: " / wk", monthly: " / mo", yearly: " / yr" };
let products = [], plans = [], variants = [], removed = [], editing = null, editingPlan = null, interval = "monthly", term = "";

function clearForm() {
  editing = null; editingPlan = null; variants = []; removed = [];
  ["prodName", "prodPrice", "prodCost", "prodNotes", "planName", "planPrice", "planFrom", "planTo", "variantLabel", "variantDelta"]
    .forEach(function (id) { el(id).value = ""; });
  el("prodType").value = "Software";
  el("planMin").value = 1;
  el("planAutoClose").checked = false;
  ["planClose", "planPause", "planRenew"].forEach(function (id) { el(id).checked = true; });
  setFrequency("monthly");
  renderEditing();
}

function setFrequency(value) {
  interval = value;
  document.querySelectorAll("#freqPick button").forEach(function (b) { b.classList.toggle("active", b.dataset.v === value); });
}

function renderEditing() {
  el("pageTitle").textContent = editing ? "Edit " + editing.name : "New product & plan";
  el("saveBtn").textContent = editing ? "Save changes" : "Save product";
  el("planHint").textContent = editingPlan ? "Editing " + editingPlan.name
    : "Leave the plan name empty to save only the product";
  document.querySelectorAll("#freqPick button").forEach(function (b) { b.disabled = !!editingPlan; });
  renderVariants();
}

function renderVariants() {
  el("variantRows").innerHTML = variants.map(function (v, i) {
    return '<div class="variant-row"><span class="name">' + BL.esc(v.label) + '</span><span class="toolbar"><span class="price">+ ' + BL.money(v.price_delta) + "</span>" +
      '<button class="btn btn-ghost btn-sm" type="button" data-i="' + i + '">Remove</button></span></div>';
  }).join("") || '<p class="hint" style="font-size:12px;color:var(--text-muted);margin-bottom:6px;">No variants.</p>';
  renderPreview();
}

function renderPreview() {
  const base = Number(el("planPrice").value || el("prodPrice").value || 0);
  const suffix = SUFFIX[interval];
  el("preview").innerHTML = '<div class="summary-line"><span class="l">Base price</span><span>' + BL.money(base) + suffix + "</span></div>" +
    variants.map(function (v) {
      return '<div class="summary-line"><span class="l">' + BL.esc(v.label) + " variant</span><span>" + BL.money(base + Number(v.price_delta)) + suffix + "</span></div>";
    }).join("") +
    '<div class="summary-line total"><span class="l">Customer sees</span><span>' + BL.money(base) + suffix + "</span></div>";
}

function matches(text) {
  return !term || text.toLowerCase().includes(term);
}

function renderLists() {
  el("productRows").innerHTML = products.filter(function (p) { return matches(p.name); }).map(function (p) {
    return '<tr class="clickable" data-product="' + BL.esc(p.id) + '"><td class="cell-strong">' + BL.esc(p.name) + '</td><td class="cell-muted">' + BL.money(p.sales_price) + "</td></tr>";
  }).join("") || '<tr><td class="empty-state">No products.</td></tr>';
  const admin = BL.role() === "admin";
  el("existingPlans").innerHTML = plans.filter(function (p) { return matches(p.name); }).map(function (p) {
    return '<tr class="clickable" data-plan="' + BL.esc(p.id) + '"><td class="cell-strong">' + BL.esc(p.name) + '</td><td class="cell-muted">' + BL.esc(BL.label(p.billing_interval)) + "</td>" +
      "<td>" + (p.is_active ? BL.badge("Live", "ok") : BL.badge("Closed", "neutral")) + "</td>" +
      "<td>" + (admin && p.is_active ? '<button class="btn btn-ghost btn-sm" data-close="' + BL.esc(p.id) + '">Close</button>' : "") + "</td></tr>";
  }).join("") || '<tr><td class="empty-state">No plans.</td></tr>';
}

async function loadLists() {
  const data = await Promise.all([BL.api("/products"), BL.api("/plans")]);
  products = data[0]; plans = data[1];
  renderLists();
}

function loadProduct(p) {
  editing = p;
  variants = (p.variants || []).filter(function (v) { return v.is_active; }).map(function (v) { return Object.assign({}, v); });
  removed = [];
  el("prodName").value = p.name;
  el("prodType").value = ["Software", "Add-on", "Service"].includes(p.type) ? p.type : "Software";
  el("prodPrice").value = p.sales_price;
  el("prodCost").value = p.cost_price || "";
  el("prodNotes").value = p.notes || "";
}

function clearPlan() {
  editingPlan = null;
  ["planName", "planPrice", "planFrom", "planTo"].forEach(function (id) { el(id).value = ""; });
  el("planMin").value = 1;
  el("planAutoClose").checked = false;
  ["planClose", "planPause", "planRenew"].forEach(function (id) { el(id).checked = true; });
}

function loadPlan(p) {
  loadProduct(products.find(function (x) { return x.id === p.product_id; }));
  editingPlan = p;
  el("planName").value = p.name;
  el("planPrice").value = p.price;
  el("planMin").value = p.min_quantity;
  el("planFrom").value = p.available_from || "";
  el("planTo").value = p.available_to || "";
  el("planAutoClose").checked = p.auto_close;
  el("planClose").checked = p.can_close_early;
  el("planPause").checked = p.can_pause;
  el("planRenew").checked = p.can_renew;
  setFrequency(p.billing_interval);
}

async function save() {
  const name = el("prodName").value.trim();
  if (!name) throw new Error("Enter a product name");
  if (el("prodPrice").value === "") throw new Error("Enter a sales price");
  const product = {
    name: name,
    type: el("prodType").value,
    sales_price: el("prodPrice").value,
    cost_price: el("prodCost").value || null,
    notes: el("prodNotes").value || null
  };
  const saved = editing ? await BL.patch("/products/" + editing.id, product) : await BL.post("/products", product);

  for (const id of removed) await BL.del("/products/" + saved.id + "/variants/" + id);
  for (const v of variants.filter(function (x) { return !x.id; })) {
    await BL.post("/products/" + saved.id + "/variants", { label: v.label, price_delta: v.price_delta });
  }

  const planName = el("planName").value.trim();
  if (planName) {
    const plan = {
      name: planName,
      price: el("planPrice").value || el("prodPrice").value,
      min_quantity: Number(el("planMin").value || 1),
      available_from: el("planFrom").value || null,
      available_to: el("planTo").value || null,
      auto_close: el("planAutoClose").checked,
      can_close_early: el("planClose").checked,
      can_pause: el("planPause").checked,
      can_renew: el("planRenew").checked
    };
    if (editingPlan) await BL.patch("/plans/" + editingPlan.id, plan);
    else await BL.post("/plans", Object.assign(plan, { product_id: saved.id, billing_interval: interval }));
  }
  BL.toast("Saved", "ok");
  clearForm();
  await loadLists();
}

(async function () {
  const me = await BL.boot(["admin", "staff"]);
  if (me.role !== "admin") {
    el("editActions").hidden = true;
    el("editForm").hidden = true;
    el("previewPanel").hidden = true;
    el("pageTitle").textContent = "Catalog";
    document.querySelector(".page-head .sub").textContent = "Only an admin can change products and plans.";
    document.querySelector(".main-grid").style.gridTemplateColumns = "1fr";
  }
  clearForm();
  await loadLists();
})().catch(function (e) { BL.toast(e.message); });

el("cancelBtn").addEventListener("click", clearForm);
el("saveBtn").addEventListener("click", function (e) { BL.run(save, e.currentTarget); });
BL.onSearch(el("catalogSearch"), function (value) { term = value.toLowerCase(); renderLists(); });
["prodPrice", "planPrice"].forEach(function (id) { el(id).addEventListener("input", renderPreview); });

el("freqPick").addEventListener("click", function (e) {
  if (e.target.dataset.v && !e.target.disabled) { setFrequency(e.target.dataset.v); renderPreview(); }
});

el("addVariantBtn").addEventListener("click", function () {
  const label = el("variantLabel").value.trim();
  if (!label) return BL.toast("Enter a variant name");
  variants.push({ label: label, price_delta: el("variantDelta").value || "0" });
  el("variantLabel").value = "";
  el("variantDelta").value = "";
  renderVariants();
});

el("variantRows").addEventListener("click", function (e) {
  if (e.target.dataset.i === undefined) return;
  const v = variants.splice(Number(e.target.dataset.i), 1)[0];
  if (v.id) removed.push(v.id);
  renderVariants();
});

el("productRows").addEventListener("click", function (e) {
  if (BL.role() !== "admin") return;
  const row = e.target.closest("tr[data-product]");
  if (!row) return;
  clearPlan();
  loadProduct(products.find(function (p) { return p.id === row.dataset.product; }));
  renderEditing();
});

el("existingPlans").addEventListener("click", function (e) {
  const close = e.target.closest("[data-close]");
  if (close) {
    return BL.ask("Close this plan? It can no longer be sold; existing subscriptions keep running.", "Close plan").then(function (yes) {
      if (yes) BL.run(async function () { await BL.post("/plans/" + close.dataset.close + "/close"); await loadLists(); });
    });
  }
  if (BL.role() !== "admin") return;
  const row = e.target.closest("tr[data-plan]");
  if (!row) return;
  loadPlan(plans.find(function (p) { return p.id === row.dataset.plan; }));
  renderEditing();
});
