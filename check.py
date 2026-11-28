#!/usr/bin/env python3
"""Pre-publish checks for dist/: JSON-LD parses and matches Google rich-result
required fields, no [placeholders], internal links resolve, unique titles and
descriptions, meta descriptions in the Ahrefs-safe band, every indexable page
has at least two incoming dofollow internal links, no redirecting site URLs,
404 canonical, FAQPage matches visible FAQ, root icons. Exit code 1 on any error."""
import os, re, json, sys, html
from urllib.parse import urljoin, urlparse
from config import SITE

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
DOMAIN = SITE["domain"].rstrip("/")  # https://www.allfoodmach.com
errors, warns = [], []
titles, descs = {}, {}
# rel html -> (page path, raw html) for the link graph, filled while scanning
pages = {}

# XML / vocabulary namespaces that are required to stay http:// and are not site URLs.
HTTP_NAMESPACE_PREFIXES = (
    "http://schema.org",
    "http://www.sitemaps.org/",
    "http://www.google.com/schemas/",
    "http://www.w3.org/",
    "http://purl.org/",
)
DURATION_RE = re.compile(r"^P(?=\d|T)(?:\d+Y)?(?:\d+M)?(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$")

def types_of(node):
    t = node.get("@type")
    if t is None:
        return []
    return list(t) if isinstance(t, list) else [t]

def is_file_path(path):
    last = path.rstrip("/").split("/")[-1]
    return "." in last

def directory_missing_slash(path):
    """GitHub Pages 301s a directory URL that omits the trailing slash."""
    if not path or path == "/":
        return False
    if path.endswith("/"):
        return False
    return not is_file_path(path)

def check_site_url(u, rel, where):
    if not u or u.startswith(("mailto:", "tel:", "data:")):
        return
    if u.startswith("http://"):
        if u.startswith(HTTP_NAMESPACE_PREFIXES):
            return
        errors.append(f"{rel}: http:// URL in {where}: {u[:140]}")
        return
    if u.startswith("//"):
        errors.append(f"{rel}: protocol-relative URL in {where}: {u[:140]}")
        return
    if not u.startswith("https://") and not u.startswith("/"):
        return
    if u.startswith("https://"):
        host = urlparse(u).netloc.lower()
        if host == "allfoodmach.com":
            errors.append(f"{rel}: non-www URL in {where}: {u[:140]}")
            return
        if host != "www.allfoodmach.com":
            return
        path = urlparse(u).path or "/"
    else:
        path = u.split("#", 1)[0].split("?", 1)[0]
    if directory_missing_slash(path):
        errors.append(f"{rel}: directory URL missing trailing slash in {where}: {u[:140]}")

def price_is_real(value):
    """A Google Offer price must be a number greater than zero. Zero means free."""
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        try:
            return float(value) > 0
        except ValueError:
            return False
    return False

def validate_offer(node, rel, path):
    tset = set(types_of(node))
    if "AggregateOffer" in tset:
        if not price_is_real(node.get("lowPrice")) or not node.get("priceCurrency"):
            errors.append(f"{rel}: AggregateOffer needs lowPrice > 0 and priceCurrency at {path}")
        return
    spec = node.get("priceSpecification") if isinstance(node.get("priceSpecification"), dict) else {}
    price = node.get("price", spec.get("price"))
    if not price_is_real(price):
        errors.append(f"{rel}: Offer price must be a number greater than 0 (do not use 0 or a made-up price) at {path}")

