#!/usr/bin/env python3
"""Build onepagers/ai-characters/index.html: one card per live AI influencer account.

Vilya 2026-11-25: every influencer with a clickable Instagram link, a short description, the most-viewed reel,
how many days it has been live, followers, and views + reach. Numbers follow the real-stats rule: read live the
same day from the logged-in profile (followers, posts, per-reel views) and Instagram insights via
bin/real_stats.py (views, reach). Each run reads them again and passes them in DATA below; nothing is reused.

    python3 onepagers/build_ai_characters.py
Keeps the <head> (Picsart tokens + embedded fonts) of the current page and replaces the body.
Assets: ai-characters/img/live/<handle>-pfp.jpg, <handle>-top.mp4/.jpg (720p, ffmpeg crf 27).
Also published on GitLab Pages (Vilya 2026-11-25): https://ai-characters-4f442c.gitlab.io (project
gitlab.com/vilya.poghosyan/ai-characters, local repo projects/ai-characters-site): copy index.html (+ noindex) and
img/live/ into its public/, commit, push.
"""

import html
import re
from datetime import date
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "ai-characters" / "index.html"
TODAY = date(2026, 11, 25)
READ = {  # when and where every number was read (Yerevan time)
    "profile": "logged-in Instagram profiles, 25 Nov 2026, 16:21–16:28",
    "insights": "Instagram account insights since each account's first post, read 25 Nov 2026, 16:27–16:28",
}

# name, handle, description, first post (Yerevan date) or None, followers, posts, top reel (code, views as shown),
# insights views, reach. None = no posts yet.
DATA = [
    ("Granny Ofik", "granny.ofik",
     "An 84-year-old, 2.5-metre glamorous granny with seashell ears and her evil poodle Baron, doing wild "
     "rich-lady things with black humour.",
     date(2026, 11, 9), "166", 42, ("Dfpb-D4En58", "342K"), 416538, 243077),
    ("Aisha Hadid", "aishahadid.ai",
     "A Miss-Universe-level girl from a small African town who does every big fashion trend with what she has, "
     "and outclasses the original.",
     date(2026, 11, 12), "449", 45, ("Dfw3bM4ALYe", "924K"), 929609, 547960),
    ("Rich Ronnie", "richronnie.ai",
     "A loud, absurdly rich uncle with a knee-length rat-tail who shows off even while doing the most ordinary "
     "things.",
     date(2026, 11, 12), "12,196", 48, ("DfuX1m7jpn5", "20.1M"), 19917185, 10561626),
    ("The Hungry Ballerina", "ballerina.ai",
     "A delicate ballerina in a tutu and pointe shoes who eats like ten men, elegantly, back straight.",
     date(2026, 11, 17), "259", 30, ("DgAuH8cDt46", "218K"), 290866, 187755),
    ("Pingi", "pingi.ai",
     "A baby emperor penguin girl, cute but aggressive, living every relatable adult moment: the office, "
     "Mondays, the gym, dating.",
     date(2026, 11, 18), "28", 36, ("DgKMkR1CLTe", "29.4K"), 65737, 49198),
    ("Rich Lolita", "richlolita.ai",
     "A trillionaire red-haired girl, Rich Ronnie's wife: supercars, jets and diamonds, told with a spoiled wink.",
     date(2026, 11, 19), "60", 17, ("DgILP2TgdbC", "25.3K"), 55086, 33621),
    ("Rich Johnny", "richjohnny.ai",
     "A super-rich, very loud show-off with wild orange eyebrows and a gold lion chain. The flex never stops.",
     date(2026, 11, 24), "1", 7, ("DgKHUukSBaq", "500"), 1323, 1043),
    ("Dolly Lucy", "dollylucy.ai",
     "A living doll who does every girl trend perfectly (make-up, hair, lip-syncs, get-ready-with-me) and "
     "never blinks.",
     None, "0", 0, None, None, None),
    ("Strong Arthur", "strongarthur.ai",
     "A 90-year-old grandpa on a champion bodybuilder's body who out-lifts, out-pulls and out-wrestles everyone, "
     "calmly.",
     None, "0", 0, None, None, None),
    ("Big Hands Boris", "bigboris.ai",
     "A deadpan street-food cook whose hands are as big as his head, cooking, serving and eating at full speed.",
     None, "0", 0, None, None, None),
]
FIRST_SLOT = {"dollylucy.ai": "17:00", "strongarthur.ai": "19:00", "bigboris.ai": "18:00"}  # 25 Nov, Yerevan


def n(v):
    return "pending" if v is None else f"{v:,}"


