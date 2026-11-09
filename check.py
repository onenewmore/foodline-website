#!/usr/bin/env python3
"""Pre-publish checks for dist/: JSON-LD parses, no [placeholders], internal links resolve,
unique titles/descriptions, title and description lengths. Exit code 1 on any error."""
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
        for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try:
                json.loads(m)
            except Exception as e:
                errors.append(f"{rel}: bad JSON-LD ({e})")
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

for w in warns: print("WARN ", w)
for e in errors: print("ERROR", e)
print(f"{len(titles)} indexable pages checked, {len(errors)} errors, {len(warns)} warnings")
sys.exit(1 if errors else 0)
