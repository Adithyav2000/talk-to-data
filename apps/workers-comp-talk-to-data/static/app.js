// ============================================================
// Workers' Comp Talk-to-Data  --  React + MUI Frontend
// ============================================================
import React, { useState, useEffect, useCallback, createContext, useContext, useMemo } from 'react';
import { createRoot } from 'react-dom/client';
import htm from 'htm';
import {
  ThemeProvider, createTheme, CssBaseline,
  Box, Grid, Paper, Card, CardContent, Typography, Button, TextField,
  Drawer, List, ListItem, ListItemButton, ListItemText,
  Divider, Avatar, Chip,
  Tabs, Tab, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  CircularProgress, Alert, LinearProgress, Snackbar,
  Select, MenuItem, FormControl, InputLabel, Stack
} from '@mui/material';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const html = htm.bind(React.createElement);

// ============================================================
// Sage-Green Palette & MUI Theme
// ============================================================
const SAGE = '#5f7161', SAGE_MID = '#6d8b74', SAGE_LIGHT = '#8fac91';
const SAGE_PALE = '#d0e3cc', FOREST = '#3d5041', GOLD = '#c9a84c';
const CORAL = '#d9735b', SKY = '#6ba3be';
const COLORS = [SAGE_MID, GOLD, SKY, CORAL, SAGE_LIGHT, '#b08d57', '#7fb5c9', SAGE, SAGE_PALE, FOREST];

const theme = createTheme({
  palette: {
    primary: { main: SAGE, light: SAGE_LIGHT, dark: FOREST },
    secondary: { main: GOLD },
    background: { default: '#f7f8f4', paper: '#ffffff' },
    text: { primary: '#2d3a2e', secondary: '#5f6b5f' },
  },
  typography: { fontFamily: "'Inter', sans-serif" },
  shape: { borderRadius: 10 },
  components: {
    MuiButton: { styleOverrides: { containedPrimary: {
      background: `linear-gradient(135deg, ${SAGE}, ${SAGE_MID})`,
      boxShadow: '0 2px 8px rgba(95,113,97,.25)',
      '&:hover': { boxShadow: '0 4px 14px rgba(95,113,97,.35)' },
    } } },
    MuiCard: { styleOverrides: { root: { boxShadow: '0 1px 4px rgba(0,0,0,.06)' } } },
  },
});

// ============================================================
// Auth Context
// ============================================================
const AuthCtx = createContext(null);
const useAuth = () => useContext(AuthCtx);

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const login = useCallback(async (username, password) => {
    const r = await fetch('/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }).then(r => r.json());
    if (r.success) { setUser({ username: r.username, name: r.name, role: r.role }); return { ok: true }; }
    return { ok: false, error: r.error };
  }, []);
  const logout = useCallback(() => setUser(null), []);
  const val = useMemo(() => ({ user, login, logout }), [user, login, logout]);
  return html`<${AuthCtx.Provider} value=${val}>${children}</${AuthCtx.Provider}>`;
}

// ============================================================
// API helper
// ============================================================
const api = (url, opts) => fetch(url, { headers: { 'Content-Type': 'application/json' }, ...opts }).then(r => r.json());
const post = (url, body) => api(url, { method: 'POST', body: JSON.stringify(body) });

// ============================================================
// Small shared components
// ============================================================
function SectionHeader({ text }) {
  return html`<${Paper} sx=${{ background: `linear-gradient(135deg, ${SAGE} 0%, ${SAGE_MID} 100%)`, color: '#fff', p: '12px 20px', borderRadius: 2, mb: 3, fontWeight: 600, fontSize: '1.1rem' }}>${text}</${Paper}>`;
}

function MetricCard({ value, label, color }) {
  return html`<${Card} sx=${{ borderTop: `3px solid ${color}`, textAlign: 'center', py: 2, transition: 'transform .15s, box-shadow .15s', '&:hover': { transform: 'translateY(-2px)', boxShadow: '0 6px 20px rgba(0,0,0,.08)' } }}>
    <${CardContent}>
      <${Typography} variant="h4" sx=${{ color: FOREST, fontWeight: 700 }}>${value}</${Typography}>
      <${Typography} variant="caption" sx=${{ color: '#5f6b5f', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.04em' }}>${label}</${Typography}>
    </${CardContent}></${Card}>`;
}

function StatusChip({ status }) {
  const s = (status || '').toUpperCase();
  const m = { TESTED_PASS: ['PASS', 'success'], TESTED_FAIL: ['FAIL', 'error'], NA: ['N/A', 'default'], PENDING: ['PENDING', 'warning'], APPROVED: ['APPROVED', 'success'], REJECTED: ['REJECTED', 'error'] };
  const [label, color] = m[s] || [s || 'N/A', 'default'];
  return html`<${Chip} label=${label} color=${color} size="small" />`;
}

