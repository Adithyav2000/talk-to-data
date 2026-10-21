// ============================================================
// Claimsight · Talk to Data  --  React frontend (no UI kit)
// ============================================================
import React, { useState, useEffect, useCallback, useRef, createContext, useContext, useMemo } from 'react';
import { createRoot } from 'react-dom/client';
import htm from 'htm';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

const html = htm.bind(React.createElement);

// ============================================================
// Icons (lucide-style, 24px grid)
// ============================================================
const ICONS = {
  home: 'M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  chat: 'M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-5.4A8 8 0 1 1 21 12z',
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4',
  code: 'M16 18l6-6-6-6M8 6l-6 6 6 6',
  chart: 'M3 3v18h18M7 15l4-4 3 3 5-6',
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3',
  send: 'M22 2 11 13M22 2l-7 20-4-9-9-4z',
  download: 'M12 3v12m0 0-4-4m4 4 4-4M4 21h16',
  sun: 'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4',
  moon: 'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z',
  logout: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9',
  check: 'M20 6 9 17l-5-5',
  x: 'M18 6 6 18M6 6l12 12',
  spark: 'M12 3l1.9 5.6 5.6 1.9-5.6 1.9L12 18l-1.9-5.6-5.6-1.9 5.6-1.9z',
  clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2',
  db: 'M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6',
  plus: 'M12 5v14M5 12h14',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  menu: 'M3 6h18M3 12h18M3 18h18',
  alert: 'M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z',
  info: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16v-4M12 8h.01',
  play: 'M6 4l14 8-14 8z',
  inbox: 'M22 12h-6l-2 3h-4l-2-3H2M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.1z',
  refresh: 'M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5',
  loader: 'M12 3a9 9 0 1 0 9 9',
  trend: 'M22 7 13.5 15.5l-5-5L2 17M16 7h6v6',
  wallet: 'M3 7a2 2 0 0 1 2-2h13v4M3 7v11a2 2 0 0 0 2 2h14a1 1 0 0 0 1-1v-9a1 1 0 0 0-1-1H5a2 2 0 0 1-2-2zM16 14h.01',
  check2: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM8 12l3 3 5-6',
};
function Icon({ name, size = 18, className = '' }) {
  return html`<svg className=${className} width=${size} height=${size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d=${ICONS[name] || ICONS.info} /></svg>`;
}
const Logo = () => html`<div className="brand-mark"><${Icon} name="trend" size=${20} /></div>`;

// ============================================================
// Formatting helpers
// ============================================================
const CH = ['#54755a', '#d99a2b', '#3b82a6', '#d1604a', '#7c6fc7', '#6aa84f', '#b08d57', '#4aa3a0'];
const TIME_RE = /date|month|year|quarter|week|day|time|period/i;
const ID_RE = /(^|_)(id|zip|code|number|no)$/i;
const isNum = v => v != null && v !== '' && typeof v !== 'boolean' && !isNaN(Number(v));
const prettify = c => String(c).replace(/_/g, ' ').replace(/\b\w/g, m => m.toUpperCase());
const nf = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });
const fmtDate = v => {
  if (!v) return '—';
  const d = new Date(v);
  return isNaN(d) ? String(v) : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
};
const greeting = () => { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'; };
const plural = (n, w) => `${n} ${w}${n === 1 ? '' : 's'}`;

function downloadCSV(columns, rows, name) {
  const esc = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const csv = [columns.map(esc).join(','), ...rows.map(r => r.map(esc).join(','))].join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = (name || 'data').replace(/[^\w-]+/g, '_') + '.csv';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

function useDebounced(value, ms = 300) {
  const [v, setV] = useState(value);
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t); }, [value, ms]);
  return v;
}

// ============================================================
// API + session
// ============================================================
let TOKEN = null;
let onAuthFail = () => {};
try { TOKEN = sessionStorage.getItem('wc-token'); } catch (e) { /* storage blocked */ }

const api = async (url, opts = {}) => {
  try {
    const headers = { 'Content-Type': 'application/json', ...(TOKEN ? { 'X-Claimsight-Token': TOKEN } : {}) };
    const r = await fetch(url, { ...opts, headers });
    const data = await r.json().catch(() => ({}));
    if (r.status === 401 && TOKEN) onAuthFail();
    if (!r.ok && !data.error) data.error = typeof data.detail === 'string' ? data.detail : data.detail ? JSON.stringify(data.detail) : `Request failed (${r.status})`;
    return data;
  } catch (e) {
    return { error: e.message };
  }
};
const post = (url, body) => api(url, { method: 'POST', body: JSON.stringify(body) });

const AuthCtx = createContext(null);
const useAuth = () => useContext(AuthCtx);

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!TOKEN);

  const logout = useCallback(() => {
    TOKEN = null;
    try { sessionStorage.removeItem('wc-token'); } catch (e) { /* ignore */ }
    setUser(null);
  }, []);
  onAuthFail = logout;

  useEffect(() => {
    if (!TOKEN) return;
    api('/api/auth/me').then(r => { if (r.user) setUser(r.user); else logout(); setReady(true); });
  }, [logout]);

  const login = useCallback(async (username, password) => {
    const r = await post('/api/auth/login', { username, password });
    if (r.success) {
      TOKEN = r.token;
      // Confirm the server accepts the session before entering the app. Behind a proxy a rejected
      // token would otherwise bounce the user straight back here with no explanation.
      const me = await api('/api/auth/me');
      if (!me.user) {
        TOKEN = null;
        return { ok: false, error: `Signed in, but the server rejected the session${me.error ? ` (${me.error})` : ''}. Please try again or contact your administrator.` };
      }
      try { sessionStorage.setItem('wc-token', r.token); } catch (e) { /* ignore */ }
      setUser(r.user);
      return { ok: true };
    }
    return { ok: false, error: r.error || 'Sign-in failed' };
  }, []);

  const val = useMemo(() => ({ user, login, logout }), [user, login, logout]);
  if (!ready) return html`<div className="boot"><div className="boot-mark"><span></span></div></div>`;
  return html`<${AuthCtx.Provider} value=${val}>${children}<//>`;
}

// ---- toasts ----
const ToastCtx = createContext(() => {});
const useToast = () => useContext(ToastCtx);
function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const push = useCallback((msg, kind = 'ok') => {
    const id = Math.random();
    setItems(p => [...p, { id, msg, kind }]);
    setTimeout(() => setItems(p => p.filter(t => t.id !== id)), 4200);
  }, []);
  return html`<${ToastCtx.Provider} value=${push}>${children}
    <div className="toasts">${items.map(t => html`<div key=${t.id} className=${'toast ' + t.kind}><${Icon} name=${t.kind === 'ok' ? 'check2' : 'alert'} />${t.msg}</div>`)}</div><//>`;
}

