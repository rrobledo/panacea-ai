// Utilidades compartidas por las páginas del plan. DATA lo embebe generar.py.
const ARS = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 });
const ARS1 = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', minimumFractionDigits: 1, maximumFractionDigits: 1 });
const ARSM = { format: v => ARS1.format(v / 1e6) + ' M' };
const NUM = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });
const DEC = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 2 });
const PCT1 = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const MESES = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
const ESTADO_KPI = { en_meta: 'En meta', mejora: 'Mejora', sin_mejora: 'Sin mejora', referencia: 'Referencia', sin_dato: 'Sin dato' };
const ESTADO_ACC = { pendiente: 'Pendiente', en_curso: 'En curso', hecha: 'Hecha', bloqueada: 'Bloqueada', descartada: 'Descartada', vencida: 'Vencida' };
const PLAN = DATA.plan;
const KPI = Object.fromEntries(PLAN.kpis.map(k => [k.id, k]));
const ACC = Object.fromEntries(PLAN.estrategias.flatMap(e => e.acciones.map(a => [a.id, { ...a, estrategia: e.id }])));
const ESTR = Object.fromEntries(PLAN.estrategias.map(e => [e.id, e]));

const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fecha = iso => { const d = new Date(iso + 'T12:00:00'); return `${d.getDate()} de ${MESES[d.getMonth()]}`; };
const fechaCorta = iso => { const [a, m, d] = iso.split('-'); return `${d}/${m}`; };
const rango = (a, b) => {
  const da = new Date(a + 'T12:00:00'), db = new Date(b + 'T12:00:00');
  return da.getMonth() === db.getMonth() ? `${da.getDate()} al ${fecha(b)}` : `${fecha(a)} al ${fecha(b)}`;
};
const signo = v => (v > 0 ? '+' : v < 0 ? '−' : '±') + PCT1.format(Math.abs(v)) + '%';
const clsVar = (v, sentido = 'subir') => v == null || v === 0 ? 'flat' : (v > 0) === (sentido === 'subir') ? 'up' : 'down';

function fmtValor(k, v) {
  if (v == null) return '—';
  if (k.unidad === 'ars') return Math.abs(v) >= 1e6 ? ARSM.format(v) : ARS.format(v);
  if (k.unidad === 'pct') return PCT1.format(v) + '%';
  if (k.unidad === 'dec') return DEC.format(v);
  return NUM.format(v);
}
// Base y meta se expresan en lo que se evalúa: variación interanual o valor
function fmtObjetivo(k, v, conSentido) {
  if (v == null) return '—';
  const pre = conSentido ? (k.sentido === 'subir' ? '≥ ' : '≤ ') : '';
  if (k.modo === 'interanual' || k.modo === 'vs_base') return pre + signo(v);
  return pre + fmtValor(k, v);
}
const st = (cls, txt) => `<span class="st ${cls}">${esc(txt)}</span>`;
const estadoAccion = (s, id) => {
  const e = s.acciones[id]?.estado || 'pendiente';
  return e !== 'hecha' && e !== 'descartada' && s.vencidas.includes(id) ? 'vencida' : e;
};
const hoyN = () => {
  const d = (new Date(DATA.generado.slice(0, 10) + 'T12:00:00') - new Date(PLAN.inicio + 'T12:00:00')) / 864e5;
  return Math.max(0, Math.min(DATA.total_semanas, Math.floor(d / 7) + 1));
};
function timeline(n) {
  const el = document.getElementById('timeline');
  el.style.setProperty('--n', DATA.total_semanas);
  el.innerHTML = Array.from({ length: DATA.total_semanas }, (_, i) =>
    `<span class="${i + 1 < n ? 'ok' : i + 1 === n ? 'now' : ''}" title="Semana ${i + 1}"></span>`).join('');
  document.getElementById('timeline-lbl').innerHTML = `<span>${fechaCorta(PLAN.inicio)}</span><span>${n ? `Semana ${n} de ${DATA.total_semanas}` : `Empieza el ${fechaCorta(PLAN.inicio)}`}</span><span>${fechaCorta(PLAN.fin)}</span>`;
}
function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
function chartDefaults() {
  Chart.defaults.font.family = css('--font-body');
  Chart.defaults.color = css('--fg-2');
  Chart.defaults.borderColor = css('--line');
  Chart.defaults.plugins.legend.display = false;
  Chart.defaults.animation = matchMedia('(prefers-reduced-motion: reduce)').matches ? false : { duration: 400 };
}

