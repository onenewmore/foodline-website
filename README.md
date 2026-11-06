# Packing-machine export inquiry website

Static, fast, SEO + AI-crawler-friendly B2B site. No database, no plugins — upload `dist/` to any static host.

## Build
```
pip install pillow          # only needed for image sizes
python3 build.py            # -> dist/     (production, clean URLs: /products/xxx/)
python3 build.py --preview  # -> preview/  (opens locally by double-clicking preview/index.html)
```
Edit `config.py` (company info, domain, form endpoint, analytics) and `data.py` (products, specs, FAQ, articles). Images go in `assets/img/` as .webp; videos in `assets/video/`.

## Live site
https://www.allfoodmach.com — served by GitHub Pages from the `docs/` folder of `main`.
To update: edit `config.py` / `data.py`, run `python3 build.py`, then copy `dist/` to `docs/` (keep `docs/CNAME`) and push.

## Deploy elsewhere (Cloudflare Pages or Netlify, free)
1. Create a project, upload the `dist/` folder (or connect a Git repo with build command `python3 build.py`, output `dist`).
2. Point your domain to it, enable HTTPS.
3. Google Search Console + Bing Webmaster Tools → verify → submit `https://your-domain/sitemap.xml`.

## What is built in
**Pages (35 indexable):** home, products hub, 6 category pages, 13 product pages, applications hub + 5 industry pages, about, FAQ, contact, blog + 3 buying guides, privacy policy; thank-you (noindex), 404.

**Technical SEO**
- One H1 per page, unique `<title>` and meta description per page, keyword-led clean URLs
- Canonical, hreflang (en + x-default, ready for more languages), Open Graph / Twitter cards
- Breadcrumb navigation and internal linking (category ↔ product ↔ application ↔ related)
- Spec tables as real HTML `<table>`, image `alt`, width/height, WebP, lazy loading → good Core Web Vitals
- `sitemap.xml` with image entries, `robots.txt`, 404 page, cache headers (`_headers`)

**Structured data (JSON-LD)**: Organization, WebSite, Product (+ additionalProperty specs), BreadcrumbList, FAQPage, VideoObject, ItemList / CollectionPage, BlogPosting, AboutPage, ContactPage.

**AI search / answer-engine (GEO) optimisation**
- `robots.txt` explicitly allows GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-SearchBot, PerplexityBot, Google-Extended, Applebot-Extended and others
- `/llms.txt` (site summary + key facts + links) and `/llms-full.txt` (all specs as Markdown)
- "At a glance" / "Short answer" boxes at the top of each page: self-contained factual sentences that AI assistants can quote
- Question-style headings and FAQ on every product page; numeric specs in plain text
- Content is server-rendered HTML (no JS needed to read it)

**Lead capture**: inquiry form on every page with qualifying fields (product, weight, speed, pack type, voltage), product pre-selected on product pages, honeypot anti-spam, falls back to email if no form endpoint is set; floating WhatsApp button; GA4 `generate_lead` event.

## Placeholders to replace
Everything in `[BRACKETS]` — search the project for `[` after editing `config.py`. See `资料清单_需要你准备.md`.