def validate_typed(node, rel, path):
    tset = set(types_of(node))
    if "Product" in tset:
        errors.append(
            f"{rel}: @type Product at {path} is a Google product snippet and requires offers, "
            "review, or aggregateRating. This catalogue is quote-only — use ProductModel and do not invent a price or rating")
    if "ProductModel" in tset:
        for key in ("name", "description", "url"):
            if not node.get(key):
                errors.append(f"{rel}: ProductModel missing {key} at {path}")
        if any(k in node for k in ("offers", "review", "aggregateRating")):
            errors.append(f"{rel}: ProductModel must not include offers, review, or aggregateRating at {path}")
        check_site_url(node.get("url") or "", rel, path + ".url")
    if "Offer" in tset or "AggregateOffer" in tset:
        validate_offer(node, rel, path)
    if "VideoObject" in tset:
        for key in ("name", "thumbnailUrl", "uploadDate"):
            if not node.get(key):
                errors.append(f"{rel}: VideoObject missing required {key} at {path}")
        upload = node.get("uploadDate")
        if isinstance(upload, str) and not ISO_DATE_RE.match(upload):
            errors.append(f"{rel}: VideoObject uploadDate is not ISO 8601 at {path}")
        duration = node.get("duration")
        if isinstance(duration, str) and not DURATION_RE.match(duration):
            errors.append(f"{rel}: VideoObject duration is not ISO 8601 at {path}")
        thumb = node.get("thumbnailUrl")
        thumbs = thumb if isinstance(thumb, list) else [thumb]
        for t in thumbs:
            if isinstance(t, str):
                check_site_url(t, rel, path + ".thumbnailUrl")
    if "BreadcrumbList" in tset:
        items = node.get("itemListElement") or []
        if not isinstance(items, list) or len(items) < 2:
            errors.append(f"{rel}: BreadcrumbList needs at least two ListItems at {path}")
        else:
            for i, it in enumerate(items):
                if not isinstance(it, dict):
                    errors.append(f"{rel}: breadcrumb {i + 1} is not a ListItem")
                    continue
                if "position" not in it or not it.get("name"):
                    errors.append(f"{rel}: breadcrumb {i + 1} missing position or name")
                if i < len(items) - 1 and not it.get("item"):
                    errors.append(f"{rel}: breadcrumb {i + 1} missing item URL")
                item = it.get("item")
                if isinstance(item, str):
                    check_site_url(item, rel, f"{path}.itemListElement[{i}].item")
    if tset & {"Article", "NewsArticle", "BlogPosting"}:
        # Google currently treats these as recommended. Requiring them keeps every
        # guide eligible and stops a page shipping with an empty article node.
        if not node.get("headline"):
            errors.append(f"{rel}: article missing headline at {path}")
        if not node.get("image"):
            errors.append(f"{rel}: article missing image at {path}")
        if not node.get("datePublished"):
            errors.append(f"{rel}: article missing datePublished at {path}")
        author = node.get("author")
        author_name = author.get("name") if isinstance(author, dict) else author
        if not author_name:
            errors.append(f"{rel}: article missing author.name at {path}")
        image = node.get("image")
        images = image if isinstance(image, list) else [image]
        for img in images:
            if isinstance(img, str):
                check_site_url(img, rel, path + ".image")
            elif isinstance(img, dict):
                check_site_url(img.get("url") or img.get("contentUrl") or "", rel, path + ".image")
    if "FAQPage" in tset:
        entities = node.get("mainEntity") or []
        if not entities:
            errors.append(f"{rel}: FAQPage has no mainEntity at {path}")
        for i, q in enumerate(entities):
            if not isinstance(q, dict) or not (q.get("name") or "").strip():
                errors.append(f"{rel}: FAQ question {i + 1} missing name")
            answer = (q.get("acceptedAnswer") or {}).get("text") if isinstance(q, dict) else ""
            if not (answer or "").strip():
                errors.append(f"{rel}: FAQ question {i + 1} missing acceptedAnswer.text")
    if tset & {"Organization", "Manufacturer"}:
        # Article authors are a small Organization (name + url). The company node
        # is the one with @id ...#organization, a logo, or a contactPoint.
        is_company = (str(node.get("@id", "")).endswith("#organization") or "logo" in node
                      or "contactPoint" in node or "Manufacturer" in tset)
        if not is_company:
            if not node.get("name"):
                errors.append(f"{rel}: Organization author missing name at {path}")
            if node.get("url"):
                check_site_url(node.get("url") or "", rel, path + ".url")
        else:
            for key in ("name", "url", "description", "logo", "telephone"):
                if not node.get(key):
                    errors.append(f"{rel}: Organization missing {key} at {path}")
            check_site_url(node.get("url") or "", rel, path + ".url")
            logo = node.get("logo")
            if isinstance(logo, str):
                check_site_url(logo, rel, path + ".logo")
            elif isinstance(logo, dict):
                logo_url = logo.get("url") or logo.get("contentUrl")
                if not logo_url:
                    errors.append(f"{rel}: Organization logo ImageObject missing url at {path}")
                else:
                    check_site_url(logo_url, rel, path + ".logo")
                for dim in ("width", "height"):
                    if not isinstance(logo.get(dim), int) or logo.get(dim) < 112:
                        errors.append(f"{rel}: Organization logo {dim} must be an integer ≥ 112 at {path}")
            elif logo:
                errors.append(f"{rel}: Organization logo must be a URL or ImageObject at {path}")
            cp = node.get("contactPoint")
            if isinstance(cp, list):
                cp = cp[0] if cp else None
            if not isinstance(cp, dict) or not cp.get("telephone") or not cp.get("url"):
                errors.append(f"{rel}: Organization contactPoint needs telephone and url at {path}")
            elif isinstance(cp, dict):
                check_site_url(cp.get("url") or "", rel, path + ".contactPoint.url")
                if not str(cp.get("url", "")).rstrip("/").endswith("/contact"):
                    errors.append(f"{rel}: Organization contactPoint url must be the /contact/ page")
            legal = node.get("legalName")
            if isinstance(legal, str) and (legal == node.get("name") or "[" in legal):
                errors.append(f"{rel}: legalName must be a real registered name different from the brand, or be omitted")
            addr = node.get("address")
            if isinstance(addr, dict):
                for key in ("streetAddress", "addressLocality", "addressCountry"):
                    if not addr.get(key) or "[" in str(addr.get(key)):
                        errors.append(f"{rel}: PostalAddress missing real {key} — omit address until config.py has it")
            if node.get("email") == "" or (isinstance(node.get("email"), str) and "[" in node["email"]):
                errors.append(f"{rel}: do not emit an empty or placeholder email")
            if isinstance(cp, dict) and "email" in cp and (cp.get("email") == "" or "[" in str(cp.get("email"))):
                errors.append(f"{rel}: do not emit an empty or placeholder contactPoint email")
    if "ItemList" in tset:
        elements = node.get("itemListElement") or []
        if not elements:
            errors.append(f"{rel}: ItemList has no itemListElement at {path}")
        for i, it in enumerate(elements):
            if isinstance(it, dict) and "position" not in it:
                errors.append(f"{rel}: ItemList entry {i + 1} missing position")

