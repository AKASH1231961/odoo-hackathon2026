/* Brightloop — shared API client and page helpers.
   Every page loads this first, then nav.js, then its own script in js/pages/.
   Permissions are enforced by the API; the checks here only hide what would fail. */
const BL = (function () {
  const API = "/api";
  const HOME = { admin: "dashboard.html", staff: "dashboard.html", customer: "customer-portal.html" };
  const PERSONA = { admin: "Admin workspace", staff: "Internal operations", customer: "Customer portal" };

  function store(key, value) {
    try {
      if (value === undefined) return localStorage.getItem(key);
      if (value === null) localStorage.removeItem(key);
      else localStorage.setItem(key, value);
    } catch (e) { return null; }
  }

  function setTokens(pair) {
    store("bl_access", pair.access_token);
    store("bl_refresh", pair.refresh_token);
  }

  function signOut() {
    ["bl_access", "bl_refresh", "bl_role"].forEach(function (k) { store(k, null); });
    location.href = "auth-rbac.html";
  }

  async function refresh() {
    const token = store("bl_refresh");
    if (!token) return false;
    const res = await fetch(API + "/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token })
    });
    if (!res.ok) return false;
    setTokens(await res.json());
    return true;
  }

  function query(params) {
    const q = new URLSearchParams();
    Object.keys(params || {}).forEach(function (k) {
      if (params[k] !== "" && params[k] !== null && params[k] !== undefined) q.set(k, params[k]);
    });
    const s = q.toString();
    return s ? "?" + s : "";
  }

  async function send(path, options, retried) {
    const opts = options || {};
    const headers = {};
    const token = store("bl_access");
    if (token) headers.Authorization = "Bearer " + token;
    if (opts.body !== undefined) headers["Content-Type"] = "application/json";
    const res = await fetch(API + path + query(opts.params), {
      method: opts.method || "GET",
      headers: headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined
    });
    if (res.status === 401 && token && !retried) {
      if (await refresh()) return send(path, options, true);
      signOut();
      throw new Error("Your session has expired. Please sign in again.");
    }
    if (!res.ok) {
      const data = await res.json().catch(function () { return {}; });
      throw new Error(typeof data.detail === "string" ? data.detail : "Something went wrong (" + res.status + ")");
    }
    return res;
  }

  async function api(path, options) {
    const res = await send(path, options);
    return (res.headers.get("content-type") || "").includes("json") ? res.json() : null;
  }

  async function list(path, params) {
    const res = await send(path, { params: params });
    return { items: await res.json(), total: Number(res.headers.get("X-Total-Count") || 0) };
  }

  const post = function (path, body) { return api(path, { method: "POST", body: body }); };
  const patch = function (path, body) { return api(path, { method: "PATCH", body: body }); };
  const del = function (path) { return api(path, { method: "DELETE" }); };

  /* A plain link cannot send the login token, so files are fetched, then saved */
  function save(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  async function download(path, filename) {
    const res = await send(path);
    save(await res.blob(), filename);
  }

  function saveCsv(rows, filename) {
    const cell = function (v) {
      let s = String(v === null || v === undefined ? "" : v);
      if (/^[=+\-@]/.test(s) && isNaN(Number(s))) s = "'" + s; // keep spreadsheets from running it
      return '"' + s.replace(/"/g, '""') + '"';
    };
    save(new Blob([rows.map(function (r) { return r.map(cell).join(","); }).join("\n")], { type: "text/csv" }), filename);
  }

  function esc(v) {
    return String(v === null || v === undefined ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function money(v) {
    return "₹" + Number(v || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function date(v) {
    if (!v) return "—";
    const d = new Date(String(v).length === 10 ? v + "T00:00:00" : v);
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  }

  function iso(d) {
    const pad = function (n) { return String(n).padStart(2, "0"); };
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }

  function label(v) {
    if (v === "upi") return "UPI";
    const s = String(v || "").replace(/_/g, " ");
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function badge(text, kind) {
    return '<span class="badge badge-' + kind + '">' + esc(text) + "</span>";
  }

  function subBadge(status) {
    const kinds = { draft: "neutral", quotation: "warn", confirmed: "accent", active: "ok", paused: "warn", closed: "neutral" };
    return badge(label(status), kinds[status] || "neutral");
  }

  function invoiceBadge(inv) {
    if (inv.is_overdue) return badge("Overdue", "danger");
    const kinds = { draft: "neutral", confirmed: "warn", paid: "ok", cancelled: "neutral" };
    return badge(label(inv.status), kinds[inv.status] || "neutral");
  }

  function toast(message, kind) {
    let stack = document.getElementById("notices");
    if (!stack) {
      stack = document.createElement("div");
      stack.id = "notices";
      stack.className = "notices";
      document.body.appendChild(stack);
    }
    const el = document.createElement("div");
    el.className = "notice" + (kind === "ok" ? " notice-ok" : "");
    el.setAttribute("role", "status");
    el.textContent = message;
    stack.appendChild(el);
    setTimeout(function () { el.remove(); }, kind === "ok" ? 3500 : 7000);
  }

  /* Runs an action, reports its failure, and keeps a button from being pressed twice */
  async function run(action, button) {
    if (button) button.disabled = true;
    try {
      return await action();
    } catch (e) {
      toast(e.message || "Something went wrong");
    } finally {
      if (button) button.disabled = false;
    }
  }

  function ask(message, confirmLabel) {
    return new Promise(function (resolve) {
      const overlay = document.createElement("div");
      overlay.className = "modal-overlay open";
      overlay.innerHTML =
        '<div class="modal"><div class="modal-head"><h3>Please confirm</h3></div>' +
        '<p class="cell-muted" style="font-size:13.5px;margin-bottom:18px;">' + esc(message) + "</p>" +
        '<div class="modal-actions"><button class="btn btn-ghost" data-a="no">Go back</button>' +
        '<button class="btn btn-primary" data-a="yes">' + esc(confirmLabel || "Confirm") + "</button></div></div>";
      overlay.addEventListener("click", function (e) {
        const a = e.target.dataset.a;
        if (!a) return;
        overlay.remove();
        resolve(a === "yes");
      });
      document.body.appendChild(overlay);
    });
  }

  function modal(id, open) {
    document.getElementById(id).classList.toggle("open", open);
  }

  function options(items, value, text, first) {
    const rows = items.map(function (i) {
      return '<option value="' + esc(value(i)) + '">' + esc(text(i)) + "</option>";
    });
    if (first) rows.unshift('<option value="">' + esc(first) + "</option>");
    return rows.join("");
  }

  function initials(user) {
    const name = user.company_name || user.full_name || user.email;
    return name.split(/[\s@.]+/).filter(Boolean).slice(0, 2).map(function (p) { return p[0]; }).join("").toUpperCase();
  }

  /* Page guard: returns the signed-in user, or leaves for sign-in or their own home */
  async function boot(roles) {
    if (!store("bl_access") && !store("bl_refresh")) {
      location.href = "auth-rbac.html";
      return new Promise(function () {});
    }
    const me = await api("/users/me");
    store("bl_role", me.role);
    if (!roles.includes(me.role)) {
      location.href = HOME[me.role];
      return new Promise(function () {});
    }
    if (window.renderNav) window.renderNav();
    const avatar = document.querySelector(".topbar .avatar");
    if (avatar) { avatar.textContent = initials(me); avatar.title = me.email; }
    const persona = document.querySelector(".topbar .persona-tag");
    if (persona) persona.textContent = PERSONA[me.role];
    const out = document.querySelector(".topbar .icon-btn");
    if (out) {
      out.textContent = "⏻";
      out.title = "Sign out";
      out.style.cursor = "pointer";
      out.onclick = signOut;
    }
    return me;
  }

  /* Calls fn after typing stops, or straight away on Enter */
  function onSearch(input, fn) {
    let timer;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(function () { fn(input.value.trim()); }, 300);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key !== "Enter") return;
      clearTimeout(timer);
      fn(input.value.trim());
    });
  }

  return {
    api: api, list: list, post: post, patch: patch, del: del, setTokens: setTokens, signOut: signOut, boot: boot,
    home: function (role) { return HOME[role]; }, role: function () { return store("bl_role"); },
    setRole: function (role) { store("bl_role", role); }, hasSession: function () { return !!store("bl_access"); },
    download: download, saveCsv: saveCsv, esc: esc, money: money, date: date, iso: iso, label: label, badge: badge,
    subBadge: subBadge, invoiceBadge: invoiceBadge, toast: toast, run: run, ask: ask, modal: modal, options: options,
    onSearch: onSearch
  };
})();