// ============================================================
// Shared components
// ============================================================
function PageHead({ title, subtitle, children }) {
  return html`<div className="page-head"><div><h1>${title}</h1>${subtitle && html`<p>${subtitle}</p>`}</div>${children && html`<div style=${{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>${children}</div>`}</div>`;
}

function Alert({ kind = 'info', children }) {
  return html`<div className=${'alert ' + kind}><${Icon} name=${kind === 'ok' ? 'check2' : kind === 'info' ? 'info' : 'alert'} size=${17} /><div>${children}</div></div>`;
}

function Empty({ icon = 'inbox', title, children }) {
  return html`<div className="empty"><div className="ring"><${Icon} name=${icon} size=${24} /></div><h3>${title}</h3>${children && html`<p>${children}</p>`}</div>`;
}

function Spinner({ size = 16 }) { return html`<${Icon} name="loader" size=${size} className="spin" />`; }

function Skeletons({ n = 3, h = 120 }) {
  return html`<div className="call-grid">${Array.from({ length: n }, (_, i) => html`<div key=${i} className="skeleton" style=${{ height: h }} />`)}</div>`;
}

const STATUS = {
  TESTED_PASS: ['Passing', 'good'], TESTED_FAIL: ['Failing', 'bad'], NA: ['Untested', ''],
  PENDING: ['Pending', 'warn'], APPROVED: ['Approved', 'good'], REJECTED: ['Rejected', 'bad'],
};
function StatusBadge({ status }) {
  const s = String(status || 'NA').toUpperCase();
  const [label, kind] = STATUS[s] || [prettify(s), ''];
  return html`<span className=${'badge ' + kind}>${label}</span>`;
}

function Segmented({ value, onChange, options }) {
  return html`<div className="seg" role="tablist">${options.map(o => {
    const [v, label, count] = Array.isArray(o) ? o : [o, o];
    return html`<button key=${v} role="tab" aria-selected=${value === v} className=${value === v ? 'on' : ''} onClick=${() => onChange(v)}>${label}${count > 0 && html`<span className="count">${count}</span>`}</button>`;
  })}</div>`;
}

function Drawer({ title, subtitle, onClose, children, modal }) {
  useEffect(() => {
    const k = e => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [onClose]);
  const head = html`<div className="drawer-head"><div><h2>${title}</h2>${subtitle && html`<p>${subtitle}</p>`}</div>
    <button className="icon-btn" onClick=${onClose} aria-label="Close"><${Icon} name="x" /></button></div>`;
  return modal
    ? html`<div className="modal-wrap"><div className="bg" onClick=${onClose} /><div className="modal" role="dialog">${head}<div className="drawer-body">${children}</div></div></div>`
    : html`<div className="drawer-wrap"><div className="bg" onClick=${onClose} /><div className="drawer" role="dialog">${head}<div className="drawer-body">${children}</div></div></div>`;
}

// ---- data table ----
function DataTable({ columns = [], rows = [], max = 500 }) {
  const numeric = useMemo(() => columns.map((c, i) => {
    const vals = rows.map(r => r[i]).filter(v => v != null && v !== '');
    return vals.length > 0 && !ID_RE.test(c) && !TIME_RE.test(c) && vals.filter(isNum).length / vals.length >= 0.9;
  }), [columns, rows]);
  if (!columns.length) return html`<${Empty} title="No columns returned" />`;
  const show = rows.slice(0, max);
  return html`<div>
    <div className="table-wrap"><table className="t">
      <thead><tr>${columns.map((c, i) => html`<th key=${i} className=${numeric[i] ? 'num' : ''}>${prettify(c)}</th>`)}</tr></thead>
      <tbody>${show.map((r, ri) => html`<tr key=${ri}>${r.map((c, ci) => html`<td key=${ci} className=${numeric[ci] ? 'num' : ''} title=${c ?? ''}>${c == null || c === '' ? '—' : numeric[ci] ? nf.format(Number(c)) : String(c)}</td>`)}</tr>`)}</tbody>
    </table></div>
    ${rows.length > max && html`<p className="hint" style=${{ marginTop: 8 }}>Showing first ${max} of ${rows.length} rows — download the CSV for everything.</p>`}
  </div>`;
}

// ---- charts ----
function analyze(columns, rows) {
  const meta = columns.map((c, i) => {
    const vals = rows.map(r => r[i]).filter(v => v != null && v !== '');
    return { c, i, numeric: vals.length > 0 && vals.filter(isNum).length / vals.length >= 0.9, time: TIME_RE.test(c), id: ID_RE.test(c) };
  });
  const x = meta.find(m => !m.numeric) || meta.find(m => m.time) || meta[0];
  // year/date columns are labels, not measures: never plot them as a series
  let ys = meta.filter(m => m !== x && m.numeric && !m.id && !m.time);
  if (!ys.length) ys = meta.filter(m => m !== x && m.numeric);
  return { x, ys: ys.slice(0, 4) };
}

function ChartView({ columns, rows }) {
  const { x, ys } = useMemo(() => analyze(columns, rows), [columns, rows]);
  // a time axis must show its whole range; category charts stay capped to stay legible
  const data = useMemo(() => (x.time ? rows.slice(0, 500) : rows.slice(0, 60)).map(r => {
    const o = { [x.c]: r[x.i] == null ? '—' : String(r[x.i]) };
    ys.forEach(y => { o[y.c] = isNum(r[y.i]) ? Number(r[y.i]) : null; });
    return o;
  }), [rows, x, ys]);
  const nCats = data.length;
  // series on a very different scale from the first one get their own right-hand axis
  const peak = y => Math.max(...data.map(d => Math.abs(d[y.c] ?? 0)), 1e-9);
  const right = ys.map((y, i) => i > 0 && (peak(ys[0]) / peak(y) > 8 || peak(y) / peak(ys[0]) > 8));
  const hasRight = right.some(Boolean);
  const axisId = i => (right[i] ? 'r' : 'l');
  const canPie = ys.length === 1 && nCats <= 12 && nCats > 1;
  const auto = x.time && nCats > 2 ? 'line' : canPie && nCats <= 6 ? 'pie' : 'bar';
  const [kind, setKind] = useState(auto);
  useEffect(() => setKind(auto), [auto]);
  if (!ys.length || !data.length) return html`<${Empty} icon="chart" title="Nothing to chart">This result has no numeric columns. Try the Data tab.<//>`;

  const tip = { contentStyle: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, boxShadow: 'var(--shadow)', color: 'var(--ink)', fontSize: 12.5 }, labelStyle: { color: 'var(--ink)', fontWeight: 600 }, cursor: { fill: 'rgba(120,150,135,.12)' }, formatter: v => (typeof v === 'number' ? nf.format(v) : v) };
  const tick = v => { const s = String(v); return s.length > 14 ? s.slice(0, 13) + '…' : s; };
  const axes = html`<${CartesianGrid} strokeDasharray="3 4" vertical=${false} />
    <${XAxis} dataKey=${x.c} tickFormatter=${tick} tickLine=${false} axisLine=${false} interval="preserveStartEnd" angle=${nCats > 8 ? -30 : 0} textAnchor=${nCats > 8 ? 'end' : 'middle'} height=${nCats > 8 ? 60 : 30} />
    <${YAxis} yAxisId="l" tickLine=${false} axisLine=${false} width=${56} tickFormatter=${v => nf.format(v)} />
    ${hasRight && html`<${YAxis} yAxisId="r" orientation="right" tickLine=${false} axisLine=${false} width=${56} tickFormatter=${v => nf.format(v)} />`}
    <${Tooltip} ...${tip} />${ys.length > 1 && html`<${Legend} />`}`;

  return html`<div>
    <div className="chart-tools">
      <span className="hint">${prettify(ys.map(y => y.c).join(', '))} by ${prettify(x.c)}</span>
      <${Segmented} value=${kind} onChange=${setKind} options=${[['bar', 'Bar'], ['line', 'Line'], ...(canPie ? [['pie', 'Pie']] : [])]} />
    </div>
    <div className="chart-box"><${ResponsiveContainer} width="100%" height="100%">
      ${kind === 'bar' ? html`<${BarChart} data=${data} margin=${{ top: 8, right: 8, left: 0, bottom: 0 }}>${axes}
          ${ys.map((y, i) => html`<${Bar} key=${y.c} yAxisId=${axisId(i)} name=${prettify(y.c)} dataKey=${y.c} fill=${CH[i]} radius=${[6, 6, 0, 0]} maxBarSize=${48} />`)}<//>`
        : kind === 'line' ? html`<${LineChart} data=${data} margin=${{ top: 8, right: 12, left: 0, bottom: 0 }}>${axes}
          ${ys.map((y, i) => html`<${Line} key=${y.c} yAxisId=${axisId(i)} name=${prettify(y.c)} type="monotone" dataKey=${y.c} stroke=${CH[i]} strokeWidth=${2.5} dot=${{ r: 3, strokeWidth: 0, fill: CH[i] }} activeDot=${{ r: 5 }} />`)}<//>`
        : html`<${PieChart}><${Tooltip} ...${tip} /><${Legend} />
          <${Pie} data=${data} dataKey=${ys[0].c} nameKey=${x.c} innerRadius="52%" outerRadius="82%" paddingAngle=${2} stroke="var(--surface)" strokeWidth=${2}>
            ${data.map((_, i) => html`<${Cell} key=${i} fill=${CH[i % CH.length]} />`)}<//><//>`}
    <//></div>
  </div>`;
}

// ---- export dialog (Excel with format options, or CSV) ----
const XL_FORMATS = [['general', 'General (as is)'], ['integer', 'Number — 1,234'], ['decimal', 'Number — 1,234.56'], ['currency', 'Currency — $1,234.56'], ['percent', 'Percent — 0.25 → 25%']];
function ExportDialog({ res, name, onClose }) {
  const toast = useToast();
  const [kind, setKind] = useState('xlsx');
  const [o, setO] = useState({ numberFormat: 'general', styledHeader: true, freezeHeader: true, autoFilter: true, zebra: false, includeSql: !!res.sql });
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setO(p => ({ ...p, [k]: v }));
  const go = async () => {
    if (kind === 'csv') { downloadCSV(res.columns, res.rows, name); onClose(); return; }
    setBusy(true);
    try {
      const r = await fetch('/api/export/xlsx', {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...(TOKEN ? { 'X-Claimsight-Token': TOKEN } : {}) },
        body: JSON.stringify({ columns: res.columns, rows: res.rows, title: name || 'Data', sql: res.sql || null, ...o }),
      });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Export failed (${r.status})`);
      const a = document.createElement('a');
      a.href = URL.createObjectURL(await r.blob());
      a.download = (name || 'export').replace(/[^\w-]+/g, '_') + '.xlsx';
      a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
      toast('Excel file downloaded'); onClose();
    } catch (e) { toast(e.message, 'error'); }
    setBusy(false);
  };
  const Check = ({ k, label, hint }) => html`<label className="check"><input type="checkbox" checked=${o[k]} onChange=${e => set(k, e.target.checked)} /><span><b>${label}</b>${hint && html`<small>${hint}</small>`}</span></label>`;
  return html`<${Drawer} modal title="Export results" subtitle=${`${plural(res.rows.length, 'row')} · ${plural(res.columns.length, 'column')}`} onClose=${onClose}>
    <div className="field"><label>File format</label>
      <${Segmented} value=${kind} onChange=${setKind} options=${[['xlsx', 'Excel (.xlsx)'], ['csv', 'CSV']]} /></div>
    ${kind === 'xlsx' ? html`<div style=${{ display: 'grid', gap: 14 }}>
      <div className="field"><label>Number format (applied to numeric columns)</label>
        <select className="select" value=${o.numberFormat} onChange=${e => set('numberFormat', e.target.value)}>${XL_FORMATS.map(([v, l]) => html`<option key=${v} value=${v}>${l}</option>`)}</select></div>
      <div className="checks">
        <${Check} k="styledHeader" label="Styled header row" hint="Green header with white bold text" />
        <${Check} k="freezeHeader" label="Freeze header row" hint="Header stays visible while scrolling" />
        <${Check} k="autoFilter" label="Filter buttons" hint="Sort and filter on every column" />
        <${Check} k="zebra" label="Banded rows" hint="Light shading on alternate rows" />
        ${res.sql && html`<${Check} k="includeSql" label="Include SQL sheet" hint="Adds the query as a second tab" />`}
      </div></div>` : html`<p className="hint">Plain comma-separated text — opens in Excel, but without formatting.</p>`}
    <button className="btn primary" onClick=${go} disabled=${busy}>${busy ? html`<${Spinner} />Preparing…` : html`<${Icon} name="download" size=${16} />Download ${kind === 'xlsx' ? 'Excel file' : 'CSV'}`}</button>
  <//>`;
}

