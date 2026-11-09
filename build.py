#!/usr/bin/env python3
"""Static site generator for the packing-machine export inquiry website.

    python3 build.py            -> ./dist      (production: clean URLs, upload to your host)
    python3 build.py --preview  -> ./preview   (links point to index.html, for local/file preview)
"""
import os, sys, json, shutil, html
from config import SITE
from data import CATEGORIES, PRODUCTS, APPLICATIONS, GLOBAL_FAQ, POSTS

PREVIEW = "--preview" in sys.argv
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "preview" if PREVIEW else "dist")
B = SITE["brand"]
D = SITE["domain"].rstrip("/")
E = html.escape
def has(v): return bool(v) and "[" not in str(v)
EMAIL = SITE["email"] if has(SITE["email"]) else ""
LEGAL = SITE["legal_name"] if has(SITE["legal_name"]) else SITE["brand"]
CONTACT_TXT = (f"email {EMAIL}, " if EMAIL else "") + f"WhatsApp {SITE['phone']}"

CAT = {c["slug"]: c for c in CATEGORIES}
PROD = {p["slug"]: p for p in PRODUCTS}
SITEMAP = []

IMG_SIZES = {}
try:
    from PIL import Image
    for f in os.listdir(os.path.join(ROOT, "assets", "img")):
        with Image.open(os.path.join(ROOT, "assets", "img", f)) as im:
            IMG_SIZES[f.rsplit(".", 1)[0]] = im.size
except Exception:
    pass

# ---------------------------------------------------------------- helpers
def url(path):
    """absolute canonical URL for a site path like 'products/x/'"""
    return D + "/" + path.lstrip("/")

class Page:
    def __init__(self, path):
        self.path = path.strip("/")                  # '' for home, 'products/x' etc.
        self.depth = 0 if self.path == "" else self.path.count("/") + 1
    def rel(self, target):
        """relative link from this page to target site path"""
        target = target.strip("/")
        up = "../" * self.depth
        if target == "":
            return (up or "./") + ("index.html" if PREVIEW else "")
        if "." in target.split("/")[-1]:             # a file
            return up + target
        return up + target + ("/index.html" if PREVIEW else "/")

def img_tag(pg, name, alt, cls="", eager=False, sizes=None):
    if not name:
        return '<div class="noimg">Photo coming soon</div>'
    w, h = IMG_SIZES.get(name, (800, 800))
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return f'<img src="{pg.rel("assets/img/"+name+".webp")}" alt="{E(alt)}" width="{w}" height="{h}" {load} class="{cls}">'

def wa_link(topic):
    from urllib.parse import quote
    return f"https://wa.me/{SITE['whatsapp']}?text=" + quote(f"Hello {B}, I'm interested in: {topic}. Please send me details and price.")

def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "</script>"

ORG_ID = D + "/#organization"
def org_ld():
    o = {"@type": "Organization", "@id": ORG_ID, "name": B, "legalName": LEGAL, "url": D + "/",
         "logo": url("assets/logo.png"), "telephone": SITE["phone"],
         "address": ({"@type": "PostalAddress", "streetAddress": SITE["address"], "addressLocality": SITE["city"],
                     "addressRegion": SITE["region"], "postalCode": SITE["postal"], "addressCountry": SITE["country"]} if has(SITE["address"]) else {"@type": "PostalAddress", "addressCountry": SITE["country"]}),
         "contactPoint": [{"@type": "ContactPoint", "contactType": "sales", "telephone": SITE["phone"],
                           "availableLanguage": ["English", "Chinese"], "areaServed": "Worldwide"}],
         "description": f"{B} designs and manufactures automatic packing machines and complete packaging lines for powder, granules, liquids and solid products.",
         **({"foundingDate": SITE["founded"]} if has(SITE["founded"]) else {}),
         "knowsAbout": ["packing machine", "vertical form fill seal machine", "multihead weigher", "stick pack machine", "sachet packing machine", "premade pouch packing machine", "flow wrap machine", "filling and capping line"]}
    same = [v for v in SITE["social"].values() if v]
    if same: o["sameAs"] = same
    return o