def card(name, handle, desc, first, followers, posts, top, views, reach):
    e = html.escape
    ig = f"https://www.instagram.com/{handle}/"
    if first:
        days = (TODAY - first).days
        live = f'<span class="pill on">Live {days} day{"s" if days != 1 else ""}</span>' \
               f'<span class="since">since {first.strftime("%-d %b")}</span>'
        cap = (f'Most viewed reel: <b>{e(top[1])} views</b> · '
               f'<a href="https://www.instagram.com/reel/{top[0]}/" target="_blank" rel="noopener">open on Instagram</a>')
    else:
        live = f'<span class="pill new">Launching today</span><span class="since">first reel 25 Nov, {FIRST_SLOT[handle]}</span>'
        cap = "First reel, scheduled for today. No views yet."
    stats = (f'<dl class="stats"><div><dt>Followers</dt><dd>{e(followers)}</dd></div>'
             f'<div><dt>Posts</dt><dd>{posts}</dd></div>'
             f'<div><dt>Views</dt><dd>{n(views) if first else "–"}</dd></div>'
             f'<div><dt>Reach</dt><dd>{n(reach) if first else "–"}</dd></div></dl>')
    return f'''<article class="ch" id="{e(handle)}">
  <header class="ch-head">
    <a class="pfp" href="{ig}" target="_blank" rel="noopener"><img src="img/live/{handle}-pfp.jpg" alt="{e(name)} profile picture" width="72" height="72" loading="lazy"></a>
    <div><h2>{e(name)}</h2><a class="handle" href="{ig}" target="_blank" rel="noopener">@{e(handle)}</a>
    <div class="live">{live}</div></div>
  </header>
  <p class="desc">{e(desc)}</p>
  {stats}
  <video src="img/live/{handle}-top.mp4" poster="img/live/{handle}-top.jpg" controls playsinline preload="none"></video>
  <p class="cap">{cap}</p>
</article>'''


CSS = """
<style>
.wrap{max-width:1180px;margin:0 auto;padding:32px var(--gutter) 56px}
.hero h1{font-family:var(--display);font-size:clamp(2rem,4vw,3rem);margin:0 0 8px;line-height:1.05}
.hero p{color:var(--muted);margin:0;max-width:62ch}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(300px,100%),1fr));gap:20px;margin-top:28px}
.ch{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-panel);padding:18px;display:flex;flex-direction:column;gap:12px;min-width:0}
.ch-head{display:flex;gap:14px;align-items:center}
.pfp img{width:72px;height:72px;border-radius:50%;object-fit:cover;display:block;border:2px solid var(--line-2)}
.ch h2{font-family:var(--ui);font-size:1.15rem;margin:0}
.handle{color:var(--accent-ink);text-decoration:none;font-weight:600}
.handle:hover,.handle:focus-visible{text-decoration:underline}
.live{display:flex;gap:8px;align-items:center;margin-top:6px;flex-wrap:wrap}
.pill{font:600 .78rem/1 var(--ui);padding:5px 9px;border-radius:999px}
.pill.on{background:var(--ok-soft);color:var(--ok-ink)}
.pill.new{background:var(--accent-soft);color:var(--accent-ink)}
.since{color:var(--faint);font-size:.82rem}
.desc{margin:0;color:var(--ink);line-height:1.5}
.stats{display:grid;grid-template-columns:repeat(2,1fr);gap:6px;margin:0}
.stats div{background:var(--surface-2);border-radius:var(--r-tile);padding:8px 12px;min-width:0;display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.stats dt{color:var(--faint);font-size:.78rem}
.stats dd{margin:0;font:700 1rem/1.2 var(--ui);font-variant-numeric:tabular-nums;white-space:nowrap}
.ch video{width:100%;aspect-ratio:9/16;background:var(--sunk);border-radius:var(--r-card);display:block;object-fit:cover}
.cap{margin:0;color:var(--muted);font-size:.85rem}
.cap a{color:var(--ink)}
.sources{margin-top:32px;color:var(--faint);font-size:.8rem;line-height:1.55;max-width:90ch}
</style>"""


def build():
    old = PAGE.read_text()
    head = old[: old.index("</head>")]
    head = re.sub(r"<title>.*?</title>", "<title>AI Characters</title>", head, flags=re.S)
    live = [d for d in DATA if d[3]]
    # most popular first (Vilya 2026-11-25): total views from insights; accounts with no posts yet go last
    order = sorted(DATA, key=lambda d: d[7] if d[7] is not None else -1, reverse=True)
    body = f"""<body>
<main class="wrap">
  <section class="hero">
    <h1>Our AI characters</h1>
    <p>{len(DATA)} AI influencers on Instagram, each built around one strange, memorable character. {len(live)} are live,
    3 launch today. Most viewed first. Tap a name to open the profile.</p>
  </section>
  <section class="grid">
{chr(10).join(card(*d) for d in order)}
  </section>
  <p class="sources">Sources. Followers, posts and the most-viewed reel: {READ['profile']} (Yerevan). Views and reach:
  {READ['insights']} (Yerevan); Instagram can still add up to 48 h of data, so an account's total can trail its top
  reel's live count (Rich Ronnie). Days live count from the first post. Dolly Lucy, Strong Arthur and Big Hands Boris post their first reels on
  25 Nov; their videos here are those first reels.</p>
</main>
</body>
</html>
"""
    PAGE.write_text(head + CSS + "\n</head>\n" + body)
    print("wrote", PAGE)


if __name__ == "__main__":
    build()
