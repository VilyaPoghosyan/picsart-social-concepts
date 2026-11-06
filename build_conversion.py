#!/usr/bin/env python3
"""Conversion page (conversion/index.html): how many people the five brands send to Picsart and how many convert.

Same one-page layout as the conversion analyzer's PNG report (Tigran's render.py), made responsive with a dark mode.
Reads the newest run file in ~/vilya-ai/context/reports/conversion/runs/, written by the conversion-analyzer agent.
Reads only local files; posts nothing.

Run: python3 onepagers/build_conversion.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = Path.home() / "vilya-ai/context/reports/conversion"

# Responsive width, phone layout and dark mode on top of the report's own CSS.
SITE_CSS = """
.wrap { width:auto; max-width:1040px; margin:0 auto; }
.top { font-size:13px; } .top a { color:var(--accent); text-decoration:none; }
.card { overflow-x:auto; }
@media (max-width:760px) {
  .wrap { padding:20px 16px; }
  .kpis { grid-template-columns:repeat(2,1fr); }
  .row { grid-template-columns:1fr; }
  h1 { font-size:21px; }
}
@media (prefers-color-scheme:dark) {
  :root:not([data-theme="light"]) { --bg:#101015; --card:#18181F; --fg:#F3F2F7; --muted:#A19FAD; --line:#28282F;
    --bad:#F0706A; --accent:#7C93F0; --na:#6C6A78; }
}
:root[data-theme="dark"] { --bg:#101015; --card:#18181F; --fg:#F3F2F7; --muted:#A19FAD; --line:#28282F;
  --bad:#F0706A; --accent:#7C93F0; --na:#6C6A78; }
"""


def load_render():
    spec = importlib.util.spec_from_file_location("render", REPORT / "render.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    render = load_render()
    run = max((REPORT / "runs").glob("*.json"))
    page = render.build(json.loads(run.read_text()))
    page = page.replace(
        "<title>Social conversion report</title>",
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Social Conversion · Picsart Social</title>"
        '<meta name="description" content="How many people the five Picsart social brands send to Picsart, and how many sign up or buy.">',
    )
    page = page.replace("</style>", SITE_CSS + "</style>", 1)
    page = page.replace('<div class="wrap">', '<div class="wrap"><div class="top"><a href="../">Picsart Social</a></div>', 1)
    if any(c in page for c in render.BANNED):
        raise SystemExit("Refusing to write: the page contains an em-dash or en-dash.")
    out = HERE / "conversion" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page)
    print(f"{out} from {run.name}")


if __name__ == "__main__":
    main()