def crumbs_ld(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": url(p)} for i, (n, p) in enumerate(items)]}

def crumbs_html(pg, items):
    lis = []
    for i, (n, p) in enumerate(items):
        if i == len(items) - 1:
            lis.append(f'<li aria-current="page">{E(n)}</li>')
        else:
            lis.append(f'<li><a href="{pg.rel(p)}">{E(n)}</a></li>')
    return f'<nav class="crumbs wrap" aria-label="Breadcrumb"><ol>{"".join(lis)}</ol></nav>'

def faq_ld(faqs):
    return {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q,
            "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}

def faq_html(faqs):
    return "".join(f'<details class="faq"><summary>{E(q)}</summary><div class="a"><p>{E(a)}</p></div></details>' for q, a in faqs)

LOGO_SVG = '<svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true"><rect width="34" height="34" rx="7" fill="#e4572e"/><path d="M9 10h16v4H9zM9 16h10v4H9zM9 22h16v4H9z" fill="#fff"/></svg>'
WA_SVG = '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 3C9 3 3.3 8.6 3.3 15.6c0 2.4.7 4.7 1.9 6.7L3 29l6.9-2.2c1.9 1 4 1.6 6.1 1.6 7 0 12.7-5.7 12.7-12.7S23 3 16 3zm0 23.1c-2 0-3.9-.6-5.5-1.6l-.4-.2-4.1 1.3 1.3-4-.3-.4c-1.1-1.7-1.7-3.6-1.7-5.6C5.3 9.8 10.1 5 16 5s10.6 4.8 10.6 10.6S21.9 26.1 16 26.1zm5.8-7.9c-.3-.2-1.9-.9-2.2-1-.3-.1-.5-.2-.7.2-.2.3-.8 1-1 1.2-.2.2-.4.2-.7.1-.3-.2-1.3-.5-2.5-1.6-.9-.8-1.6-1.8-1.7-2.1-.2-.3 0-.5.1-.6l.5-.6c.2-.2.2-.3.3-.5.1-.2 0-.4 0-.6l-1-2.4c-.3-.6-.5-.5-.7-.5h-.6c-.2 0-.6.1-.9.4-.3.3-1.2 1.1-1.2 2.8s1.2 3.2 1.4 3.5c.2.2 2.4 3.6 5.7 5 .8.4 1.4.6 1.9.7.8.3 1.5.2 2.1.1.6-.1 1.9-.8 2.2-1.5.3-.7.3-1.4.2-1.5-.1-.1-.3-.2-.6-.4z"/></svg>'

def header(pg, active=""):
    nav = [("Products", "products"), ("Applications", "applications"), ("About", "about"), ("Blog", "blog"), ("FAQ", "faq"), ("Contact", "contact")]
    lis = "".join(f'<li><a href="{pg.rel(p)}"{" aria-current=\"page\"" if active == p else ""}>{n}</a></li>' for n, p in nav)
    return f'''<a class="skip" href="#main">Skip to content</a>
<div class="topbar"><div class="wrap"><span>Factory-direct packing machines · Free sample testing</span>{f'<a href="mailto:{EMAIL}">{EMAIL}</a>' if EMAIL else ""}<a href="https://wa.me/{SITE["whatsapp"]}" rel="nofollow">WhatsApp {E(SITE["phone"])}</a></div></div>
<header class="site"><div class="wrap">
<a class="logo" href="{pg.rel("")}" aria-label="{E(B)} home">{LOGO_SVG}<span>{E(B)}</span></a>
<button class="menu-btn" aria-expanded="false" aria-controls="mainnav" onclick="var n=document.getElementById('mainnav');var o=n.classList.toggle('open');this.setAttribute('aria-expanded',o)">Menu</button>
<nav class="main" id="mainnav" aria-label="Main"><ul>{lis}<li><a class="btn btn-primary" href="{pg.rel("contact")}#quote">Get a Quote</a></li></ul></nav>
</div></header>'''

def footer(pg, topic="your packing machine"):
    cats = "".join(f'<li><a href="{pg.rel("products/"+c["slug"])}">{E(c["short"])}</a></li>' for c in CATEGORIES)
    apps = "".join(f'<li><a href="{pg.rel("applications/"+a["slug"])}">{E(a["name"])}</a></li>' for a in APPLICATIONS)
    return f'''<footer class="site"><div class="wrap"><div class="fgrid">
<div><a class="logo" href="{pg.rel("")}" style="color:#fff">{LOGO_SVG}<span>{E(B)}</span></a>
<p style="margin-top:14px">{E(SITE["tagline"])} — powder, granule, liquid and solid product packing, from single machines to turnkey lines.</p>
<address style="font-style:normal">{E(LEGAL)}<br>{E(SITE["address"])+"<br>" if has(SITE["address"]) else "China<br>"}
{f'Email: <a href="mailto:{EMAIL}">{EMAIL}</a><br>' if EMAIL else ""}Tel / WhatsApp: <a href="tel:{SITE["phone"].replace(" ","")}">{E(SITE["phone"])}</a>{"<br>WeChat: "+E(SITE["wechat"]) if has(SITE["wechat"]) else ""}</address></div>
<div><h3>Products</h3><ul>{cats}</ul></div>
<div><h3>Applications</h3><ul>{apps}</ul></div>
<div><h3>Company</h3><ul><li><a href="{pg.rel("about")}">About us</a></li><li><a href="{pg.rel("faq")}">FAQ</a></li><li><a href="{pg.rel("blog")}">Buying guides</a></li><li><a href="{pg.rel("contact")}">Contact &amp; quote</a></li><li><a href="{pg.rel("privacy-policy")}">Privacy policy</a></li><li><a href="{pg.rel("sitemap.xml")}">Sitemap</a></li></ul></div>
</div><div class="legal"><span>© 2026 {E(LEGAL)}. All rights reserved.</span><span>Made in China · Exported worldwide</span></div></div></footer>
<a class="wa" href="{wa_link(topic)}" aria-label="Chat on WhatsApp" rel="nofollow" data-track="whatsapp_float">{WA_SVG}</a>
<nav class="mbar" aria-label="Quick contact"><a class="mb-wa" href="{wa_link(topic)}" rel="nofollow" data-track="whatsapp_bar">{WA_SVG}<span>WhatsApp</span></a><a class="mb-q" href="#quote" data-track="quote_bar">Get a Quote</a></nav>'''

def quote_form(pg, product="", heading="Get a free quote & machine recommendation"):
    opts = "".join(f'<option{" selected" if p["name"] == product else ""}>{E(p["name"])}</option>' for p in PRODUCTS)
    return f'''<div class="quote" id="quote"><h2>{E(heading)}</h2>
<p>Tell us your product, pack weight and speed. An engineer replies within 24 hours with a recommended configuration, layout and price. Free product testing with video.</p>
<form class="inq" method="POST" action="{SITE["form_endpoint"] or "#"}" data-wa="{SITE["whatsapp"]}" data-endpoint="{"1" if has(SITE["form_endpoint"]) else ""}">
<label>Your name *<input name="name" required autocomplete="name"></label>
<label>Email<input type="email" name="email" autocomplete="email"></label>
<label>WhatsApp / phone<input name="phone" autocomplete="tel"></label>
<label>Country *<input name="country" required autocomplete="country-name"></label>
<label class="full">Machine of interest<select name="machine"><option value="">Not sure — please recommend</option>{opts}</select></label>
<label>Product to pack *<input name="product" required placeholder="e.g. coffee powder, peanuts, ketchup"></label>
<label>Weight / volume per pack<input name="pack_weight" placeholder="e.g. 10 g, 500 g, 1 kg, 30 ml"></label>
<label>Required speed<input name="speed" placeholder="e.g. 40 bags/min or 20,000 bags/day"></label>
<label>Pack type<select name="pack_type"><option value="">Select…</option><option>Stick pack</option><option>Sachet (3/4-side seal)</option><option>Pillow bag (back seal)</option><option>Gusset / stand-up bag from film</option><option>Premade zipper / doypack pouch</option><option>Flat-bottom pouch</option><option>Spout pouch</option><option>Bottle / jar / can</option><option>20–30 kg bag</option><option>Flow-wrapped item</option><option>Not sure</option></select></label>
<label class="full">Voltage &amp; other requirements<textarea name="message" rows="4" placeholder="Voltage (e.g. 220V 1-phase / 380V 3-phase 50Hz), bag size, budget, delivery date, photos link…"></textarea></label>
<input class="hp" name="_gotcha" tabindex="-1" autocomplete="off" aria-hidden="true">
<input type="hidden" name="page" value="">
<div class="full"><button class="btn btn-primary" type="submit">{"Send inquiry" if has(SITE["form_endpoint"]) else "Send inquiry via WhatsApp"}</button> <small>&nbsp;We reply within 24 h. Your data is only used to answer your inquiry.</small></div>
<div class="form-msg" role="status" aria-live="polite"></div>
</form></div>'''

FORM_JS = r"""<script>
document.querySelectorAll('form.inq').forEach(function(f){
 f.page.value=location.href;
 f.addEventListener('submit',function(e){
  e.preventDefault(); if(f._gotcha.value) return;
  var msg=f.querySelector('.form-msg'), d=new FormData(f);
  var toWA=function(){var lab={name:'Name',email:'Email',phone:'Phone',country:'Country',machine:'Machine',product:'Product',pack_weight:'Pack weight',speed:'Speed',pack_type:'Pack type',message:'Notes',page:'Page'};
    var t='Hello, I would like a quote.\n';d.forEach(function(v,k){if(v&&lab[k])t+=lab[k]+': '+v+'\n'});
    msg.textContent='Opening WhatsApp… If nothing happens, message us at +'+f.dataset.wa+'.';
    if(window.gtag)gtag('event','generate_lead',{method:'whatsapp'});
    window.location.href='https://wa.me/'+f.dataset.wa+'?text='+encodeURIComponent(t);};
  var fallback=toWA;
  if(!f.dataset.endpoint){toWA();return;}
  msg.textContent='Sending…';
  fetch(f.action,{method:'POST',body:d,headers:{'Accept':'application/json'}}).then(function(r){
   if(r.ok){msg.textContent='Thank you! We will reply within 24 hours.';f.reset();
     if(window.gtag)gtag('event','generate_lead');}
   else{fallback();}}).catch(fallback);
 });
});
document.addEventListener('click',function(e){var a=e.target.closest('a');if(!a||!window.gtag)return;
 if(a.href.indexOf('wa.me/')>-1){gtag('event','whatsapp_click',{link_location:a.dataset.track||'inline'});}
 else if(a.getAttribute('href')&&a.getAttribute('href').indexOf('#quote')>-1){gtag('event','quote_cta_click',{link_location:a.dataset.track||'inline'});}});
document.querySelectorAll('.thumbs button').forEach(function(b){b.addEventListener('click',function(){
 var m=document.querySelector('.p-media .main img');m.src=b.dataset.src;m.alt=b.dataset.alt;
 document.querySelectorAll('.thumbs button').forEach(function(x){x.setAttribute('aria-pressed',x===b)});});});
</script>"""

def layout(pg, title, desc, body, schema=None, active="", og_img="fl-cover", og_type="website", noindex=False):
    canon = url(pg.path + "/" if pg.path else "")
    parts = title.split(" | ")
    while len(" | ".join(parts)) > 65 and len(parts) > 2:
        parts.pop(-2)                      # drop middle segment (e.g. model list) first
    if len(" | ".join(parts)) > 65 and len(parts) == 2:
        parts = parts[:1]                  # then drop the brand suffix
    title = " | ".join(parts)
    ga = ""
    if SITE["ga4_id"]:
        ga = f'<script async src="https://www.googletagmanager.com/gtag/js?id={SITE["ga4_id"]}"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag("js",new Date());gtag("config","{SITE["ga4_id"]}");</script>'
    ver = ""
    if SITE["gsc_verification"]: ver += f'<meta name="google-site-verification" content="{SITE["gsc_verification"]}">'
    if SITE["bing_verification"]: ver += f'<meta name="msvalidate.01" content="{SITE["bing_verification"]}">'
    graph = [org_ld()] + (schema or [])
    sch = ld({"@context": "https://schema.org", "@graph": graph})
    robots = "noindex,follow" if noindex else "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"
    if not noindex:
        SITEMAP.append((canon, og_img))
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canon}">
<link rel="alternate" hreflang="en" href="{canon}">
<link rel="alternate" hreflang="x-default" href="{canon}">
<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="{E(B)}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{canon}"><meta property="og:image" content="{url("assets/img/"+og_img+".webp")}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#1d3346">
{ver}
<link rel="icon" href="{pg.rel("assets/favicon.svg")}" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{pg.rel("assets/style.css")}">
{sch}
{ga}
</head>
<body>
{header(pg, active)}
<main id="main">
{body}
</main>
{footer(pg, title.split(" | ")[0])}
{FORM_JS}
</body>
</html>'''

def write(pg, content):
    d = os.path.join(OUT, pg.path)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
        f.write(content)

def product_card(pg, p):
    return f'''<a class="card" href="{pg.rel("products/"+p["slug"])}"><div class="ph">{img_tag(pg, p["img"], p["name"])}</div>
<div class="bd"><span class="tag">{E(CAT[p["cat"]]["short"])}</span><h3>{E(p["short"])}</h3><p>{E(p["lead"])}</p><span class="more">View specs →</span></div></a>'''

# ---------------------------------------------------------------- pages
def build_home():
    pg = Page("")
    cats = "".join(f'''<a class="card" href="{pg.rel("products/"+c["slug"])}"><div class="ph">{img_tag(pg, c["img"], c["name"])}</div>
<div class="bd"><h3>{E(c["short"])}</h3><p>{E(c["summary"])}</p><span class="more">Explore →</span></div></a>''' for c in CATEGORIES)
    apps = "".join(f'''<a class="card" href="{pg.rel("applications/"+a["slug"])}"><div class="bd"><h3>{E(a["name"])}</h3><p>{E(a["lead"])}</p><span class="more">See solutions →</span></div></a>''' for a in APPLICATIONS)
    v = PROD["multi-lane-4-side-seal-powder-packing-machine"]["video"]
    faqs = GLOBAL_FAQ[:5]
    body = f'''
<section class="hero"><div class="wrap">
<div><span class="eyebrow">Packing machine manufacturer · China</span>
<h1>Automatic Packing Machines &amp; Turnkey Packaging Lines</h1>
<p class="lead">{E(B)} builds sachet, stick-pack, vertical form fill seal (VFFS), premade-pouch, flow-wrap and bottle-filling machines for powder, granules, liquids and solid products — tested with your product before shipment.</p>
<div class="cta-row"><a class="btn btn-primary" href="#quote">Get a free quote in 24 h</a><a class="btn btn-ghost" href="{pg.rel("products")}">Browse machines</a></div>
<ul class="ticks"><li>Free sample test with video</li><li>SUS304 / 316L food-grade build</li><li>Voltage built to your country</li><li>18-month warranty &amp; on-site installation</li></ul>
</div>
<div class="hero-img">{img_tag(pg, "fl-cover", "Multi-lane stick pack and sachet packing machines", eager=True)}</div>
</div></section>

<section style="padding-top:24px"><div class="wrap">
<div class="stats"><div><b>30+</b><span>Machine models</span></div><div><b>2–16</b><span>Lanes on multi-lane machines</span></div><div><b>18 months</b><span>Machine warranty</span></div><div><b>24 h</b><span>Quotation reply</span></div></div>
</div></section>

<section><div class="wrap">
<span class="eyebrow">Product range</span><h2>Packing machines for every product and pack format</h2>
<p class="muted prose">Choose by pack format: small sachets and sticks, bags made from roll film, premade pouches, flow-wrapped items, bottles and jars, or 25 kg bags.</p>
<div class="grid g3" style="margin-top:28px">{cats}</div>
</div></section>

<section class="alt"><div class="wrap split">
<div><span class="eyebrow">See it running</span><h2>4-lane 4-side seal powder sachet machine</h2>
<p>The FL-M500 packs powder into four lanes of flat four-side-sealed sachets at 25–40 cuts per lane per minute, with auger dosing, servo film pulling and film-break detection. Every machine is run-tested like this before it ships.</p>
<a class="btn btn-primary" href="{pg.rel("products/multi-lane-4-side-seal-powder-packing-machine")}">View specifications</a></div>
<div class="video-box"><video controls preload="none" playsinline poster="{pg.rel("assets/img/"+v["poster"]+".webp")}" width="1280" height="720"><source src="{pg.rel("assets/video/"+v["file"])}" type="video/mp4"></video></div>
</div></section>

<section><div class="wrap">
<span class="eyebrow">How we work</span><h2>From your sample to a running line</h2>
<ol class="steps" style="margin-top:24px">
<li><h3>Tell us your product</h3><p class="muted">Product, pack weight, speed, pack type and voltage.</p></li>
<li><h3>Free test &amp; proposal</h3><p class="muted">We test your sample, send video, layout drawing and quotation.</p></li>
<li><h3>Build &amp; FAT</h3><p class="muted">Machine built and factory-acceptance tested with your film and product.</p></li>
<li><h3>Ship &amp; install</h3><p class="muted">Export packing, on-site or video installation, training and spare parts.</p></li>
</ol></div></section>

<section class="alt"><div class="wrap">
<span class="eyebrow">Applications</span><h2>Solutions by industry</h2>
<div class="grid g4" style="margin-top:24px">{apps}</div>
</div></section>

<section><div class="wrap prose">
<span class="eyebrow">FAQ</span><h2>Buying a packing machine — common questions</h2>
{faq_html(faqs)}
<p><a class="link" href="{pg.rel("faq")}">See all FAQs →</a></p>
</div></section>

<section style="padding-top:0"><div class="wrap">{quote_form(pg)}</div></section>'''
    schema = [{"@type": "WebSite", "@id": D + "/#website", "url": D + "/", "name": B, "publisher": {"@id": ORG_ID}, "inLanguage": "en"},
              faq_ld(faqs)]
    write(pg, layout(pg, f"Automatic Packing Machine Manufacturer in China | {B}",
          f"{B}: sachet, stick pack, VFFS, premade pouch, flow wrap & filling machines for powder, granules, liquid and snacks. Free sample test, factory price, global installation.",
          body, schema))

def build_products_hub():
    pg = Page("products")
    blocks = ""
    for c in CATEGORIES:
        items = "".join(product_card(pg, p) for p in PRODUCTS if p["cat"] == c["slug"])
        blocks += f'''<section style="padding:36px 0"><div class="wrap"><h2><a href="{pg.rel("products/"+c["slug"])}" style="text-decoration:none">{E(c["name"])}</a></h2>
<p class="muted prose">{E(c["summary"])}</p><div class="grid g3" style="margin-top:20px">{items}</div></div></section>'''
    body = crumbs_html(pg, [("Home", ""), ("Products", "products")]) + f'''
<section style="padding-bottom:12px"><div class="wrap prose"><h1>Packing Machines</h1>
<div class="answer"><p>{E(B)} supplies {len(PRODUCTS)} packing machine families in {len(CATEGORIES)} categories: multi-lane sachet and stick-pack machines, vertical form fill seal (VFFS) machines, premade-pouch machines, horizontal flow wrappers, bottle filling lines and 25 kg bagging lines with auxiliary equipment.</p></div></div></section>
{blocks}<section><div class="wrap">{quote_form(pg)}</div></section>'''
    schema = [crumbs_ld([("Home", ""), ("Products", "products/")]),
              {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": url("products/" + p["slug"] + "/"), "name": p["name"]} for i, p in enumerate(PRODUCTS)]}]
    write(pg, layout(pg, f"Packing Machines: Sachet, VFFS, Pouch, Flow Wrap & Filling | {B}",
          "Full range of automatic packing machines: multi-lane stick pack, sachet, VFFS with weigher, auger powder, liquid, premade pouch, flow wrap, filling lines and 25 kg bagging.",
          body, schema, active="products"))

def build_category(c):
    pg = Page("products/" + c["slug"])
    items = [p for p in PRODUCTS if p["cat"] == c["slug"]]
    cards = "".join(product_card(pg, p) for p in items)
    rows = "".join(f'<tr><td><a href="{pg.rel("products/"+p["slug"])}">{E(p["short"])}</a></td><td>{E(p["models"])}</td>' + "".join(f"<td><span class=\"muted\">{E(k)}:</span> {E(v)}</td>" for k, v in p["facts"][:2]) + "</tr>" for p in items)
    body = crumbs_html(pg, [("Home", ""), ("Products", "products"), (c["short"], "products/" + c["slug"])]) + f'''
<section style="padding-bottom:24px"><div class="wrap split"><div><h1>{E(c["name"])}</h1>
<div class="answer"><p>{E(c["summary"])}</p></div><p>{E(c["intro"])}</p>
<a class="btn btn-primary" href="#quote">Ask for a recommendation</a></div>
<div class="hero-img">{img_tag(pg, c["img"], c["name"], eager=True)}</div></div></section>
<section class="alt" style="padding:40px 0"><div class="wrap"><h2>Models in this range</h2><div class="grid g3" style="margin-top:20px">{cards}</div>
<h3 style="margin-top:36px">Quick comparison</h3><div class="tbl"><table><thead><tr><th>Machine</th><th>Models</th><th>Highlight</th><th>Highlight</th></tr></thead><tbody>{rows}</tbody></table></div></div></section>
<section><div class="wrap">{quote_form(pg)}</div></section>'''
    schema = [crumbs_ld([("Home", ""), ("Products", "products/"), (c["short"], "products/" + c["slug"] + "/")]),
              {"@type": "CollectionPage", "name": c["name"], "description": c["summary"],
               "mainEntity": {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": url("products/" + p["slug"] + "/"), "name": p["name"]} for i, p in enumerate(items)]}}]
    write(pg, layout(pg, f"{c['name']} | {B}", c["summary"][:158], body, schema, active="products", og_img=c["img"] or "fl-cover"))

def spec_table(p):
    s = p.get("specs")
    if not s: return ""
    n = len(s["cols"])
    head = "<tr><th scope=\"col\">Model</th>" + "".join(f'<th scope="col">{E(c)}</th>' for c in s["cols"]) + "</tr>"
    rows = ""
    for k, vals in s["rows"]:
        if len(vals) == 1 and n > 1:
            rows += f'<tr><th scope="row">{E(k)}</th><td colspan="{n}">{E(vals[0])}</td></tr>'
        else:
            rows += f'<tr><th scope="row">{E(k)}</th>' + "".join(f"<td>{E(v)}</td>" for v in vals) + "</tr>"
    return f'<h2 id="specs">{E(p["short"])} technical specifications</h2><div class="tbl"><table><thead>{head}</thead><tbody>{rows}</tbody></table></div><p class="muted" style="font-size:.88rem">Speed and accuracy depend on the product, fill weight and film. Specifications may be customised.</p>'

def build_product(p):
    c = CAT[p["cat"]]
    path = "products/" + p["slug"]
    pg = Page(path)
    trail = [("Home", ""), ("Products", "products"), (c["short"], "products/" + c["slug"]), (p["short"], path)]
    imgs = [p["img"]] + p["gallery"] if p["img"] else []
    thumbs = ""
    if len(imgs) > 1:
        thumbs = '<div class="thumbs">' + "".join(
            f'<button type="button" aria-pressed="{str(i==0).lower()}" data-src="{pg.rel("assets/img/"+n+".webp")}" data-alt="{E(p["name"])} view {i+1}" aria-label="View image {i+1}">{img_tag(pg, n, "")}</button>' for i, n in enumerate(imgs)) + "</div>"
    main_img = img_tag(pg, p["img"], p["name"] + " " + p["models"], eager=True) if p["img"] else '<div class="ph-box">Machine photo to be added<br>(see asset checklist)</div>'
    facts = "".join(f"<div><dt>{E(k)}</dt><dd>{E(v)}</dd></div>" for k, v in p["facts"])
    feats = "".join(f"<li>{E(x)}</li>" for x in p["features"])
    video = ""
    if p.get("video"):
        v = p["video"]
        video = f'''<h2>Video: {E(p["short"])} running test</h2><div class="video-box"><video controls preload="none" playsinline poster="{pg.rel("assets/img/"+v["poster"]+".webp")}" width="1280" height="720"><source src="{pg.rel("assets/video/"+v["file"])}" type="video/mp4"></video></div><p class="muted">{E(v["desc"])}</p>'''
    related = [x for x in PRODUCTS if x["cat"] == p["cat"] and x["slug"] != p["slug"]][:3]
    if len(related) < 3:
        related += [x for x in PRODUCTS if x["slug"] != p["slug"] and x not in related][:3 - len(related)]
    rel_cards = "".join(product_card(pg, x) for x in related)
    answer = f'{p["name"]} ({p["models"]}): ' + "; ".join(f"{k.lower()} {v}" for k, v in p["facts"]) + "."
    body = crumbs_html(pg, trail) + f'''
<div class="wrap"><div class="p-top">
<div class="p-media"><div class="main">{main_img}</div>{thumbs}</div>
<div><h1>{E(p["name"])}</h1><p class="models">Models: {E(p["models"])}</p>
<p style="font-size:1.08rem;color:var(--ink-2)">{E(p["lead"])}</p>
<dl class="facts">{facts}</dl>
<div class="cta-row"><a class="btn btn-primary" href="#quote">Get price &amp; recommendation</a><a class="btn btn-ghost" href="{wa_link(p["name"]+" ("+p["models"]+")")}" rel="nofollow" data-track="whatsapp_product">WhatsApp us</a></div>
</div></div></div>
<section class="alt" style="padding:48px 0"><div class="wrap prose">
<div class="answer"><p><strong>At a glance:</strong> {E(answer)}</p></div>
<h2>What it packs</h2><p>{E(p["applications"])}</p>
<h2>Key features</h2><ul>{feats}</ul>
{spec_table(p)}
{"<h2>Options &amp; configurations</h2><p>"+E(p["options"])+"</p>" if p["options"] else ""}
{video}
<h2>FAQ about the {E(p["short"])}</h2>{faq_html(p["faq"])}
</div></section>
<section><div class="wrap"><h2>Related machines</h2><div class="grid g3" style="margin-top:20px">{rel_cards}</div></div></section>
<section style="padding-top:0"><div class="wrap">{quote_form(pg, p["name"], "Get a quote for the " + p["short"])}</div></section>'''
    props = [{"@type": "PropertyValue", "name": k, "value": v} for k, v in p["facts"]]
    prod = {"@type": "Product", "@id": url(path + "/") + "#product", "name": p["name"], "description": p["lead"],
            "sku": p["models"], "mpn": p["models"], "model": p["models"], "category": c["name"],
            "brand": {"@type": "Brand", "name": B}, "manufacturer": {"@id": ORG_ID}, "additionalProperty": props,
            "url": url(path + "/")}
    if p["img"]:
        prod["image"] = [url("assets/img/" + n + ".webp") for n in imgs]
    schema = [prod, crumbs_ld([(n, (x + "/" if x else "")) for n, x in trail]), faq_ld(p["faq"])]
    if p.get("video"):
        v = p["video"]
        schema.append({"@type": "VideoObject", "name": v["title"], "description": v["desc"],
                       "thumbnailUrl": url("assets/img/" + v["poster"] + ".webp"), "contentUrl": url("assets/video/" + v["file"]),
                       "uploadDate": SITE["lastmod"], "duration": v["duration"], "publisher": {"@id": ORG_ID}})
        prod["subjectOf"] = {"@type": "VideoObject", "name": v["title"]}
    write(pg, layout(pg, f"{p['short']} | {p['models']} | {B}", p["meta"], body, schema, active="products", og_img=p["img"] or "fl-cover", og_type="product"))

def build_applications():
    pg = Page("applications")
    cards = "".join(f'''<a class="card" href="{pg.rel("applications/"+a["slug"])}"><div class="ph">{img_tag(pg, a["img"], a["name"])}</div><div class="bd"><h3>{E(a["name"])}</h3><p>{E(a["lead"])}</p><span class="more">See solutions →</span></div></a>''' for a in APPLICATIONS)
    body = crumbs_html(pg, [("Home", ""), ("Applications", "applications")]) + f'''<section><div class="wrap"><h1>Packaging Solutions by Product</h1>
<div class="answer prose"><p>Pick your product type to see which packing machines, dosing systems and pack formats fit — powder, snacks and granules, liquids and sauces, bakery and candy, or frozen food.</p></div>
<div class="grid g4" style="margin-top:24px">{cards}</div></div></section><section style="padding-top:0"><div class="wrap">{quote_form(pg)}</div></section>'''
    write(pg, layout(pg, f"Packaging Solutions by Industry & Product | {B}", "Packing machine solutions for powder, snacks & granules, liquid & sauce, bakery & candy, and frozen food — dosing systems, pack formats and complete lines.", body,
          [crumbs_ld([("Home", ""), ("Applications", "applications/")])], active="applications"))
    for a in APPLICATIONS:
        path = "applications/" + a["slug"]; pg = Page(path)
        cards = "".join(product_card(pg, PROD[s]) for s in a["products"])
        extra = ""
        if a.get("sections") or a.get("faq"):
            secs = "".join(f"<h2>{E(h)}</h2>{c}" for h, c in a.get("sections", []))
            fq = ("<h2>FAQ</h2>" + faq_html(a["faq"])) if a.get("faq") else ""
            extra = f'<section style="padding:24px 0 48px"><div class="wrap prose">{secs}{fq}</div></section>'
        body = crumbs_html(pg, [("Home", ""), ("Applications", "applications"), (a["name"], path)]) + f'''
<section style="padding-bottom:24px"><div class="wrap split"><div><h1>{E(a["name"])}</h1><div class="answer"><p>{E(a["lead"])}</p></div><p>{E(a["body"])}</p>
<a class="btn btn-primary" href="#quote">Send your product details</a></div><div class="hero-img">{img_tag(pg, a["img"], a["name"], eager=True)}</div></div></section>
{extra}
<section class="alt" style="padding:40px 0"><div class="wrap"><h2>Recommended machines</h2><div class="grid g3" style="margin-top:20px">{cards}</div></div></section>
<section><div class="wrap">{quote_form(pg)}</div></section>'''
        sch = [crumbs_ld([("Home", ""), ("Applications", "applications/"), (a["name"], path + "/")])]
        if a.get("faq"): sch.append(faq_ld(a["faq"]))
        write(pg, layout(pg, f"{a['name']} | {B}", a["meta"], body, sch, active="applications", og_img=a["img"]))

def build_about():
    pg = Page("about")
    body = crumbs_html(pg, [("Home", ""), ("About", "about")]) + f'''
<section><div class="wrap split"><div><span class="eyebrow">About {E(B)}</span><h1>Packing machine maker and line integrator</h1>
<div class="answer"><p>{E(LEGAL)} is a China-based manufacturer of automatic packing machines and complete packaging lines for food, beverage, pharmaceutical, daily-chemical and agricultural products.</p></div>
<p>We design, build and test packing equipment for food, beverage, pharmaceutical, daily-chemical and agricultural products — multi-lane stick-pack and sachet machines, vertical form fill seal machines with weighers, augers and pumps, rotary premade-pouch machines, flow wrappers, filling and capping lines and 25 kg bagging lines.</p>
<p>Every project starts with your product. We test samples on our machines, propose a configuration and layout, build to your voltage and standards, and run a factory acceptance test with your film or pouches before shipping.</p></div>
<div class="hero-img">{img_tag(pg, "workshop", B + " packing machine assembly workshop")}</div></div></section>
<section class="alt"><div class="wrap"><h2>Why buyers choose us</h2><div class="grid g3" style="margin-top:20px">
<div class="card"><div class="bd"><h3>Factory-direct</h3><p>Own design and assembly, so you get factory pricing, custom engineering and direct access to engineers.</p></div></div>
<div class="card"><div class="bd"><h3>One-stop lines</h3><p>Feeding, weighing, packing, inspection, coding, boxing and utilities supplied and tested together.</p></div></div>
<div class="card"><div class="bd"><h3>Tested with your product</h3><p>Free sample test and FAT video before shipment — you see the result before you pay the balance.</p></div></div>
<div class="card"><div class="bd"><h3>Food-grade build</h3><p>SUS304 contact parts (SUS316L on request), GMP-oriented design, branded PLC and servo components.</p></div></div>
<div class="card"><div class="bd"><h3>Built for your country</h3><p>110/220/380/415/440 V, 50/60 Hz; English HMI and documentation; other HMI languages on request.</p></div></div>
<div class="card"><div class="bd"><h3>After-sales support</h3><p>18-month warranty, engineers for on-site installation and training, spare parts in stock, lifetime technical support.</p></div></div>
</div></div></section>
<section style="padding-top:0"><div class="wrap">{quote_form(pg)}</div></section>'''
    write(pg, layout(pg, f"About {B} — Packing Machine Manufacturer in China", f"About {B}: China packing machine manufacturer and line integrator. Factory-direct, free sample testing, SUS304 build, installation and support worldwide.", body,
          [crumbs_ld([("Home", ""), ("About", "about/")]), {"@type": "AboutPage", "name": f"About {B}", "about": {"@id": ORG_ID}}], active="about"))

def build_faq():
    pg = Page("faq")
    allq = GLOBAL_FAQ + [q for p in PRODUCTS for q in p["faq"]]
    body = crumbs_html(pg, [("Home", ""), ("FAQ", "faq")]) + f'''<section><div class="wrap prose"><h1>Packing Machine FAQ</h1>
<div class="answer"><p>Answers about quotations, testing, voltage, lead time, payment, installation, warranty and choosing the right packing machine.</p></div>
<h2>Ordering &amp; service</h2>{faq_html(GLOBAL_FAQ)}
<h2>Choosing a machine</h2>{faq_html([q for p in PRODUCTS for q in p["faq"]])}</div></section>
<section style="padding-top:0"><div class="wrap">{quote_form(pg)}</div></section>'''
    write(pg, layout(pg, f"Packing Machine FAQ: Price, Lead Time, Voltage, Warranty | {B}", "Frequently asked questions about buying packing machines from China: quotation details, free testing, voltage, lead time, payment, installation, warranty and machine selection.", body,
          [crumbs_ld([("Home", ""), ("FAQ", "faq/")]), faq_ld(allq)], active="faq"))

def build_contact():
    pg = Page("contact")
    body = crumbs_html(pg, [("Home", ""), ("Contact", "contact")]) + f'''<section><div class="wrap split" style="align-items:start">
<div><h1>Contact us &amp; get a quote</h1><div class="answer"><p>{f'Email <a href="mailto:{EMAIL}">{EMAIL}</a> or ' if EMAIL else "Message us on "}WhatsApp <a href="https://wa.me/{SITE["whatsapp"]}" rel="nofollow">{E(SITE["phone"])}</a>. We reply within 24 hours (Mon–Sat, GMT+8).</p></div>
<h2>To quote quickly, please tell us</h2><ol><li>Product name and form (powder / granule / liquid / solid) — a photo helps</li><li>Weight or volume per pack</li><li>Required speed (packs per minute or per day)</li><li>Pack type and size (sachet, stick, pillow bag, zipper pouch, bottle…)</li><li>Voltage, phase and frequency at your factory</li><li>Budget and target delivery date (optional)</li></ol>
{"<h2>Factory address</h2><address style='font-style:normal'>"+E(LEGAL)+"<br>"+E(SITE["address"])+"</address>" if has(SITE["address"]) else ""}
<p class="muted">Factory visits are welcome — contact us on WhatsApp to arrange a time.</p></div>
<div>{quote_form(pg, heading="Send your inquiry")}</div></div></section>'''
    write(pg, layout(pg, f"Contact {B} — Request a Packing Machine Quote", f"Contact {B} for a packing machine quotation: {CONTACT_TXT}. Reply within 24 hours with configuration, layout and price.", body,
          [crumbs_ld([("Home", ""), ("Contact", "contact/")]), {"@type": "ContactPage", "name": "Contact", "about": {"@id": ORG_ID}}], active="contact"))

def build_blog():
    pg = Page("blog")
    cards = "".join(f'''<a class="card" href="{pg.rel("blog/"+a["slug"])}"><div class="ph">{img_tag(pg, a["img"], a["title"])}</div><div class="bd"><span class="tag">Buying guide</span><h3>{E(a["title"])}</h3><p>{E(a["summary"])}</p><span class="more">Read →</span></div></a>''' for a in POSTS)
    body = crumbs_html(pg, [("Home", ""), ("Blog", "blog")]) + f'''<section><div class="wrap"><h1>Packing Machine Buying Guides</h1><p class="muted prose">Practical guides from our engineers on choosing, comparing and running packing machines.</p>
<div class="grid g3" style="margin-top:24px">{cards}</div></div></section>'''
    write(pg, layout(pg, f"Packing Machine Buying Guides & Articles | {B}", "Engineer-written guides on choosing a packing machine, VFFS vs premade pouch, multi-lane stick pack machines and more.", body,
          [crumbs_ld([("Home", ""), ("Blog", "blog/")])], active="blog"))
    for a in POSTS:
        path = "blog/" + a["slug"]; pg = Page(path)
        secs = "".join(f"<h2>{E(h)}</h2>{(c if 'table' not in c else '<div class=\"tbl\">'+c+'</div>')}" for h, c in a["body"])
        body = crumbs_html(pg, [("Home", ""), ("Blog", "blog"), (a["title"], path)]) + f'''<article class="article"><section><div class="wrap prose">
<span class="tag">Buying guide</span><h1>{E(a["title"])}</h1><p class="muted">By the {E(B)} engineering team · Updated <time datetime="{a["date"]}">{a["date"]}</time></p>
<div class="answer"><p><strong>Short answer:</strong> {E(a["summary"])}</p></div>
{img_tag(pg, a["img"], a["title"], cls="cover", eager=True)}
{secs}
<p style="margin-top:32px"><a class="btn btn-primary" href="#quote">Ask an engineer</a></p></div></section></article>
<section style="padding-top:0"><div class="wrap">{quote_form(pg)}</div></section>'''
        schema = [crumbs_ld([("Home", ""), ("Blog", "blog/"), (a["title"], path + "/")]),
                  {"@type": "BlogPosting", "headline": a["title"], "description": a["meta"], "datePublished": a["date"], "dateModified": a["date"],
                   "author": {"@type": "Organization", "name": f"{B} engineering team", "url": D + "/about/"}, "publisher": {"@id": ORG_ID},
                   "image": url("assets/img/" + a["img"] + ".webp"), "mainEntityOfPage": url(path + "/")}]
        write(pg, layout(pg, f"{a['title']} | {B}", a["meta"], body, schema, active="blog", og_img=a["img"], og_type="article"))

def build_misc():
    pg = Page("privacy-policy")
    body = crumbs_html(pg, [("Home", ""), ("Privacy policy", "privacy-policy")]) + f'''<section><div class="wrap prose"><h1>Privacy Policy</h1>
<p>{E(LEGAL)} ("we") collects the information you submit through our inquiry forms, email or WhatsApp — such as your name, email, phone number, company, country and project details — only to answer your inquiry and provide quotations and service.</p>
<p>We do not sell your data. Form submissions are processed by our form provider and stored in our email/CRM system. We may use analytics cookies (Google Analytics) to understand site usage; you can block cookies in your browser.</p>
<p>You may ask us to access, correct or delete your data at any time by messaging us on WhatsApp at {E(SITE["phone"])}.</p>
</div></section>'''
    write(pg, layout(pg, f"Privacy Policy | {B}", f"How {B} handles data submitted through inquiry forms, email and WhatsApp.", body, active=""))
    # thank-you (noindex)
    pg = Page("thank-you")
    write(pg, layout(pg, f"Thank you | {B}", "Inquiry received.", f'<section><div class="wrap prose"><h1>Thank you — inquiry received</h1><p>An engineer will reply within 24 hours. For faster contact, message us on <a href="https://wa.me/{SITE["whatsapp"]}">WhatsApp</a>.</p><p><a class="btn btn-primary" href="{pg.rel("products")}">Back to products</a></p></div></section>', noindex=True))
    # 404
    pg = Page("")
    html404 = layout(Page("404"), f"Page not found | {B}", "Page not found.", f'<section><div class="wrap prose"><h1>Page not found</h1><p>The page may have moved. Try our <a href="/products/">packing machines</a> or <a href="/contact/">contact us</a>.</p></div></section>', noindex=True)
    with open(os.path.join(OUT, "404.html"), "w", encoding="utf-8") as f:
        f.write(html404.replace('href="../', 'href="/').replace('src="../', 'src="/'))
    shutil.rmtree(os.path.join(OUT, "404"), ignore_errors=True)

# ---------------------------------------------------------------- machine-readable files
def build_txt():
    # robots.txt — explicitly welcome search & AI crawlers
    bots = ["Googlebot", "Bingbot", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
            "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot", "Applebot-Extended", "DuckDuckBot", "YandexBot", "Baiduspider", "Bytespider", "CCBot", "meta-externalagent"]
    r = "# Search engines and AI assistants are welcome to crawl this site.\n"
    for b in bots:
        r += f"User-agent: {b}\nAllow: /\n\n"
    r += "User-agent: *\nAllow: /\nDisallow: /thank-you/\n\nSitemap: " + url("sitemap.xml") + "\n"
    open(os.path.join(OUT, "robots.txt"), "w").write(r)

    # sitemap.xml with image entries
    xs = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    for loc, im in SITEMAP:
        xs.append(f"<url><loc>{loc}</loc><lastmod>{SITE['lastmod']}</lastmod><image:image><image:loc>{url('assets/img/'+im+'.webp')}</image:loc></image:image></url>")
    xs.append("</urlset>")
    open(os.path.join(OUT, "sitemap.xml"), "w").write("\n".join(xs))

    # llms.txt (summary index for AI assistants)
    L = [f"# {B}", "", f"> {B}  is a China-based manufacturer of automatic packing machines and turnkey packaging lines for powder, granules, liquids/pastes and solid products. Free sample testing, voltage built to the buyer's country, installation and training worldwide. Contact: {CONTACT_TXT}.", "",
         "## How to request a quote", "Provide: product and its form; weight/volume per pack; required speed; pack type and size; voltage/phase/frequency. Reply within 24 hours.", f"- [Contact & quote]({url('contact/')})", "",
         "## Product categories"]
    for c in CATEGORIES:
        L.append(f"- [{c['name']}]({url('products/'+c['slug']+'/')}): {c['summary']}")
    L += ["", "## Products"]
    for p in PRODUCTS:
        L.append(f"- [{p['name']} ({p['models']})]({url('products/'+p['slug']+'/')}): " + "; ".join(f"{k}: {v}" for k, v in p["facts"]))
    L += ["", "## Applications"] + [f"- [{a['name']}]({url('applications/'+a['slug']+'/')}): {a['lead']}" for a in APPLICATIONS]
    L += ["", "## Guides"] + [f"- [{a['title']}]({url('blog/'+a['slug']+'/')}): {a['summary']}" for a in POSTS]
    L += ["", "## Optional", f"- [Full product specifications in one file]({url('llms-full.txt')})", f"- [FAQ]({url('faq/')})", f"- [About]({url('about/')})"]
    open(os.path.join(OUT, "llms.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")

    # llms-full.txt — all specs as markdown
    F = [f"# {B} — full product specifications", "", f"Source: {D}/  ·  Updated {SITE['lastmod']}  ·  Contact {CONTACT_TXT}", ""]
    for p in PRODUCTS:
        F += [f"## {p['name']}", f"URL: {url('products/'+p['slug']+'/')}", f"Models: {p['models']}", "", p["lead"], "", f"Applications: {p['applications']}", "", "Features:"] + [f"- {x}" for x in p["features"]]
        s = p.get("specs")
        if s:
            F += ["", "| Spec | " + " | ".join(s["cols"]) + " |", "|---" * (len(s["cols"]) + 1) + "|"]
            for k, vals in s["rows"]:
                vv = vals if len(vals) == len(s["cols"]) else vals * len(s["cols"]) if len(vals) == 1 else vals
                F.append(f"| {k} | " + " | ".join(vv) + " |")
        if p["options"]: F += ["", "Options: " + p["options"]]
        F += ["", "FAQ:"] + [f"- Q: {q}\n  A: {a}" for q, a in p["faq"]] + [""]
    F += ["## General FAQ"] + [f"- Q: {q}\n  A: {a}" for q, a in GLOBAL_FAQ]
    open(os.path.join(OUT, "llms-full.txt"), "w", encoding="utf-8").write("\n".join(F) + "\n")

    # favicon + simple logo png placeholder
    open(os.path.join(OUT, "assets", "favicon.svg"), "w").write(LOGO_SVG.replace('aria-hidden="true"', 'xmlns="http://www.w3.org/2000/svg"'))
    try:
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (512, 512), "#e4572e"); d = ImageDraw.Draw(im)
        for y, w in ((140, 340), (230, 220), (320, 340)): d.rectangle([90, y, 90 + w, y + 55], fill="white")
        im.save(os.path.join(OUT, "assets", "logo.png"))
    except Exception:
        pass
    # IndexNow key placeholder + headers for Netlify/Cloudflare Pages
    open(os.path.join(OUT, "_headers"), "w").write("/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n")

def main():
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(OUT, "assets"))
    build_home(); build_products_hub()
    for c in CATEGORIES: build_category(c)
    for p in PRODUCTS: build_product(p)
    build_applications(); build_about(); build_faq(); build_contact(); build_blog(); build_misc(); build_txt()
    print(f"Built {len(SITEMAP)} indexable pages -> {OUT}")

if __name__ == "__main__":
    main()