function DataTable({ columns = [], rows = [], max }) {
  if (!columns.length) return html`<${Alert} severity="info">No data available</${Alert}>`;
  const show = max ? rows.slice(0, max) : rows;
  return html`<${TableContainer} component=${Paper} sx=${{ maxHeight: 400, overflow: 'auto' }}>
    <${Table} size="small" stickyHeader>
      <${TableHead}><${TableRow}>
        ${columns.map((c, i) => html`<${TableCell} key=${i} sx=${{ fontWeight: 700, bgcolor: SAGE_PALE, color: FOREST }}>${c}</${TableCell}>`)}
      </${TableRow}></${TableHead}>
      <${TableBody}>
        ${show.map((r, ri) => html`<${TableRow} key=${ri} sx=${{ '&:hover': { bgcolor: '#f0f4ec' } }}>
          ${r.map((c, ci) => html`<${TableCell} key=${ci}>${c != null ? c : ''}</${TableCell}>`)}
        </${TableRow}>`)}
      </${TableBody}>
    </${Table}></${TableContainer}>`;
}

function downloadCSV(columns, rows, name) {
  const esc = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const csv = [columns.map(esc).join(','), ...rows.map(r => r.map(esc).join(','))].join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = (name || 'data') + '.csv'; a.click();
}

// ============================================================
// AutoChart  --  pick best chart type from data shape
// ============================================================
function AutoChart({ columns = [], rows = [], title = '' }) {
  if (!columns.length || !rows.length) return null;
  const data = rows.map(r => { const o = {}; columns.forEach((c, i) => { const v = r[i]; o[c] = v === '' || v == null ? null : isNaN(Number(v)) ? v : Number(v); }); return o; });
  const numCols = columns.filter(c => data.some(d => typeof d[c] === 'number'));
  const catCols = columns.filter(c => !numCols.includes(c));
  if (!numCols.length) return null;

  const hasTime = catCols.some(c => /date|month|year|quarter|week|day|time|period/i.test(c));
  const nCats = catCols[0] ? new Set(data.map(d => d[catCols[0]])).size : 0;
  const type = hasTime ? 'line' : nCats <= 6 && catCols.length ? 'pie' : 'bar';
  const xKey = catCols[0] || columns[0], yKey = numCols[0];

  return html`<${Box} sx=${{ width: '100%', height: 360, mt: 2 }}>
    <${ResponsiveContainer} width="100%" height="100%">
      ${type === 'bar' ? html`
        <${BarChart} data=${data}><${CartesianGrid} strokeDasharray="3 3" />
          <${XAxis} dataKey=${xKey} tick=${{ fontSize: 11 }} /><${YAxis} tick=${{ fontSize: 11 }} />
          <${Tooltip} /><${Legend} />
          ${numCols.slice(0, 3).map((c, i) => html`<${Bar} key=${c} dataKey=${c} fill=${COLORS[i]} radius=${[4, 4, 0, 0]} />`)}
        </${BarChart}>` : type === 'line' ? html`
        <${LineChart} data=${data}><${CartesianGrid} strokeDasharray="3 3" />
          <${XAxis} dataKey=${xKey} tick=${{ fontSize: 11 }} /><${YAxis} tick=${{ fontSize: 11 }} />
          <${Tooltip} /><${Legend} />
          ${numCols.slice(0, 3).map((c, i) => html`<${Line} key=${c} type="monotone" dataKey=${c} stroke=${COLORS[i]} strokeWidth=${2} dot=${{ r: 3 }} />`)}
        </${LineChart}>` : html`
        <${PieChart}><${Tooltip} /><${Legend} />
          <${Pie} data=${data.slice(0, 10)} dataKey=${yKey} nameKey=${xKey} cx="50%" cy="50%" innerRadius="30%" outerRadius="70%" label>
            ${data.slice(0, 10).map((_, i) => html`<${Cell} key=${i} fill=${COLORS[i % COLORS.length]} />`)}
          </${Pie}></${PieChart}>`}
    </${ResponsiveContainer}></${Box}>`;
}