// ---- unified result view ----
const timeAgo = iso => {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`;
};

function ResultView({ res, name = 'result', onRefresh }) {
  const hasData = !!(res?.columns?.length && res?.rows?.length);
  const [tab, setTab] = useState(hasData ? 'chart' : 'data');
  const [exporting, setExporting] = useState(false);
  useEffect(() => setTab(hasData ? 'chart' : 'data'), [hasData, res]);
  if (!res) return null;
  if (res.error) return html`<${Alert} kind="error">${res.error}<//>`;
  const tabs = [...(hasData ? [['chart', 'Chart'], ['data', `Data (${res.rows.length})`]] : []), ...(res.sql ? [['sql', 'SQL']] : [])];
  return html`<div className="result">
    ${res.text && html`<div className="result-note">${res.text}</div>`}
    ${!hasData && res.columns && !res.text && html`<${Empty} title="No rows returned">The query ran, but nothing matched.<//>`}
    ${res.cached && html`<div className="cache-note"><span><${Icon} name="clock" size=${14} />Cached result from ${timeAgo(res.cachedAt)} · refreshes daily</span>
      ${onRefresh && html`<button className="btn ghost sm" onClick=${onRefresh}><${Icon} name="refresh" size=${13} />Refresh now</button>`}</div>`}
    ${tabs.length > 0 && html`<div className="result-head">
      <${Segmented} value=${tab} onChange=${setTab} options=${tabs} />
      ${hasData && html`<button className="btn sm" onClick=${() => setExporting(true)}><${Icon} name="download" size=${15} />Export</button>`}
    </div>`}
    ${tab === 'chart' && hasData && html`<${ChartView} columns=${res.columns} rows=${res.rows} />`}
    ${tab === 'data' && hasData && html`<${DataTable} columns=${res.columns} rows=${res.rows} />`}
    ${tab === 'sql' && html`<pre className="sql">${res.sql}</pre>`}
    ${exporting && html`<${ExportDialog} res=${res} name=${name} onClose=${() => setExporting(false)} />`}
  </div>`;
}

// ---- Genie conversation (lets the user answer Genie's clarifying questions) ----
function useGenie(endpoint, onResult) {
  const [msgs, setMsgs] = useState([]);
  const [convId, setConvId] = useState(null);
  const [busy, setBusy] = useState(false);
  const send = async (label, body, fresh = false) => {
    setMsgs(m => [...m, { role: 'user', text: label }]); setBusy(true);
    const res = await post(endpoint, { ...body, conversationId: fresh ? null : convId });
    if (res.conversation_id) setConvId(res.conversation_id);
    setMsgs(m => [...m, { role: 'bot', res, q: label }]); setBusy(false);
    if (onResult) onResult(res);
    return res;
  };
  const reset = () => { setMsgs([]); setConvId(null); };
  return { msgs, busy, send, reset };
}

function GenieThread({ g, name, onReply, onRefresh, placeholder = 'Reply to Genie…' }) {
  const [text, setText] = useState('');
  if (!g.msgs.length && !g.busy) return null;
  const last = g.msgs[g.msgs.length - 1];
  const asking = last?.role === 'bot' && !last.res.error && last.res.text && !last.res.columns?.length;
  const submit = e => { e.preventDefault(); const t = text.trim(); if (!t || g.busy) return; setText(''); onReply(t); };
  return html`<div className="thread">
    ${g.msgs.map((m, i) => m.role === 'user'
      ? html`<div key=${i} className="msg-user sm">${m.text}</div>`
      : html`<div key=${i} className="msg-bot"><div className="bot-av"><${Icon} name="spark" size=${17} /></div>
          <div className="card bubble"><${ResultView} res=${m.res} name=${name} onRefresh=${onRefresh} /></div></div>`)}
    ${g.busy && html`<div className="msg-bot"><div className="bot-av"><${Icon} name="spark" size=${17} /></div>
      <div className="card bubble"><span className="typing"><i></i><i></i><i></i></span><span className="hint" style=${{ marginLeft: 8 }}>Genie is working…</span></div></div>`}
    ${asking && !g.busy && html`<${Alert} kind="info">Genie needs a bit more detail. Answer below and it will carry on.<//>`}
    <form className="composer" onSubmit=${submit}>
      <input value=${text} onChange=${e => setText(e.target.value)} placeholder=${placeholder} disabled=${g.busy} />
      <button className="send" type="submit" disabled=${g.busy || !text.trim()} aria-label="Send"><${Icon} name="send" size=${18} /></button>
    </form>
    <div><button className="btn ghost sm" onClick=${g.reset}><${Icon} name="refresh" size=${14} />Start over</button></div>
  </div>`;
}

// ============================================================
// Login  --  persona picker
// ============================================================
const PAGE_LABEL = { 'Data Calls': 'Data calls', 'Ask Data': 'Ask data', 'IT Review': 'IT review' };

function LoginPage() {
  const { login } = useAuth();
  const [personas, setPersonas] = useState(null);
  const [hint, setHint] = useState('');
  const [sel, setSel] = useState(null);
  const [pw, setPw] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const pwRef = useRef(null);

  useEffect(() => { api('/api/personas').then(d => { setPersonas(d.personas || []); setHint(d.demoHint || ''); if (d.demoHint) setPw(d.demoHint); }); }, []);
  useEffect(() => { if (sel && pwRef.current) pwRef.current.focus(); }, [sel]);

  const go = async e => {
    e.preventDefault(); if (!sel) return;
    setBusy(true); setErr('');
    const r = await login(sel.username, pw);
    setBusy(false);
    if (!r.ok) setErr(r.error);
  };

  return html`<div className="login">
    <section className="login-hero">
      <div className="brand"><${Logo} /><div><b>Claimsight</b><span>Talk to Data</span></div></div>
      <div>
        <h1>Ask your claims data <em>anything.</em></h1>
        <p className="lead">One workspace for the data-call registry, natural-language analytics and the IT review pipeline — tailored to how you work.</p>
      </div>
      <div className="hero-stats">
        <div><b>2</b><span>Registries unified</span></div>
        <div><b>20</b><span>Curated report prompts</span></div>
        <div><b>5</b><span>Role-based workspaces</span></div>
      </div>
    </section>
    <section className="login-main"><div className="login-box">
      <h2>Choose your workspace</h2>
      <p>Pick the persona that matches your role. Each one opens a different home screen and set of tools.</p>
      ${!personas ? html`<div className="persona-grid">${[0, 1, 2, 3].map(i => html`<div key=${i} className="skeleton" style=${{ height: 150 }} />`)}</div>` : html`
      <div className="persona-grid">${personas.map(p => html`
        <button key=${p.username} type="button" className=${'persona' + (sel?.username === p.username ? ' on' : '')} style=${{ '--p': p.accent }} onClick=${() => { setSel(p); setErr(''); }}>
          <span className="tick"><${Icon} name="check" size=${12} /></span>
          <span className="pi"><${Icon} name=${p.icon} size=${21} /></span>
          <div><b>${p.name}</b><small>${p.title}</small></div>
          <p>${p.tagline}</p>
          <div className="access">${p.registries?.length === 1 && html`<span className="reg">${p.registries[0]} only</span>`}${p.pages.filter(x => x !== 'Home').map(x => html`<span key=${x}>${PAGE_LABEL[x] || x}</span>`)}</div>
        </button>`)}</div>
      ${sel && html`<form className="card signin" onSubmit=${go}>
        ${err && html`<${Alert} kind="error">${err}<//>`}
        <div className="field"><label htmlFor="pw">Password for ${sel.name}</label>
          <div className="signin-row">
            <input id="pw" ref=${pwRef} className="input" type="password" value=${pw} onChange=${e => setPw(e.target.value)} placeholder="Enter password" autoComplete="current-password" />
            <button className="btn primary" type="submit" disabled=${busy || !pw}>${busy ? html`<${Spinner} />` : html`Continue<${Icon} name="arrow" size=${16} />`}</button>
          </div></div>
        ${hint && html`<p className="hint">Demo environment — password is <code>${hint}</code> (prefilled).</p>`}
      </form>`}`}
    </div></section>
  </div>`;
}

// ============================================================
// Home  --  persona-aware dashboard
// ============================================================
const KPI_DEF = {
  totalCalls: { label: 'Registered data calls', icon: 'db', color: '--accent', soft: '--accent-soft', sub: () => 'across all registries' },
  passRate: { label: 'Test pass rate', icon: 'shield', color: '--blue', soft: '--blue-soft', suffix: '%', sub: () => 'of tested calls' },
  pendingReviews: { label: 'Awaiting review', icon: 'clock', color: '--amber', soft: '--amber-soft', sub: () => 'needs IT attention' },
  totalRequests: { label: 'Requests logged', icon: 'inbox', color: '--violet', soft: '--violet-soft', sub: s => (s === 'all' ? 'from everyone' : 'from you') },
  approvedCount: { label: 'Approved', icon: 'check2', color: '--accent', soft: '--accent-soft', sub: () => 'became data calls' },
  rejectedCount: { label: 'Rejected', icon: 'x', color: '--red', soft: '--red-soft', sub: () => 'declined with notes' },
  myRequests: { label: 'Your requests', icon: 'inbox', color: '--violet', soft: '--violet-soft', sub: () => 'submitted by you' },
  myPending: { label: 'Your pending', icon: 'clock', color: '--amber', soft: '--amber-soft', sub: () => 'awaiting IT' },
  needsAttention: { label: 'Need attention', icon: 'alert', color: '--red', soft: '--red-soft', sub: () => 'failing or untested calls' },
  oldestPendingDays: { label: 'Oldest pending', icon: 'clock', color: '--amber', soft: '--amber-soft', suffix: ' d', sub: () => 'waiting on IT review' },
  avgReviewDays: { label: 'Avg review time', icon: 'trend', color: '--violet', soft: '--violet-soft', suffix: ' d', sub: () => 'request to decision' },
  reportCategories: { label: 'Report libraries', icon: 'chart', color: '--blue', soft: '--blue-soft', sub: () => 'ready-made prompts' },
};

function Kpi({ def, value, scope }) {
  return html`<div className="card kpi" style=${{ '--c': `var(${def.color})`, '--c-soft': `var(${def.soft})` }}>
    <div className="k-top"><span>${def.label}</span><span className="k-ico"><${Icon} name=${def.icon} size=${17} /></span></div>
    <div className="k-val">${value == null ? '—' : nf.format(value)}${value != null && def.suffix && html`<small>${def.suffix}</small>`}</div>
    <div className="k-sub">${def.sub(scope)}</div>
  </div>`;
}

function HomePage({ go }) {
  const { user } = useAuth();
  const [d, setD] = useState(null);
  const [suggest, setSuggest] = useState([]);
  const load = () => { setD(null); api('/api/dashboard').then(setD); };
  useEffect(load, []);
  useEffect(() => {
    if (user.permissions.includes('reports')) api('/api/reports/categories').then(r => setSuggest(Object.values(r.categories || {}).flatMap(a => a.slice(0, 2))));
  }, [user]);

  const hero = html`<div className="hello" style=${{ '--p': user.accent }}>
    <span className="eyebrow"><${Icon} name=${user.icon} size=${14} />${user.title}</span>
    <h1>${greeting()}, ${user.name}</h1><p>${user.tagline}</p></div>`;

  const actions = html`<div className="actions">${user.quickActions.map(a => {
    const pg = a.page; const ic = pg === 'Data Calls' ? 'list' : pg === 'Ask Data' ? 'chat' : pg === 'Governance' ? 'shield' : 'code';
    return html`<button key=${a.label} className="action" onClick=${() => go(pg, a)}>
      <span className="a-ico"><${Icon} name=${ic} /></span><b>${a.label}<${Icon} name="arrow" size=${16} /></b><span>${a.desc}</span></button>`;
  })}</div>`;

  if (!d) return html`<div>${hero}${actions}<div className="kpis">${user.kpis.map(k => html`<div key=${k} className="skeleton" style=${{ height: 118 }} />`)}</div></div>`;
  if (d.error || !d.metrics) return html`<div>${hero}${actions}<${Alert} kind="error">Couldn't load live figures: ${d.error || 'unexpected response'}
    <div style=${{ marginTop: 8 }}><button className="btn sm" onClick=${load}><${Icon} name="refresh" size=${14} />Retry</button></div><//></div>`;

  const sb = d.stateBreakdown || {};
  const health = [['TESTED_PASS', 'Passing', '#54755a'], ['TESTED_FAIL', 'Failing', '#d1604a'], ['NA', 'Untested', '#b4c0b8']].map(([k, l, c]) => ({ k, name: l, value: sb[k] || 0, color: c }));
  const healthTotal = health.reduce((s, h) => s + h.value, 0);
  const rs = d.requestStatus || {};
  const pipeline = [['pending', 'Pending', 'var(--amber)'], ['approved', 'Approved', 'var(--accent)'], ['rejected', 'Rejected', 'var(--red)']];
  const pipeTotal = Object.values(rs).reduce((s, v) => s + v, 0);
  const canSeeCalls = user.permissions.includes('data_calls');

  return html`<div>
    ${hero}${actions}
    ${d.warnings?.length > 0 && html`<div style=${{ marginBottom: 16 }}><${Alert} kind="warn">Some figures are partial: ${d.warnings.join(' · ')}<//></div>`}
    <div className="kpis">${user.kpis.map(k => html`<${Kpi} key=${k} def=${KPI_DEF[k]} value=${d.metrics[k]} scope=${d.scope} />`)}</div>
    <div className="grid-2">
      <div className="card pad"><div className="card-title">Data call health<small>${plural(healthTotal, 'call')}</small></div>
        ${healthTotal === 0 ? html`<${Empty} icon="db" title="No data calls yet" />` : html`<div className="donut-row">
          <div style=${{ height: 170 }}><${ResponsiveContainer} width="100%" height="100%"><${PieChart}>
            <${Pie} data=${health} dataKey="value" innerRadius="62%" outerRadius="95%" paddingAngle=${3} stroke="var(--surface)" strokeWidth=${2}>${health.map(h => html`<${Cell} key=${h.k} fill=${h.color} />`)}<//><//><//></div>
          <div className="legend">${health.map(h => html`<div key=${h.k}><i style=${{ background: h.color }} />${h.name}<b>${h.value}</b></div>`)}</div></div>`}
      </div>
      ${canSeeCalls ? html`<div className="card pad"><div className="card-title">Request pipeline<small>${d.scope === 'all' ? 'everyone' : 'yours'}</small></div>
        ${pipeTotal === 0 ? html`<${Empty} icon="inbox" title="No requests yet">${user.permissions.includes('it_review') ? 'New requests will show up here.' : 'Request a data call and track it here.'}<//>` : html`<div style=${{ display: 'grid', gap: 16 }}>${pipeline.map(([k, l, c]) => html`<div key=${k}>
          <div style=${{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}><span>${l}</span><b>${rs[k] || 0}</b></div>
          <div className="meter"><i style=${{ width: `${100 * (rs[k] || 0) / pipeTotal}%`, background: c }} /></div></div>`)}</div>`}
      </div>` : html`<div className="card pad"><div className="card-title">Try asking</div>
        <div className="list">${suggest.slice(0, 5).map(s => html`<div key=${s} className="list-item"><div className="li-main"><b style=${{ whiteSpace: 'normal' }}>${s}</b></div>
          <button className="btn sm" onClick=${() => go('Ask Data', { prompt: s })}>Ask<${Icon} name="arrow" size=${14} /></button></div>`)}</div></div>`}
    </div>
    ${canSeeCalls && html`<div className="grid-2">
      <div className="card pad"><div className="card-title">Newest data calls<button className="btn ghost sm" onClick=${() => go('Data Calls')}>View all</button></div>
        ${d.recentCalls.length === 0 ? html`<${Empty} icon="db" title="Nothing registered" />` : html`<div className="list">${d.recentCalls.map(c => html`<div key=${c.category + c.data_call_id} className="list-item">
          <div className="li-main"><b>${c.data_call_name}</b><span>${c.category}</span></div><${StatusBadge} status=${c.state} /></div>`)}</div>`}</div>
      <div className="card pad"><div className="card-title">Recent requests${user.permissions.includes('it_review') && html`<button className="btn ghost sm" onClick=${() => go('IT Review')}>Open queue</button>`}</div>
        ${d.recentRequests.length === 0 ? html`<${Empty} icon="inbox" title="No requests" />` : html`<div className="list">${d.recentRequests.map(r => html`<div key=${r.id} className="list-item">
          <div className="li-main"><b>${r.request_description}</b><span>${fmtDate(r.requested_at)}${d.scope === 'all' && r.requested_by ? ` · ${r.requested_by}` : ''}</span></div><${StatusBadge} status=${r.status} /></div>`)}</div>`}</div>
    </div>`}
  </div>`;
}

// ============================================================
// Data Calls
// ============================================================
const STATE_FILTERS = [['All', 'All'], ['TESTED_PASS', 'Passing'], ['TESTED_FAIL', 'Failing'], ['NA', 'Untested']];

function DateNote({ res }) {
  if (!res || res.error || !res.dateMode) return null;
  const [from, to] = res.period || [];
  const range = from && to ? `${fmtDate(from)} – ${fmtDate(to)}` : 'your range';
  if (res.dateMode === 'placeholders') return html`<${Alert} kind="ok">Ran for <b>${range}</b>. Date placeholders in the SQL file were filled in (${plural(res.replaced, 'place')}).<//>`;
  if (res.dateMode === 'year_filter') return html`<${Alert} kind="ok">Ran for <b>${range}</b>. The SQL file's year filter (like <code>YEAR(accident_date) &gt;= 2020</code>) was rewritten to that date range. Check the SQL tab.<//>`;
  if (res.dateMode === 'as_of') return html`<${Alert} kind="info">This SQL is relative to today (<code>CURRENT_DATE</code>), so it ran <b>as of ${fmtDate(to)}</b>: for example, “this quarter” means the quarter containing that date. Your start date isn't used. Check the SQL tab.<//>`;
  if (res.dateMode === 'literals') return html`<${Alert} kind="info">This SQL file hard-codes its dates, so ${plural(res.replaced, 'date literal')} were replaced with <b>${range}</b> (earliest → from, latest → to). Check the SQL tab.<//>`;
  return html`<${Alert} kind="warn"><b>Your date range was not applied.</b> This SQL file has no date placeholder (like <code>:from_date</code> / <code>:to_date</code>), so it ran exactly as written.<//>`;
}

function RunPanel({ call, category, onClose }) {
  const [from, setFrom] = useState('2020-01-01');
  const [to, setTo] = useState(new Date().toISOString().split('T')[0]);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = async (refresh = false) => {
    setBusy(true); setRes(null);
    setRes(await post('/api/data-calls/execute', { category, dataCallId: Number(call.data_call_id), fromDate: from, toDate: to, refresh }));
    setBusy(false);
  };
  return html`<${Drawer} title=${call.data_call_name} subtitle=${call.description} onClose=${onClose}>
    <div className="card pad" style=${{ display: 'grid', gap: 14 }}>
      <div className="row2">
        <div className="field"><label>From</label><input className="input" type="date" value=${from} max=${to} onChange=${e => setFrom(e.target.value)} /></div>
        <div className="field"><label>To</label><input className="input" type="date" value=${to} min=${from} onChange=${e => setTo(e.target.value)} /></div>
      </div>
      <button className="btn primary" onClick=${() => run(!!res)} disabled=${busy}>${busy ? html`<${Spinner} />Running on SQL warehouse…` : html`<${Icon} name="play" size=${14} />${res ? 'Run again' : 'Run data call'}`}</button>
    </div>
    ${busy && html`<div className="skeleton" style=${{ height: 220 }} />`}
    ${res && html`<div style=${{ display: 'grid', gap: 12 }}>
      <${DateNote} res=${res} />
      <div className="card pad"><${ResultView} res=${res} name=${call.data_call_name} onRefresh=${() => run(true)} />
        ${res.source && html`<p className="hint" style=${{ marginTop: 12 }}>Source: <span className="mono">${res.source}</span></p>`}</div>
    </div>`}
  <//>`;
}

function RequestModal({ onClose, cats = [], initialCat = '' }) {
  const [desc, setDesc] = useState('');
  const [cat, setCat] = useState(initialCat || cats[0] || '');
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState(null);
  const submit = async e => {
    e.preventDefault(); setBusy(true);
    setRes(await post('/api/data-calls/request', { description: desc.trim(), category: cat || null }));
    setBusy(false);
  };
  return html`<${Drawer} modal title="Request a new data call" subtitle="Describe the data you need. We'll check the registry for a close match before sending it to IT." onClose=${onClose}>
    ${!res || res.error ? html`<form onSubmit=${submit} style=${{ display: 'grid', gap: 14 }}>
      ${res?.error && html`<${Alert} kind="error">${res.error}<//>`}
      ${cats.length > 1 && html`<div className="field"><label>Registry</label><${Segmented} value=${cat} onChange=${setCat} options=${cats} /></div>`}
      <div className="field"><label>What do you need?</label>
        <textarea className="textarea" rows="5" value=${desc} onChange=${e => setDesc(e.target.value)} placeholder="e.g. Quarterly claim counts by state, split by open vs. closed status, for the last three years" autoFocus /></div>
      <button className="btn primary" disabled=${busy || desc.trim().length < 8}>${busy ? html`<${Spinner} />Checking registry…` : 'Submit request'}</button>
    </form>` : res.isNew ? html`<div style=${{ display: 'grid', gap: 14 }}>
      <${Alert} kind="ok"><b>Request sent to IT.</b> Nothing in the registry matched closely (best match ${Math.round(res.similarityScore * 100)}%). Track it under <b>My requests</b>.<//>
      <button className="btn primary" onClick=${onClose}>Done</button></div>` : html`<div style=${{ display: 'grid', gap: 14 }}>
      <${Alert} kind="warn"><b>A similar data call already exists.</b> Your request was still logged for IT to review.<//>
      <div className="card pad match"><b>${res.matchedName}</b>
        <div className="meter"><i style=${{ width: `${Math.round(res.similarityScore * 100)}%` }} /></div>
        <span className="hint">${Math.round(res.similarityScore * 100)}% semantic match</span></div>
      <button className="btn primary" onClick=${onClose}>Done</button></div>`}
  <//>`;
}

function DataCallsPage({ opts = {} }) {
  const [cats, setCats] = useState([]);
  const [cat, setCat] = useState('');
  const [state, setState] = useState('All');
  const [search, setSearch] = useState('');
  const q = useDebounced(search);
  const [calls, setCalls] = useState(null);
  const [view, setView] = useState('registry');
  const [run, setRun] = useState(null);
  const [asking, setAsking] = useState(opts.tab === 'request');
  const [mine, setMine] = useState(null);

  useEffect(() => { api('/api/data-calls/categories').then(d => { if (d.categories) { setCats(d.categories); setCat(d.categories[0]); } }); }, []);
  useEffect(() => {
    if (!cat) return undefined;
    let live = true; setCalls(null);
    api(`/api/data-calls?category=${encodeURIComponent(cat)}&state=${state}&search=${encodeURIComponent(q)}`).then(d => live && setCalls(d));
    return () => { live = false; };
  }, [cat, state, q]);
  const loadMine = () => api('/api/data-calls/my-requests').then(setMine);
  useEffect(() => { if (view === 'mine') loadMine(); }, [view, asking]);

  const records = calls?.records || [];
  return html`<div>
    <${PageHead} title="Data calls" subtitle="Browse the regulatory data-call registry, run any call for a chosen period, or ask IT for a new one.">
      <button className="btn primary" onClick=${() => setAsking(true)}><${Icon} name="plus" size=${16} />Request new call</button>
    <//>
    <div className="toolbar">
      <${Segmented} value=${view} onChange=${setView} options=${[['registry', 'Registry'], ['mine', 'My requests']]} />
      ${view === 'registry' && cats.length > 1 && html`<${Segmented} value=${cat} onChange=${setCat} options=${cats} />`}
      ${view === 'registry' && cats.length === 1 && html`<span className="badge info plain">${cats[0]} registry</span>`}
    </div>

    ${view === 'registry' ? html`<div>
      <div className="toolbar">
        <div className="input-icon grow"><${Icon} name="search" size=${16} /><input className="input" value=${search} onChange=${e => setSearch(e.target.value)} placeholder="Search data calls by name…" /></div>
        <div style=${{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>${STATE_FILTERS.map(([v, l]) => html`<button key=${v} className=${'chip' + (state === v ? ' on' : '')} onClick=${() => setState(v)}>${l}</button>`)}</div>
      </div>
      ${!calls ? html`<${Skeletons} n=${6} h=${150} />` : calls.error ? html`<${Alert} kind="error">${calls.error}<//>`
        : records.length === 0 ? html`<div className="card"><${Empty} icon="search" title="No data calls match">Try a different search term or clear the status filter.<//></div>`
        : html`<p className="hint" style=${{ marginBottom: 12 }}>${plural(records.length, 'data call')}</p>
          <div className="call-grid">${records.map((c, i) => html`<article key=${c.data_call_id} className="card call" style=${{ animationDelay: `${Math.min(i, 12) * 25}ms` }}>
            <div className="c-top"><h3>${c.data_call_name}</h3><${StatusBadge} status=${c.state} /></div>
            <p>${c.description || 'No description provided.'}</p>
            <div className="c-foot"><span className="file" title=${c.file_name}>${c.file_name}</span>
              <button className="btn sm" onClick=${() => setRun(c)}><${Icon} name="play" size=${12} />Run</button></div>
          </article>`)}</div>`}
    </div>` : html`<div className="card pad">
      ${!mine ? html`<div className="skeleton" style=${{ height: 140 }} />` : mine.error ? html`<${Alert} kind="error">${mine.error}<//>`
        : mine.records.length === 0 ? html`<${Empty} title="No requests yet">Can't find the data call you need? Request a new one and track it here.<//>`
        : html`<div className="list">${mine.records.map(r => html`<div key=${r.id} className="list-item" style=${{ alignItems: 'flex-start' }}>
          <div className="li-main"><b style=${{ whiteSpace: 'normal' }}>${r.request_description}</b>
            <span style=${{ whiteSpace: 'normal' }}>Submitted ${fmtDate(r.requested_at)}${r.matched_data_call ? ` · similar to “${r.matched_data_call}”` : ''}${r.review_notes ? ` · IT note: ${r.review_notes}` : ''}</span></div>
          <${StatusBadge} status=${r.status} /></div>`)}</div>`}
    </div>`}

    ${run && html`<${RunPanel} call=${run} category=${cat} onClose=${() => setRun(null)} />`}
    ${asking && html`<${RequestModal} onClose=${() => setAsking(false)} cats=${cats} initialCat=${cat} />`}
  </div>`;
}

// ============================================================
// Ask Data  --  conversational analytics
// ============================================================
function AskDataPage({ opts = {} }) {
  const [cats, setCats] = useState({});
  const [cat, setCat] = useState(opts.category || '');
  const [msgs, setMsgs] = useState([]);
  const [convId, setConvId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState('');
  const endRef = useRef(null);
  const sent = useRef(false);
  const hist = useRef([]);  // earlier questions in this conversation; lets the server cache follow-ups

  const send = useCallback(async (prompt, cid, refresh = false, history = hist.current) => {
    const p = prompt.trim(); if (!p) return;
    const before = [...history];
    setMsgs(m => [...m, { role: 'user', text: p }]); setText(''); setBusy(true);
    const res = await post('/api/reports/generate', { prompt: p, conversationId: cid ?? null, refresh, history: before });
    if (res.conversation_id) setConvId(res.conversation_id);
    if (!res.error && history === hist.current) hist.current = [...before, p];
    setMsgs(m => [...m, { role: 'bot', res, q: p, before }]); setBusy(false);
  }, []);

  useEffect(() => {
    api('/api/reports/categories').then(d => { const c = d.categories || {}; setCats(c); setCat(x => x || Object.keys(c)[0] || ''); });
  }, []);
  useEffect(() => { if (opts.prompt && !sent.current) { sent.current = true; send(opts.prompt); } }, [opts.prompt, send]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [msgs, busy]);

  const reset = () => { setMsgs([]); setConvId(null); setText(''); hist.current = []; };
  const onKey = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (!busy) send(text, convId); } };

  return html`<div className="page chat-page">
    <${PageHead} title="Ask data" subtitle="Plain-English questions, answered by Databricks Genie with charts, tables and the SQL behind them.">
      ${msgs.length > 0 && html`<button className="btn" onClick=${reset}><${Icon} name="plus" size=${16} />New conversation</button>`}
    <//>
    <div className="chat-scroll">
      ${msgs.length === 0 && html`<div className="welcome">
        <div><div className="orb"><${Icon} name="spark" size=${26} /></div></div>
        <div><h1>What would you like to know?</h1><p>Start with a ready-made question, or type your own below. Follow-ups keep the context of the conversation.</p></div>
        <div style=${{ display: 'grid', gap: 12 }}>
          <${Segmented} value=${cat} onChange=${setCat} options=${Object.keys(cats)} />
          <div className="suggest">${(cats[cat] || []).map(s => html`<button key=${s} onClick=${() => send(s, convId)}><${Icon} name="spark" size=${15} /><span>${s}</span></button>`)}</div>
        </div>
      </div>`}
      ${msgs.map((m, i) => m.role === 'user' ? html`<div key=${i} className="msg-user">${m.text}</div>` : html`<div key=${i} className="msg-bot">
        <div className="bot-av"><${Icon} name="spark" size=${17} /></div>
        <div className="card bubble"><${ResultView} res=${m.res} name=${m.q} onRefresh=${() => send(m.q, m.before.length ? convId : null, true, m.before)} />
          ${!m.res.error && !m.res.text && !m.res.columns && html`<span className="hint">Genie didn't return anything for that. Try rephrasing.</span>`}</div></div>`)}
      ${busy && html`<div className="msg-bot"><div className="bot-av"><${Icon} name="spark" size=${17} /></div>
        <div className="card bubble"><span className="typing"><i></i><i></i><i></i></span> <span className="hint" style=${{ marginLeft: 8 }}>Genie is analysing your data…</span></div></div>`}
      <div ref=${endRef} />
    </div>
    <div className="composer-wrap"><form className="composer" onSubmit=${e => { e.preventDefault(); if (!busy) send(text, convId); }}>
      <textarea rows="1" value=${text} onChange=${e => { setText(e.target.value); e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px'; }} onKeyDown=${onKey} placeholder=${msgs.length ? 'Ask a follow-up…' : 'Ask anything about claims, costs or compliance…'} />
      <button className="send" type="submit" disabled=${busy || !text.trim()} aria-label="Send"><${Icon} name="send" size=${18} /></button>
    </form></div>
  </div>`;
}

// ============================================================
// Governance  --  Admin control tower
// ============================================================
const SC_DEF = {
  passRate: { label: 'Test pass rate', icon: 'shield', color: '--accent', soft: '--accent-soft', suffix: '%', sub: () => 'of tested calls' },
  coverage: { label: 'Test coverage', icon: 'check2', color: '--blue', soft: '--blue-soft', suffix: '%', sub: () => 'calls with a test result' },
  failing: { label: 'Failing', icon: 'alert', color: '--red', soft: '--red-soft', sub: () => 'must be fixed or retired' },
  untested: { label: 'Untested', icon: 'clock', color: '--amber', soft: '--amber-soft', sub: () => 'no test result yet' },
};

function GovernancePage({ go }) {
  const toast = useToast();
  const [d, setD] = useState(null);
  const { user } = useAuth();
  const [busyId, setBusyId] = useState(null);
  const [reg, setReg] = useState('');
  const load = () => { setD(null); api(`/api/governance${reg ? `?category=${encodeURIComponent(reg)}` : ''}`).then(setD); };
  useEffect(load, [reg]);

  const signOff = async (c, state) => {
    setBusyId(c.data_call_id);
    const r = await post('/api/governance/set-state', { category: c.category, dataCallId: Number(c.data_call_id), state });
    setBusyId(null);
    if (r.success) { toast(`“${c.data_call_name}” marked ${state === 'TESTED_PASS' ? 'passing' : 'failing'}`); load(); } else toast(r.error || 'Update failed', 'error');
  };

  const tabs = user.registries.length > 1 ? html`<div className="toolbar"><${Segmented} value=${reg} onChange=${setReg} options=${[['', 'All registries'], ...user.registries.map(r => [r, r])]} /></div>` : null;
  if (!d) return html`<div><${PageHead} title="Governance" subtitle="Loading registry health…" />${tabs}<${Skeletons} n=${4} h=${118} /></div>`;
  if (d.error) return html`<div><${PageHead} title="Governance" /><${Alert} kind="error">${d.error}<//></div>`;

  const s = d.scorecard;
  const maxDemand = Math.max(1, ...d.demand.map(x => x.requests));
  return html`<div>
    <${PageHead} title="Governance" subtitle="Registry control tower — what needs retesting, what is waiting on IT, and what people keep asking for.">
      <button className="btn" onClick=${load}><${Icon} name="refresh" size=${15} />Refresh</button>
    <//>
    ${tabs}
    ${d.warnings?.length > 0 && html`<div style=${{ marginBottom: 16 }}><${Alert} kind="warn">Some figures are partial: ${d.warnings.join(' · ')}<//></div>`}
    <div className="kpis">${Object.keys(SC_DEF).map(k => html`<${Kpi} key=${k} def=${SC_DEF[k]} value=${s[k]} />`)}</div>

    <div className="grid-2">
      <div className="card pad"><div className="card-title">Retest queue<small>${plural(d.attention.length, 'call')} need sign-off</small></div>
        ${d.attention.length === 0 ? html`<${Empty} icon="check2" title="Everything is tested and passing" />` : html`<div className="list scroll-list">${d.attention.map(c => html`<div key=${c.category + c.data_call_id} className="list-item">
          <div className="li-main"><b>${c.data_call_name}</b><span>${c.category} · ${c.file_name}</span></div>
          <${StatusBadge} status=${c.state} />
          <div className="mini-actions">
            <button className="btn sm" disabled=${busyId === c.data_call_id} title="Record a passing test" onClick=${() => signOff(c, 'TESTED_PASS')}><${Icon} name="check" size=${13} />Pass</button>
            <button className="btn sm danger" disabled=${busyId === c.data_call_id} title="Record a failing test" onClick=${() => signOff(c, 'TESTED_FAIL')}><${Icon} name="x" size=${13} />Fail</button>
          </div></div>`)}</div>`}
      </div>

      <div className="card pad"><div className="card-title">Review SLA<small>target ${d.slaDays} days · avg ${d.stats.avgReviewDays ?? '—'} d</small></div>
        ${d.pending.length === 0 ? html`<${Empty} icon="check2" title="No requests waiting on IT" />` : html`<div className="list scroll-list">${d.pending.map(r => html`<div key=${r.id} className="list-item">
          <div className="li-main"><b>${r.request_description}</b><span>${r.category || 'Compliance'} · ${r.requested_by} · ${fmtDate(r.requested_at)}</span></div>
          <span className=${'badge ' + (r.overdue ? 'bad' : 'warn')}>${r.ageDays == null ? '—' : `${Math.round(r.ageDays)} d`}${r.overdue ? ' overdue' : ''}</span></div>`)}</div>`}
      </div>
    </div>

    <div className="grid-2">
      <div className="card pad"><div className="card-title">Demand signals<small>existing calls people keep requesting</small></div>
        ${d.demand.length === 0 ? html`<${Empty} icon="trend" title="No demand data yet">Requests that resemble an existing call will show up here, which is a hint it is hard to find or incomplete.<//>` : html`<div style=${{ display: 'grid', gap: 14 }}>${d.demand.map(x => html`<div key=${x.name}>
          <div style=${{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6, gap: 10 }}><span>${x.name}</span><b>${plural(x.requests, 'request')}</b></div>
          <div className="meter"><i style=${{ width: `${100 * x.requests / maxDemand}%` }} /></div></div>`)}</div>`}
      </div>

      <div className="card pad"><div className="card-title">Audit trail<small>latest IT decisions</small></div>
        ${d.audit.length === 0 ? html`<${Empty} icon="inbox" title="No decisions yet" />` : html`<div className="list scroll-list">${d.audit.map(r => html`<div key=${r.id} className="list-item">
          <div className="li-main"><b>${r.request_description}</b><span>${r.reviewed_by || '—'} · ${fmtDate(r.reviewed_at)}${r.turnaroundDays != null ? ` · ${r.turnaroundDays} d turnaround` : ''}</span></div>
          <${StatusBadge} status=${r.status} /></div>`)}</div>`}
      </div>
    </div>
  </div>`;
}

// ============================================================
// IT Review
// ============================================================
function SqlCheck({ chk }) {
  if (!chk) return null;
  if (chk.error && chk.ok === undefined) return null;
  if (!chk.ok) return html`<${Alert} kind="error">${chk.error}<//>`;
  const m = {
    placeholders: ['ok', 'Uses :from_date / :to_date, so the date range users pick will apply exactly.'],
    year_filter: ['ok', 'Filters by YEAR(...). The date range users pick will be rewritten onto that column.'],
    literals: ['info', 'Has fixed dates. The earliest and latest will be replaced by the date range users pick.'],
    as_of: ['info', 'Relative to today (CURRENT_DATE). It will run as of the end date users pick; their start date is not used.'],
    none: ['warn', 'No date filter found, so the date range users pick will be ignored. Tip: filter your main date column with :from_date and :to_date.'],
  }[chk.dateMode];
  return m ? html`<${Alert} kind=${m[0]}>${m[1]}<//>` : null;
}

function ReviewPanel({ req, onDone }) {
  const toast = useToast();
  const pending = String(req.status).toLowerCase() === 'pending';
  const [busy, setBusy] = useState('');
  const [name, setName] = useState('');
  const [cat, setCat] = useState(req.category || 'Compliance');
  const [state, setState] = useState('TESTED_PASS');
  const [sql, setSql] = useState('');
  const [notes, setNotes] = useState('');
  const g = useGenie('/api/it-review/generate-sql', r => { if (r.sql) setSql(r.sql); });
  const sqlQ = useDebounced(sql, 500);
  const [chk, setChk] = useState(null);
  useEffect(() => {
    if (!sqlQ.trim()) { setChk(null); return undefined; }
    let live = true;
    post('/api/it-review/check-sql', { sql: sqlQ }).then(r => live && setChk(r));
    return () => { live = false; };
  }, [sqlQ]);

  const generate = () => { g.reset(); g.send('Draft the SQL for this request', { description: req.request_description }, true); };
  const approve = async e => {
    e.preventDefault(); setBusy('approve');
    const r = await post('/api/it-review/approve', { requestId: Number(req.id), sqlQuery: sql, dataCallName: name.trim(), description: req.request_description, state, category: cat });
    setBusy('');
    if (r.success) { toast(`“${name.trim()}” is now in the registry`); onDone(); } else toast(r.error || 'Approval failed', 'error');
  };
  const reject = async e => {
    e.preventDefault(); setBusy('reject');
    const r = await post('/api/it-review/reject', { requestId: Number(req.id), notes });
    setBusy('');
    if (r.success) { toast('Request rejected'); onDone(); } else toast(r.error || 'Rejection failed', 'error');
  };

  return html`<div className="review">
    <div className="card pad">
      <div className="card-title">Request #${req.id}<${StatusBadge} status=${req.status} /></div>
      <p style=${{ fontSize: 15, lineHeight: 1.6, marginBottom: 16 }}>${req.request_description}</p>
      <div className="kv">
        <div><span>Requested by</span><b>${req.requested_by || '—'}</b></div>
        <div><span>Registry</span><b>${req.category || 'Compliance'}</b></div>
        <div><span>Submitted</span><b>${fmtDate(req.requested_at)}</b></div>
        <div><span>Closest existing call</span><b>${req.matched_data_call ? `${req.matched_data_call} (${Math.round(Number(req.similarity_score) * 100)}%)` : 'None — looks new'}</b></div>
        ${!pending && html`<div><span>Reviewed by</span><b>${req.reviewed_by || '—'} · ${fmtDate(req.reviewed_at)}</b></div>`}
      </div>
      ${!pending && req.review_notes && html`<div style=${{ marginTop: 14 }}><${Alert} kind="warn"><b>Reviewer notes:</b> ${req.review_notes}<//></div>`}
    </div>

    ${!pending && req.genie_sql && html`<div className="card pad"><div className="card-title">Approved SQL</div><pre className="sql">${req.genie_sql}</pre></div>`}

    ${pending && html`<div className="review"><div className="card pad" style=${{ display: 'grid', gap: 14 }}>
      <div className="card-title" style=${{ margin: 0 }}>Draft the query<button className="btn sm" onClick=${generate} disabled=${g.busy}>${g.busy ? html`<${Spinner} size=${14} />Asking Genie…` : html`<${Icon} name="spark" size=${14} />${g.msgs.length ? 'Regenerate' : 'Generate with Genie'}`}</button></div>
      <${GenieThread} g=${g} name=${`request_${req.id}`} onReply=${t => g.send(t, { description: t })} placeholder="Answer Genie, or refine the query (e.g. group by quarter of accident date)…" />
    </div>

    <div className="decision">
      <form className="card pad" onSubmit=${approve} style=${{ display: 'grid', gap: 14, alignContent: 'start' }}>
        <div className="card-title" style=${{ margin: 0 }}>Approve & register</div>
        <div className="field"><label>Data call name</label><input className="input" value=${name} onChange=${e => setName(e.target.value)} required placeholder="e.g. Quarterly Claims by State" /></div>
        <div className="row2">
          <div className="field"><label>Registry</label><select className="select" value=${cat} onChange=${e => setCat(e.target.value)}><option>Compliance</option><option>Financial Reporting</option></select></div>
          <div className="field"><label>Test status</label><select className="select" value=${state} onChange=${e => setState(e.target.value)}><option value="TESTED_PASS">Passing</option><option value="TESTED_FAIL">Failing</option><option value="NA">Untested</option></select></div>
        </div>
        <div className="field"><label>SQL</label><textarea className="textarea mono" rows="6" value=${sql} onChange=${e => setSql(e.target.value)} required placeholder="Generate with Genie, or paste your own" style=${{ fontSize: 12.5 }} /></div>
        <${SqlCheck} chk=${chk} />
        <button className="btn primary" disabled=${!!busy || !name.trim() || !sql.trim() || chk?.ok === false}>${busy === 'approve' ? html`<${Spinner} />Registering…` : html`<${Icon} name="check" size=${16} />Approve`}</button>
      </form>
      <form className="card pad" onSubmit=${reject} style=${{ display: 'grid', gap: 14, alignContent: 'start' }}>
        <div className="card-title" style=${{ margin: 0 }}>Reject</div>
        <div className="field"><label>Reason (shown to the requester)</label><textarea className="textarea" rows="5" value=${notes} onChange=${e => setNotes(e.target.value)} placeholder="Explain what's missing or where to find existing data" /></div>
        <button className="btn danger" disabled=${!!busy || !notes.trim()}>${busy === 'reject' ? html`<${Spinner} />Rejecting…` : 'Reject request'}</button>
      </form>
    </div></div>`}
  </div>`;
}

function SyncCard() {
  const toast = useToast();
  const [items, setItems] = useState(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState([]);
  const load = useCallback(() => api('/api/it-review/unsynced').then(d => setItems(d.error ? { error: d.error } : d.items)), []);
  useEffect(() => { load(); }, [load]);

  const sync = async () => {
    setBusy(true); setFailed([]);
    const r = await post('/api/it-review/sync', {});
    setBusy(false);
    if (r.error) { toast(r.error, 'error'); return; }
    if (r.synced) toast(`Synced ${plural(r.synced, 'data call')} to the registry`);
    setFailed(r.results.filter(x => !x.ok));
    load();
  };

  if (!items) return null;
  if (items.error) return html`<div style=${{ marginBottom: 16 }}><${Alert} kind="warn">Couldn't check registry sync: ${items.error}<//></div>`;
  if (items.length === 0 && failed.length === 0) return html`<div className="toolbar"><span className="badge good">Registry in sync — every data call has a SQL file</span></div>`;
  const ready = items.filter(i => i.hasSql);
  return html`<div className="card pad sync-card">
    <div className="card-title" style=${{ marginBottom: 8 }}>Sync to registry<small>${plural(items.length, 'data call')} without a SQL file</small></div>
    <p className="hint" style=${{ marginBottom: 12 }}>These were approved in IT review, so their SQL only lives in the request log. Syncing saves each one as a <span className="mono">.sql</span> file next to the other registry files and links it in the registry.</p>
    <div className="list">${items.map(i => html`<div key=${i.category + i.dataCallId} className="list-item">
      <div className="li-main"><b>${i.name}</b><span>${i.category} · currently <span className="mono">${i.fileName}</span></span></div>
      ${i.hasSql ? html`<span className="badge info plain">Ready</span>` : html`<span className="badge bad plain">No SQL found</span>`}</div>`)}</div>
    ${failed.map(f => html`<div key=${f.dataCallId} style=${{ marginTop: 10 }}><${Alert} kind="error"><b>${f.name}:</b> ${f.error}<//></div>`)}
    <div style=${{ marginTop: 14 }}><button className="btn primary" onClick=${sync} disabled=${busy || ready.length === 0}>${busy ? html`<${Spinner} />Syncing…` : html`<${Icon} name="refresh" size=${15} />Sync ${ready.length} to registry`}</button></div>
  </div>`;
}

function ITReviewPage() {
  const [status, setStatus] = useState('pending');
  const [data, setData] = useState(null);
  const [selId, setSelId] = useState(null);
  const load = useCallback(() => { setData(null); api(`/api/it-review?status=${status}`).then(setData); }, [status]);
  useEffect(load, [load]);
  useEffect(() => setSelId(null), [status]);

  const records = data?.records || [];
  const sel = records.find(r => String(r.id) === String(selId)) || records[0];

  return html`<div>
    <${PageHead} title="IT review queue" subtitle="Turn requests into registered data calls — draft the SQL with Genie, test it, then approve or send it back with notes.">
      <button className="btn" onClick=${load}><${Icon} name="refresh" size=${15} />Refresh</button>
    <//>
    <${SyncCard} />
    <div className="toolbar"><${Segmented} value=${status} onChange=${setStatus} options=${[['pending', 'Pending'], ['approved', 'Approved'], ['rejected', 'Rejected'], ['All', 'All']]} /></div>
    ${!data ? html`<${Skeletons} n=${3} h=${100} />` : data.error ? html`<${Alert} kind="error">${data.error}<//>`
      : records.length === 0 ? html`<div className="card"><${Empty} icon="check2" title=${status === 'pending' ? 'Queue is clear' : 'Nothing here'}>${status === 'pending' ? 'No requests are waiting for review.' : 'No requests with this status.'}<//></div>`
      : html`<div className="split">
        <div className="queue">${records.map(r => html`<button key=${r.id} className=${'q-item' + (sel && String(sel.id) === String(r.id) ? ' on' : '')} onClick=${() => setSelId(r.id)}>
          <div className="q-top"><span>#${r.id} · ${r.requested_by || 'unknown'}</span><${StatusBadge} status=${r.status} /></div>
          <p>${r.request_description}</p>
          <div className="q-top"><span>${fmtDate(r.requested_at)}</span>${r.is_new_request === true || r.is_new_request === 'true' ? html`<span className="badge info plain">New</span>` : html`<span className="badge plain">Similar exists</span>`}</div>
        </button>`)}</div>
        ${sel && html`<${ReviewPanel} key=${sel.id} req=${sel} onDone=${load} />`}
      </div>`}
  </div>`;
}

// ============================================================
// Shell
// ============================================================
const NAV = [
  { page: 'Home', label: 'Home', icon: 'home' },
  { page: 'Data Calls', label: 'Data calls', icon: 'list' },
  { page: 'Governance', label: 'Governance', icon: 'shield' },
  { page: 'Ask Data', label: 'Ask data', icon: 'chat' },
  { page: 'IT Review', label: 'IT review', icon: 'code' },
];

class ErrorBoundary extends React.Component {
  constructor(p) { super(p); this.state = { err: null }; }
  static getDerivedStateFromError(err) { return { err }; }
  componentDidCatch(err, info) { console.error('Page render failed:', err, info); }
  render() {
    return this.state.err
      ? html`<div className="page"><${Alert} kind="error">Something went wrong rendering this page: ${String(this.state.err.message || this.state.err)}<//></div>`
      : this.props.children;
  }
}

function Shell() {
  const { user, logout } = useAuth();
  const [view, setView] = useState({ page: 'Home', opts: {}, n: 0 });
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));

  const go = useCallback((page, opts = {}) => { setView(v => ({ page, opts, n: v.n + 1 })); setOpen(false); window.scrollTo(0, 0); }, []);
  const flip = () => {
    const t = theme === 'dark' ? 'light' : 'dark';
    setTheme(t); document.documentElement.dataset.theme = t;
    try { localStorage.setItem('wc-theme', t); } catch (e) { /* ignore */ }
  };

  const allowed = NAV.filter(n => user.pages.includes(n.page));
  const page = user.pages.includes(view.page) ? view.page : 'Home';
  const key = `${page}-${view.n}`;
  const body = page === 'Home' ? html`<${HomePage} go=${go} />`
    : page === 'Data Calls' ? html`<${DataCallsPage} opts=${view.opts} />`
    : page === 'Governance' ? html`<${GovernancePage} go=${go} />`
    : page === 'Ask Data' ? html`<${AskDataPage} opts=${view.opts} />`
    : html`<${ITReviewPage} />`;

  return html`<div className="shell">
    <div className=${'scrim' + (open ? ' show' : '')} onClick=${() => setOpen(false)} />
    <aside className=${'side' + (open ? ' open' : '')}>
      <div className="brand"><${Logo} /><div><b>Claimsight</b><span>Talk to Data</span></div></div>
      <div className="nav-label">Workspace</div>
      <nav className="nav">${allowed.map(n => html`<button key=${n.page} className=${page === n.page ? 'on' : ''} onClick=${() => go(n.page)}><${Icon} name=${n.icon} size=${19} />${n.label}</button>`)}</nav>
      <div className="side-foot">
        <div className="me"><div className="avatar" style=${{ '--p': user.accent }}><${Icon} name=${user.icon} size=${19} /></div><div><b>${user.name}</b><span>${user.title}</span></div></div>
        <div className="side-actions">
          <button onClick=${flip} aria-label="Toggle theme"><${Icon} name=${theme === 'dark' ? 'sun' : 'moon'} size=${16} />${theme === 'dark' ? 'Light' : 'Dark'}</button>
          <button onClick=${logout}><${Icon} name="logout" size=${16} />Sign out</button>
        </div>
      </div>
    </aside>
    <div className="main">
      <div className="topbar"><button className="icon-btn" onClick=${() => setOpen(true)} aria-label="Menu"><${Icon} name="menu" /></button>
        <div className="brand" style=${{ color: 'var(--ink)' }}><b>${NAV.find(n => n.page === page)?.label}</b></div></div>
      <${ErrorBoundary} key=${key}>${page === 'Ask Data' ? body : html`<main className="page">${body}</main>`}<//>
    </div>
  </div>`;
}

function App() {
  return html`<${ToastProvider}><${AuthProvider}><${Gate} /><//><//>`;
}
function Gate() { const { user } = useAuth(); return user ? html`<${Shell} />` : html`<${LoginPage} />`; }

createRoot(document.getElementById('root')).render(html`<${App} />`);
