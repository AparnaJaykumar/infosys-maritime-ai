"use strict";
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const k in (attrs || {})) {
    const v = attrs[k];
    if (v == null || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "html") e.innerHTML = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) {
    if (c != null && c !== false) e.append(c.nodeType ? c : document.createTextNode(c));
  }
  return e;
}

const TONE = {
  Critical: "#dc2626", High: "#dc2626", Fail: "#dc2626", rejected: "#dc2626", "On Hold": "#dc2626", overdue: "#dc2626",
  Warning: "#d97706", Medium: "#d97706", "Pending Approval": "#d97706", proposed: "#7c3aed",
  Info: "#2563eb", open: "#2563eb", Low: "#059669", Pass: "#059669", Approved: "#059669", approved: "#059669",
  resolved: "#059669", "auto-closed": "#64748b", live: "#059669", Healthy: "#059669", Watch: "#d97706", Rejected: "#64748b"
};
const tone = v => TONE[v] || (/crit|high|fail|bad|reject|hold/i.test(v) ? "#dc2626" : /warn|med|pend/i.test(v) ? "#d97706" : /ok|pass|low|good|appr|done|clear|live/i.test(v) ? "#059669" : "#64748b");

const ICON = { bot: "M12 8V4H8M4 12a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2zM2 14h2M20 14h2M9 15v1M15 15v1", users: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8", store: "M3 9l1-5h16l1 5M3 9v11h18V9M3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0M9 20v-6h6v6", boxes: "M21 8l-9-5-9 5 9 5zM3 8v8l9 5 9-5V8M12 13v8", megaphone: "M3 11v2a1 1 0 0 0 1 1h3l8 5V5L7 10H4a1 1 0 0 0-1 1zM19 8a5 5 0 0 1 0 8", messages: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z", clipboard: "M9 4h6v3H9zM8 5H6a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 13l2 2 4-4", bell: "M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0", network: "M12 2v6M12 16v6M5 6l5 4M19 6l-5 4M5 18l5-4M19 18l-5-4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8", flask: "M10 2v7L4 20a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1l-6-11V2M8 2h8M7 15h10", upload: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12", shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10", radar: "M12 12l7-7M12 2a10 10 0 1 0 10 10M12 6a6 6 0 1 0 6 6M12 10a2 2 0 1 0 2 2", route: "M6 19a3 3 0 1 0 0-6 3 3 0 0 0 0 6M18 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6M9 16h6a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h3", dollar: "M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6", truck: "M1 3h15v13H1zM16 8h4l3 3v5h-7M5.5 21a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5M18.5 21a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5", cloud: "M17.5 19a4.5 4.5 0 1 0-1.4-8.8A6 6 0 1 0 5 15a4 4 0 0 0 1 4z", trend: "M3 17l6-6 4 4 8-8M15 7h6v6", chart: "M3 3v18h18M7 15l4-4 3 3 5-6", check: "M22 11.1V12a10 10 0 1 1-5.9-9.1M22 4L12 14l-3-3", user: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8", file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M9 13h6M9 17h6" };

const icon = n => {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  s.setAttribute("viewBox", "0 0 24 24");
  const d = ICON[n] || ICON.bot;
  s.innerHTML = d.split("|").map(p => `<path d="${p}" />`).join("");
  return s;
};

async function api(url, opts = {}) {
  const token = localStorage.getItem("fq_token");
  const headers = { ...(opts.headers || {}) };
  if (token) headers["Authorization"] = "Bearer " + token;
  let body = opts.body;
  if (opts.json) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  }
  try {
    const res = await fetch(url, { ...opts, method: opts.method || (opts.json !== undefined ? 'POST' : 'GET'), headers, body });
    // Auth endpoints return meaningful errors (including account lockout).
    // Never overwrite them with the generic protected-session message.
    if (res.status === 401) {
      const data = await res.json().catch(() => ({}));
      const reason = data.msg || data.detail || "Session expired. Please sign in.";
      if (!url.startsWith("/api/auth/")) {
        localStorage.removeItem("fq_token");
        S.me = null;
        shellMounted = false;
        if (!location.hash.startsWith("#/login") && !location.hash.startsWith("#/signup") && location.hash !== "#/" && location.hash !== "") {
          window.location.hash = "#/login";
        }
      }
      return { ...data, ok: false, status: 401, msg: reason };
    }
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      const data = await res.json();
      if (!res.ok && data && typeof data === "object") {
        data.ok = false;
        data.status = res.status;
        data.msg = data.msg || data.detail || `Request failed (HTTP ${res.status}).`;
      }
      return data;
    }
    const responseText = await res.text();
    return { ok: res.ok, status: res.status, msg: res.ok ? "Done" : `Server error (HTTP ${res.status}).`, text: responseText };
  } catch (err) {
    console.error("FreightQuote API connection failed:", url, err);
    return { ok: false, msg: "Cannot reach the server. Check that the Colab runtime and application are still running." };
  }
}

function toast(msg, bad = false) {
  if (!msg) return;
  const t = $("#toast");
  if (!t) return;
  const d = h("div", { class: bad ? "bad" : "" }, msg);
  t.append(d);
  setTimeout(() => {
    d.style.opacity = "0";
    d.style.transform = "translateY(10px)";
    d.style.transition = "all 0.25s";
    setTimeout(() => d.remove(), 260);
  }, 3500);
}