// ============================================================
// LoginPage
// ============================================================
function LoginPage() {
  const { login } = useAuth();
  const [u, setU] = useState('compliance_admin');
  const [p, setP] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const users = ['compliance_admin', 'compliance_analyst', 'it_reviewer', 'leadership'];
  const go = async e => { e.preventDefault(); setBusy(true); setErr(''); const r = await login(u, p); setBusy(false); if (!r.ok) setErr(r.error || 'Login failed'); };
  return html`<${Box} sx=${{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#f7f8f4' }}>
    <${Box} sx=${{ width: 420, maxWidth: '90%' }}>
      <${Paper} sx=${{ background: `linear-gradient(135deg, ${SAGE} 0%, ${SAGE_MID} 50%, ${SAGE_LIGHT} 100%)`, p: 4, borderRadius: 3, textAlign: 'center', mb: 3, boxShadow: '0 4px 20px rgba(95,113,97,.25)' }}>
        <${Typography} variant="h4" sx=${{ color: '#fff', fontWeight: 700 }}>Workers' Compensation</${Typography}>
        <${Typography} variant="subtitle1" sx=${{ color: SAGE_PALE, mt: .5 }}>Talk-to-Data Platform</${Typography}>
        <${Typography} variant="body2" sx=${{ color: '#efead8', mt: .5 }}>Compliance \u00b7 Analytics \u00b7 Enterprise Reports</${Typography}>
      </${Paper}>
      <${Paper} sx=${{ p: 4, borderRadius: 3 }}>
        <${Typography} variant="h6" gutterBottom>Sign In</${Typography}>
        ${err && html`<${Alert} severity="error" sx=${{ mb: 2 }}>${err}</${Alert}>`}
        <form onSubmit=${go}>
          <${FormControl} fullWidth sx=${{ mb: 2 }}><${InputLabel}>Username</${InputLabel}>
            <${Select} value=${u} label="Username" onChange=${e => setU(e.target.value)}>
              ${users.map(x => html`<${MenuItem} key=${x} value=${x}>${x}</${MenuItem}>`)}
            </${Select}></${FormControl}>
          <${TextField} fullWidth label="Password" type="password" value=${p} onChange=${e => setP(e.target.value)} sx=${{ mb: 3 }} />
          <${Button} type="submit" variant="contained" fullWidth size="large" disabled=${busy}>
            ${busy ? html`<${CircularProgress} size=${24} color="inherit" />` : 'Login'}</${Button}>
        </form>
      </${Paper}>
    </${Box}></${Box}>`;
}

// ============================================================
// DashboardPage
// ============================================================
function DashboardPage() {
  const [d, setD] = useState(null);
  useEffect(() => { api('/api/dashboard').then(setD); }, []);
  if (!d) return html`<${Box} sx=${{ display: 'flex', justifyContent: 'center', py: 8 }}><${CircularProgress} /></${Box}>`;
  const m = d.metrics;
  const cards = [
    { value: m.totalCalls, label: 'Active Data Calls', color: SAGE_MID },
    { value: m.totalRequests, label: 'IT Requests', color: SAGE_LIGHT },
    { value: m.pendingReviews, label: 'Pending Reviews', color: GOLD },
    { value: m.reportCategories, label: 'Report Categories', color: CORAL },
  ];
  return html`<${Box}>
    <${SectionHeader} text="Dashboard Overview" />
    <${Grid} container spacing=${3} sx=${{ mb: 4 }}>
      ${cards.map((c, i) => html`<${Grid} item xs=${12} sm=${6} md=${3} key=${i}><${MetricCard} ...${c} /></${Grid}>`)}
    </${Grid}>
    <${Grid} container spacing=${3}>
      <${Grid} item xs=${12} md=${6}>
        <${Typography} variant="h6" gutterBottom>Recent Data Calls</${Typography}>
        <${DataTable} columns=${d.recentCalls.columns} rows=${d.recentCalls.rows} max=${5} />
      </${Grid}>
      <${Grid} item xs=${12} md=${6}>
        <${Typography} variant="h6" gutterBottom>Recent IT Requests</${Typography}>
        <${DataTable} columns=${d.recentRequests.columns} rows=${d.recentRequests.rows} max=${5} />
      </${Grid}>
    </${Grid}></${Box}>`;
}

