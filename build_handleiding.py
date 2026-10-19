"""Zet de wiki-pagina's (../sumo-tools-wiki/*.md) om naar HTML in handleiding/.

De wiki blijft de bron. Na een aanpassing in de wiki:  python build_handleiding.py
Ondersteunt het beperkte Markdown dat de wiki gebruikt: koppen, alinea's,
lijsten, tabellen, codeblokken, **vet**, `code`, [tekst](url) en [[Wiki-links]].
"""
import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WIKI = os.path.join(os.path.dirname(HERE), "sumo-tools-wiki")
OUT = os.path.join(HERE, "handleiding")
SITE = "https://wimmichiels76.github.io/sumo-tools/"

# volgorde in de navigatie
PAGES = ["Home", "netconvert Batch Generator", "SUMO Simulation Manager", "SUMO VRI Manager",
         "SUMO TLS Editor", "SUMO E1 Detector Linker", "SUMO TripInfo Analyzer", "SUMO Network Link Manager", "SUMO Decal Generator"]


def slug(name):
    return "index" if name == "Home" else name.replace(" ", "-")


def inline(t):
    t = html.escape(t, quote=False)
    codes = []
    t = re.sub(r"`([^`]+)`", lambda m: codes.append(m.group(1)) or f"\x00{len(codes) - 1}\x00", t)
    t = re.sub(r"\[\[([^\]]+)\]\]", lambda m: f'<a href="{slug(m.group(1))}.html">{m.group(1)}</a>', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{link(m.group(2))}">{m.group(1)}</a>', t)
    t = re.sub(r"(?<![\"'>=])(https?://[^\s<)]+)", lambda m: f'<a href="{link(m.group(1))}">{m.group(1)}</a>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\w)\*([^*]+)\*(?!\w)", r"<i>\1</i>", t)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{codes[int(m.group(1))]}</code>", t)


def link(url):
    # tools op dezelfde site: relatief, zodat het ook lokaal werkt
    return "../" + url[len(SITE):] if url.startswith(SITE) else url


def convert(md):
    lines = md.replace("\r\n", "\n").split("\n")
    out, i, title = [], 0, None
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
            continue
        m = re.match(r"(#{1,3}) (.*)", ln)
        if m:
            lvl = len(m.group(1))
            if lvl == 1 and title is None:
                title = m.group(2)
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], [r for r in rows[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
                       + "</tbody></table>")
            continue
        if re.match(r"\s*([-*]|\d+\.) ", ln):
            i = parse_list(lines, i, out)
            continue
        if not ln.strip():
            i += 1
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r"(#{1,3} |```|\||\s*([-*]|\d+\.) )", lines[i]):
            para.append(lines[i].strip())
            i += 1
        out.append("<p>" + inline(" ".join(para)) + "</p>")
    return title, "\n".join(out)


def parse_list(lines, i, out, indent=0):
    ordered = bool(re.match(r"\s*\d+\. ", lines[i]))
    out.append("<ol>" if ordered else "<ul>")
    while i < len(lines):
        m = re.match(r"(\s*)([-*]|\d+\.) (.*)", lines[i])
        if not m or len(m.group(1)) < indent:
            break
        if len(m.group(1)) > indent:
            out[-1] = out[-1].removesuffix("</li>")
            i = parse_list(lines, i, out, len(m.group(1)))
            out.append("</li>")
            continue
        out.append(f"<li>{inline(m.group(3))}</li>")
        i += 1
    out.append("</ol>" if ordered else "</ul>")
    return i


TEMPLATE = """<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Handleiding SUMO-tools</title>
<style>
  :root {{ --bg:#f6f7f9; --card:#fff; --fg:#1d2330; --muted:#5b6475; --line:#e2e5eb; --accent:#1f6feb; --code:#eef1f5; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#14171c; --card:#1c2027; --fg:#e6e9ef; --muted:#9aa3b2; --line:#2c323c; --accent:#58a6ff; --code:#262b34; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  .wrap {{ max-width:1040px; margin:0 auto; padding:32px 16px 64px; display:grid; grid-template-columns:220px minmax(0,1fr); gap:32px; }}
  @media (max-width:760px) {{ .wrap {{ grid-template-columns:1fr; gap:16px; }} nav {{ position:static !important; }} }}
  nav {{ position:sticky; top:24px; align-self:start; font-size:14px; }}
  nav .home {{ display:block; font-weight:700; margin-bottom:12px; color:var(--fg); text-decoration:none; }}
  nav a {{ display:block; padding:6px 10px; border-radius:6px; color:var(--muted); text-decoration:none; }}
  nav a:hover {{ color:var(--fg); background:var(--card); }}
  nav a.active {{ color:var(--accent); background:var(--card); border:1px solid var(--line); }}
  nav .back {{ margin-top:16px; font-size:13px; }}
  article {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:28px 32px; min-width:0; }}
  @media (max-width:760px) {{ article {{ padding:20px 18px; }} }}
  h1 {{ margin:0 0 12px; font-size:28px; line-height:1.25; }}
  h2 {{ margin:32px 0 8px; font-size:20px; padding-bottom:6px; border-bottom:1px solid var(--line); }}
  h3 {{ margin:22px 0 6px; font-size:16px; }}
  a {{ color:var(--accent); }}
  code {{ font-family:ui-monospace, Consolas, monospace; font-size:.88em; background:var(--code); padding:1px 5px; border-radius:4px; }}
  pre {{ background:var(--code); padding:12px 14px; border-radius:8px; overflow-x:auto; }}
  pre code {{ background:none; padding:0; }}
  table {{ border-collapse:collapse; width:100%; margin:12px 0; font-size:15px; display:block; overflow-x:auto; }}
  th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ color:var(--muted); font-weight:600; }}
  li {{ margin:4px 0; }}
</style>
</head>
<body>
<div class="wrap">
  <nav>
    <a class="home" href="index.html">Handleiding</a>
{nav}
    <a class="back" href="../index.html">← alle tools</a>
  </nav>
  <article>
{body}
  </article>
</div>
</body>
</html>
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    for name in PAGES:
        md = open(os.path.join(WIKI, name.replace(" ", "-") + ".md"), encoding="utf-8").read()
        title, body = convert(md)
        nav = "\n".join(f'    <a href="{slug(p)}.html"{" class=\"active\"" if p == name else ""}>{"Overzicht" if p == "Home" else p}</a>'
                        for p in PAGES)
        with open(os.path.join(OUT, slug(name) + ".html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(TEMPLATE.format(title=html.escape(title or name), nav=nav, body=body))
        print("geschreven:", slug(name) + ".html")


if __name__ == "__main__":
    main()