def norm_page(path):
    path = path.split("#", 1)[0].split("?", 1)[0]
    if path.endswith("/index.html"):
        path = path[:-len("index.html")]
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and not path.endswith("/") and not is_file_path(path):
        path += "/"
    return path

def page_path(rel):
    if rel == "index.html":
        return "/"
    if rel == "404.html":
        return "/404.html"
    if rel.endswith("/index.html"):
        return "/" + rel[:-len("index.html")]
    return "/" + rel

for dirpath, _, files in os.walk(DIST):
    for f in files:
        if not f.endswith(".html"):
            continue
        p = os.path.join(dirpath, f)
        rel = os.path.relpath(p, DIST).replace("\\", "/")
        s = open(p, encoding="utf-8").read()
        pages[rel] = s
        ld_faqs = []
        for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try:
                data = json.loads(m)
            except Exception as e:
                errors.append(f"{rel}: bad JSON-LD ({e})")
                continue
            def walk(o, path="$"):
                if isinstance(o, dict):
                    if "@type" in o:
                        validate_typed(o, rel, path)
                    for k, v in o.items():
                        if v == "" or v is None:
                            errors.append(f"{rel}: empty JSON-LD value at {path}.{k}")
                        else:
                            walk(v, path + "." + str(k))
                elif isinstance(o, list):
                    if not o:
                        errors.append(f"{rel}: empty JSON-LD array at {path}")
                    for i, v in enumerate(o):
                        walk(v, f"{path}[{i}]")
                elif isinstance(o, str) and "[" in o:
                    errors.append(f"{rel}: placeholder in JSON-LD at {path} ({o[:80]})")
                elif isinstance(o, str) and (o.startswith("http") or o.startswith("/")):
                    check_site_url(o, rel, path)
            walk(data)
            for node in data.get("@graph", [data]):
                if isinstance(node, dict) and node.get("@type") == "FAQPage":
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
            dlen = len(html.unescape(d))
            if not 115 <= dlen <= 155:
                errors.append(f"{rel}: description {dlen} chars (required 115–155)")
            if s.count("<h1") != 1: errors.append(f"{rel}: {s.count('<h1')} <h1> tags")
            if "/products/" in ("/" + rel) and '"@type":"ProductModel"' not in s:
                errors.append(f"{rel}: product URL missing ProductModel JSON-LD")
            if re.search(r'"@type":"Product"', s) or re.search(r'"@type":\[(?:"[^"]*",)*"Product"', s):
                errors.append(f"{rel}: literal @type Product is not allowed on quote-only pages")
        if rel == "404.html":
            if re.search(r'rel="canonical"', s):
                errors.append(f"{rel}: 404 page must not emit a canonical URL (it would point at /404/, which 404s)")
            if 'content="noindex' not in s:
                errors.append(f"{rel}: missing noindex")
            if re.search(r'property="og:url" content="[^"]*/404/?', s):
                errors.append(f"{rel}: og:url points at /404/")
        for href in re.findall(r'(?:href|src)="([^"#:?]+)"', s):
            # Root-absolute paths (used by 404.html) and off-site URLs are not files next to this page.
            if href.startswith(("http", "mailto", "tel", "//", "data:", "/")):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(p), href))
            if href.endswith("/"):
                target = os.path.join(target, "index.html")
            if not os.path.exists(target):
                errors.append(f"{rel}: broken link {href}")
        for href in re.findall(r'(?:href|src|content)="([^"]+)"', s):
            if href.startswith(("http://", "https://", "/")):
                check_site_url(href, rel, "href/src/content")