// ============================================================
// DataCallsPage
// ============================================================
function DataCallsPage() {
  const { user } = useAuth();
  const [cat, setCat] = useState('Compliance');
  const [cats, setCats] = useState([]);
  const [state, setState] = useState('All');
  const [search, setSearch] = useState('');
  const [calls, setCalls] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState(0);
  const [sel, setSel] = useState('');
  const [fromDt, setFromDt] = useState('2020-01-01');
  const [toDt, setToDt] = useState(new Date().toISOString().split('T')[0]);
  const [execRes, setExecRes] = useState(null);
  const [execBusy, setExecBusy] = useState(false);
  const [reqDesc, setReqDesc] = useState('');
  const [reqRes, setReqRes] = useState(null);
  const [reqBusy, setReqBusy] = useState(false);
  const STATES = ['All', 'TESTED_PASS', 'TESTED_FAIL', 'NA'];

  useEffect(() => { api('/api/data-calls/categories').then(d => setCats(d.categories || [])); }, []);
  useEffect(() => {
    setLoading(true);
    api(`/api/data-calls?category=${encodeURIComponent(cat)}&state=${state}&search=${encodeURIComponent(search)}`)
      .then(d => { setCalls(d); setLoading(false); });
  }, [cat, state, search]);

  const doExec = async () => {
    if (!sel) return; setExecBusy(true);
    const row = (calls?.rows || []).find(r => r[1] === sel);
    const res = await post('/api/data-calls/execute', { description: row ? (row[3] || sel) : sel, fromDate: fromDt, toDate: toDt });
    setExecRes(res); setExecBusy(false);
  };
  const doReq = async e => {
    e.preventDefault(); if (!reqDesc) return; setReqBusy(true);
    const res = await post('/api/data-calls/request', { description: reqDesc, requestedBy: user?.username || 'unknown' });
    setReqRes(res); setReqBusy(false);
  };
  const names = (calls?.rows || []).map(r => r[1]);

  return html`<${Box}>
    <${SectionHeader} text="Data Calls Registry" />
    <${Stack} direction="row" spacing=${1} sx=${{ mb: 2 }}>
      ${(cats.length ? cats : ['Compliance', 'Financial Reporting']).map(c => html`<${Button} key=${c} variant=${cat === c ? 'contained' : 'outlined'} size="small" onClick=${() => setCat(c)}>${c}</${Button}>`)}
    </${Stack}>
    <${Tabs} value=${tab} onChange=${(_, v) => setTab(v)} sx=${{ mb: 2 }}><${Tab} label="Browse Data Calls" /><${Tab} label="Request New" /></${Tabs}>

    ${tab === 0 ? html`<${Box}>
      <${Grid} container spacing=${2} sx=${{ mb: 2 }}>
        <${Grid} item xs=${12} sm=${4}><${TextField} fullWidth size="small" label="Search by name" value=${search} onChange=${e => setSearch(e.target.value)} placeholder="e.g. COVID, aging, audit..." /></${Grid}>
        <${Grid} item xs=${6} sm=${2}><${FormControl} fullWidth size="small"><${InputLabel}>State</${InputLabel}><${Select} value=${state} label="State" onChange=${e => setState(e.target.value)}>${STATES.map(s => html`<${MenuItem} key=${s} value=${s}>${s}</${MenuItem}>`)}</${Select}></${FormControl}></${Grid}>
        <${Grid} item xs=${6} sm=${3}><${TextField} fullWidth size="small" type="date" label="From" value=${fromDt} onChange=${e => setFromDt(e.target.value)} InputLabelProps=${{ shrink: true }} /></${Grid}>
        <${Grid} item xs=${6} sm=${3}><${TextField} fullWidth size="small" type="date" label="To" value=${toDt} onChange=${e => setToDt(e.target.value)} InputLabelProps=${{ shrink: true }} /></${Grid}>
      </${Grid}>
      ${loading ? html`<${LinearProgress} />` : calls?.error ? html`<${Alert} severity="error">${calls.error}</${Alert}>` : html`<${Box}>
        <${Typography} variant="body2" color="text.secondary" sx=${{ mb: 1 }}>${(calls?.rows || []).length} data call(s) found</${Typography}>
        ${(calls?.rows || []).map((row, i) => html`<${Paper} key=${i} sx=${{ p: 2, mb: 1, borderLeft: `4px solid ${SAGE_MID}`, '&:hover': { boxShadow: '0 4px 14px rgba(0,0,0,.08)' } }}>
          <${Stack} direction="row" justifyContent="space-between" alignItems="center">
            <${Typography} sx=${{ fontWeight: 600, color: FOREST }}>${row[1]}</${Typography}>
            <${StatusChip} status=${row[4]} />
          </${Stack}>
          <${Typography} variant="body2" color="text.secondary" sx=${{ mt: .5 }}>${row[3]}</${Typography}>
          <${Typography} variant="caption" sx=${{ color: '#8a9a8c', fontFamily: 'monospace' }}>${row[2]}</${Typography}>
        </${Paper}>`)}
        ${names.length > 0 && html`<${Divider} sx=${{ my: 3 }} />
          <${Typography} variant="h6" gutterBottom>Execute a Data Call</${Typography}>
          <${Stack} direction="row" spacing=${2} alignItems="center" sx=${{ mb: 2 }}>
            <${FormControl} sx=${{ minWidth: 300 }} size="small"><${InputLabel}>Select</${InputLabel}><${Select} value=${sel} label="Select" onChange=${e => setSel(e.target.value)}>${names.map(n => html`<${MenuItem} key=${n} value=${n}>${n}</${MenuItem}>`)}</${Select}></${FormControl}>
            <${Button} variant="contained" onClick=${doExec} disabled=${execBusy || !sel}>${execBusy ? html`<${CircularProgress} size=${20} />` : 'Query'}</${Button}>
          </${Stack}>
          ${execRes?.error && html`<${Alert} severity="error" sx=${{ mb: 2 }}>${execRes.error}</${Alert}>`}
          ${execRes?.columns && html`<${Box}>
            <${Stack} direction="row" justifyContent="space-between" alignItems="center" sx=${{ mb: 1 }}>
              <${Typography} variant="body2" sx=${{ color: SAGE, fontWeight: 600 }}>${(execRes.rows||[]).length} rows</${Typography}>
              <${Button} size="small" onClick=${() => downloadCSV(execRes.columns, execRes.rows, sel)}>Download CSV</${Button}>
            </${Stack}>
            <${DataTable} columns=${execRes.columns} rows=${execRes.rows} />
            <${AutoChart} columns=${execRes.columns} rows=${execRes.rows} title=${sel} />
            ${execRes.sql && html`<${Paper} sx=${{ p: 2, mt: 2, bgcolor: '#f5f2e8' }}><${Typography} variant="caption" sx=${{ fontWeight: 600 }}>Generated SQL</${Typography}><pre style=${{ margin: 0, fontSize: '.8rem', overflow: 'auto' }}>${execRes.sql}</pre></${Paper}>`}
          </${Box}>`}
        `}
      </${Box}>`}
    </${Box}>` : html`<${Box}>
      <${Typography} variant="body2" color="text.secondary" sx=${{ mb: 2 }}>Describe the data you need. The system will semantically match your request against existing data calls.</${Typography}>
      <form onSubmit=${doReq}>
        <${TextField} fullWidth multiline rows=${4} label="Describe the data call you need" value=${reqDesc} onChange=${e => setReqDesc(e.target.value)} placeholder="e.g. I need quarterly claim counts..." sx=${{ mb: 2 }} />
        <${Button} type="submit" variant="contained" fullWidth disabled=${reqBusy || !reqDesc}>${reqBusy ? html`<${CircularProgress} size=${20} />` : 'Submit Request'}</${Button}>
      </form>
      ${reqRes && html`<${Alert} severity=${reqRes.isNew ? 'success' : 'warning'} sx=${{ mt: 2 }}>${reqRes.isNew ? 'New data call request created. IT team will review.' : `Similar call exists: ${reqRes.matchedName} (${(reqRes.similarityScore * 100).toFixed(0)}% match)`}</${Alert}>`}
    </${Box}>`}
  </${Box}>`;
}