function md(text) {
  if (!text) return "";
  let s = esc(text);
  // Markdown tables
  s = s.replace(/((?:\|[^\n]+\|\r?\n)+)/g, (match) => {
    const lines = match.trim().split(/\r?\n/);
    if (lines.length >= 2 && lines[0].includes("|") && lines[1].includes("---")) {
      const headers = lines[0].split("|").slice(1, -1).map(c => `<th>${c.trim()}</th>`).join("");
      const bodyRows = lines.slice(2).map(row => {
        const cells = row.split("|").slice(1, -1).map(c => `<td>${c.trim()}</td>`).join("");
        return `<tr>${cells}</tr>`;
      }).join("");
      return `<div class="tbl" style="margin:10px 0;"><table style="width:100%;border-collapse:collapse;"><thead><tr>${headers}</tr></thead><tbody>${bodyRows}</tbody></table></div>`;
    }
    return match;
  });
  s = s.replace(/^### (.*$)/gim, '<h4 style="margin:8px 0 4px;font-size:14px;">$1</h4>');
  s = s.replace(/^## (.*$)/gim, '<h3 style="margin:10px 0 6px;font-size:15px;">$1</h3>');
  s = s.replace(/^# (.*$)/gim, '<h2 style="margin:12px 0 8px;font-size:16px;">$1</h2>');
  s = s.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
  s = s.replace(/\*(.*?)\*/g, '<i>$1</i>');
  s = s.replace(/`([^`]+)`/g, '<code style="background:rgba(0,0,0,0.06);padding:2px 5px;border-radius:4px;font-size:12px;font-family:monospace;">$1</code>');
  s = s.replace(/\n/g, '<br>');
  return s;
}

const S = {
  me: null,
  page: null,
  tab: null,
  params: {},
  seq: 0,
  timer: null,
  live: 0,
  tree: null,
  es: null,
  pulse: null,
  lang: "English"
};

// ---------------------------------------------------------------- mountList & updList
function mountList(parent, blocks, key) { const hs = blocks.map((b, i) => mount(b, key + "/" + i)); hs.forEach(x => parent.append(x.el)); return hs }
function updList(parent, hs, blocks, key) { if (hs.length !== blocks.length || hs.some((x, i) => x.t !== blocks[i].t || x.k !== (blocks[i].key || blocks[i].id || ""))) { parent.replaceChildren(); return mountList(parent, blocks, key) } hs.forEach((x, i) => x.update(blocks[i])); return hs }

const R = {};

// Every server-driven page is assembled from typed blocks. Keep the adapter
// separate from individual renderers so all pages (including nested layouts)
// can render and update consistently.
function mount(block, key = "block") {
  const b = block && typeof block === "object" ? block : { t: "callout", tone: "warn", text: "This section could not be displayed." };
  const type = String(b.t || "");
  const id = String(b.key || b.id || "");
  const factory = R[type];
  if (typeof factory !== "function") {
    const el = h("div", { class: "callout warn", role: "status" }, "This section is temporarily unavailable.");
    console.warn("FreightQuote: unrecognized page block", type);
    return { t: type, k: id, el, update() {} };
  }
  try {
    const view = factory(b, id, key);
    if (!view || !view.el) throw new Error("Invalid block view");
    return {
      t: type, k: id, el: view.el,
      update(next) {
        try {
          if (typeof view.update === "function") view.update(next);
        } catch (err) {
          console.error("FreightQuote: update error in", type, err);
          view.el.replaceChildren(h("div", { class: "callout warn" }, "Unable to refresh this section. Please reopen the page."));
        }
      }
    };
  } catch (err) {
    console.error("FreightQuote: render error in", type, err);
    const el = h("div", { class: "callout warn", role: "alert" }, "Unable to display this section. Please try again.");
    return { t: type, k: id, el, update() {} };
  }
}

// ---------------------------------------------------------------- Blocks: Table
R.table = b => {
  const el = h("div");
  const title = h("h3", { style: "margin:0 0 6px;font-size:14px;font-weight:700;color:var(--tx);" });
  const sub = h("div", { class: "sub", style: "color:var(--mut);font-size:12.5px;margin-bottom:8px;" });
  const srch = h("input", { class: "srch", placeholder: "Search records…", oninput: () => { st.q = srch.value.toLowerCase(); draw(); } });
  const box = h("div", { class: "tbl" });
  const st = { sort: null, dir: 1, q: "" };
  let cur = b;
  el.append(title, sub, srch, box);

  const draw = () => {
    const b = cur;
    title.textContent = b.title || "";
    title.style.display = b.title ? "" : "none";
    sub.textContent = b.sub || "";
    sub.style.display = b.sub ? "" : "none";
    srch.style.display = b.search ? "" : "none";
    if (b.h) box.style.maxHeight = b.h + "px";

    let rows = b.rows || [];
    if (st.q) rows = rows.filter(r => Object.values(r).some(v => String(v).toLowerCase().includes(st.q)));
    if (st.sort) rows = [...rows].sort((x, y) => {
      const a = x[st.sort], c = y[st.sort];
      return (a == null) - (c == null) || (a > c ? 1 : a < c ? -1 : 0) * st.dir;
    });

    const th = h("tr", null, ...b.cols.map(c => h("th", {
      onclick: () => {
        st.dir = st.sort === c.k ? -st.dir : 1;
        st.sort = c.k;
        draw();
      }
    }, c.label + (st.sort === c.k ? (st.dir > 0 ? " ▲" : " ▼") : ""))));

    const tb = rows.slice(0, 400).map(r => {
      const tr = h("tr", null, ...b.cols.map(c => {
        const v = r[c.k];
        let n;
        if (c.type === "pill") n = h("span", { class: "pill " + String(v).replace(/\s+/g, "_") }, String(v));
        else if (c.type === "money") n = "$" + Number(v || 0).toLocaleString();
        else if (c.type === "num") n = Number(v || 0).toLocaleString();
        else if (c.type === "bar") {
          const pct = Math.min(100, Math.max(0, (Number(v || 0) / (c.max || 5)) * 100));
          n = h("div", { style: "display:flex;align-items:center;gap:8px;" },
            h("div", { style: `height:6px;width:70px;background:var(--line);border-radius:99px;overflow:hidden;` },
              h("div", { style: `height:100%;width:${pct}%;background:var(--pri);border-radius:99px;` })
            ),
            h("span", { style: "font-size:12px;font-weight:600;" }, String(v))
          );
        }
        else n = String(v == null ? "—" : v);
        return h("td", null, n);
      }));

      if (b.open) {
        tr.classList.add("clickable-row");
        tr.onclick = (e) => {
          if (e.target.closest("button, a, input, select, label, .no-open")) return;
          UI.openEntity(r[b.open.col]);
        };
      }
      return tr;
    });

    const sc = box.scrollTop;
    box.replaceChildren(h("table", null, h("thead", null, th), h("tbody", null, ...tb)));
    box.scrollTop = sc;
    if (!rows.length) box.append(h("div", { style: "padding:20px;text-align:center;color:var(--mut);font-size:13px;" }, "No matching records found."));
  };

  draw();
  return { el, update: nb => { cur = nb; draw(); } };
};

// ---------------------------------------------------------------- Blocks: KPIs, Hero, Cards
R.kpis = b => {
  const el = h("div", { class: "kpis" });
  const render = it => {
    // The server-side blocks.KPIs contract uses {label, value, sub, tone}.
    // Handle old payloads without ever showing literal "undefined".
    const v = it.value ?? it.val;
    return h("div", { class: "kpi " + (it.tone || it.sev || "") },
      h("div", { class: "l" }, it.label || "Metric"),
      h("div", { class: "v" }, v == null || v === "" ? "—" : String(v)),
      it.sub ? h("div", { class: "s" }, it.sub) : null
    );
  };
  const update = next => el.replaceChildren(...(next.items || []).map(render));
  update(b);
  return { el, update };
};

R.card = (b, id, pfx) => {
  const el = h("div", { class: "card" });
  if (b.title) el.append(h("h3", null, b.title));
  mountList(el, b.blocks || [], pfx);
  return { el, update() {} };
};

R.row = (b, id, pfx) => {
  const el = h("div", { class: "row" });
  if (b.ratio) el.style.gridTemplateColumns = b.ratio.map(r => r + "fr").join(" ");
  mountList(el, b.blocks || [], pfx);
  return { el, update() {} };
};

R.col = (b, id, pfx) => {
  const el = h("div", { class: "col" });
  mountList(el, b.blocks || [], pfx);
  return { el, update() {} };
};

R.callout = b => {
  const el = h("div", { class: "callout " + (b.tone || "info") });
  if (b.title) el.append(h("div", { style: "font-weight:700;margin-bottom:4px;" }, b.title));
  el.append(h("div", null, b.text));
  return { el, update() {} };
};

R.button = b => {
  const el = h("button", {
    class: "btn " + (b.tone || "primary"),
    onclick: async () => {
      if (b.payload && b.payload.download) { window.open(b.url, "_blank"); return; }
      if (b.confirm && !confirm(b.confirm)) return;
      el.disabled = true;
      const r = await api(b.url, { json: b.payload || {} });
      toast(r.msg || "Done", !r.ok);
      el.disabled = false;
      if (r.refresh) reloadPage();
    }
  }, b.label);
  return { el, update() {} };
};

R.hero = b => {
  const el = h("div", { class: "card", style: "display:flex;align-items:center;gap:20px;border-left:4px solid var(--pri);" });
  const up = b => {
    const c = b.risk ? tone(b.risk) : "var(--pri)";
    el.replaceChildren(
      h("div", { style: "flex:1" },
        h("div", { style: "display:flex;align-items:center;gap:10px;margin-bottom:6px;" },
          h("h2", { style: "margin:0;font-size:17px;font-weight:700;color:var(--tx);" }, b.title),
          b.risk ? h("span", { class: "pill " + b.risk }, b.risk) : null
        ),
        h("p", { style: "margin:0;color:var(--mut);font-size:13px;" }, b.blurb)
      ),
      b.can_run ? h("button", {
        class: "btn primary sm",
        onclick: async e => {
          e.target.disabled = true;
          const r = await api("/api/run_agent", { json: { agent: b.agent } });
          toast(r.msg, !r.ok);
          e.target.disabled = false;
          reloadPage();
        }
      }, "Run analysis") : null
    );
  };
  up(b);
  return { el, update: up };
};

// ---------------------------------------------------------------- Tickets block
R.tickets = b => {
  const el = h("div"), st = { f: "all", open: new Set() }; let cur = b; const body = h("div"), fl = h("div", { class: "filters" }); el.append(h("h3", { style: "margin:0 0 6px;font-size:13.5px" }, b.title || "Tickets"), h("div", { class: "sub" }, b.sub || ""), fl, body);
  const act = async (id, a, json) => { const r = await api(`/api/ticket/${id}/${a}`, { json: json || {} }); toast(r.msg, !r.ok); if (document.activeElement) document.activeElement.blur(); st.sig = null; reloadPage(true) };
  const draw = () => {
    const items = cur.items; st.sig = JSON.stringify(items) + st.f + [...st.open]; const cnt = k => k === "all" ? items.length : k === "proposed" ? items.filter(i => i.status === "proposed").length : k === "overdue" ? items.filter(i => i.overdue).length : items.filter(i => i.sev === k).length;
    fl.replaceChildren(...["all", "proposed", "Critical", "Warning", "Info", "overdue"].map(k => h("span", { class: "chip" + (st.f === k ? " on" : ""), onclick: () => { st.f = k; draw() } }, (k === "proposed" ? "awaiting approval" : k) + " · " + cnt(k))));
    const list = items.filter(i => st.f === "all" || (st.f === "proposed" ? i.status === "proposed" : st.f === "overdue" ? i.overdue : i.sev === st.f));
    body.replaceChildren(...list.slice(0, 80).map(i => {
      const c = tone(i.sev); const t = h("div", { class: "tk " + i.sev + " " + i.status },
        h("div", { class: "h" }, h("b", null, "#" + i.id + " " + i.type.replace(/_/g, " ")), h("span", { class: "pill", style: `color:${c};border-color:${c}66` }, i.sev), i.status === "proposed" ? h("span", { class: "pill", style: "color:#8e4ec6;border-color:#8e4ec666" }, "awaiting approval") : null, i.overdue ? h("span", { class: "pill", style: "color:#e5484d;border-color:#e5484d66" }, "overdue") : null, h("a", { href: "#", onclick: e => { e.preventDefault(); UI.openEntity(i.target) } }, i.target)),
        h("div", { class: "d" }, i.detail), h("div", { class: "m" }, h("span", null, "agent: " + i.agent), h("span", null, "owner: " + (i.owner || "–")), h("span", null, "assignee: " + (i.assignee || "unassigned")), h("span", null, "due " + (i.due || "–")), h("span", null, i.ts)),
        i.chain && i.chain.length ? h("div", { class: "m" }, h("span", null, "approval chain: "), ...i.chain.map(s => h("span", { class: "pill", style: `color:${s.status === "approved" ? "#1a9e6e" : s.status === "rejected" ? "#e5484d" : "#8e4ec6"};border-color:currentColor` }, "L" + s.step + " " + s.role + (s.status === "approved" ? " ✓ " + s.by : s.status === "rejected" ? " ✗" : " …")))) : null,
        i.status === "proposed" && i.turn && !i.can_approve ? h("div", { class: "m" }, "Waiting for a " + i.turn + " to decide") : null,
        i.note ? h("div", { class: "m" }, "note: " + i.note) : null,
        h("div", { class: "a" }, i.status === "proposed" && i.can_approve ? [h("button", { class: "btn ok sm", onclick: () => act(i.id, "approve") }, "Approve & execute"), h("button", { class: "btn danger sm", onclick: () => act(i.id, "reject") }, "Reject")] : null,
          i.quote && i.can_approve && i.status !== "proposed" ? [h("button", { class: "btn ok sm", onclick: () => act(i.id, "approve") }, "Approve quote"), h("button", { class: "btn danger sm", onclick: () => act(i.id, "reject") }, "Reject")] : null,
          i.can_resolve ? [h("button", { class: "btn sm", onclick: () => act(i.id, "resolve") }, "Resolve"), (() => { const a = h("input", { class: "in", style: "width:170px", placeholder: "assign to email", value: i.assignee || "" }); return h("span", { style: "display:flex;gap:4px" }, a, h("button", { class: "btn sm", onclick: () => a.value && act(i.id, "assign", { assignee: a.value }) }, "Assign")) })()] : null,
          h("button", { class: "btn sm", onclick: () => { st.open.has(i.id) ? st.open.delete(i.id) : st.open.add(i.id); draw() } }, "Comments (" + i.comments.length + ")")),
        st.open.has(i.id) ? h("div", { class: "cm" }, ...i.comments.map(c => h("div", null, h("b", null, c.by), ` ${c.ts}: ${c.body}`)), (() => { const t = h("input", { class: "in", placeholder: "Write a comment and press Enter", onkeydown: e => { if (e.key === "Enter" && t.value.trim()) act(i.id, "comment", { body: t.value }) } }); return t })()) : null); return t
    })); if (!list.length) body.append(h("div", { class: "sub" }, "Nothing here."))
  };
  draw(); return { el, update: nb => { if (el.contains(document.activeElement) && document.activeElement.tagName === "INPUT") { cur = nb; return } if (JSON.stringify(nb.items) + st.f + [...st.open] === st.sig) return; cur = nb; draw() } }
};

// ---------------------------------------------------------------- Charts block
const FN = { size3: v => Math.max(8, Math.min(34, Math.sqrt(Math.abs(v[3] || 10)) * 1.6)), scatterTip: p => `<b>${esc(p.value[2] || "")}</b><br>${esc(p.seriesName || "")}<br>${p.value[0]}, ${p.value[1]}`, nodeTip: p => p.dataType === "node" ? `<b>${esc(p.name)}</b><br>${esc(p.data.tip || "")}` : "", nodeLabel: p => p.data.showLabel ? p.name : "" };
function revive(o) { if (Array.isArray(o)) return o.map(revive); if (o && typeof o === "object") { if (o.__fn) return FN[o.__fn]; const r = {}; for (const k in o) r[k] = revive(o[k]); return r } return o }
if(typeof echarts!=="undefined"&&echarts&&echarts.registerTheme)echarts.registerTheme("lt", { color: ["#5b5bd6", "#12a594", "#f5a524", "#8e4ec6", "#e5484d", "#30a46c", "#d6409f", "#3e63dd", "#8b8d98"], backgroundColor: "transparent", textStyle: { fontFamily: "Inter, system-ui, sans-serif", color: "#454a58" }, legend: { textStyle: { color: "#454a58" } }, categoryAxis: { axisLine: { lineStyle: { color: "#d9dce8" } }, axisTick: { show: false }, axisLabel: { color: "#6b7080" }, splitLine: { lineStyle: { color: "#eceef6" } } }, valueAxis: { axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: "#6b7080" }, splitLine: { lineStyle: { color: "#eceef6" } } }, tooltip: { backgroundColor: "#fff", borderColor: "#e6e8f0", textStyle: { color: "#1c2024" }, extraCssText: "box-shadow:0 8px 24px rgba(20,24,40,.12);border-radius:10px" } });
const CH = []; function lazy(box, fn) { let d = 0; const t = () => { if (d) return; if (box.isConnected && box.clientWidth > 0) { d = 1; fn() } else setTimeout(t, 60) }; t() }
R.chart = b => {
  const el = h("div"), box = h("div", { style: `height:${b.h || 290}px` }); el.append(h("h3", { style: "margin:0 0 4px;font-size:13.5px;display:" + (b.title ? "block" : "none") }, b.title || ""), box); let ch = null, cur = b;
  const init = () => {
    if(typeof echarts==="undefined"||!echarts||!echarts.init){box.innerHTML="<div style=\"padding:16px;color:#64748b;font-size:13px;\">Chart library loading...</div>";return;}ch = echarts.init(box, "lt", { renderer: "canvas" }); CH.push(ch); ch.setOption(revive(cur.opt), true);
    ch.on("click", p => { const o = cur.open; if (!o) return; let id = null; if (o.bar) id = p.name; else if (o.scatter) id = p.value && p.value[2]; else if (o.graph) id = p.data && p.data.open; else if (p.data && p.data.open) id = p.data.open; if (id) UI.openEntity(id) });
    if (cur.open) box.style.cursor = "pointer"
  };
  lazy(box, init);
  return { el, update: nb => { cur = nb; if (ch) { const r = JSON.stringify(nb.opt); if (box._h !== r) { box._h = r; ch.setOption(revive(nb.opt), { replaceMerge: ["series", "xAxis", "yAxis"] }) } } }, };
};
window.addEventListener("resize", () => CH.forEach(c => { try { c.resize() } catch (e) { } }));

// ---------------------------------------------------------------- Maps block
function shiftGeo(g, sh) { const mv = c => typeof c[0] === "number" ? [c[0] + sh, c[1]] : c.map(mv); return { type: "FeatureCollection", features: g.features.map(f => ({ type: "Feature", properties: f.properties, geometry: { type: f.geometry.type, coordinates: mv(f.geometry.coordinates) } })) } }
let WORLD = null; async function world() { if (WORLD) return WORLD; try { const t = await (await fetch("/static/vendor/world.topo.json")).json(); WORLD = topojson.feature(t, t.objects.countries) } catch (e) { WORLD = { type: "FeatureCollection", features: [] } } return WORLD }
R.map = b => {
  const el = h("div"), box = h("div", { class: "map", style: `height:${b.h || 470}px` }), lg = h("div", { class: "lg" }); el.append(box, lg); let M = null, grp = null, cur = b;
  const draw = () => {
    grp.clearLayers(); const SH = [-360, 0, 360]; cur.layers.forEach(L => {
      if (L.type === "lines") L.lines.forEach(l => { if (l.pts.length < 2) return; SH.forEach(sh => { const p = L2.polyline(l.pts.map(q => [q[0], q[1] + sh]), { color: l.color || "#5b5bd6", weight: l.w || 2, dashArray: l.dash || null, opacity: .9, lineJoin: "round", renderer: M._r }); if (l.tip) p.bindTooltip(l.tip, { sticky: true }); grp.addLayer(p) }) });
      else if (L.type === "circles") L.items.forEach(c => SH.forEach(sh => { const k = L2.circle([c.lat, c.lon + sh], { radius: c.r_m, color: c.color || "#e5484d", weight: 1, fillOpacity: .18, renderer: M._r }); if (c.tip) k.bindTooltip(c.tip); grp.addLayer(k) }));
      else if (L.type === "points") [...L.pts].sort((a, c) => (a.z || 0) - (c.z || 0)).forEach(p => SH.forEach(sh => { const m = L2.circleMarker([p.lat, p.lon + sh], { radius: p.r || 5, color: "#ffffff", weight: 1.2, fillColor: p.color || "#5b5bd6", fillOpacity: .95, renderer: M._r }); if (p.tip) m.bindTooltip(p.tip, { sticky: true }); const o = p.open || (cur.open ? p.id : null) || p.id; if (o) m.on("click", () => UI.openEntity(o)); grp.addLayer(m) }))
    });
    lg.replaceChildren(...(cur.legend || []).map(([t, c]) => h("span", null, h("i", { style: "background:" + c }), t)))
  };
  const L2 = typeof L !== "undefined" ? L : null; if (!L2) { box.innerHTML = "<div style=\"padding:16px;color:#64748b;font-size:13px;\">Map library loading...</div>"; return; } const go = async () => {
    M = L2.map(box, { zoomControl: true, worldCopyJump: true, attributionControl: false, minZoom: 1, preferCanvas: true }); M._r = L2.canvas({ padding: .5 }); const w = await world();[-360, 0, 360].forEach(sh => L2.geoJSON(sh ? shiftGeo(w, sh) : w, { renderer: M._r, style: { color: "#b9b2a0", weight: .8, fillColor: "#f3efe6", fillOpacity: 1 }, interactive: false }).addTo(M)); grp = L2.layerGroup().addTo(M);
    const v = cur.view || {}; if (v.bounds) M.fitBounds(v.bounds); else M.setView(v.center || [20, 0], v.zoom || 2); draw(); setTimeout(() => M.invalidateSize(), 50)
  };
  lazy(box, go);
  return { el, update: nb => { cur = nb; if (M && grp) draw() } }
};

// ---------------------------------------------------------------- Forms block
R.form = b => {
  const el = h("div");
  const res = h("div", { class: "res" });
  const f = h("form", { class: "f" + (b.inline ? " inline" : "") });
  let ins = {};

  b.fields.forEach(fl => {
    const w = h("div", { class: "fld" });
    if (fl.type !== "hidden") w.append(h("label", null, fl.label || fl.name));
    let i;
    if (fl.type === "select") i = h("select", { name: fl.name }, ...fl.options.map(o => h("option", { value: o, selected: String(o) === String(fl.value) }, o)));
    else if (fl.type === "multi") { i = h("select", { name: fl.name, multiple: true, size: 5 }, ...fl.options.map(o => h("option", { value: o, selected: (fl.value || []).includes(o) }, o))); }
    else if (fl.type === "checks") { i = h("div", { class: "chk" }, ...fl.options.map(o => h("label", null, h("input", { type: "checkbox", value: o, checked: (fl.value || []).includes(o) }), o))); i.get = () => [...i.querySelectorAll("input:checked")].map(x => x.value); }
    else if (fl.type === "textarea") i = h("textarea", { name: fl.name, placeholder: fl.placeholder || "" }, fl.value || "");
    else if (fl.type === "range") { const v = h("span", { style: "color:var(--pri);font-weight:700;margin-left:8px;" }, fl.value); i = h("input", { type: "range", name: fl.name, min: fl.min, max: fl.max, step: fl.step || 1, value: fl.value, oninput: e => v.textContent = e.target.value }); w.firstChild.append(" ", v); }
    else if (fl.type === "file") i = h("input", { type: "file", name: fl.name, accept: fl.accept || null });
    else if (fl.type === "hidden") { i = h("input", { type: "hidden", name: fl.name, value: fl.value }); w.style.display = "none"; }
    else i = h("input", { type: fl.type === "number" ? "number" : fl.type === "date" ? "date" : fl.type === "password" ? "password" : "text", name: fl.name, value: fl.value == null ? "" : fl.value, min: fl.min, max: fl.max, step: fl.step || (fl.type === "number" ? "any" : null), placeholder: fl.placeholder || "" });
    i.fl = fl;
    ins[fl.name] = i;
    w.append(i);
    f.append(w);
  });

  const btn = h("button", { class: "btn " + (b.tone || "primary"), type: "submit" }, b.submit || "Submit");
  f.append(h("div", { class: "fld" }, btn));

  f.addEventListener("submit", async e => {
    e.preventDefault();
    const v = {};
    let fd = null;
    for (const n in ins) {
      const i = ins[n], fl = i.fl;
      if (fl.type === "file") { if (i.files[0]) { fd = fd || new FormData(); fd.append(n, i.files[0]); } }
      else if (fl.type === "checks") v[n] = i.get();
      else if (fl.type === "multi") v[n] = [...i.selectedOptions].map(o => o.value);
      else if (fl.type === "number" || fl.type === "range") v[n] = i.value === "" ? null : +i.value;
      else v[n] = i.value;
    }
    if (b.url.startsWith("get:")) {
      const q = new URLSearchParams();
      for (const n in v) if (v[n] !== "" && v[n] != null) q.set(n, v[n]);
      window.open(b.url.slice(4) + "?" + q, "_blank");
      return;
    }
    if (b.url.startsWith("page:")) {
      const parts = b.url.split(":");
      const pid = parts[1];
      const tab = parts[2] || S.tab;
      UI.go(pid, tab, v);
      return;
    }
    btn.disabled = true;
    const t0 = btn.textContent;
    btn.textContent = "Processing…";
    let r;
    if (fd) {
      for (const n in v) fd.append(n, Array.isArray(v[n]) ? v[n].join(",") : v[n]);
      r = await api(b.url, { method: "POST", body: fd });
    } else {
      r = await api(b.url, { json: v });
    }
    btn.disabled = false;
    btn.textContent = t0;
    toast(r.msg || (r.ok ? "Done" : "Failed"), !r.ok);
    res.replaceChildren();
    if (r.blocks) mountList(res, r.blocks, "res");
    if (r.refresh) reloadPage(true);
  });

  if (b.title || b.sub) {
    const c = h("div", { class: "card" }, b.title ? h("h3", null, b.title) : null, b.sub ? h("div", { class: "sub", style: "color:var(--mut);font-size:12.5px;margin-bottom:14px;" }, b.sub) : null, f, res);
    el.append(c);
  } else {
    el.append(f, res);
  }
  return { el, update() {} };
};

// ---------------------------------------------------------------- Blocks: AI Copilot Chat
async function sse(url, json, on) {
  const token = localStorage.getItem("fq_token");
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = "Bearer " + token;
  const r = await fetch(url, { method: "POST", credentials: "same-origin", headers, body: JSON.stringify(json) });
  if (!r.ok) {
    on({ ev: "final", text: "Error " + r.status + " connecting to database." });
    return;
  }
  const rd = r.body.getReader(), dec = new TextDecoder();
  let buf = "";
  for (; ;) {
    const { value, done } = await rd.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const m = buf.slice(0, i);
      buf = buf.slice(i + 2);
      if (m.startsWith("data: ")) {
        try { on(JSON.parse(m.slice(6))); } catch (e) {}
      }
    }
  }
}

R.chat = b => {
  let cid = null, hist = [];
  const el = h("div", { class: "card chat" });
  const msgs = h("div", { class: "msgs" });
  const inp = h("input", {
    placeholder: "Ask about routes, quotes, carriers, weather or customs in plain English…",
    onkeydown: e => { if (e.key === "Enter") send(inp.value); }
  });
  const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
  const voiceStatus = h("small", { class: "fq-voice-status", role: "status", "aria-live": "polite" }, "You can type a question or use the microphone.");
  let recognition = null;
  let listening = false;
  const micBtn = h("button", {
    type: "button", class: "btn fq-mic-button",
    title: "Speak your Copilot question", "aria-label": "Speak your Copilot question",
    onclick: () => {
      if (!SpeechRecognitionClass) {
        voiceStatus.textContent = "Voice input is not supported here. Try Chrome or Edge, or type your question.";
        return;
      }
      if (!window.isSecureContext) {
        voiceStatus.textContent = "Voice input needs HTTPS or localhost.";
        return;
      }
      if (listening && recognition) { recognition.stop(); return; }
      try {
        recognition = new SpeechRecognitionClass();
        recognition.lang = navigator.language || "en-US";
        recognition.interimResults = true;
        recognition.continuous = false;
        recognition.maxAlternatives = 1;
        let finalText = "";
        recognition.onstart = () => {
          listening = true; micBtn.textContent = "Stop";
          micBtn.setAttribute("aria-pressed", "true");
          voiceStatus.textContent = "Listening… speak your freight question.";
        };
        recognition.onresult = event => {
          let interim = "";
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const part = event.results[i][0].transcript;
            if (event.results[i].isFinal) finalText += part + " ";
            else interim += part;
          }
          inp.value = (finalText + interim).trim();
          if (finalText.trim()) voiceStatus.textContent = "Question captured. Review it, then press Ask Copilot.";
        };
        recognition.onerror = event => {
          const reason = event.error === "not-allowed" || event.error === "service-not-allowed"
            ? "Microphone access was denied. Allow microphone access in your browser."
            : event.error === "no-speech" ? "No speech detected. Try again."
            : "Voice recognition unavailable. You can type instead.";
          voiceStatus.textContent = reason;
        };
        recognition.onend = () => {
          listening = false; micBtn.textContent = "🎤 Speak";
          micBtn.setAttribute("aria-pressed", "false");
          if (voiceStatus.textContent.startsWith("Listening"))
            voiceStatus.textContent = inp.value.trim() ? "Question captured. Press Ask Copilot." : "Press Speak to try again.";
        };
        recognition.start();
      } catch (err) {
        listening = false; micBtn.textContent = "🎤 Speak";
        voiceStatus.textContent = "Microphone could not start. Check browser permissions or type your question.";
      }
    }
  }, "🎤 Speak");
  if (!SpeechRecognitionClass) micBtn.title = "Voice dictation requires a browser with SpeechRecognition support";
  const attachReadButton = (parent, content) => {
    if (!("speechSynthesis" in window)) return;
    parent.append(h("button", { class: "btn fq-voice-read", type: "button", "aria-label": "Read Copilot answer aloud", onclick: () => {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(String(content || "").slice(0, 2500));
      utterance.lang = navigator.language || "en-US";
      window.speechSynthesis.speak(utterance);
    } }, "🔊 Read answer"));
  };

  const examples = b.examples || [
    "Which carrier is cheapest to Rotterdam?",
    "How many shipments are on customs hold?",
    "Show quotes below 10% margin",
    "Which ports are most congested?",
    "Show storms near the Red Sea"
  ];
  const chips = h("div", { class: "chat-suggestions" },
    ...examples.map(ex => h("span", {
      class: "chat-chip",
      onclick: () => send(ex)
    }, ex))
  );

  const showMsg = m => {
    if (m.role === "user") {
      msgs.append(h("div", { class: "m u" }, m.text));
    } else {
      const o = h("div", { class: "md" });
      o.innerHTML = md(m.text);
      const a = h("div", { class: "m a" }, o);
      if (m.sql) {
        a.append(h("details", { class: "cites" },
          h("summary", null, `Show exact SQL query (${m.rows !== undefined ? m.rows : 0} rows)`),
          h("pre", null, m.sql)
        ));
      }
      attachReadButton(a, m.text);
      msgs.append(a);
    }
    msgs.scrollTop = msgs.scrollHeight;
  };

  const send = async q => {
    q = q.trim();
    if (!q) return;
    inp.value = "";
    hist.push({ role: "user", text: q });
    showMsg({ role: "user", text: q });

    const a = h("div", { class: "m a" });
    const loadingText = h("div", { style: "color:var(--mut);display:flex;align-items:center;gap:8px;" },
      h("div", { class: "spin", style: "width:16px;height:16px;border-width:2px;margin:0;" }),
      "Querying database…"
    );
    a.append(loadingText);
    msgs.append(a);
    msgs.scrollTop = msgs.scrollHeight;

    let received = false;
    await sse("/api/copilot", { q }, ev => {
      if (ev.ev === "final") {
        received = true;
        a.replaceChildren();
        const o = h("div", { class: "md" });
        o.innerHTML = md(ev.text);
        a.append(o);
        if (ev.sql) {
          a.append(h("details", { class: "cites" },
            h("summary", null, `Show exact SQL query (${ev.rows !== undefined ? ev.rows : 0} rows)`),
            h("pre", null, ev.sql)
          ));
        }
        attachReadButton(a, ev.text);
        hist.push({ role: "assistant", text: ev.text, sql: ev.sql, rows: ev.rows });
        msgs.scrollTop = msgs.scrollHeight;
      }
    });
    if (!received) {
      loadingText.textContent = "No response received.";
    }
  };

  const inputBar = h("div", { class: "cin" },
    inp,
    micBtn,
    h("button", { class: "btn primary", onclick: () => send(inp.value) }, "Ask Copilot")
  );

  el.append(chips, msgs, inputBar, voiceStatus);
  return { el, update() {} };
};

// ---------------------------------------------------------------- Admin Dashboard Block
R.admin_page = b => {
  const el = h("div", { class: "admin-container" });
  const metrics = b.metrics || { total_users: 0, locked_users: 0, roles: {} };
  const currentAdmin = b.current_admin || (S.me ? S.me.user.username : "");

  const rolesSummary = Object.entries(metrics.roles || {}).map(([r, c]) => `${r}: ${c}`).join(" · ");

  // 1. KPI Cards
  const kpiGrid = h("div", { class: "admin-kpi-grid" },
    h("div", { class: "admin-kpi-card" },
      h("span", { class: "admin-kpi-title" }, "Total Platform Accounts"),
      h("span", { class: "admin-kpi-val" }, String(metrics.total_users || 0)),
      h("span", { class: "admin-kpi-sub" }, rolesSummary || "All registered users")
    ),
    h("div", { class: "admin-kpi-card" },
      h("span", { class: "admin-kpi-title" }, "Active Accounts"),
      h("span", { class: "admin-kpi-val", style: "color:var(--green);" }, String((metrics.total_users || 0) - (metrics.locked_users || 0))),
      h("span", { class: "admin-kpi-sub" }, "Sign-in enabled")
    ),
    h("div", { class: "admin-kpi-card" },
      h("span", { class: "admin-kpi-title" }, "Locked Accounts"),
      h("span", { class: "admin-kpi-val", style: "color:" + ((metrics.locked_users || 0) > 0 ? "var(--red)" : "var(--mut)") + ";" }, String(metrics.locked_users || 0)),
      h("span", { class: "admin-kpi-sub" }, "Access suspended")
    )
  );

  // 2. Add User Form
  const addAlert = h("div", { class: "fq-alert", style: "display:none;" });
  const newU = h("input", { class: "in", placeholder: "e.g. operations_lead", required: true });
  const newE = h("input", { class: "in", placeholder: "e.g. user@freight.ai", type: "email", required: true });
  const newP = h("input", { class: "in", placeholder: "Temporary strong password", type: "password", required: true });
  let showPw = false;
  const pwToggle = h("button", {
    type: "button", class: "fq-pw-toggle", onclick: () => {
      showPw = !showPw;
      newP.type = showPw ? "text" : "password";
      pwToggle.textContent = showPw ? "Hide" : "Show";
    }
  }, "Show");

  const newR = h("select", { class: "in" },
    h("option", { value: "Customer" }, "Customer"),
    h("option", { value: "Freight Broker" }, "Freight Broker"),
    h("option", { value: "Operations Manager" }, "Operations Manager"),
    h("option", { value: "Auditor" }, "Auditor"),
    h("option", { value: "Admin" }, "Admin")
  );
  const newC = h("input", { class: "in", placeholder: "Optional (e.g. CUST-002)" });
  const addBtn = h("button", { class: "btn primary", type: "submit" }, "Create User Account");

  const addForm = h("form", {
    onsubmit: async e => {
      e.preventDefault();
      addAlert.style.display = "none";
      addBtn.disabled = true;
      addBtn.textContent = "Creating account…";

      const r = await api("/api/admin/users/create", {
        json: {
          username: newU.value.trim(),
          email: newE.value.trim(),
          password: newP.value,
          role: newR.value,
          customer_id: newC.value.trim() || null
        }
      });
      addBtn.disabled = false;
      addBtn.textContent = "Create User Account";

      if (r.ok) {
        toast(r.msg || "User created successfully.", false);
        loadPage(false);
      } else {
        addAlert.className = "fq-alert fq-alert-error";
        addAlert.textContent = r.msg || "Failed to create user.";
        addAlert.style.display = "block";
      }
    }
  },
    h("div", { style: "display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:16px;margin-bottom:16px;" },
      h("div", { class: "fld" }, h("label", null, "Username"), newU),
      h("div", { class: "fld" }, h("label", null, "Email Address"), newE),
      h("div", { class: "fld" }, h("label", null, "RBAC Role"), newR),
      h("div", { class: "fld" }, h("label", null, "Customer ID (Optional)"), newC),
      h("div", { class: "fld", style: "grid-column: 1 / -1;" },
        h("label", null, "Temporary Password"),
        h("div", { class: "profile-input-wrap" }, newP, pwToggle),
        h("small", { style: "color:var(--mut);font-size:11.5px;margin-top:4px;" }, "Requires 8+ characters, uppercase, lowercase, digit, and special symbol.")
      )
    ),
    addAlert,
    addBtn
  );

  const addSection = h("div", { class: "admin-section" },
    h("div", { class: "admin-section-header" },
      h("h3", { class: "admin-section-title" }, "Provision New User Account"),
      h("div", { class: "admin-section-sub" }, "Create platform credentials and assign authorization role.")
    ),
    addForm
  );

  // 2b. Link Customer Account (map a public signup to an existing freight customer profile)
  const linkUsers = (b.users || []).filter(u => u.role === "Customer" && !u.customer_id);
  const linkCusts = b.customers || [];
  const linkAlert = h("div", { class: "fq-alert", style: "display:none;" });
  const linkU = h("select", { class: "in" },
    ...linkUsers.map(u => h("option", { value: String(u.id) }, `${u.username} - ${u.email}`)));
  const linkC = h("select", { class: "in" },
    ...linkCusts.map(c => h("option", { value: c.customer_id }, `${c.customer_id} - ${c.name || ""}`)));
  const linkBtn = h("button", { class: "btn primary", type: "submit" }, "Link Account");
  const linkForm = h("form", {
    onsubmit: async e => {
      e.preventDefault();
      linkAlert.style.display = "none";
      linkBtn.disabled = true;
      linkBtn.textContent = "Linking account…";
      const r = await api("/api/admin/link_customer", { json: { user_id: linkU.value, customer_id: linkC.value } });
      linkBtn.disabled = false;
      linkBtn.textContent = "Link Account";
      if (r.ok) {
        toast(r.msg || "Account linked.", false);
        loadPage(false);
      } else {
        linkAlert.className = "fq-alert fq-alert-error";
        linkAlert.textContent = r.msg || "Failed to link account.";
        linkAlert.style.display = "block";
      }
    }
  },
    h("div", { style: "display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:16px;margin-bottom:16px;" },
      h("div", { class: "fld" }, h("label", null, "Pending Customer Account"), linkU),
      h("div", { class: "fld" }, h("label", null, "Corporate Freight Profile"), linkC)
    ),
    linkAlert,
    linkBtn
  );
  const linkSection = h("div", { class: "admin-section" },
    h("div", { class: "admin-section-header" },
      h("h3", { class: "admin-section-title" }, "Link Customer Account"),
      h("div", { class: "admin-section-sub" }, "Connect a signed-up user to their freight data.")
    ),
    (linkUsers.length && linkCusts.length)
      ? linkForm
      : h("div", { style: "color:var(--mut);font-size:13px;" }, "No unlinked customer accounts are waiting to be linked.")
  );

  // 3. User Table Section
  const modalContainer = h("div", null);
  const usersRows = (b.users || []).map(u => {
    const isSelf = u.username === currentAdmin;

    const roleSelect = h("select", {
      class: "admin-select",
      onchange: async e => {
        const nextRole = e.target.value;
        const res = await api("/api/admin/users/role", { json: { target_id: u.id, role: nextRole } });
        if (res.ok) {
          toast(res.msg || "Role updated.", false);
          loadPage(false);
        } else {
          toast(res.msg || "Failed to update role.", true);
          e.target.value = u.role;
        }
      }
    },
      h("option", { value: "Customer", selected: u.role === "Customer" }, "Customer"),
      h("option", { value: "Freight Broker", selected: u.role === "Freight Broker" }, "Freight Broker"),
      h("option", { value: "Operations Manager", selected: u.role === "Operations Manager" }, "Operations Manager"),
      h("option", { value: "Auditor", selected: u.role === "Auditor" }, "Auditor"),
      h("option", { value: "Admin", selected: u.role === "Admin" }, "Admin")
    );

    const lockBtn = h("button", {
      class: "admin-btn-action " + (u.locked ? "admin-btn-unlock" : "admin-btn-lock"),
      disabled: isSelf,
      onclick: async () => {
        const actionUrl = u.locked ? "/api/admin/users/unlock" : "/api/admin/users/lock";
        const res = await api(actionUrl, { json: { target_id: u.id } });
        if (res.ok) {
          toast(res.msg || "Status updated.", false);
          loadPage(false);
        } else {
          toast(res.msg || "Failed to change lock status.", true);
        }
      }
    }, u.locked ? "Unlock" : "Lock");

    const deleteBtn = h("button", {
      class: "admin-btn-action admin-btn-delete",
      disabled: isSelf,
      onclick: () => {
        const modal = h("div", { class: "admin-modal-overlay", onclick: e => { if (e.target === modal) modal.remove(); } },
          h("div", { class: "admin-modal-card" },
            h("h3", { class: "admin-modal-title" }, "Confirm Permanent Deletion"),
            h("p", { class: "admin-modal-desc" }, `Permanently delete account ${u.username} (${u.email})? This action cannot be undone.`),
            h("div", { class: "admin-modal-acts" },
              h("button", { class: "btn ghost sm", onclick: () => modal.remove() }, "Cancel"),
              h("button", {
                class: "btn danger sm",
                onclick: async () => {
                  modal.remove();
                  const res = await api("/api/admin/users/delete", { json: { target_id: u.id } });
                  if (res.ok) {
                    toast(res.msg || "User deleted.", false);
                    loadPage(false);
                  } else {
                    toast(res.msg || "Failed to delete user.", true);
                  }
                }
              }, "Confirm Delete")
            )
          )
        );
        modalContainer.replaceChildren(modal);
      }
    }, "Delete");

    const rolePill = h("span", { class: "pill " + (u.role === "Admin" ? "Info" : u.role === "Operations Manager" ? "Low" : u.role === "Freight Broker" ? "Approved" : u.role === "Auditor" ? "proposed" : "Warning") }, u.role);
    const statusPill = h("span", { class: "pill " + (u.locked ? "Critical" : "Approved") }, u.locked ? "Locked" : "Active");

    return h("tr", null,
      h("td", { style: "font-weight:700;" }, u.username, isSelf ? h("span", { style: "margin-left:6px;font-size:11px;color:var(--mut);" }, "(You)") : null),
      h("td", null, u.email),
      h("td", null, rolePill),
      h("td", null, statusPill),
      h("td", { style: "color:var(--mut);" }, u.customer_id || "—"),
      h("td", { style: "color:var(--mut);font-size:12px;" }, u.created_at ? u.created_at.slice(0, 16) : "—"),
      h("td", { style: "color:var(--mut);font-size:12px;" }, u.last_login ? u.last_login.slice(0, 16) : "Never"),
      h("td", null, h("div", { class: "admin-actions-cell" }, roleSelect, lockBtn, deleteBtn))
    );
  });

  const usersTable = h("div", { class: "admin-table-wrap" },
    h("table", { class: "admin-table" },
      h("thead", null,
        h("tr", null,
          h("th", null, "Username"),
          h("th", null, "Email"),
          h("th", null, "Role"),
          h("th", null, "Status"),
          h("th", null, "Customer ID"),
          h("th", null, "Joined Date"),
          h("th", null, "Last Login"),
          h("th", null, "Actions")
        )
      ),
      h("tbody", null, ...usersRows)
    )
  );

  const usersSection = h("div", { class: "admin-section" },
    h("div", { class: "admin-section-header" },
      h("h3", { class: "admin-section-title" }, "Platform Accounts & Access Control"),
      h("div", { class: "admin-section-sub" }, "Manage roles, lock accounts, or remove users. Self-protection and last-admin rules enforced.")
    ),
    usersTable
  );

  // 4. Activity Log Table
  const actRows = (b.activity || []).map(a => h("tr", null,
    h("td", { style: "font-family:monospace;font-size:12px;color:var(--mut);" }, a.timestamp ? a.timestamp.slice(0, 19).replace("T", " ") : "—"),
    h("td", { style: "font-weight:600;" }, a.actor),
    h("td", null, h("span", { class: "pill Info", style: "font-family:monospace;font-size:11px;" }, a.action)),
    h("td", null, a.details)
  ));

  const activitySection = h("div", { class: "admin-section" },
    h("div", { class: "admin-section-header" },
      h("h3", { class: "admin-section-title" }, "Admin Activity Audit Log (Latest 50 Events)"),
      h("div", { class: "admin-section-sub" }, "Immutable record of user creations, promotions, demotions, locks, and removals.")
    ),
    h("div", { class: "admin-table-wrap" },
      h("table", { class: "admin-table" },
        h("thead", null,
          h("tr", null,
            h("th", null, "Timestamp (UTC)"),
            h("th", null, "Admin Actor"),
            h("th", null, "Action"),
            h("th", null, "Details")
          )
        ),
        h("tbody", null, ...actRows)
      )
    )
  );

  // 5. RBAC Permission Matrix Reference
  const permMatrixSection = h("div", { class: "admin-section" },
    h("div", { class: "admin-section-header" },
      h("h3", { class: "admin-section-title" }, "Role-Based Access Control (RBAC) Privilege Matrix"),
      h("div", { class: "admin-section-sub" }, "Module authorization mapping across platform roles.")
    ),
    h("div", { class: "admin-table-wrap" },
      h("table", { class: "admin-table", style: "text-align:center;" },
        h("thead", null,
          h("tr", null,
            h("th", { style: "text-align:left;" }, "Role"),
            h("th", null, "Copilot"),
            h("th", null, "Route AI"),
            h("th", null, "Spot Quotes"),
            h("th", null, "Carriers"),
            h("th", null, "Weather"),
            h("th", null, "Margin"),
            h("th", null, "Customs"),
            h("th", null, "Run Agents"),
            h("th", null, "Manage Users")
          )
        ),
        h("tbody", null,
          h("tr", null, h("td", { style: "text-align:left;font-weight:700;" }, "Admin"), h("td", null, "✓"), h("td", null, "✓"), h("td", null, "✓"), h("td", null, "✓"), h("td", null, "✓"), h("td", null, "✓"), h("td", null, "✓"), h("td", null, "✓"), h("td", null, "✓")),
          h("tr", null, h("td", { style: "text-align:left;font-weight:700;" }, "Operations Manager"), h("td", null, "✓"), h("td", null, "✓"), h("td", { style: "color:var(--mut);" }, "✗"), h("td", null, "✓"), h("td", null, "✓"), h("td", { style: "color:var(--mut);" }, "✗"), h("td", null, "✓"), h("td", null, "✓"), h("td", { style: "color:var(--mut);" }, "✗")),
          h("tr", null, h("td", { style: "text-align:left;font-weight:700;" }, "Freight Broker"), h("td", null, "✓"), h("td", { style: "color:var(--mut);" }, "✗"), h("td", null, "✓"), h("td", null, "✓"), h("td", { style: "color:var(--mut);" }, "✗"), h("td", null, "✓"), h("td", { style: "color:var(--mut);" }, "✗"), h("td", { style: "color:var(--mut);" }, "✗"), h("td", { style: "color:var(--mut);" }, "✗")),
          h("tr", null, h("td", { style: "text-align:left;font-weight:700;" }, "Auditor (Read-Only)"), h("td", null, "✓"), h("td", null, "✓"), h("td", null, "✓"), h("td", null, "✓"), h("td", null, "✓"), h("td", null, "✓"), h("td", null, "✓"), h("td", { style: "color:var(--mut);" }, "✗"), h("td", { style: "color:var(--mut);" }, "✗")),
          h("tr", null, h("td", { style: "text-align:left;font-weight:700;" }, "Customer (Scoped)"), h("td", null, "✓"), h("td", { style: "color:var(--mut);" }, "✗"), h("td", null, "✓ (Own)"), h("td", { style: "color:var(--mut);" }, "✗"), h("td", { style: "color:var(--mut);" }, "✗"), h("td", { style: "color:var(--mut);" }, "✗"), h("td", { style: "color:var(--mut);" }, "✗"), h("td", { style: "color:var(--mut);" }, "✗"), h("td", { style: "color:var(--mut);" }, "✗"))
        )
      )
    )
  );

  el.append(kpiGrid, addSection, linkSection, usersSection, activitySection, permMatrixSection, modalContainer);
  return { el, update() {} };
};

// ---------------------------------------------------------------- Profile Page Block
R.profile_page = b => {
  const u = b.user || (S.me ? S.me.user : {});
  const el = h("div", { class: "profile-container" });

  const initial = (u.username || "U")[0].toUpperCase();
  const roleColor = u.role === "Admin" ? "var(--blue)" : u.role === "Operations Manager" ? "var(--teal)" : u.role === "Freight Broker" ? "var(--green)" : u.role === "Auditor" ? "var(--violet)" : "var(--amber)";

  const avatarEl = h("div", { class: "profile-avatar", style: "background:linear-gradient(135deg, " + roleColor + ", var(--pri));box-shadow:0 6px 18px rgba(2,132,199,0.3);" }, initial);
  const titleEl = h("h2", null, u.username);
  const emailEl = h("p", null, u.email);
  const badgeEl = h("span", { class: "profile-role-badge", style: "background:rgba(2,132,199,0.12);color:" + roleColor + ";border-color:currentColor;" }, u.role);

  const headerCard = h("div", { class: "profile-header-card" },
    h("div", { class: "profile-header-top" },
      avatarEl,
      h("div", { class: "profile-info" }, titleEl, emailEl, badgeEl)
    ),
    h("div", { class: "profile-meta-grid" },
      h("div", { class: "profile-meta-item" }, h("span", { class: "profile-meta-label" }, "Account Role"), h("span", { class: "profile-meta-val" }, u.role)),
      h("div", { class: "profile-meta-item" }, h("span", { class: "profile-meta-label" }, "Customer Identifier"), h("span", { class: "profile-meta-val" }, u.customer_id || "None (Internal User)")),
      h("div", { class: "profile-meta-item" }, h("span", { class: "profile-meta-label" }, "Joined Date"), h("span", { class: "profile-meta-val" }, u.created_at ? u.created_at.slice(0, 10) : "—")),
      h("div", { class: "profile-meta-item" }, h("span", { class: "profile-meta-label" }, "Last Active Session"), h("span", { class: "profile-meta-val" }, u.last_login ? u.last_login.slice(0, 16).replace("T", " ") : "Active now"))
    )
  );

  // Form 1: Username Update
  const unAlert = h("div", { class: "fq-alert", style: "display:none;" });
  const newUsernameInput = h("input", { class: "in", type: "text", value: u.username, required: true });
  const unPwInput = h("input", { class: "in", type: "password", placeholder: "Enter current password to verify", required: true });
  let showUnPw = false;
  const unPwToggle = h("button", {
    type: "button", class: "fq-pw-toggle", onclick: () => {
      showUnPw = !showUnPw;
      unPwInput.type = showUnPw ? "text" : "password";
      unPwToggle.textContent = showUnPw ? "Hide" : "Show";
    }
  }, "Show");
  const unBtn = h("button", { class: "btn primary", type: "submit" }, "Update Username");

  const unForm = h("form", {
    onsubmit: async e => {
      e.preventDefault();
      unAlert.style.display = "none";
      unBtn.disabled = true;
      unBtn.textContent = "Updating…";

      const r = await api("/api/profile/username", {
        json: {
          new_username: newUsernameInput.value.trim(),
          current_password: unPwInput.value
        }
      });
      unBtn.disabled = false;
      unBtn.textContent = "Update Username";

      if (r.ok && r.token) {
        localStorage.setItem("fq_token", r.token);
        S.me.user.username = r.user.username;
        titleEl.textContent = r.user.username;
        avatarEl.textContent = r.user.username[0].toUpperCase();
        renderNav();
        toast("Username updated successfully!", false);
        unAlert.className = "fq-alert fq-alert-success";
        unAlert.textContent = r.msg || "Username updated successfully.";
        unAlert.style.display = "block";
        unPwInput.value = "";
      } else {
        unAlert.className = "fq-alert fq-alert-error";
        unAlert.textContent = r.msg || "Could not update username.";
        unAlert.style.display = "block";
      }
    }
  },
    h("div", { class: "card" },
      h("h3", null, "Change Username"),
      h("div", { style: "display:grid;gap:14px;max-width:440px;" },
        h("div", { class: "fld" }, h("label", null, "New Username"), newUsernameInput),
        h("div", { class: "fld" }, h("label", null, "Current Password"), h("div", { class: "profile-input-wrap" }, unPwInput, unPwToggle)),
        unAlert,
        unBtn
      )
    )
  );

  // Form 2: Password Update
  const pwAlert = h("div", { class: "fq-alert", style: "display:none;" });
  const curPwInput = h("input", { class: "in", type: "password", placeholder: "Current password", required: true });
  const newPwInput = h("input", { class: "in", type: "password", placeholder: "New strong password", required: true });
  const confPwInput = h("input", { class: "in", type: "password", placeholder: "Confirm new password", required: true });
  let showCur = false, showNew = false;
  const curToggle = h("button", { type: "button", class: "fq-pw-toggle", onclick: () => { showCur = !showCur; curPwInput.type = showCur ? "text" : "password"; curToggle.textContent = showCur ? "Hide" : "Show"; } }, "Show");
  const newToggle = h("button", { type: "button", class: "fq-pw-toggle", onclick: () => { showNew = !showNew; newPwInput.type = showNew ? "text" : "password"; newToggle.textContent = showNew ? "Hide" : "Show"; } }, "Show");
  const pwBtn = h("button", { class: "btn primary", type: "submit" }, "Update Password");

  const pwForm = h("form", {
    onsubmit: async e => {
      e.preventDefault();
      pwAlert.style.display = "none";
      pwBtn.disabled = true;
      pwBtn.textContent = "Updating password…";

      const r = await api("/api/profile/password", {
        json: {
          current_password: curPwInput.value,
          new_password: newPwInput.value,
          confirm_password: confPwInput.value
        }
      });
      pwBtn.disabled = false;
      pwBtn.textContent = "Update Password";

      if (r.ok) {
        toast("Password changed successfully!", false);
        pwAlert.className = "fq-alert fq-alert-success";
        pwAlert.textContent = r.msg || "Password updated successfully.";
        pwAlert.style.display = "block";
        curPwInput.value = "";
        newPwInput.value = "";
        confPwInput.value = "";
      } else {
        pwAlert.className = "fq-alert fq-alert-error";
        pwAlert.textContent = r.msg || "Failed to update password.";
        pwAlert.style.display = "block";
      }
    }
  },
    h("div", { class: "card" },
      h("h3", null, "Security Credentials"),
      h("div", { style: "display:grid;gap:14px;max-width:440px;" },
        h("div", { class: "fld" }, h("label", null, "Current Password"), h("div", { class: "profile-input-wrap" }, curPwInput, curToggle)),
        h("div", { class: "fld" }, h("label", null, "New Password"), h("div", { class: "profile-input-wrap" }, newPwInput, newToggle)),
        h("div", { class: "fld" }, h("label", null, "Confirm New Password"), confPwInput),
        h("small", { style: "color:var(--mut);font-size:11.5px;" }, "Requires 8+ characters, uppercase, lowercase, digit, and special symbol."),
        pwAlert,
        pwBtn
      )
    )
  );

  el.append(headerCard, unForm, pwForm);
  return { el, update() {} };
};

// ---------------------------------------------------------------- Navigation & Command Shell
const GROUPS = [
  ["Assistant", ["copilot"]],
  ["Operations", ["route", "quotes", "carriers", "weather", "margin", "customs"]],
  ["Account", ["profile", "admin"]]
];

function renderNav() {
  const nav = $("#nav");
  if (!nav || !S.me) return;
  const items = [];
  const used = new Set();
  const mk = m => h("div", {
    class: "nav" + (m.id === S.page ? " on" : ""),
    "data-id": m.id,
    onclick: () => UI.go(m.id)
  },
    icon(m.icon || "bot"),
    h("span", null, m.label.replace(/^Agent \d+ · /, "")),
    h("em", { class: "bd", style: "display:none" })
  );

  GROUPS.forEach(([g, ids]) => {
    const ms = (S.me.menu || []).filter(m => ids.includes(m.id));
    if (!ms.length) return;
    items.push(h("div", { class: "ngrp" }, g));
    ms.forEach(m => { used.add(m.id); items.push(mk(m)); });
  });
  (S.me.menu || []).filter(m => !used.has(m.id)).forEach(m => items.push(mk(m)));
  nav.replaceChildren(...items);
  updBadges();
}

function updBadges() {
  const p = S.pulse;
  if (!p) return;
  const hl = $("#hl");
  if (hl) {
    const state = p.worker_alive ? (p.health == null ? "Checking health" : `Health ${Math.round(p.health)}%`) : "Starting";
    hl.innerHTML = `<span class="live-dot"></span>Fleet engine · ${state}`;
  }
}

function openStream() {
  if (S.es) S.es.close();
  let active = true;
  const update = async () => {
    if (!active || !S.me) return;
    try {
      const p = await api("/api/pulse");
      if (!active || !p || p.ok === false || p.stage === undefined) return;
      const prev = S.pulse;
      S.pulse = p;
      updBadges();
      if (prev && p.dec !== prev.dec && S.live) loadPage(true);
    } catch (e) {}
  };
  const timer = setInterval(update, 8000);
  S.es = { close() { active = false; clearInterval(timer); } };
  update();
}

// ---------------------------------------------------------------- UI Global Methods
const UI = {};

UI.openEntity = async id => {
  if (!id) return;
  $("#dt").textContent = id;
  $("#db").replaceChildren(h("div", { class: "boot", style: "min-height:200px;display:flex;align-items:center;justify-content:center;gap:10px;" }, h("div", { class: "spin" }), "Loading details…"));
  $("#drawer").classList.add("on");
  const b = $("#drawer-backdrop");
  if (b) b.classList.add("on");

  const d = await api("/api/detail/" + encodeURIComponent(id));
  if (d.title === undefined) {
    $("#db").replaceChildren(h("div", { class: "callout warn" }, d.msg || "Details not accessible for this account role."));
    return;
  }
  $("#dt").textContent = d.title || id;
  $("#db").replaceChildren();
  mountList($("#db"), d.blocks || [], "d");
};

UI.closeDrawer = () => {
  const d = $("#drawer");
  const b = $("#drawer-backdrop");
  if (d) d.classList.remove("on");
  if (b) b.classList.remove("on");
};

UI.go = (id, tab, params) => {
  S.page = id;
  S.tab = tab || null;
  S.params = params || {};
  window.location.hash = "#/app/" + id + (tab ? ":" + tab : "");
  UI.closeDrawer();
  renderNav();
  loadPage(false);
};

UI.palette = () => {
  if ($(".kpal")) return;
  let sel = 0, rows = [];
  const inp = h("input", { placeholder: "Jump to module, entity (e.g. QTE-001, SHP-…), or question…" });
  const lst = h("div", { class: "lst" });
  const ov = h("div", { class: "kpal", onclick: e => { if (e.target === ov) close(); } }, h("div", null, inp, lst));

  const close = () => { ov.remove(); document.removeEventListener("keydown", kd, true); };
  const build = () => {
    const q = inp.value.trim(), ql = q.toLowerCase();
    rows = [];
    (S.me ? S.me.menu : []).filter(m => !ql || m.label.toLowerCase().includes(ql) || m.id.includes(ql)).forEach(m => {
      rows.push({ g: "Modules", t: m.label.replace(/^Agent \d+ · /, ""), s: "navigate", f: () => UI.go(m.id) });
    });
    if (/^[A-Za-z]{2,5}-?[A-Za-z]?\d+$/.test(q)) {
      rows.unshift({ g: "Entity", t: q.toUpperCase(), s: "inspect", f: () => UI.openEntity(q.toUpperCase()) });
    }
    if (q.length > 2) {
      rows.push({
        g: "Copilot", t: "Ask Copilot: " + q, s: "query", f: () => {
          UI.go("copilot");
          setTimeout(() => {
            const i = document.querySelector(".cin input");
            if (i) { i.value = q; i.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" })); }
          }, 500);
        }
      });
    }
    if (sel >= rows.length) sel = Math.max(0, rows.length - 1);
    let last = "";
    lst.replaceChildren(...rows.flatMap((r, i) => {
      const e = [];
      if (r.g !== last) { last = r.g; e.push(h("div", { class: "gl" }, r.g)); }
      e.push(h("div", { class: "it" + (i === sel ? " on" : ""), onclick: () => { close(); r.f(); } }, r.t, h("small", null, r.s)));
      return e;
    }));
  };

  const kd = e => {
    if (e.key === "Escape") close();
    else if (e.key === "ArrowDown") { sel = Math.min(rows.length - 1, sel + 1); build(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { sel = Math.max(0, sel - 1); build(); e.preventDefault(); }
    else if (e.key === "Enter" && document.activeElement === inp) { const r = rows[sel]; if (r) { close(); r.f(); } }
  };

  document.addEventListener("keydown", kd, true);
  inp.addEventListener("input", () => { sel = 0; build(); });
  document.body.append(ov);
  build();
  inp.focus();
};

document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    UI.closeDrawer();
    const m = $(".admin-modal-overlay");
    if (m) m.remove();
  }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k" && S.me) {
    e.preventDefault();
    UI.palette();
  }
});

// ---------------------------------------------------------------- Page Loader
async function loadPage(silent) {
  const seq = ++S.seq;
  clearTimeout(S.timer);
  const q = new URLSearchParams();
  if (S.tab) q.set("tab", S.tab);
  if (Object.keys(S.params || {}).length) q.set("p", JSON.stringify(S.params));

  if (!silent) {
    S.tree = null;
    $("#blocks").replaceChildren(
      h("div", { class: "boot", style: "min-height:240px;display:flex;align-items:center;justify-content:center;gap:12px;" },
        h("div", { class: "spin" }),
        h("span", { style: "color:var(--mut);font-weight:600;" }, "Loading module data…")
      )
    );
  }

  const d = await api(`/api/page/${S.page}?` + q);
  if (seq !== S.seq) return;

  if (d.blocks === undefined) {
    $("#blocks").replaceChildren(h("div", { class: "callout error" }, d.msg || d.detail || "Could not load module data."));
    return;
  }

  $("#ttl").textContent = d.title || "";
  $("#sub").textContent = d.sub || "";
  document.title = (d.title || "") + " · " + (S.me ? S.me.name : "FreightQuote AI");

  // Tabs
  const tabs = $("#tabs");
  if (d.tabs && d.tabs.length) {
    tabs.style.display = "flex";
    tabs.replaceChildren(
      ...d.tabs.map(x => h("b", {
        class: (S.tab || d.tabs[0].id) === x.id ? "on" : "",
        onclick: () => {
          S.params = {};
          UI.go(S.page, x.id);
        }
      }, x.label))
    );
  } else {
    tabs.style.display = "none";
    tabs.replaceChildren();
  }

  // Actions
  $("#acts").replaceChildren(
    ...(d.actions || []).map(a => h("button", {
      class: "btn " + (a.tone || "primary"),
      onclick: async e => {
        e.target.disabled = true;
        const r = await api(a.url, { json: {} });
        toast(r.msg, !r.ok);
        e.target.disabled = false;
        reloadPage(true);
      }
    }, a.label))
  );

  const box = $("#blocks");
  try {
    const blocks = Array.isArray(d.blocks) ? d.blocks : [];
    if (!S.tree || silent === false || !S.tree.ok || S.tree.id !== S.page || S.tree.tab !== S.tab) {
      box.replaceChildren();
      S.tree = { hs: mountList(box, blocks, "p"), ok: 1, id: S.page, tab: S.tab };
    } else {
      S.tree.hs = updList(box, S.tree.hs, blocks, "p");
    }
    if (!blocks.length) {
      box.replaceChildren(h("div", { class: "card fq-empty-module" },
        h("h3", null, "Nothing to show yet"),
        h("p", null, "This section will appear when there is data to display.")));
    }
  } catch (err) {
    console.error("FreightQuote: page render error", err);
    S.tree = null;
    box.replaceChildren(h("div", { class: "card fq-empty-module", role: "alert" },
      h("h3", null, "We couldn't open this page"),
      h("p", null, "Please try again. If the issue continues, check the application log."),
      h("button", { class: "btn primary", onclick: () => loadPage(false) }, "Try again")));
  }

  S.live = d.live || 0;
  sched();
}

function sched() {
  clearTimeout(S.timer);
  if (S.live && !document.hidden) {
    S.timer = setTimeout(() => loadPage(true), S.live * 1000);
  }
}

function reloadPage(soft) {
  loadPage(!!soft);
}

// ---------------------------------------------------------------- Application Shell Mount
let shellMounted = false;

function mountAppShell() {
  const app = $("#app");
  const signOutBtn = h("button", {
    class: "btn sm danger",
    style: "margin-top:12px;width:100%;",
    onclick: () => {
      localStorage.removeItem("fq_token");
      S.me = null;
      shellMounted = false;
      toast("Signed out successfully.", false);
      window.location.hash = "#/";
    }
  }, "Sign out");

  app.replaceChildren(
    h("div", { class: "side" },
      h("div", { class: "brand" },
        h("i", null, icon("radar")),
        h("div", null,
          "FreightQuote AI",
          h("small", null, S.me.user.role + " · " + S.me.user.username)
        )
      ),
      h("div", { class: "ksearch", onclick: () => UI.palette() }, "Quick search…", h("kbd", null, "Ctrl K")),
      h("div", { id: "nav" }),
      h("div", { style: "flex:1;" }),
      h("button", {
        class: "fq-theme-toggle",
        type: "button",
        onclick: (e) => {
          const enabled = !document.body.classList.contains("fq-dark");
          document.body.classList.toggle("fq-dark", enabled);
          localStorage.setItem("fq_dark", enabled ? "1" : "0");
          e.currentTarget.textContent = enabled ? "☀  Light appearance" : "☾  Dark appearance";
        }
      }, localStorage.getItem("fq_dark") === "1" ? "☀  Light appearance" : "☾  Dark appearance"),
      signOutBtn
    ),
    h("div", { class: "main" },
      h("div", { class: "top" },
        h("div", null, h("h1", { id: "ttl" }), h("div", { class: "sub", id: "sub" })),
        h("div", { style: "flex:1;" }),
        h("div", { id: "acts", style: "display:flex;gap:8px;" }),
        h("span", { class: "chip live-chip", id: "hl" },
          h("span", { class: "live-dot" }),
          "Live Fleet Engine"
        )
      ),
      h("div", { class: "content" },
        h("div", { class: "tabs", id: "tabs" }),
        h("div", { id: "pg" }, h("div", { class: "blocks", id: "blocks" }))
      )
    )
  );
  openStream();
}

async function renderApp(pageId, tabId) {
  const app = $("#app");
  if (!app) return;

  const token = localStorage.getItem("fq_token");
  if (!token) {
    shellMounted = false;
    window.location.hash = "#/login";
    return;
  }

  if (!shellMounted || !S.me) {
    const m = await api("/api/me");
    if (!m || !m.user) {
      localStorage.removeItem("fq_token");
      shellMounted = false;
      window.location.hash = "#/login";
      return;
    }
    S.me = m;
    mountAppShell();
    shellMounted = true;
  }

  document.body.classList.toggle("fq-dark", localStorage.getItem("fq_dark") === "1");

  const allowedMenu = S.me.menu || [];
  const validPage = allowedMenu.find(item => item.id === pageId);
  if (!validPage) {
    S.page = null;
    $("#ttl").textContent = "Access Denied";
    $("#sub").textContent = "403 Forbidden - Role Permission Required";
    $("#tabs").style.display = "none";
    $("#acts").replaceChildren();
    $("#blocks").replaceChildren(
      h("div", { class: "callout error", style: "margin: 20px 0; padding: 24px;" },
        h("h3", { style: "margin-top:0; color:#ef4444;" }, "Access Denied (403)"),
        h("p", null, `Your role (${S.me.user.role}) does not have permission to access the '${pageId}' module. Please choose an authorized module from the sidebar.`)
      )
    );
    renderNav();
    return;
  }

  S.page = pageId;
  S.tab = tabId || null;
  UI.closeDrawer();
  renderNav();
  loadPage(false);
}

// ---------------------------------------------------------------- Landing Page View
let cachedLandingHTML = null;

async function renderLanding() {
  const app = $("#app");
  shellMounted = false;
  if (S.es) { S.es.close(); S.es = null; }
  document.body.classList.remove("fq-dark");

  if (cachedLandingHTML) {
    app.innerHTML = cachedLandingHTML;
    bindLandingEvents(app);
    return;
  }

  try {
    const response = await fetch("/static/landing_exact.html");
    if (!response.ok) throw new Error("Landing page unavailable");
    cachedLandingHTML = await response.text();
    app.innerHTML = cachedLandingHTML;
    bindLandingEvents(app);
  } catch (err) {
    app.replaceChildren(h("div", { class: "boot", style: "padding:60px;text-align:center;" },
      h("h2", null, "FreightQuote AI"),
      h("p", { style: "color:var(--mut);" }, "Unable to load landing page."),
      h("button", { class: "btn primary", onclick: renderLanding }, "Retry")
    ));
  }
}

function bindLandingEvents(app) {
  const root = app.querySelector(".fq-exact-page") || app;
  root.querySelectorAll(".fq-access-login").forEach(el => el.addEventListener("click", () => { location.hash = "#/login"; }));
  root.querySelectorAll(".fq-access-create").forEach(el => el.addEventListener("click", () => { location.hash = "#/signup"; }));
  root.querySelectorAll(".fq-nav-links a").forEach(el => el.addEventListener("click", event => {
    event.preventDefault();
    const id = el.getAttribute("href").replace(/^#\/?/, "");
    history.replaceState(null, "", "#/" + id);
    root.querySelector("#" + id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }));
  const section = location.hash.replace(/^#\/?/, "");
  if (["platform", "how-it-works", "security", "faq"].includes(section)) {
    requestAnimationFrame(() => root.querySelector("#" + section)?.scrollIntoView({ behavior: "instant", block: "start" }));
  } else {
    scrollTo(0, 0);
  }
}

// ---------------------------------------------------------------- Auth Views
function authHero(title, desc) {
  return h("div", { class: "fq-auth-hero" },
    h("img", { class: "fq-auth-hero-img", src: "/static/login-hero.webp", onerror: (e) => { e.target.src = "/static/ship.jpg"; }, alt: "Maritime cargo vessel" }),
    h("div", { class: "fq-auth-hero-gradient" }),
    h("div", { class: "fq-auth-hero-content" },
      h("h1", { class: "fq-auth-hero-title" }, title),
      h("p", { class: "fq-auth-hero-desc" }, desc)
    )
  );
}

function renderLogin() {
  const app = $("#app");
  shellMounted = false;
  if (S.es) { S.es.close(); S.es = null; }
  document.body.classList.remove("fq-dark");

  const alertBox = h("div", { class: "fq-alert", style: "display:none;" });
  const unInput = h("input", { class: "in", type: "text", placeholder: "Username or email address", required: true });
  const pwInput = h("input", { class: "in", type: "password", placeholder: "Enter password", required: true });
  // The role is assigned by an administrator, not granted by this selector.
  const roleInput = h("select", { class: "in", required: true, "aria-label": "Assigned account role" },
    h("option", { value: "", disabled: true, selected: true }, "Select your assigned role"),
    ...["Admin", "Operations Manager", "Freight Broker", "Auditor", "Customer"].map(role => h("option", { value: role }, role))
  );

  let showPw = false;
  const pwToggle = h("button", {
    type: "button", class: "fq-pw-toggle", onclick: () => {
      showPw = !showPw;
      pwInput.type = showPw ? "text" : "password";
      pwToggle.textContent = showPw ? "Hide" : "Show";
    }
  }, "Show");

  const submitBtn = h("button", { class: "fq-btn-primary", type: "submit" }, "Sign in to Workspace");

  const form = h("form", {
    onsubmit: async e => {
      e.preventDefault();
      alertBox.style.display = "none";
      submitBtn.disabled = true;
      submitBtn.textContent = "Authenticating…";

      const res = await api("/api/auth/login", {
        method: "POST",
        json: { identity: unInput.value.trim(), password: pwInput.value, role: roleInput.value }
      });

      submitBtn.disabled = false;
      submitBtn.textContent = "Sign in to Workspace";

      if (res.ok && res.token) {
        localStorage.setItem("fq_token", res.token);
        toast("Sign in successful!", false);
        window.location.hash = "#/app/route";
      } else {
        alertBox.className = "fq-alert fq-alert-error";
        alertBox.textContent = res.msg || "Invalid username/email or password.";
        alertBox.style.display = "block";
      }
    }
  },
    h("div", { style: "display:grid;gap:16px;" },
      h("div", { class: "fld" }, h("label", null, "Account Identifier"), unInput),
      h("div", { class: "fld" }, h("label", null, "Assigned Role"), roleInput,
        h("small", { style: "color:var(--mut);" }, "Use the role assigned to your account by an administrator.")),
      h("div", { class: "fld" },
        h("div", { style: "display:flex;justify-content:space-between;align-items:center;" },
          h("label", null, "Password"),
          h("a", { href: "#/forgot", style: "font-size:12px;" }, "Forgot password?")
        ),
        h("div", { class: "profile-input-wrap" }, pwInput, pwToggle)
      ),
      alertBox,
      submitBtn,
      h("div", { style: "text-align:center;font-size:13px;color:var(--mut);margin-top:10px;" },
        h("a", { href: "#/verify-email", style: "font-weight:600;" }, "Verify your email"),
        h("span", null, " · "),
        "Don't have an account? ",
        h("a", { href: "#/signup", style: "font-weight:600;" }, "Create customer account")
      )
    )
  );

  const card = h("div", { class: "fq-auth-card" },
    h("div", { style: "display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;" },
      h("div", { style: "display:flex;align-items:center;gap:10px;cursor:pointer;", onclick: () => { window.location.hash = "#/"; } },
        h("div", { class: "brand", style: "padding:0;border:none;margin:0;" }, h("i", null, icon("radar"))),
        h("b", { style: "font-size:16px;" }, "FreightQuote AI")
      ),
      h("a", { href: "#/", class: "fq-btn-outline", style: "padding:6px 12px;font-size:12px;" }, "Home")
    ),
    h("div", { class: "fq-auth-header" },
      h("h2", { class: "fq-auth-title" }, "Sign in"),
      h("p", { class: "fq-auth-sub" }, "Access your freight logistics workspace.")
    ),
    form
  );

  app.replaceChildren(h("div", { class: "fq-auth-wrap" },
    authHero("Ocean Freight Intelligence", "Automate spot quotes, track carrier reliability, and analyze voyage congestion with verified data."),
    h("div", { class: "fq-auth-card-wrap" }, card)
  ));
}

function renderSignup() {
  const app = $("#app");
  shellMounted = false;
  if (S.es) { S.es.close(); S.es = null; }
  document.body.classList.remove("fq-dark");

  const alertBox = h("div", { class: "fq-alert", style: "display:none;" });
  const unInput = h("input", { class: "in", type: "text", placeholder: "Choose username", required: true });
  const emailInput = h("input", { class: "in", type: "email", placeholder: "e.g. shipper@company.com", required: true });
  const pwInput = h("input", { class: "in", type: "password", placeholder: "Choose strong password", required: true });
  const confPwInput = h("input", { class: "in", type: "password", placeholder: "Confirm password", required: true });

  const questionSelect = h("select", { class: "in" },
    h("option", { value: "What was the name of your first school?" }, "What was the name of your first school?"),
    h("option", { value: "In which city were you born?" }, "In which city were you born?"),
    h("option", { value: "What was the name of your first pet?" }, "What was the name of your first pet?"),
    h("option", { value: "What is the middle name of your oldest sibling?" }, "What is the middle name of your oldest sibling?")
  );
  const ansInput = h("input", { class: "in", type: "text", placeholder: "Your security answer", required: true });

  const submitBtn = h("button", { class: "fq-btn-primary", type: "submit" }, "Create Customer Account");

  const form = h("form", {
    onsubmit: async e => {
      e.preventDefault();
      alertBox.style.display = "none";
      submitBtn.disabled = true;
      submitBtn.textContent = "Creating account…";

      const res = await api("/api/auth/signup", {
        method: "POST",
        json: {
          username: unInput.value.trim(),
          email: emailInput.value.trim(),
          password: pwInput.value,
          confirm_password: confPwInput.value,
          question: questionSelect.value,
          answer: ansInput.value.trim(),
          role: "Customer"
        }
      });

      submitBtn.disabled = false;
      submitBtn.textContent = "Create Customer Account";

      if (res.ok) {
        toast("Account created. Verify your email to continue.", false);
        sessionStorage.setItem("fq_verify_email", emailInput.value.trim());
        window.location.hash = "#/verify-email";
      } else {
        alertBox.className = "fq-alert fq-alert-error";
        alertBox.textContent = res.msg || "Registration failed.";
        alertBox.style.display = "block";
      }
    }
  },
    h("div", { style: "display:grid;gap:14px;" },
      h("div", { class: "fld" }, h("label", null, "Username"), unInput),
      h("div", { class: "fld" }, h("label", null, "Email Address"), emailInput),
      h("div", { class: "fld" }, h("label", null, "Password"), pwInput),
      h("div", { class: "fld" }, h("label", null, "Confirm Password"), confPwInput),
      h("small", { style: "color:var(--mut);font-size:11.5px;" }, "Password needs 8+ chars, uppercase, lowercase, digit, and symbol."),
      h("div", { class: "fld" }, h("label", null, "Security Question"), questionSelect),
      h("div", { class: "fld" }, h("label", null, "Security Answer"), ansInput),
      alertBox,
      submitBtn,
      h("div", { style: "text-align:center;font-size:13px;color:var(--mut);margin-top:10px;" },
        "Already have an account? ",
        h("a", { href: "#/login", style: "font-weight:600;" }, "Sign in")
      )
    )
  );

  const card = h("div", { class: "fq-auth-card" },
    h("div", { style: "display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;" },
      h("div", { style: "display:flex;align-items:center;gap:10px;cursor:pointer;", onclick: () => { window.location.hash = "#/"; } },
        h("div", { class: "brand", style: "padding:0;border:none;margin:0;" }, h("i", null, icon("radar"))),
        h("b", { style: "font-size:16px;" }, "FreightQuote AI")
      ),
      h("a", { href: "#/", class: "fq-btn-outline", style: "padding:6px 12px;font-size:12px;" }, "Home")
    ),
    h("div", { class: "fq-auth-header" },
      h("h2", { class: "fq-auth-title" }, "Register"),
      h("p", { class: "fq-auth-sub" }, "Create a verified customer shipper account.")
    ),
    form
  );

  app.replaceChildren(h("div", { class: "fq-auth-wrap" },
    authHero("Maritime Logistics Platform", "Access instant rate calculations, customs documentation checks, and live voyage monitoring."),
    h("div", { class: "fq-auth-card-wrap" }, card)
  ));
}

function renderVerifyEmail() {
  const app = $("#app");
  shellMounted = false;
  if (S.es) { S.es.close(); S.es = null; }
  document.body.classList.remove("fq-dark");
  const email = h("input", { class: "in", type: "email", placeholder: "Registered email address", required: true, value: sessionStorage.getItem("fq_verify_email") || "" });
  const code = h("input", { class: "in", type: "text", inputmode: "numeric", maxlength: "6", pattern: "[0-9]{6}", placeholder: "Six-digit verification code", required: true });
  const alert = h("div", { class: "fq-alert", style: "display:none" });
  const sendBtn = h("button", { class: "fq-btn-outline", type: "button" }, "Send verification code");
  const verifyBtn = h("button", { class: "fq-btn-primary", type: "submit" }, "Verify email");
  const show = (msg, ok=false) => { alert.style.display="block"; alert.className="fq-alert " + (ok?"fq-alert-success":"fq-alert-error"); alert.textContent=msg; };
  let cooldown = 0;
  sendBtn.onclick = async () => {
    sendBtn.disabled=true;
    const r = await api("/api/auth/verify-email/request", {method:"POST",json:{email:email.value.trim()}});
    show(r.msg || (r.ok?"Code sent":"Unable to send code"),!!r.ok);
    if(r.ok) sessionStorage.setItem("fq_verify_email",email.value.trim());
    cooldown = Number(r.retry_after_seconds||0);
    if(cooldown>0){sendBtn.textContent=`Resend in ${cooldown}s`;const tick=setInterval(()=>{if(!sendBtn.isConnected){clearInterval(tick);return;}cooldown--;if(cooldown<=0){clearInterval(tick);sendBtn.disabled=false;sendBtn.textContent="Resend code";}else sendBtn.textContent=`Resend in ${cooldown}s`;},1000);} else sendBtn.disabled=false;
  };
  const form=h("form",{onsubmit:async e=>{e.preventDefault();verifyBtn.disabled=true;const r=await api("/api/auth/verify-email/confirm",{method:"POST",json:{email:email.value.trim(),code:code.value.trim()}});verifyBtn.disabled=false;if(r.ok){sessionStorage.removeItem("fq_verify_email");toast("Email verified. Sign in to continue.",false);location.hash="#/login";}else show(r.msg||"Verification failed");}},
    h("div",{style:"display:grid;gap:15px"},h("div",{class:"fld"},h("label",null,"Email address"),email),h("div",{class:"fld"},h("label",null,"Six-digit code"),code),sendBtn,alert,verifyBtn,h("a",{href:"#/login",style:"text-align:center"},"Back to Sign In")));
  app.replaceChildren(h("div",{class:"fq-auth-wrap"},authHero("Verify Your Email","Your account is almost ready. Check your inbox for the verification code."),h("div",{class:"fq-auth-card-wrap"},h("div",{class:"fq-auth-card"},h("div",{class:"fq-auth-header"},h("h2",{class:"fq-auth-title"},"Email Verification"),h("p",{class:"fq-auth-sub"},"Verify your address before signing in.")),form))));
}

function renderForgot() {
  const app=$("#app"); shellMounted=false;
  if(S.es){S.es.close();S.es=null;}
  document.body.classList.remove("fq-dark");
  let method="otp", grant=null, verifiedIdentity="", currentIdentity="", cooldown=0;
  const card=h("div",{class:"fq-auth-card"});
  const draw=()=>{
    const alert=h("div",{class:"fq-alert",style:"display:none"});
    const show=(msg,ok=false)=>{alert.style.display="block";alert.className="fq-alert "+(ok?"fq-alert-success":"fq-alert-error");alert.textContent=msg;};
    if(grant){
      const pw=h("input",{class:"in",type:"password",required:true,placeholder:"New password"});
      const confirm=h("input",{class:"in",type:"password",required:true,placeholder:"Confirm new password"});
      const btn=h("button",{type:"submit",class:"fq-btn-primary"},"Reset Password");
      const form=h("form",{onsubmit:async e=>{e.preventDefault();btn.disabled=true;const r=await api("/api/auth/reset",{method:"POST",json:{identity:verifiedIdentity,grant,new_password:pw.value,confirm_password:confirm.value}});btn.disabled=false;if(r.ok){toast("Password updated. Sign in with your new password.",false);location.hash="#/login";}else show(r.msg||"Password reset failed.");}},
        h("div",{style:"display:grid;gap:15px"},h("div",{class:"fld"},h("label",null,"New password"),pw),h("div",{class:"fld"},h("label",null,"Confirm new password"),confirm),h("small",{style:"color:var(--mut)"},"8+ characters, uppercase, lowercase, digit, symbol, no spaces."),alert,btn));
      card.replaceChildren(h("div",{class:"fq-auth-header"},h("h2",{class:"fq-auth-title"},"Set New Password"),h("p",{class:"fq-auth-sub"},"Verification successful. Choose a new password.")),form);return;
    }
    const otpChoice=h("input",{type:"radio",name:"fq-recovery-method",value:"otp",checked:method==="otp"});
    const questionChoice=h("input",{type:"radio",name:"fq-recovery-method",value:"question",checked:method==="question"});
    for(const [button,kind] of [[otpChoice,"otp"],[questionChoice,"question"]]) button.addEventListener("change",()=>{method=kind;currentIdentity="";draw();});
    const id=h("input",{class:"in",type:method==="otp"?"email":"text",required:true,placeholder:method==="otp"?"Registered email address":"Username or email",value:currentIdentity});
    id.addEventListener("input",()=>{currentIdentity=id.value.trim();});
    const code=h("input",{class:"in",type:"text",inputmode:"numeric",maxlength:"6",placeholder:"Six-digit code",required:true});
    const answer=h("input",{class:"in",type:"password",placeholder:"Your security answer",required:true});
    const question=h("div",{style:"display:none;font-weight:600;padding:12px;background:var(--line-subtle);border-radius:9px"});
    let questionLoaded = false;
    let questionLocked = false;
    const loadQuestion = async () => {
      const identity = id.value.trim();
      if (!identity) { show("Enter your username or email first."); return; }
      question.textContent = "Finding your security question…";
      question.style.display = "block";
      const r = await api("/api/auth/forgot/question", { method: "POST", json: { identity } });
      if (identity !== id.value.trim() || !question.isConnected) return;
      questionLoaded = !!(r.ok && r.question);
      questionLocked = !!r.locked;
      question.textContent = questionLoaded ? r.question : "Security question unavailable.";
      answer.disabled = !questionLoaded || questionLocked;
      submit.disabled = !questionLoaded || questionLocked;
      if (questionLocked) show(r.msg || "Account locked. Contact the administrator to unlock it.");
      else if (!questionLoaded) show(r.msg || "Unable to find security question.");
      else alert.style.display = "none";
    };
    if (method === "question") {
      answer.disabled = true;
      id.addEventListener("blur", loadQuestion);
      id.addEventListener("input", () => {
        questionLoaded = false; questionLocked = false;
        question.style.display = "none";
        answer.disabled = true;
        submit.disabled = true;
        alert.style.display = "none";
      });
    }
    const showQuestion = h("button", { type: "button", class: "fq-btn-outline", onclick: loadQuestion }, "Show security question");
    const send=h("button",{type:"button",class:"fq-btn-outline"},"Send email code");
    send.addEventListener("click",async()=>{send.disabled=true;const r=await api("/api/auth/forgot/request_otp",{method:"POST",json:{email:id.value.trim()}});show(r.msg||"Unable to send code",!!r.ok);cooldown=Number(r.retry_after_seconds||0);if(cooldown>0){send.textContent=`Resend in ${cooldown}s`;const tick=setInterval(()=>{if(!send.isConnected){clearInterval(tick);return;}cooldown--;if(cooldown<=0){clearInterval(tick);send.disabled=false;send.textContent="Resend code";}else send.textContent=`Resend in ${cooldown}s`;},1000);}else send.disabled=false;});
    const submit=h("button",{class:"fq-btn-primary",type:"submit",disabled:method==="question"},method==="otp"?"Verify email code":"Verify security answer");
    const form=h("form",{onsubmit:async e=>{e.preventDefault();submit.disabled=true;const identity=id.value.trim();const path=method==="otp"?"/api/auth/forgot/verify_otp":"/api/auth/forgot/verify_answer";const json=method==="otp"?{email:identity,code:code.value.trim()}:{identity,answer:answer.value};const r=await api(path,{method:"POST",json});submit.disabled=false;if(r.ok&&r.grant){grant=r.grant;verifiedIdentity=identity;draw();}else show(r.msg||"Verification failed.");}},
      h("div",{style:"display:grid;gap:15px"},
        h("div",{style:"display:flex;gap:18px;flex-wrap:wrap;align-items:center"},h("label",{style:"display:flex;gap:8px;align-items:center"},otpChoice,"Email OTP"),h("label",{style:"display:flex;gap:8px;align-items:center"},questionChoice,"Security question")),
        h("div",{class:"fld"},h("label",null,method==="otp"?"Registered email":"Username or email"),id),
        ...(method==="otp"?[send,h("div",{class:"fld"},h("label",null,"Six-digit verification code"),code)]:[showQuestion,question,h("div",{class:"fld"},h("label",null,"Security answer"),answer)]),
        alert,submit,h("a",{href:"#/login",style:"text-align:center"},"Back to Sign In")));
    card.replaceChildren(h("div",{class:"fq-auth-header"},h("h2",{class:"fq-auth-title"},"Password Recovery"),h("p",{class:"fq-auth-sub"},"Recover your account using email verification or a security question.")),form);
  };
  draw();app.replaceChildren(h("div",{class:"fq-auth-wrap"},authHero("Account Recovery","Recover access to your FreightQuote AI workspace."),h("div",{class:"fq-auth-card-wrap"},card)));
}

// ---------------------------------------------------------------- Hash Router
async function handleRouting() {
  const hash = window.location.hash || "#/";

  if (hash === "#/" || hash === "#" || hash === "") {
    renderLanding();
  } else if (hash.startsWith("#/platform") || hash.startsWith("#/how-it-works") || hash.startsWith("#/security") || hash.startsWith("#/faq")) {
    renderLanding();
  } else if (hash === "#/login") {
    renderLogin();
  } else if (hash === "#/signup") {
    renderSignup();
  } else if (hash === "#/forgot") {
    renderForgot();
  } else if (hash === "#/verify-email") {
    renderVerifyEmail();
  } else if (hash.startsWith("#/app/")) {
    const raw = hash.slice(6);
    const parts = raw.split(":");
    const pid = parts[0];
    const tab = parts[1] || null;
    await renderApp(pid, tab);
  } else {
    renderLanding();
  }
}

window.addEventListener("hashchange", handleRouting);
window.UI = UI;

// Bootstrapping
handleRouting();