for k, v in titles.items():
    if len(v) > 1: errors.append(f"duplicate title on {v}")
for k, v in descs.items():
    if len(v) > 1: errors.append(f"duplicate description on {v}")

for req in ("favicon.ico", "apple-touch-icon.png", "assets/favicon.svg", "assets/logo.png",
            "robots.txt", "sitemap.xml", "llms.txt", "llms-full.txt"):
    if not os.path.exists(os.path.join(DIST, req)):
        errors.append(f"missing {req}")
app_hub = os.path.join(DIST, "applications", "index.html")
if os.path.exists(app_hub) and '"@type":"ItemList"' not in open(app_hub, encoding="utf-8").read():
    errors.append("applications/index.html: missing ItemList JSON-LD")

# Dofollow internal link graph. Self-links do not count. One source page counts once.
indexable = {}
for rel, s in pages.items():
    if rel == "404.html" or 'name="robots" content="noindex' in s:
        continue
    indexable[norm_page(page_path(rel))] = rel
incoming = {path: set() for path in indexable}
for rel, s in pages.items():
    src = norm_page(page_path(rel))
    if src not in indexable:
        continue
    base = DOMAIN + src
    for tag in re.findall(r"<a\b[^>]*>", s, re.I):
        hm = re.search(r'href="([^"]*)"', tag)
        if not hm:
            continue
        href = html.unescape(hm.group(1)).strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
            continue
        rm = re.search(r'rel="([^"]*)"', tag, re.I)
        if rm and "nofollow" in rm.group(1).lower():
            continue
        if href.startswith("//"):
            continue
        abs_url = urljoin(base, href)
        host = urlparse(abs_url).netloc.lower()
        if host and host not in ("www.allfoodmach.com", "allfoodmach.com"):
            continue
        target = norm_page(urlparse(abs_url).path or "/")
        if target in incoming and target != src:
            incoming[target].add(src)
for path, sources in sorted(incoming.items()):
    if len(sources) < 2:
        errors.append(f"{indexable[path]}: only {len(sources)} incoming dofollow internal link(s); need at least 2")

for name in ("sitemap.xml", "robots.txt", "llms.txt", "llms-full.txt", "_headers"):
    fp = os.path.join(DIST, name)
    if not os.path.exists(fp):
        continue
    text = open(fp, encoding="utf-8").read()
    for u in re.findall(r"https?://[^\s<\"')]+", text):
        check_site_url(u, name, "text")

for w in warns: print("WARN ", w)
for e in errors: print("ERROR", e)
print(f"{len(titles)} indexable pages checked, {len(errors)} errors, {len(warns)} warnings")
sys.exit(1 if errors else 0)
