/* Brightloop — shared sidebar nav.
   Each screen only needs: <nav class="rail" id="rail-mount"></nav>
   and <script src="static/js/nav.js"></script>, after api.js.
   Editing the list below updates navigation on every screen at once. */
(function () {
  const ICONS = {
    dashboard: '<path d="M3 20V10M10 20V4M17 20v-7"/>',
    pipeline: '<path d="M3 12h4l3 8 4-16 3 8h4"/>',
    invoices: '<path d="M4 4h16v4H4zM4 10h16v10H4z"/>',
    catalog: '<path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"/>',
    staff: '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6M16 9c1.7 0 3 1.3 3 3M21 20c0-2.6-1.8-4.8-4-5.6"/>',
    pricing: '<path d="M4 4h8l8 8-8 8-8-8zM8.5 8.5h.01"/>',
    portal: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"/>'
  };

  const NAV = [
    { file: "dashboard.html",             label: "Dashboard", icon: "dashboard", roles: ["admin", "staff"] },
    { file: "pipeline.html",              label: "Pipeline",  icon: "pipeline",  roles: ["admin", "staff"] },
    { file: "invoicing.html",             label: "Invoices",  icon: "invoices",  roles: ["admin", "staff"] },
    { file: "plan-builder.html",          label: "Catalog",   icon: "catalog",   roles: ["admin", "staff"] },
    { file: "pricing.html",               label: "Pricing",   icon: "pricing",   roles: ["admin", "staff"] },
    { file: "auth-rbac.html?view=rbac",   label: "Staff",     icon: "staff",     roles: ["admin"] },
    { file: "customer-portal.html",       label: "Portal",    icon: "portal",    roles: ["customer"] }
  ];

  window.renderNav = function () {
  const rail = document.getElementById("rail-mount");
  if (!rail) return;

  const role = typeof BL !== "undefined" ? BL.role() : null;
  const currentFile = location.pathname.split("/").pop() || "dashboard.html";

  let html = '<a class="rail-logo" href="dashboard.html" title="Home">B</a>';
  NAV.filter(function (item) { return !role || item.roles.includes(role); }).forEach(function (item) {
    const targetFile = item.file.split("?")[0];
    const active = targetFile === currentFile ? " active" : "";
    html +=
      '<a class="rail-link' + active + '" href="' + item.file + '">' +
      '<svg viewBox="0 0 24 24">' + ICONS[item.icon] + "</svg>" +
      item.label +
      "</a>";
  });
  rail.innerHTML = html;
  };

  window.renderNav();
})();