// ---------------------------------------------------------------- sucursales
// Colores fijos por sucursal (nunca por ranking). 'Todas' va en tinta neutra.
const SUC_COLOR = { 'Carlos Paz': '--s1', 'Villa Allende': '--s2', 'Villa General Belgrano': '--s3', 'Todas': '--fg-2' };
const SUC_MOSTRADOR = ['Carlos Paz', 'Villa Allende', 'Villa General Belgrano'];
const etiquetaModo = k => k.modo === 'interanual' ? 'Variación contra 2025' : k.modo === 'vs_base' ? 'Contra la base previa al plan' : k.modo === 'acumulado' ? 'Acumulado desde el inicio' : 'Valor semanal';
const deltaPct = (a, b) => a != null && b ? 100 * (a / b - 1) : null;
const celdaDelta = (d, sentido = 'subir', pp) => d == null ? '—' : `<span class="delta ${Math.abs(d) < (pp ? 1 : 2) ? 'flat' : clsVar(d, sentido)}">${pp ? (d > 0 ? '+' : d < 0 ? '−' : '±') + PCT1.format(Math.abs(d)) + ' pp' : signo(d)}</span>`;

// Tabla de mostrador por sucursal contra la base previa al plan. filas: [{lugar, tp, tp_base, upt, ...}]
function tablaMostrador(filas) {
  const col = (r, c, f, sentido, pp) => `<td class="r">${r[c] != null ? f(r[c]) : '—'}<span class="sub">base ${r[c + '_base'] != null ? f(r[c + '_base']) : '—'}</span></td><td class="r">${celdaDelta(pp ? (r[c] != null && r[c + '_base'] != null ? r[c] - r[c + '_base'] : null) : deltaPct(r[c], r[c + '_base']), sentido, pp)}</td>`;
  const pct = v => PCT1.format(v) + '%';
  return `<thead><tr><th>Sucursal</th><th class="r">Tickets</th><th class="r">Var.</th><th class="r">Ticket promedio</th><th class="r">Var.</th><th class="r">Unidades por ticket</th><th class="r">Var.</th><th class="r">Con un solo producto</th><th class="r">Var.</th><th class="r">Con café</th><th class="r">Var.</th></tr></thead><tbody>` +
    filas.map(r => `<tr${r.lugar === 'Todas' ? ' style="font-weight:600"' : ''}><td>${r.lugar === 'Todas' ? 'Total mostrador' : esc(r.lugar)}</td>
      ${col({ ...r, tickets: r.tickets_most, tickets_base: r.tickets_most_base }, 'tickets', v => NUM.format(v), 'subir')}
      ${col(r, 'tp', v => ARS.format(v), 'subir')}${col(r, 'upt', v => DEC.format(v), 'subir')}
      ${col(r, 'pct_uno', pct, 'bajar', true)}${col(r, 'pct_cafe', pct, 'subir', true)}</tr>`).join('') + '</tbody>';
}

