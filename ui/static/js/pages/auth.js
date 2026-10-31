const TABS = ["signin", "signup", "reset"];
const params = new URLSearchParams(location.search);
const resetToken = location.pathname.endsWith("/reset-password") ? params.get("token") : null;
let staff = [];

function message(text, kind) {
  const el = document.getElementById("authMsg");
  el.hidden = !text;
  el.textContent = text || "";
  el.className = "form-msg " + (kind || "err");
}

function showTab(name) {
  message("");
  [...TABS, "newpw"].forEach(function (t) {
    document.getElementById("tab-" + t).style.display = t === name ? "block" : "none";
  });
  document.querySelectorAll(".auth-tabs button").forEach(function (b, i) {
    b.classList.toggle("active", TABS[i] === name);
  });
}

function checkPw(input, rulesId) {
  const v = document.getElementById(input).value;
  const rules = {
    len: v.length > 8,
    upper: /[A-Z]/.test(v),
    lower: /[a-z]/.test(v),
    special: /[^A-Za-z0-9]/.test(v)
  };
  document.querySelectorAll("#" + rulesId + " .rule").forEach(function (el) {
    el.classList.toggle("met", rules[el.dataset.rule]);
  });
}

async function signIn(email, password) {
  BL.setTokens(await BL.post("/auth/login", { email: email, password: password }));
  const me = await BL.api("/users/me");
  BL.setRole(me.role);
  location.href = BL.home(me.role);
}

function onSubmit(id, action) {
  const form = document.getElementById(id);
  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    message("");
    button.disabled = true;
    try {
      await action();
    } catch (err) {
      message(err.message);
    } finally {
      button.disabled = false;
    }
  });
}

onSubmit("tab-signin", function () {
  return signIn(document.getElementById("signinEmail").value, document.getElementById("signinPassword").value);
});

onSubmit("tab-signup", async function () {
  const email = document.getElementById("signupEmail").value;
  const password = document.getElementById("pw").value;
  await BL.post("/auth/register", {
    email: email, password: password, full_name: document.getElementById("signupName").value
  });
  await signIn(email, password);
});

onSubmit("tab-reset", async function () {
  const res = await BL.post("/auth/forgot-password", { email: document.getElementById("resetEmail").value });
  message(res.message, "ok");
});

onSubmit("tab-newpw", async function () {
  await BL.post("/auth/reset-password", { token: resetToken, new_password: document.getElementById("newPw").value });
  history.replaceState(null, "", "auth-rbac.html");
  showTab("signin");
  message("Password updated. Sign in with your new password.", "ok");
});

/* ---------- Staff & access ---------- */
function renderStaff() {
  const role = document.getElementById("roleFilter").value;
  const status = document.getElementById("statusFilter").value;
  const term = document.getElementById("staffSearch").value.trim().toLowerCase();
  const rows = staff.filter(function (u) {
    return (!role || u.role === role) &&
      (!status || String(u.is_active) === status) &&
      (!term || [u.full_name, u.email, u.role].join(" ").toLowerCase().includes(term));
  });
  document.getElementById("staffCount").textContent = rows.length + (rows.length === 1 ? " member" : " members");
  document.getElementById("staffRows").innerHTML = rows.map(function (u) {
    const name = u.full_name || u.email;
    const initials = name.split(/\s+/).slice(0, 2).map(function (p) { return p[0]; }).join("").toUpperCase();
    return "<tr><td><span class=\"avatar-sm\">" + BL.esc(initials) + "</span> &nbsp;<span class=\"cell-strong\">" + BL.esc(name) + "</span></td>" +
      '<td class="cell-muted">' + BL.esc(u.email) + "</td><td>" + BL.esc(BL.label(u.role)) + "</td>" +
      "<td>" + (u.is_active ? BL.badge("Active", "ok") : BL.badge("Deactivated", "neutral")) + "</td>" +
      '<td class="cell-muted">' + BL.date(u.created_at) + "</td>" +
      '<td><button class="btn btn-ghost btn-sm" data-id="' + BL.esc(u.id) + '" data-active="' + u.is_active + '">' +
      (u.is_active ? "Deactivate" : "Reactivate") + "</button></td></tr>";
  }).join("") || '<tr><td colspan="6" class="empty-state">No staff members match.</td></tr>';
}

async function loadStaff() {
  const rows = await Promise.all([
    BL.list("/users", { role: "admin", limit: 200 }),
    BL.list("/users", { role: "staff", limit: 200 })
  ]);
  staff = rows[0].items.concat(rows[1].items);
  renderStaff();
}

async function showStaffView() {
  document.getElementById("view-auth").classList.remove("active");
  document.getElementById("view-rbac").classList.add("active");
  document.body.classList.remove("auth-mode");
  document.title = "Brightloop — Staff & access";
  await BL.boot(["admin"]);
  await BL.run(loadStaff);

  ["roleFilter", "statusFilter"].forEach(function (id) {
    document.getElementById(id).addEventListener("change", renderStaff);
  });
  BL.onSearch(document.getElementById("staffSearch"), renderStaff);

  document.getElementById("staffRows").addEventListener("click", function (e) {
    const b = e.target.closest("button[data-id]");
    if (!b) return;
    const action = b.dataset.active === "true" ? "deactivate" : "activate";
    BL.run(async function () {
      await BL.patch("/users/" + b.dataset.id + "/" + action);
      await loadStaff();
    }, b);
  });

  const form = document.getElementById("inviteForm");
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    BL.run(async function () {
      await BL.post("/users", {
        full_name: document.getElementById("inviteName").value,
        email: document.getElementById("inviteEmail").value,
        password: document.getElementById("invitePassword").value,
        role: document.getElementById("inviteRole").value
      });
      form.reset();
      BL.modal("inviteModal", false);
      BL.toast("Staff member added", "ok");
      await loadStaff();
    }, form.querySelector('button[type="submit"]'));
  });
}

if (params.get("view") === "rbac") {
  BL.run(showStaffView);
} else if (resetToken) {
  showTab("newpw");
  document.querySelectorAll(".auth-tabs button").forEach(function (b) { b.classList.remove("active"); });
} else if (BL.hasSession() && BL.role()) {
  location.href = BL.home(BL.role());
}
