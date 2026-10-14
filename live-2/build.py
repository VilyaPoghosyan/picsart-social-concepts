#!/usr/bin/env python3
"""Build live-2/index.html: the microdramas.ai + Dwell Instagram showcase.

Data sources (read at build time, nothing generated here):
  - ../../out/microdrama/*/schedule.json and ../../out/dwell/**/schedule.json  -> post status and dates
  - stats.json (next to this file)  -> per-post Instagram metrics exported from Zernio
  - assets/  -> 720p mp4s, posters and carousel slides made by the transcode step

Run:  python3 build.py   (from this folder)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent  # ~/vilya-ai
OUT = ROOT / "out"
YEREVAN = timezone(timedelta(hours=4))
NOW = datetime.now(YEREVAN)
STATS = json.loads((HERE / "stats.json").read_text()) if (HERE / "stats.json").exists() else {}


# ---------- helpers ----------
def sched(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def when_of(entry: dict | None) -> datetime | None:
    if not entry:
        return None
    w = entry["when"]
    dt = datetime.fromisoformat(w)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=YEREVAN)
    return dt.astimezone(YEREVAN)


def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%b %-d, %H:%M")


def status_for(ig: dict | None, tt: dict | None) -> tuple[str, str]:
    """Return (css class, label) from the Instagram and TikTok ledger entries."""
    w = when_of(ig) or when_of(tt)
    if w is None:
        return "made", "Made, not posted yet"
    plat = "IG" + (" + TikTok" if tt else "")
    if w <= NOW:
        return "live", f"Live on {plat} · {fmt_dt(w)}"
    return "soon", f"Scheduled {plat} · {fmt_dt(w)}"


def n(v) -> str:
    return "–" if v in (None, "") else f"{int(v):,}"


def stat_chips(post_id: str | None) -> str:
    s = STATS.get(f"{post_id}:instagram") if post_id else None
    if not s or s.get("views") in (None, 0) and s.get("likes") in (None, 0):
        return ""
    chips = [
        ("views", s.get("views")),
        ("likes", s.get("likes")),
        ("saves", s.get("saves")),
        ("shares", s.get("shares")),
        ("comments", s.get("comments")),
    ]
    html = "".join(f'<span><b>{n(v)}</b> {k}</span>' for k, v in chips)
    link = f' <a href="{s["url"]}" target="_blank" rel="noopener">open</a>' if s.get("url") else ""
    return f'<div class="stats">{html}{link}</div>'


def video_card(asset: str, label: str, title: str, desc: str, status: tuple[str, str], post_id: str | None = None) -> str:
    cls, text = status
    return f"""      <article class="post">
        <video src="assets/{asset}.mp4" poster="assets/{asset}.jpg" controls playsinline preload="none"></video>
        <span class="t">{label}</span>
        <span class="h">{title}</span>
        <span class="d">{desc}</span>
        <span class="st {cls}">{text}</span>
{stat_chips(post_id)}      </article>
"""


def carousel_card(prefix: str, slides: int, label: str, title: str, desc: str, status: tuple[str, str], post_id: str | None = None) -> str:
    cls, text = status
    imgs = "".join(f'<img src="assets/{prefix}-slide{i}.jpg" alt="" loading="lazy">' for i in range(1, slides + 1))
    return f"""      <article class="post">
        <div class="car">{imgs}</div>
        <span class="t">{label} · {slides} slides · swipe</span>
        <span class="h">{title}</span>
        <span class="d">{desc}</span>
        <span class="st {cls}">{text}</span>
{stat_chips(post_id)}      </article>
"""


# ---------- microdramas ----------
sn = sched(OUT / "microdrama/speak-now/schedule.json")
lb = sched(OUT / "microdrama/the-last-bite/schedule.json")

SPEAK_NOW = [
    # (asset, label, tease, what happens)
    ("speak-now-1", "Part 1 · 28 s", "Everyone looked at the wrong woman.",
     "A 1990s Manhattan church wedding. The bride objects to her own marriage, a soaked stranger walks in, and the groom's mother says one word: \"Finally.\""),
    ("speak-now-2", "Part 2 · The Letters · 26 s", "Twelve letters. Not one arrived.",
     "Luca wrote every month for a year. Claire never got a single letter. Her bridesmaid goes pale."),
    ("speak-now-3", "Part 3 · Second Time · 28 s", "Second time's the charm… if she says yes.",
     "The letters were hidden by the bridesmaid who loves the groom. Claire leaves with Luca; Julian walks into the rain toward Vivienne."),
    ("speak-now-4", "Part 4 · Tomorrow · 29 s", "She said ask me tomorrow. She didn't say what he'd find.",
     "A thirteenth letter, hidden a year ago. Julian kneels on Vivienne's stoop. Across the street a man says: \"You're still my wife.\""),
    ("speak-now-5", "Part 5 · The Husband · 28 s", "He waited all night. She waited a whole year.",
     "Mateo crosses the street. Vivienne's letter is finally read. He will let her go on one condition: \"Say you never loved me.\""),
    ("speak-now-6", "Part 6 · The Sister · 26 s", "Everyone has a secret. Hers was in the same family all along.",
     "Vivienne can't say it. Rosalind tells Claire why she helped: \"Because I'm your sister.\" That night, the ring disappears."),
    ("speak-now-7", "Part 7 · The Ring · 29 s", "Forty years ago he bought a ring. She said no. He never asked again.",
     "Sloane returns the ring to the priest. It was never Julian's: Harold bought it for Eleanor forty years ago. Mateo signs the papers."),
    ("speak-now-8", "Part 8 · Speak Now. Again. · 30 s", "Forty years ago she said no. Today he asked again.",
     "Season finale. Same church, a new wedding, \"If anyone objects…\" Eleanor stands, turns to Harold: \"Ask me again.\""),
]

LAST_BITE = [
    ("last-bite-1", "Part 1 · The Reflection · 45 s", "She survived the attack. Her reflection didn't.",
     "Elara washes pink water from her face. Her reflection keeps staring after she turns away. The phone: \"Don't let them see your eyes.\""),
    ("last-bite-2", "Part 2 · Someone Else's Death · 39 s", "The knock didn't come from the door.",
     "One drop of blood and she is running through a candlelit castle as a terrified woman, eight centuries ago. The dead woman's face is hers."),
]

FAMILY = [
    ("family-portrait-1", "Part 1 · The Drawing · 49 s", "Every family portrait has someone standing just outside the frame.",
     "Connecticut, autumn 1995. Seven-year-old Oliver keeps drawing a fifth figure outside the garden gate: a lady with yellow hair who waves at his sister."),
    ("family-portrait-2", "Part 2 · The School Gate · 40 s", "Rosie knows the lady at the gate. Margot doesn't. Yet.",
     "A blonde in a camel coat across the street at pickup. That night in the study: the wedding album, one page torn out, a photograph of Theo with another woman and a newborn."),
]


def micro_cards(items, ledger, key_fmt):
    html = ""
    for i, (asset, label, tease, desc) in enumerate(items, start=1):
        ig = ledger.get(key_fmt.format(i=i))
        tt = ledger.get(key_fmt.format(i=i) + ":tiktok")
        html += video_card(asset, label, tease, desc, status_for(ig, tt), ig["postId"] if ig else None)
    return html


speak_now_html = micro_cards(SPEAK_NOW, sn, "speak-now-part-{i}")
mtot = {"views": 0, "likes": 0, "saves": 0, "shares": 0}
for i in range(1, 9):
    e = sn.get(f"speak-now-part-{i}")
    s_ = STATS.get(f"{e['postId']}:instagram") if e else None
    for k in mtot:
        mtot[k] += int((s_ or {}).get(k) or 0)
last_bite_html = micro_cards(LAST_BITE, lb, "last-bite-part-{i}")
family_html = micro_cards(FAMILY, {}, "family-portrait-part-{i}")

sn_live = sum(1 for i in range(1, 9) if (w := when_of(sn.get(f"speak-now-part-{i}"))) and w <= NOW)
lb_live = sum(1 for i in range(1, 3) if (w := when_of(lb.get(f"last-bite-part-{i}"))) and w <= NOW)

# ---------- Dwell ----------
w42 = sched(OUT / "dwell/2026-W42/schedule.json")
w43 = sched(OUT / "dwell/2026-W43/schedule.json")
cp = sched(OUT / "dwell/colour-pairs-2026-10-14/schedule.json")
pm = sched(OUT / "dwell/power-of-moulding-2026-10-14/schedule.json")

# (ledger, key, asset prefix, kind, slides, label, hook, desc)
DWELL = [
    (w42, "01-parisian-salon", "dwell-W42-01-parisian-salon", "reel", 0, "Before / after · 19 s",
     "Some rooms never go out of style.", "Raw plaster to a Parisian salon on one match cut: same walls, same light."),
    (w42, "02-old-world-house", "dwell-W42-02-old-world-house", "reel", 0, "Statement tour · 17 s",
     "The best homes look collected, not decorated.", "Old books, older paintings and a fire that's always lit."),
    (w42, "03-bedroom-trends-2027", "dwell-W42-03-bedroom-trends-2027", "car", 7, "Trend carousel",
     "5 bedroom trends we're betting on for 2027.", "Limewash walls, upholstered walls, burgundy accents, sculptural lighting, canopy alcoves."),
    (cp, ".", "dwell-colour-pairs", "reel", 0, "Colour pairs · 21 s",
     "Same room, 5 colour pairs. Which one would you live with?", "Navy + brass, sage + travertine, bordeaux + bouclé, ivory + black marble, mocha + Calacatta."),
    (pm, ".", "dwell-power-of-moulding", "reel", 0, "Mouldings · 23 s",
     "The power of moulding. Same rooms, same paint, a completely different level.", "Coffered ceilings, picture-frame panels, fluted pilasters, a marble mantel, Parisian boiserie."),
    (w42, "04-ivory-closet-reveal", "dwell-W42-04-ivory-closet-reveal", "reel", 0, "Walkthrough reveal · 19 s",
     "Wait for the closet.", "Ivory bouclé, warm brass and a walk-in that glows."),
    (w42, "05-japandi-headboard-swap", "dwell-W42-05-japandi-headboard-swap", "reel", 0, "Variation swap · 15 s",
     "Same bed, 12 walls. Which one would you choose?", "Oak, stone, clay, walnut: one Japandi bedroom, twelve headboard walls."),
    (w42, "06-mediterranean-villa-set", "dwell-W42-06-mediterranean-villa-set", "car", 8, "Photo-set carousel",
     "Limewash, travertine and one very old olive tree.", "One Mediterranean villa at golden hour, room by room."),
    (w42, "07-night-penthouse", "dwell-W42-07-night-penthouse", "reel", 0, "Statement tour · 20 s",
     "This is what quiet money looks like.", "Walnut, black marble and a city that never quite sleeps."),
    (w43, "01-wabi-sabi-spa-bath", "dwell-W43-01-wabi-sabi-spa-bath", "reel", 0, "Before / after · 19 s",
     "Slow mornings start in the right room.", "A bare bathroom becomes a warm wabi-sabi spa on the beat."),
    (w43, "02-kitchen-trends-2027", "dwell-W43-02-kitchen-trends-2027", "car", 7, "Trend carousel",
     "5 kitchen trends we're betting on for 2027.", "Five warm kitchens, one trend each."),
    (w43, "03-alpine-chalet", "dwell-W43-03-alpine-chalet", "reel", 0, "Statement tour · 23 s",
     "Winter is just an excuse to stay in.", "A warm alpine chalet: timber, wool, fire and snow outside."),
    (w43, "04-scandi-fireplace-swap", "dwell-W43-04-scandi-fireplace-swap", "reel", 0, "Variation swap · 15 s",
     "Same room, 12 fireplaces. Which one would you choose?", "One Scandinavian living room, twelve fireplaces."),
    (w43, "05-midcentury-conversation-pit", "dwell-W43-05-midcentury-conversation-pit", "reel", 0, "Walkthrough reveal · 19 s",
     "Wait for the step down.", "A mid-century home that ends in a sunken conversation pit."),
    (w43, "06-desert-adobe-set", "dwell-W43-06-desert-adobe-set", "car", 8, "Photo-set carousel",
     "Rammed earth, warm steel and a sunset every single night.", "One desert adobe home, room by room."),
    (w43, "07-industrial-loft", "dwell-W43-07-industrial-loft", "reel", 0, "Before / after · 18 s",
     "Every great home starts as a shell.", "A concrete shell becomes a warm industrial loft."),
    (w43, "08-coastal-beach-house", "dwell-W43-08-coastal-beach-house", "reel", 0, "Statement tour · 23 s",
     "Salt air, linen, nowhere to be.", "A warm coastal beach house, open to the sea."),
    (w43, "09-dining-chandelier-swap", "dwell-W43-09-dining-chandelier-swap", "reel", 0, "Variation swap · 15 s",
     "Same dining room, 12 chandeliers. Which one would you hang?", "One classic dining room, twelve chandeliers."),
    (w43, "10-living-room-trends-2027", "dwell-W43-10-living-room-trends-2027", "car", 7, "Trend carousel",
     "5 living room trends we're betting on for 2027.", "Five warm living rooms, one trend each."),
    (w43, "11-tuscan-farmhouse-kitchen", "dwell-W43-11-tuscan-farmhouse-kitchen", "reel", 0, "Before / after · 19 s",
     "Every kitchen should feel like Sunday.", "A bare room becomes a Tuscan farmhouse kitchen."),
    (w43, "12-art-deco-apartment", "dwell-W43-12-art-deco-apartment", "reel", 0, "Walkthrough reveal · 19 s",
     "Wait for the living room.", "An art deco apartment, hallway to the big reveal."),
    (w43, "13-attic-bedroom", "dwell-W43-13-attic-bedroom", "reel", 0, "Before / after · 19 s",
     "Every house has a secret room.", "A dusty attic becomes a cosy bedroom under the roof."),
    (w43, "14-moroccan-riad-set", "dwell-W43-14-moroccan-riad-set", "car", 8, "Photo-set carousel",
     "Cedar, tadelakt and a courtyard full of light.", "One Moroccan riad, room by room."),
]


def dwell_rows():
    rows = []
    for ledger, key, asset, kind, slides, label, hook, desc in DWELL:
        ig = ledger.get(f"{key}:instagram")
        tt = ledger.get(f"{key}:tiktok")
        rows.append((when_of(ig) or NOW + timedelta(days=365), ledger, key, asset, kind, slides, label, hook, desc, ig, tt))
    rows.sort(key=lambda r: r[0])
    return rows


dwell_html = ""
dwell_live = 0
totals = {"views": 0, "likes": 0, "saves": 0, "shares": 0, "comments": 0}
for w, ledger, key, asset, kind, slides, label, hook, desc, ig, tt in dwell_rows():
    st = status_for(ig, tt)
    pid = ig["postId"] if ig else None
    if st[0] == "live":
        dwell_live += 1
        s = STATS.get(f"{pid}:instagram") or {}
        for k in totals:
            totals[k] += int(s.get(k) or 0)
    if kind == "reel":
        dwell_html += video_card(asset, label, hook, desc, st, pid)
    else:
        dwell_html += carousel_card(asset, slides, label, hook, desc, st, pid)

stats_as_of = max((s.get("lastUpdated") or "" for s in STATS.values()), default="")

# ---------- page ----------
page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Microdramas and Dwell</title>
<meta name="description" content="Two Picsart Social pages: @microdramas.ai (three AI microdrama series) and @dwell.rooms (interiors), with every post and its Instagram numbers.">
<style>
  @font-face{{font-family:"Gilroy";font-weight:400;src:url("https://pastatic.picsart.com/cms-pastatic/d018cb40-40a8-4efa-a202-947285ae8329.woff2") format("woff2");font-display:swap}}
  @font-face{{font-family:"Gilroy";font-weight:600;src:url("https://pastatic.picsart.com/cms-pastatic/eae6e1ea-9319-406c-a3de-00431f8f03f4.woff2") format("woff2");font-display:swap}}
  @font-face{{font-family:"Gilroy";font-weight:700;src:url("https://pastatic.picsart.com/cms-pastatic/0ea441d6-d0d4-4236-b649-67a987887865.woff2") format("woff2");font-display:swap}}
  :root{{--ink:#141414;--paper:#f7f4ee;--muted:#6b6b70;--line:#e3ded5;--card:#fff;--accent:#5C4636;--ok:#1d6b3a;--okbg:#e7f3ea;--warn:#8a5a00;--warnbg:#fbf1dc;--off:#555;--offbg:#ebe8e2}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 "Gilroy",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
  a{{color:var(--accent)}}
  .wrap{{max-width:1120px;margin:0 auto;padding:0 20px}}
  header{{padding:56px 0 40px;border-bottom:1px solid var(--line)}}
  h1{{font-size:clamp(32px,5vw,52px);margin:0;line-height:1.05;letter-spacing:-.02em}}
  header p{{color:var(--muted);margin:12px 0 0;font-size:18px;max-width:640px}}
  .logos{{display:flex;gap:10px;margin-top:22px}}
  .logos img{{width:48px;height:48px;border-radius:50%;object-fit:cover;border:1px solid var(--line)}}
  main{{padding:8px 0 48px}}
  section.page{{margin:40px 0 0}}
  .profile{{display:grid;grid-template-columns:104px 1fr auto;gap:22px;align-items:start;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px}}
  .profile img{{width:104px;height:104px;border-radius:50%;display:block;object-fit:cover}}
  .profile h2{{margin:0;font-size:26px;line-height:1.15;letter-spacing:-.01em}}
  .handle{{font-weight:600;color:var(--muted);margin-top:2px}}
  .bio{{margin:10px 0 0;white-space:pre-line;font-size:15px}}
  .who{{margin:8px 0 0;color:var(--muted);font-size:14.5px}}
  .status{{display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:700;padding:4px 10px;border-radius:999px;margin-left:8px;vertical-align:middle}}
  .status::before{{content:"";width:8px;height:8px;border-radius:50%;background:currentColor}}
  .status.live{{color:var(--ok);background:var(--okbg)}}
  .actions{{display:flex;flex-direction:column;gap:8px}}
  .btn{{display:inline-block;text-align:center;font-weight:700;font-size:14px;text-decoration:none;padding:10px 16px;border-radius:10px;white-space:nowrap}}
  .btn.primary{{background:var(--ink);color:#fff}}
  .btn.ghost{{border:1px solid var(--line);color:var(--ink);background:var(--card)}}
  .kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:10px;margin-top:14px}}
  .kpi{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}}
  .kpi b{{display:block;font-size:24px;line-height:1.1;letter-spacing:-.01em}}
  .kpi span{{font-size:12.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;font-weight:600}}
  .series{{margin-top:34px}}
  .series h3{{margin:0;font-size:22px;letter-spacing:-.01em}}
  .series .meta{{color:var(--muted);font-size:14px;margin:4px 0 0}}
  .series .brief{{margin:10px 0 0;max-width:760px;font-size:15.5px}}
  .posts{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:16px}}
  .post{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:10px;display:flex;flex-direction:column;gap:7px}}
  .post video{{width:100%;aspect-ratio:9/16;border-radius:10px;display:block;background:#111;object-fit:cover}}
  .car{{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;gap:6px;border-radius:10px;aspect-ratio:4/5;background:#111;scrollbar-width:none}}
  .car::-webkit-scrollbar{{display:none}}
  .car img{{flex:0 0 100%;width:100%;height:100%;object-fit:cover;scroll-snap-align:start;border-radius:10px}}
  .post .t{{font-size:12px;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.06em;margin-top:2px}}
  .post .h{{font-weight:700;font-size:15px;line-height:1.3}}
  .post .d{{font-size:13px;color:var(--muted)}}
  .post .st{{font-size:12px;font-weight:700;padding:3px 8px;border-radius:999px;align-self:start;margin-top:auto}}
  .st.live{{color:var(--ok);background:var(--okbg)}}
  .st.soon{{color:var(--warn);background:var(--warnbg)}}
  .st.made{{color:var(--off);background:var(--offbg)}}
  .stats{{display:flex;flex-wrap:wrap;gap:6px 10px;font-size:12.5px;color:var(--muted);border-top:1px solid var(--line);padding-top:8px}}
  .stats b{{color:var(--ink)}}
  .stats a{{margin-left:auto;font-weight:600}}
  .note{{color:var(--muted);font-size:14px;margin-top:32px}}
  footer{{border-top:1px solid var(--line);padding:18px 0 48px;color:var(--muted);font-size:13.5px}}
  @media (max-width:980px){{.posts{{grid-template-columns:repeat(3,1fr)}}}}
  @media (max-width:760px){{
    .profile{{grid-template-columns:72px 1fr}}
    .profile img{{width:72px;height:72px}}
    .actions{{grid-column:1/-1;flex-direction:row;flex-wrap:wrap}}
    .posts{{grid-template-columns:1fr 1fr}}
  }}
  @media (max-width:460px){{.posts{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header><div class="wrap">
  <h1>Microdramas and Dwell</h1>
  <p>Two more Picsart Social pages, both live on Instagram and TikTok. Below: every post, its status and its Instagram numbers.</p>
  <div class="logos"><img src="assets/logo-microdramas.jpg" alt=""><img src="assets/logo-dwell.jpg" alt=""></div>
</div></header>
<main><div class="wrap">

  <section class="page" id="microdramas">
    <div class="profile">
      <img src="assets/logo-microdramas.jpg" alt="microdramas.ai profile picture">
      <div>
        <h2>Microdramas · AI love stories <span class="status live">Live on Instagram + TikTok</span></h2>
        <div class="handle">@microdramas.ai</div>
        <p class="bio">Tiny love stories, big 90s drama 🎬&nbsp; New part every week. An official Picsart channel, made with Picsart AI.</p>
        <p class="who">Serialized AI microdramas shot like a 1990s film: one scene, one twist, 30 to 50 seconds, a new part at a time. Three series so far, each with its own cast.</p>
      </div>
      <div class="actions">
        <a class="btn primary" href="https://www.instagram.com/microdramas.ai/" target="_blank" rel="noopener">Open on Instagram</a>
        <a class="btn ghost" href="https://www.tiktok.com/@microdramas.ai" target="_blank" rel="noopener">Open on TikTok</a>
      </div>
    </div>
    <div class="kpis">
      <div class="kpi"><b>3</b><span>series</span></div>
      <div class="kpi"><b>{sn_live + lb_live}</b><span>parts live</span></div>
      <div class="kpi"><b>{(8 - sn_live) + (2 - lb_live)}</b><span>parts scheduled</span></div>
      <div class="kpi"><b>{n(mtot['views'])}</b><span>views</span></div>
      <div class="kpi"><b>{n(mtot['likes'])}</b><span>likes</span></div>
      <div class="kpi"><b>{n(mtot['saves'])}</b><span>saves</span></div>
      <div class="kpi"><b>7</b><span>IG followers (day 2)</span></div>
    </div>

    <div class="series" id="speak-now">
      <h3>SPEAK NOW</h3>
      <p class="meta">Series 1 · romance · 8 parts, complete · {sn_live} live, {8 - sn_live} scheduled through Oct 15 · Instagram numbers under each part</p>
      <p class="brief">At a 1990s Manhattan church wedding the bride objects to her own marriage, and every guest has a secret about why. One rainy afternoon and the morning after, told in eight parts: hidden letters, a husband nobody mentioned, a sister nobody knew about, and a ring bought forty years ago.</p>
      <div class="posts">
{speak_now_html}      </div>
    </div>

    <div class="series" id="the-last-bite">
      <h3>THE LAST BITE</h3>
      <p class="meta">Series 2 · gothic romance · 2 of 8 parts made · {lb_live} live, {2 - lb_live} scheduled</p>
      <p class="brief">A young woman survives a vampire attack and starts remembering murders from eight centuries before her birth. The immortal who protects her, the friend who swears she is still human and the Regent who hunts her are all afraid of the same thing: what she remembers next. Modern city, rain, cold blue light, one drop of red per frame.</p>
      <div class="posts">
{last_bite_html}      </div>
    </div>

    <div class="series" id="family-portrait">
      <h3>FAMILY PORTRAIT</h3>
      <p class="meta">Series 3 · family drama · 2 of 8 parts made · not posted yet</p>
      <p class="brief">A lakeside house in Connecticut, autumn 1995. A perfect family's seven-year-old keeps drawing a fifth figure outside the garden gate: a lady with yellow hair who waves at his little sister. She is the children's mother, declared drowned five years ago by the grandmother who paid her to disappear. The wife who raised them has known for three years.</p>
      <div class="posts">
{family_html}      </div>
    </div>
  </section>

  <section class="page" id="dwell">
    <div class="profile">
      <img src="assets/logo-dwell.jpg" alt="Dwell profile picture">
      <div>
        <h2>Dwell <span class="status live">Live on Instagram + TikTok</span></h2>
        <div class="handle">@dwell.rooms</div>
        <p class="bio">Empty room → dream room ✨ AI makeovers daily. An official Picsart channel, made with Picsart AI.</p>
        <p class="who">Interiors, decoded. Two posts a day at 18:00 and 21:00: before/after match cuts, statement tours, walkthrough reveals, variation swaps, colour pairs and trend carousels. Every room is made with Picsart.</p>
      </div>
      <div class="actions">
        <a class="btn primary" href="https://www.instagram.com/dwell.rooms/" target="_blank" rel="noopener">Open on Instagram</a>
        <a class="btn ghost" href="https://www.tiktok.com/@dwellrooms" target="_blank" rel="noopener">Open on TikTok</a>
      </div>
    </div>
    <div class="kpis">
      <div class="kpi"><b>{dwell_live}</b><span>posts live</span></div>
      <div class="kpi"><b>{len(DWELL) - dwell_live}</b><span>scheduled</span></div>
      <div class="kpi"><b>{n(totals['views'])}</b><span>views</span></div>
      <div class="kpi"><b>{n(totals['likes'])}</b><span>likes</span></div>
      <div class="kpi"><b>{n(totals['saves'])}</b><span>saves</span></div>
      <div class="kpi"><b>{n(totals['shares'])}</b><span>shares</span></div>
      <div class="kpi"><b>11</b><span>IG followers (day 3)</span></div>
    </div>
    <div class="series">
      <h3>All posts, in posting order</h3>
      <p class="meta">Instagram numbers from Zernio analytics, last synced {stats_as_of or "n/a"} UTC. Posts without numbers are scheduled or still syncing.</p>
      <div class="posts">
{dwell_html}      </div>
    </div>
  </section>

  <p class="note">Every face in the microdramas is an original AI character and every post is labelled as AI on the platform. Every caption ends with "made with Picsart". Instagram numbers come from Zernio and refresh with each rebuild of this page; follower counts are from {NOW.strftime("%b %-d")}. The first three pages are on <a href="../live/">our new pages</a>.</p>
</div></main>
<footer><div class="wrap">Picsart Social automation project · October 2026 · made with Picsart</div></footer>
</body>
</html>
"""
(HERE / "index.html").write_text(page)
print(f"wrote index.html: speak-now live {sn_live}/8, last-bite live {lb_live}/2, dwell live {dwell_live}/{len(DWELL)}, totals {totals}")