// Gráficos de evolución semanal por sucursal desde el histórico. defs: [{id, titulo, nota, f(fila, semana) -> valor, fmt}]
function graficosHistorico(cont, defs) {
  const H = DATA.historico;
  if (!H) { cont.innerHTML = '<p class="empty">Falta el histórico: correr historico.py.</p>'; return; }
  const sems = H.semanas, base = new Set(H.semanas_base);
  cont.innerHTML = defs.map(d => `<figure><figcaption><h3>${esc(d.titulo)}</h3><span class="note">${esc(d.nota)}</span></figcaption>
    <div class="chart" style="height:220px"><canvas id="h-${d.id}" aria-label="${esc(d.titulo)}"></canvas></div></figure>`).join('');
  chartDefaults();
  const sombra = { id: 'sombraBase', beforeDraw(c) {   // banda de las semanas base previa al plan
    const x = c.scales.x, a = c.chartArea, idx = sems.map((s, i) => base.has(s.semana) ? i : -1).filter(i => i >= 0);
    if (!idx.length) return; const g = c.ctx; g.save(); g.fillStyle = css('--accent-soft');
    const w = (x.getPixelForValue(1) - x.getPixelForValue(0)) / 2;
    g.fillRect(x.getPixelForValue(idx[0]) - w, a.top, x.getPixelForValue(idx[idx.length - 1]) - x.getPixelForValue(idx[0]) + 2 * w, a.bottom - a.top); g.restore(); } };
  defs.forEach(d => {
    const lugares = d.lugares || [...SUC_MOSTRADOR, 'Todas'];
    new Chart(document.getElementById('h-' + d.id), {
      type: 'line', plugins: [sombra],
      data: { labels: sems.map(s => fechaCorta(s.desde)),
        datasets: lugares.map(l => ({ label: l === 'Todas' ? 'Total' : l, data: sems.map(s => s.sucursales[l] ? d.f(s.sucursales[l], s) : null),
          borderColor: css(SUC_COLOR[l]), backgroundColor: css(SUC_COLOR[l]), borderWidth: l === 'Todas' ? 2.5 : 2,
          borderDash: l === 'Todas' ? [5, 3] : [], pointRadius: 0, pointHoverRadius: 5, tension: 0.25, spanGaps: false })) },
      options: { maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
        scales: { x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkipPadding: 12 } }, y: { grace: '8%', ticks: { callback: v => d.fmt(v) } } },
        plugins: { tooltip: { callbacks: { label: c => `${c.dataset.label}: ${c.raw == null ? '—' : d.fmt(c.raw)}` } } } }
    });
  });
}
const leyendaSucursales = (lugares = [...SUC_MOSTRADOR, 'Todas']) => lugares.map(l => `<span><i ${l === 'Todas' ? 'class="dash"' : `style="background:var(${SUC_COLOR[l]})"`}></i>${l === 'Todas' ? 'Total' : l}</span>`).join('') + '<span><i style="background:var(--accent-soft);height:10px"></i>Semanas base previa al plan</span>';
const DEFS_HIST = [
  { id: 'tk', titulo: 'Tickets por semana', nota: 'Todos los clientes.', f: r => r.tickets, fmt: v => NUM.format(v) },
  { id: 'tc', titulo: 'Ticket de mostrador a precios constantes', nota: 'Ticket dividido por el índice de precios: en pesos de la base previa al plan.', f: (r, s) => r.tp && s.indice ? r.tp / s.indice * 100 : null, fmt: v => ARS.format(v) },
  { id: 'upt', titulo: 'Unidades por ticket de mostrador', nota: 'No depende del precio.', f: r => r.upt, fmt: v => DEC.format(v) },
  { id: 'uno', titulo: 'Tickets de mostrador con un solo producto', nota: 'Cuanto más bajo, mejor.', f: r => r.pct_uno, fmt: v => NUM.format(v) + '%' },
  { id: 'cafe', titulo: 'Tickets de mostrador con café', nota: 'Meta del plan: 15% en el total.', f: r => r.pct_cafe, fmt: v => NUM.format(v) + '%' },
  { id: 'yoy', titulo: 'Tickets contra la misma semana de 2025', nota: 'Variación % por sucursal comparable.', lugares: ['Carlos Paz', 'Villa Allende'], f: r => r.tickets && r.tickets_ant ? 100 * (r.tickets / r.tickets_ant - 1) : null, fmt: v => (v > 0 ? '+' : '') + NUM.format(v) + '%' }
];
