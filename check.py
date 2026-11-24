#!/usr/bin/env python3
"""Pre-publish checks for dist/: JSON-LD parses, no [placeholders], internal links resolve,
unique titles/descriptions, title and description lengths, 404 canonical, FAQPage matches
visible FAQ, root icons. Exit code 1 on any error."""
import os, re, json, sys, html

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
errors, warns = [], []
titles, descs = {}, {}

for dirpath, _, files in os.walk(DIST):
    for f in files:
        if not f.endswith(".html"):
            continue
        p = os.path.join(dirpath, f)
        rel = os.path.relpath(p, DIST)
        s = open(p, encoding="utf-8").read()
        ld_faqs = []
        for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try:
                data = json.loads(m)
            except Exception as e:
                errors.append(f"{rel}: bad JSON-LD ({e})")
                continue
            def walk(o, path="$"):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if v == "" or v is None:
                            errors.append(f"{rel}: empty JSON-LD value at {path}.{k}")
                        else:
                            walk(v, path + "." + str(k))
                elif isinstance(o, list):
                    for i, v in enumerate(o):
                        walk(v, f"{path}[{i}]")
                elif isinstance(o, str) and o.startswith("http") and "[" in o:
                    errors.append(f"{rel}: placeholder URL in JSON-LD ({o[:80]})")
            walk(data)
            for node in data.get("@graph", [data]):
                if node.get("@type") == "FAQPage":
                    for ent in node.get("mainEntity") or []:
                        q = ent.get("name") or ""
                        a = (ent.get("acceptedAnswer") or {}).get("text") or ""
                        ld_faqs.append((q, a))
                        if not q.strip() or not a.strip():
                            errors.append(f"{rel}: FAQPage question or answer is empty")
        visible = [(html.unescape(q), html.unescape(a)) for q, a in re.findall(
            r'<details class="faq"><summary>(.*?)</summary><div class="a"><p>(.*?)</p></div></details>', s)]
        if visible != ld_faqs:
            errors.append(f"{rel}: FAQPage JSON-LD does not match the visible FAQ ({len(visible)} on page, {len(ld_faqs)} in JSON-LD)")
        text = re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S)
        for ph in re.findall(r"\[[A-Za-z][^\]<>\"]{1,80}\]", re.sub(r"<[^>]+>", " ", text)):
            errors.append(f"{rel}: visible placeholder {ph}")
        if 'name="robots" content="noindex' not in s and rel != "404.html":
            t = re.search(r"<title>(.*?)</title>", s, re.S).group(1)
            d = re.search(r'<meta name="description" content="(.*?)">', s, re.S).group(1)
            titles.setdefault(t, []).append(rel); descs.setdefault(d, []).append(rel)
            if len(html.unescape(t)) > 70: warns.append(f"{rel}: title {len(html.unescape(t))} chars (>70)")
            if not 70 <= len(html.unescape(d)) <= 170: warns.append(f"{rel}: description {len(html.unescape(d))} chars")
            if s.count("<h1") != 1: errors.append(f"{rel}: {s.count('<h1')} <h1> tags")
        if rel == "404.html":
            if re.search(r'rel="canonical"', s):
                errors.append(f"{rel}: 404 page must not emit a canonical URL (it would point at /404/, which 404s)")
            if 'content="noindex' not in s:
                errors.append(f"{rel}: missing noindex")
            if re.search(r'property="og:url" content="[^"]*/404/?', s):
                errors.append(f"{rel}: og:url points at /404/")
            continue
        for href in re.findall(r'(?:href|src)="([^"#:?]+)"', s):
            if href.startswith(("http", "mailto", "tel", "//", "data:")):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(p), href))
            if href.endswith("/"):
                target = os.path.join(target, "index.html")
            if not os.path.exists(target):
                errors.append(f"{rel}: broken link {href}")

for k, v in titles.items():
    if len(v) > 1: errors.append(f"duplicate title on {v}")
for k, v in descs.items():
    if len(v) > 1: errors.append(f"duplicate description on {v}")

for req in ("favicon.ico", "apple-touch-icon.png", "assets/favicon.svg", "robots.txt", "sitemap.xml", "llms.txt", "llms-full.txt"):
    if not os.path.exists(os.path.join(DIST, req)):
        errors.append(f"missing {req}")
app_hub = os.path.join(DIST, "applications", "index.html")
if os.path.exists(app_hub) and '"@type":"ItemList"' not in open(app_hub, encoding="utf-8").read():
    errors.append("applications/index.html: missing ItemList JSON-LD")

for w in warns: print("WARN ", w)
for e in errors: print("ERROR", e)
print(f"{len(titles)} indexable pages checked, {len(errors)} errors, {len(warns)} warnings")
sys.exit(1 if errors else 0)