// ============================================================
// ReportsPage
// ============================================================
function ReportsPage() {
  const [cats, setCats] = useState({});
  const [cat, setCat] = useState('');
  const [result, setResult] = useState(null);
  const [convId, setConvId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [active, setActive] = useState('');
  const [chat, setChat] = useState([]);
  const [fu, setFu] = useState('');
  const [fuBusy, setFuBusy] = useState(false);
  const [tab, setTab] = useState(0);

  useEffect(() => { api('/api/reports/categories').then(d => { setCats(d.categories || {}); const k = Object.keys(d.categories || {}); if (k.length) setCat(k[0]); }); }, []);

  const run = async prompt => {
    setActive(prompt); setBusy(true); setResult(null); setChat([]); setConvId(null); setTab(0);
    const res = await post('/api/reports/generate', { prompt });
    setResult(res); setConvId(res.conversation_id || null);
    setChat([{ role: 'user', text: prompt }, { role: 'genie', data: res }]);
    setBusy(false);
  };
  const sendFu = async e => {
    e.preventDefault(); if (!fu) return; setFuBusy(true);
    setChat(prev => [...prev, { role: 'user', text: fu }]);
    const res = await post('/api/reports/generate', { prompt: fu, conversationId: convId });
    setConvId(res.conversation_id || convId);
    setChat(prev => [...prev, { role: 'genie', data: res }]);
    setFu(''); setFuBusy(false);
  };
  const prompts = cats[cat] || [];

  return html`<${Box}>
    <${SectionHeader} text="Enterprise Reports \u2014 Leadership Analytics" />
    <${FormControl} sx=${{ minWidth: 250, mb: 2 }} size="small"><${InputLabel}>Category</${InputLabel}>
      <${Select} value=${cat} label="Category" onChange=${e => setCat(e.target.value)}>${Object.keys(cats).map(k => html`<${MenuItem} key=${k} value=${k}>${k}</${MenuItem}>`)}</${Select}></${FormControl}>
    <${Typography} variant="subtitle2" sx=${{ mb: 1 }}>Select a report prompt:</${Typography}>
    <${Grid} container spacing=${1} sx=${{ mb: 3 }}>
      ${prompts.map((p, i) => html`<${Grid} item xs=${12} sm=${6} key=${i}>
        <${Button} variant=${active === p ? 'contained' : 'outlined'} size="small" fullWidth onClick=${() => run(p)} sx=${{ justifyContent: 'flex-start', textTransform: 'none', textAlign: 'left' }}>${p}</${Button}></${Grid}>`)}
    </${Grid}>
    ${busy && html`<${Box} sx=${{ textAlign: 'center', py: 4 }}><${CircularProgress} /><${Typography} sx=${{ mt: 1 }}>Generating report...</${Typography}></${Box}>`}
    ${result && !busy && html`<${Box}>
      <${Divider} sx=${{ mb: 2 }} />
      <${Typography} variant="h6" gutterBottom>Report: ${active}</${Typography}>
      ${result.error ? html`<${Alert} severity="error">${result.error}</${Alert}>` : html`<${Box}>
        <${Tabs} value=${tab} onChange=${(_, v) => setTab(v)} sx=${{ mb: 2 }}><${Tab} label="Chart" /><${Tab} label="Data" /><${Tab} label="SQL" /></${Tabs}>
        ${tab === 0 && html`<${AutoChart} columns=${result.columns || []} rows=${result.rows || []} title=${active} />`}
        ${tab === 1 && html`<${Box}><${DataTable} columns=${result.columns || []} rows=${result.rows || []} />
          <${Button} size="small" sx=${{ mt: 1 }} onClick=${() => downloadCSV(result.columns, result.rows, 'report')}>Download CSV</${Button}></${Box}>`}
        ${tab === 2 && html`<${Paper} sx=${{ p: 2, bgcolor: '#f5f2e8' }}><pre style=${{ margin: 0, fontSize: '.8rem', overflow: 'auto' }}>${result.sql || 'N/A'}</pre></${Paper}>`}
        ${result.text && html`<${Alert} severity="info" sx=${{ mt: 2 }}>${result.text}</${Alert}>`}
      </${Box}>`}
      <${Divider} sx=${{ my: 3 }} />
      <${Typography} variant="h6" gutterBottom>Follow-up questions</${Typography}>
      <${Box} sx=${{ maxHeight: 300, overflow: 'auto', mb: 2 }}>
        ${chat.map((m, i) => html`<${Paper} key=${i} sx=${{ p: 1.5, mb: 1, borderLeft: m.role === 'user' ? `3px solid ${SAGE_MID}` : `3px solid ${GOLD}`, bgcolor: m.role === 'user' ? '#eef4eb' : '#f5f2e8' }}>
          <${Typography} variant="body2"><strong>${m.role === 'user' ? 'You' : 'Genie'}:</strong>${' '}${m.text || m.data?.text || '(see data above)'}</${Typography}></${Paper}>`)}
      </${Box}>
      <form onSubmit=${sendFu}><${Stack} direction="row" spacing=${1}>
        <${TextField} fullWidth size="small" value=${fu} onChange=${e => setFu(e.target.value)} placeholder="Ask a follow-up..." disabled=${fuBusy} />
        <${Button} type="submit" variant="contained" disabled=${fuBusy || !fu}>${fuBusy ? html`<${CircularProgress} size=${20} />` : 'Send'}</${Button}>
      </${Stack}></form>
    </${Box}>`}
  </${Box}>`;
}

// ============================================================
// ITReviewPage
// ============================================================
function ITReviewPage() {
  const { user } = useAuth();
  const [sf, setSf] = useState('All');
  const [reqs, setReqs] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selId, setSelId] = useState('');
  const [gen, setGen] = useState(null);
  const [genBusy, setGenBusy] = useState(false);
  const [dcName, setDcName] = useState('');
  const [dcState, setDcState] = useState('TESTED_PASS');
  const [dcSql, setDcSql] = useState('');
  const [rejNotes, setRejNotes] = useState('');
  const [snack, setSnack] = useState({ open: false, msg: '', sev: 'success' });

  const load = () => { setLoading(true); api(`/api/it-review?status=${sf}`).then(d => { setReqs(d); setLoading(false); }); };
  useEffect(load, [sf]);

  const pending = (reqs?.rows || []).filter(r => String(r).toLowerCase().includes('pending'));
  const ids = pending.map(r => String(r[0]));
  const selRow = pending.find(r => String(r[0]) === selId);
  const desc = selRow ? (selRow[1] || '') : '';

  const doGen = async () => { setGenBusy(true); const r = await post('/api/it-review/generate-sql', { description: desc }); setGen(r); if (r.sql) setDcSql(r.sql); setGenBusy(false); };
  const doApprove = async e => { e.preventDefault(); if (!dcName || !dcSql) return;
    const r = await post('/api/it-review/approve', { requestId: +selId, reviewer: user?.username || 'it', sqlQuery: dcSql, dataCallName: dcName, description: desc, state: dcState });
    setSnack({ open: true, msg: r.success ? 'Approved!' : (r.error || 'Error'), sev: r.success ? 'success' : 'error' }); load(); };
  const doReject = async e => { e.preventDefault();
    const r = await post('/api/it-review/reject', { requestId: +selId, reviewer: user?.username || 'it', notes: rejNotes });
    setSnack({ open: true, msg: r.success ? 'Rejected.' : (r.error || 'Error'), sev: r.success ? 'warning' : 'error' }); load(); };

  return html`<${Box}>
    <${SectionHeader} text="IT Review Queue" />
    <${FormControl} sx=${{ minWidth: 200, mb: 2 }} size="small"><${InputLabel}>Status</${InputLabel}>
      <${Select} value=${sf} label="Status" onChange=${e => setSf(e.target.value)}>${['All', 'pending', 'approved', 'rejected'].map(s => html`<${MenuItem} key=${s} value=${s}>${s}</${MenuItem}>`)}</${Select}></${FormControl}>
    ${loading ? html`<${LinearProgress} />` : reqs?.error ? html`<${Alert} severity="error">${reqs.error}</${Alert}>` : !reqs?.rows?.length ? html`<${Alert} severity="info">No requests to review.</${Alert}>` : html`<${Box}>
      <${DataTable} columns=${reqs.columns} rows=${reqs.rows} />
      ${pending.length > 0 && html`<${Box}>
        <${Divider} sx=${{ my: 3 }} /><${Typography} variant="h6" gutterBottom>Review a pending request</${Typography}>
        <${Stack} direction="row" spacing=${2} alignItems="center" sx=${{ mb: 2 }}>
          <${FormControl} sx=${{ minWidth: 200 }} size="small"><${InputLabel}>Request ID</${InputLabel}><${Select} value=${selId} label="Request ID" onChange=${e => setSelId(e.target.value)}>${ids.map(id => html`<${MenuItem} key=${id} value=${id}>${id}</${MenuItem}>`)}</${Select}></${FormControl}>
          ${selId && html`<${Button} variant="outlined" onClick=${doGen} disabled=${genBusy}>${genBusy ? html`<${CircularProgress} size=${20} />` : 'Generate SQL with Genie'}</${Button}>`}
        </${Stack}>
        ${selId && html`<${Box}>
          <${Typography} variant="body2" sx=${{ mb: 2 }}><strong>Description:</strong> ${desc}</${Typography}>
          ${gen?.sql && html`<${Paper} sx=${{ p: 2, mb: 2, bgcolor: '#f5f2e8' }}><pre style=${{ margin: 0, fontSize: '.8rem' }}>${gen.sql}</pre></${Paper}>`}
          ${gen?.columns && html`<${DataTable} columns=${gen.columns} rows=${gen.rows || []} />`}
          <${Grid} container spacing=${3} sx=${{ mt: 1 }}>
            <${Grid} item xs=${12} md=${6}><${Paper} sx=${{ p: 2 }}>
              <${Typography} variant="subtitle1" sx=${{ fontWeight: 600, mb: 2 }}>Approve & Create Data Call</${Typography}>
              <form onSubmit=${doApprove}>
                <${TextField} fullWidth size="small" label="Data call name" value=${dcName} onChange=${e => setDcName(e.target.value)} sx=${{ mb: 2 }} required />
                <${FormControl} fullWidth size="small" sx=${{ mb: 2 }}><${InputLabel}>State</${InputLabel}><${Select} value=${dcState} label="State" onChange=${e => setDcState(e.target.value)}>${['TESTED_PASS', 'TESTED_FAIL', 'NA'].map(s => html`<${MenuItem} key=${s} value=${s}>${s}</${MenuItem}>`)}</${Select}></${FormControl}>
                <${TextField} fullWidth size="small" multiline rows=${4} label="SQL query" value=${dcSql} onChange=${e => setDcSql(e.target.value)} sx=${{ mb: 2 }} required />
                <${Button} type="submit" variant="contained" fullWidth color="success">Approve</${Button}>
              </form></${Paper}></${Grid}>
            <${Grid} item xs=${12} md=${6}><${Paper} sx=${{ p: 2 }}>
              <${Typography} variant="subtitle1" sx=${{ fontWeight: 600, mb: 2 }}>Reject Request</${Typography}>
              <form onSubmit=${doReject}>
                <${TextField} fullWidth size="small" multiline rows=${4} label="Rejection notes" value=${rejNotes} onChange=${e => setRejNotes(e.target.value)} sx=${{ mb: 2 }} />
                <${Button} type="submit" variant="contained" fullWidth color="error">Reject</${Button}>
              </form></${Paper}></${Grid}>
          </${Grid}></${Box}>`}
      </${Box}>`}
    </${Box}>`}
    <${Snackbar} open=${snack.open} autoHideDuration=${4000} onClose=${() => setSnack(s => ({ ...s, open: false }))}>
      <${Alert} severity=${snack.sev}>${snack.msg}</${Alert}></${Snackbar}>
  </${Box}>`;
}

