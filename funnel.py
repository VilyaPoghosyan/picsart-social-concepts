"""The full funnel for the portfolio page: views on Instagram and TikTok down to paying, one tapered chart.

Tigran (2026-11-16): put the whole funnel in the main report, as a funnel visual, clear without context, with
details on click; Mika: end it with who made something / used credits. Every value comes from the data dict the
caller passes (real reads only); None renders as "pending" with the reason from `pending`.

render(data) -> (css, html, js). data = {
  "windows": [{"key", "label", "note"}],                      # e.g. overall, this week
  "steps":   [{"key", "label", "def", "source"}],             # top of the funnel first
  "accounts":[{"slug", "name", "img"}],                       # highest reach first
  "values":  {window: {slug: {step: int | None}}},
  "pending": {step: "why it is not counted yet"},
}
"""

from __future__ import annotations

import html
import json

E = html.escape

# Picsart magenta into violet, blue and teal: one hue per step, top to bottom.
RAMP = ["#FF47FF", "#E23BE8", "#C23BEF", "#9B4DF7", "#7C5CFF", "#5B6CFF", "#3D8BFF", "#2BA6D9", "#2BB3C0", "#3FD68F"]

CSS = """
.fn { display: grid; gap: 1.1rem; padding: clamp(16px, 2.4vw, 28px) }
.fn-top { display: flex; flex-wrap: wrap; gap: .8rem 1.2rem; align-items: center; justify-content: space-between }
.fn-top h2 { margin: 0 }
.seg { display: inline-flex; padding: 3px; border-radius: 999px; background: var(--sunk); border: 1px solid var(--line) }
.seg button { font: 600 .82rem var(--ui); color: var(--muted); background: none; border: 0; padding: .45rem .95rem; border-radius: 999px; cursor: pointer }
.seg button[aria-pressed="true"] { background: var(--surface-2); color: var(--ink) }
.who { display: flex; flex-wrap: wrap; gap: .45rem }
.who button { display: inline-flex; align-items: center; gap: .4rem; font: 600 .8rem var(--ui); color: var(--muted); background: var(--sunk);
  border: 1px solid var(--line); border-radius: 999px; padding: .25rem .7rem .25rem .25rem; cursor: pointer }
.who button.all { padding-left: .7rem }
.who button img { width: 22px; height: 22px; border-radius: 50%; object-fit: cover }
.who button[aria-pressed="true"] { color: var(--ink); border-color: var(--accent); background: var(--accent-soft) }
.fn-rows { display: grid; gap: 0 }
.fr { display: grid; grid-template-columns: minmax(170px, 27%) 1fr minmax(150px, 22%); align-items: center; gap: 1rem;
  cursor: pointer; border-radius: var(--r-tile); padding: 0 .4rem }
.fr:hover, .fr[aria-expanded="true"] { background: var(--surface-2) }
.fr .lab { display: flex; align-items: center; gap: .6rem; min-width: 0 }
.fr .n { font: 600 .72rem var(--ui); color: var(--faint); width: 1.4rem; flex: none }
.fr .lab b { font: 600 .95rem var(--ui); line-height: 1.25 }
.fr .lab small { display: block; color: var(--faint); font: 500 .72rem var(--ui) }
.fr svg { display: block; width: 100%; height: 46px; overflow: visible }
.fr .val { text-align: right; font-variant-numeric: tabular-nums }
.fr .val b { display: block; font: 400 1.45rem/1.1 var(--display) }
.fr .val small { color: var(--muted); font: 500 .76rem var(--ui) }
.fr .val .pend { font: 600 .9rem var(--ui); color: var(--faint) }
.fd { display: none; margin: .2rem .4rem .8rem; padding: .9rem 1rem; border-radius: var(--r-tile); background: var(--sunk); border: 1px solid var(--line) }
.fd.open { display: grid; gap: .6rem }
.fd p { margin: 0; color: var(--muted); font-size: .88rem; line-height: 1.5 }
.fd ul { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: .35rem .9rem }
.fd li { display: flex; align-items: center; gap: .45rem; font-size: .86rem }
.fd li img { width: 20px; height: 20px; border-radius: 50%; object-fit: cover }
.fd li b { margin-left: auto; font: 600 .86rem var(--ui); font-variant-numeric: tabular-nums }
.fn-foot { margin: 0; color: var(--faint); font-size: .78rem; line-height: 1.5 }
@media (max-width: 760px) {
  .fr { grid-template-columns: 1fr auto; padding: .35rem .3rem }
  .fr svg { grid-column: 1 / -1; grid-row: 2; height: 30px }
}
"""

