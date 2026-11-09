# Website maintenance guide (for people and scheduled agents)

Site: https://www.allfoodmach.com — FOOD LINE automatic packing machines, English B2B inquiry site.
Hosting: GitHub Pages serves `docs/` on branch `main` (custom domain in `docs/CNAME`).
Goal: more qualified visitors from Google, Bing and AI assistants, and more WhatsApp / form inquiries.

## Source of truth
| File | What it holds |
|---|---|
| `config.py` | Brand, domain, WhatsApp, email, analytics IDs, `lastmod` date |
| `data.py` | CATEGORIES, PRODUCTS (specs, FAQ), APPLICATIONS (landing pages), GLOBAL_FAQ, POSTS (blog) |
| `build.py` | Templates, JSON-LD, sitemap, robots.txt, llms.txt / llms-full.txt |
| `assets/` | `style.css`, `img/*.webp`, `video/*.mp4` |
| `CONTENT_PLAN.md` | Topic backlog and log of what was published |

Never edit `docs/` or `dist/` by hand — they are generated.

## Publish workflow
```bash
# 1. edit data.py / build.py / assets
# 2. set config.py "lastmod" to today's date (YYYY-MM-DD)
./publish.sh                 # build + checks + refresh docs/ (stops on any check error)
git add -A && git commit -m "Content: <what changed>" && git push origin main
```
GitHub Pages redeploys in 1–2 minutes.

## Content rules (important)
- **Only state facts that are already in `data.py`** (specs, speeds, ranges, models) or general engineering knowledge that is true for any machine of that type. Do not invent specs, certificates, customer names, testimonials, case studies, factory size, founding year, export-country counts or awards.
- No prices or price ranges on the site (owner decision). Price articles explain cost factors and point to a quote.
- Commercial terms used on the site (confirmed by owner): 30 % T/T deposit + 70 % before shipment after FAT video, L/C at sight for large orders; standard machines 20–35 working days, lines 35–60 days; **18-month warranty** (wear parts excluded) + lifetime technical support; engineers can travel for installation with buyer paying travel, visa, accommodation and daily allowance; remote video support free.
- Model naming: all models use the FL prefix (see each product's `models` field in `data.py`). Never use CY-, SW-, HMD- or LS- names.
- Brand is FOOD LINE. Do not mention any other manufacturer's name.
- Contact is WhatsApp +86 183 3929 5069 only (no email yet). Do not add an email address until `config.py` has one.
- Write in plain, specific English for industrial buyers. Lead every page with a 1–2 sentence direct answer, use question-style H2s, include numbers from the spec data, end with an FAQ of 2–4 real buyer questions.
- Every new application page or post must link to 3–6 relevant product pages (application `products` list does this automatically).
- One topic per page; check `CONTENT_PLAN.md` so you never publish a near-duplicate of an existing page (same keyword intent).

## Adding content
- **Application / landing page** → add a dict to `APPLICATIONS` in `data.py` with `slug, name, img, meta (≤160 chars), lead, body, sections [(h2, html)], faq [(q, a)], products [product slugs]`. `img` must be an existing file name in `assets/img/` without extension.
- **Blog guide** → add a dict at the top of `POSTS` with `slug, title (≤65 chars), meta, date, img, summary, body [(h2, html)]`.
- **Product page** → add to `PRODUCTS` only when real specs and photos exist (ask the owner).
- After adding, `./publish.sh` must report `0 errors`. Fix warnings about title length (>70) on new pages.

## Weekly checklist
1. Publish 1 new item from the top of the backlog in `CONTENT_PLAN.md` and move it to the log with the date and URL.
2. Improve 1 existing page: add a missing FAQ, tighten a meta description, add internal links from older pages to the new one.
3. Run `./publish.sh`, commit, push. Confirm the homepage still loads at https://www.allfoodmach.com/.
4. Report: what was published (URLs), what was improved, and anything the owner needs to supply (photos, specs, analytics data).

## Things only the owner can provide (ask, don't invent)
Real machine photos and videos (YouTube links), customer cases with permission, certificates under the company's own name, company legal name and address, sales email, GA4 measurement ID, Search Console screenshots.