// ============================================================
// AppLayout  --  permanent sidebar + main content
// ============================================================
const DW = 260;

function AppLayout() {
  const { user, logout } = useAuth();
  const [page, setPage] = useState('Home');
  const role = user?.role || '';
  const nav = [{ l: 'Home', i: '\ud83c\udfe0' }];
  if (['admin', 'analyst'].includes(role)) nav.push({ l: 'Data Calls', i: '\ud83d\udccb' });
  if (['admin', 'executive'].includes(role)) nav.push({ l: 'Enterprise Reports', i: '\ud83d\udcca' });
  if (['admin', 'it_admin'].includes(role)) nav.push({ l: 'IT Review', i: '\u2699\ufe0f' });
  const initials = (user?.name || '').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);

  const pages = { Home: html`<${DashboardPage} />`, 'Data Calls': html`<${DataCallsPage} />`, 'Enterprise Reports': html`<${ReportsPage} />`, 'IT Review': html`<${ITReviewPage} />` };

  return html`<${Box} sx=${{ display: 'flex', minHeight: '100vh' }}>
    <${Drawer} variant="permanent" sx=${{ width: DW, flexShrink: 0, '& .MuiDrawer-paper': { width: DW, background: `linear-gradient(175deg, ${SAGE} 0%, ${FOREST} 100%)`, color: '#f0f4ec', border: 'none' } }}>
      <${Box} sx=${{ textAlign: 'center', py: 3, borderBottom: '1px solid rgba(255,255,255,.1)' }}>
        <${Typography} sx=${{ fontWeight: 700, color: '#fff', fontSize: '1.2rem' }}>Workers' Comp</${Typography}>
        <${Typography} sx=${{ fontSize: '.72rem', color: 'rgba(208,227,204,.7)', letterSpacing: '.03em', mt: .5 }}>TALK-TO-DATA PLATFORM</${Typography}>
      </${Box}>
      <${Box} sx=${{ display: 'flex', alignItems: 'center', gap: 1.5, px: 2.5, py: 1.5, mx: 1, mt: 1, borderRadius: 1.5, bgcolor: 'rgba(255,255,255,.06)' }}>
        <${Avatar} sx=${{ width: 34, height: 34, background: `linear-gradient(135deg,${SAGE_LIGHT},${SAGE_PALE})`, color: FOREST, fontWeight: 700, fontSize: '.72rem' }}>${initials}</${Avatar}>
        <${Box}>
          <${Typography} sx=${{ fontWeight: 600, fontSize: '.82rem', lineHeight: 1.2, color: '#f0f4ec' }}>${user?.name}</${Typography}>
          <${Typography} sx=${{ fontSize: '.62rem', textTransform: 'uppercase', letterSpacing: '.05em', color: 'rgba(168,196,170,.8)', mt: '1px' }}>${user?.role}</${Typography}>
        </${Box}>
      </${Box}>
      <${Typography} sx=${{ fontSize: '.6rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.1em', color: 'rgba(143,172,145,.6)', px: 2.5, pt: 2, pb: .5, ml: 1 }}>Menu</${Typography}>
      <${List} sx=${{ px: 1 }}>
        ${nav.map(({ l, i }) => html`<${ListItem} key=${l} disablePadding>
          <${ListItemButton} selected=${page === l} onClick=${() => setPage(l)} sx=${{ borderRadius: 1.5, mb: .3, py: .8, color: page === l ? '#fff' : 'rgba(240,244,236,.7)', bgcolor: page === l ? 'rgba(255,255,255,.12)' : 'transparent', borderLeft: page === l ? '3px solid #d0e3cc' : '3px solid transparent', '&:hover': { bgcolor: 'rgba(255,255,255,.08)', color: '#fff' } }}>
            <${ListItemText} primary=${`${i}  ${l}`} primaryTypographyProps=${{ fontSize: '.87rem', fontWeight: page === l ? 600 : 400 }} />
          </${ListItemButton}></${ListItem}>`)}
      </${List}>
      <${Box} sx=${{ mt: 'auto', px: 1, pb: 2 }}>
        <${Divider} sx=${{ borderColor: 'rgba(255,255,255,.08)', mb: 1 }} />
        <${ListItemButton} onClick=${logout} sx=${{ borderRadius: 1.5, color: 'rgba(240,244,236,.7)', '&:hover': { bgcolor: 'rgba(255,255,255,.08)', color: '#fff' } }}>
          <${ListItemText} primary="Logout" primaryTypographyProps=${{ fontSize: '.87rem' }} />
        </${ListItemButton}>
      </${Box}>
    </${Drawer}>
    <${Box} component="main" sx=${{ flexGrow: 1, p: 3, bgcolor: '#f7f8f4', minHeight: '100vh' }}>${pages[page] || null}</${Box}>
  </${Box}>`;
}

// ============================================================
// App root
// ============================================================
function App() {
  return html`<${ThemeProvider} theme=${theme}><${CssBaseline} /><${AuthProvider}><${AppInner} /></${AuthProvider}></${ThemeProvider}>`;
}
function AppInner() { const { user } = useAuth(); return user ? html`<${AppLayout} />` : html`<${LoginPage} />`; }

// ============================================================
// Mount
// ============================================================
createRoot(document.getElementById('root')).render(html`<${App} />`);