JS = r"""
(() => {
  const D = JSON.parse(document.getElementById('fn-data').textContent);
  const box = document.getElementById('fn-rows');
  let win = D.windows[0].key, who = 'all';
  const fmt = n => n.toLocaleString('en-US');
  const val = (w, slug, k) => {
    if (slug !== 'all') return D.values[w][slug] ? D.values[w][slug][k] : null;
    const xs = D.accounts.map(a => (D.values[w][a.slug] || {})[k]);
    return xs.some(x => x === null || x === undefined) ? null : xs.reduce((s, x) => s + x, 0);  // one account pending = total pending
  };
  const width = (v, top) => v === null ? 0 : v <= 0 ? 1.5 : 10 + 90 * Math.log10(v + 1) / Math.log10(top + 1);
  function draw() {
    const vs = D.steps.map(s => val(win, who, s.key));
    const top = Math.max(1, ...vs.filter(v => v !== null));
    const ws = vs.map(v => width(v, top));
    box.innerHTML = '';
    D.steps.forEach((s, i) => {
      const v = vs[i], wt = ws[i] || 1.5, wb = i + 1 < ws.length ? (ws[i + 1] || 1.5) : wt * 0.82;
      const prev = i ? vs[i - 1] : null;
      const share = v !== null && prev ? (100 * v / prev) : null;
      const pts = [(100 - wt) / 2, 0, (100 + wt) / 2, 0, (100 + wb) / 2, 46, (100 - wb) / 2, 46].map(x => x.toFixed(2));
      const row = document.createElement('div');
      row.className = 'fr'; row.setAttribute('role', 'button'); row.tabIndex = 0; row.setAttribute('aria-expanded', 'false');
      row.innerHTML = `<div class="lab"><span class="n">${String(i + 1).padStart(2, '0')}</span><span><b>${s.label}</b><small>${s.source}</small></span></div>
        <svg viewBox="0 0 100 46" preserveAspectRatio="none" aria-hidden="true"><polygon points="${pts[0]},${pts[1]} ${pts[2]},${pts[3]} ${pts[4]},${pts[5]} ${pts[6]},${pts[7]}" fill="${D.ramp[i % D.ramp.length]}" opacity="${v === null ? .18 : .92}"/></svg>
        <div class="val">${v === null ? `<span class="pend">pending</span>` : `<b>${fmt(v)}</b>`}<small>${share === null ? (i ? '' : 'top of the funnel') : (share === 0 || share >= 10 ? share.toFixed(0) : share.toFixed(share >= 1 ? 1 : 2)) + '% of the step above'}</small></div>`;
      const det = document.createElement('div');
      det.className = 'fd';
      const per = D.accounts.map(a => [a, val(win, a.slug, s.key)]).filter(([, x]) => x !== null && x > 0).sort((p, q) => q[1] - p[1]);
      det.innerHTML = `<p>${s.def}${v === null && D.pending[s.key] ? ' <b>Pending:</b> ' + D.pending[s.key] : ''}</p>` +
        (who === 'all' && per.length ? `<ul>${per.map(([a, x]) => `<li><img src="${a.img}" alt="">${a.name}<b>${fmt(x)}</b></li>`).join('')}</ul>` : '');
      const toggle = () => { const o = det.classList.toggle('open'); row.setAttribute('aria-expanded', o); };
      row.addEventListener('click', toggle);
      row.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
      box.append(row, det);
    });
    document.getElementById('fn-note').textContent = D.windows.find(w => w.key === win).note;
  }
  document.querySelectorAll('#fn-win button').forEach(b => b.addEventListener('click', () => {
    win = b.dataset.w; document.querySelectorAll('#fn-win button').forEach(x => x.setAttribute('aria-pressed', x === b)); draw();
  }));
  document.querySelectorAll('#fn-who button').forEach(b => b.addEventListener('click', () => {
    who = b.dataset.s; document.querySelectorAll('#fn-who button').forEach(x => x.setAttribute('aria-pressed', x === b)); draw();
  }));
  draw();
})();
"""


def render(data: dict) -> tuple[str, str, str]:
    """(css, html, js) for the funnel section."""
    wins = "".join(f'<button type="button" data-w="{E(w["key"])}" aria-pressed="{str(i == 0).lower()}">{E(w["label"])}</button>'
                   for i, w in enumerate(data["windows"]))
    who = '<button type="button" class="all" data-s="all" aria-pressed="true">All accounts</button>' + "".join(
        f'<button type="button" data-s="{E(a["slug"])}" aria-pressed="false"><img src="{E(a["img"])}" alt="">{E(a["name"])}</button>'
        for a in data["accounts"])
    payload = json.dumps({**data, "ramp": RAMP}).replace("</", "<\\/")
    body = f"""<section class="panel fn" aria-labelledby="fn-h">
      <div class="fn-top"><h2 id="fn-h">From views to paying</h2><div class="seg" id="fn-win" role="group" aria-label="Period">{wins}</div></div>
      <div class="who" id="fn-who" role="group" aria-label="Account">{who}</div>
      <div class="fn-rows" id="fn-rows"></div>
      <p class="fn-foot"><span id="fn-note"></span> Tap a step for what it counts and each account's number. Bar widths use a log scale so the small steps stay visible.</p>
      <script type="application/json" id="fn-data">{payload}</script>
    </section>"""
    return CSS, body, JS
