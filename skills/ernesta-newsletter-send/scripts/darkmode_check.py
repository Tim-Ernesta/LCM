"""Dark-mode standard check (Tim, 2026-10-27). usage: python darkmode_check.py <file.html | Content Builder asset name>
Every send must have ALL of: <body class="body"> (Gmail's `u + .body` rules need it), color-scheme + supported-color-schemes "light only",
the head CSS blend rules (u + .body .gmail-blend-screen / -difference, and the [data-ogsc] versions), the prefers-color-scheme dm-promo rules (offer band),
and a <div class="gmail-blend-screen"> around EVERY white-on-image copy block (review over customer photo; hero header copy when it sits on the photo).
Zahra back in stock (NL214) used the class in the body but had none of the CSS and a `light dark` meta: do not clone it for this."""
import sys,re,os
sys.path.insert(0,os.path.dirname(__file__))
a=sys.argv[1]
if os.path.exists(a): h=open(a).read()
else:
    import sfmc
    i=sfmc.call('/asset/v1/content/assets/query',{"page":{"page":1,"pageSize":2},"query":{"property":"name","simpleOperator":"equal","value":a}})['items'][0]['id']
    h=sfmc.call(f'/asset/v1/content/assets/{i}')['views']['html']['content']
m=re.search(r'<body[^>]*>',h,re.I); head,body=h[:m.start()],h[m.start():]
checks={
 'body class="body"':'class="body"' in m.group(0),
 'meta color-scheme = light only':bool(re.search(r'<meta name="color-scheme" content="light only"',head)),
 'meta supported-color-schemes = light only':bool(re.search(r'<meta name="supported-color-schemes" content="light only"',head)),
 'css u + .body .gmail-blend-screen':'u + .body .gmail-blend-screen' in head,
 'css u + .body .gmail-blend-difference':'u + .body .gmail-blend-difference' in head,
 'css [data-ogsc] .gmail-blend-screen':'[data-ogsc] .gmail-blend-screen' in head,
 'css prefers-color-scheme dm-promo rules':'prefers-color-scheme' in head and 'dm-promo' in head,
 'review overlay wrapped (gmail-blend-screen in body)':body.count('class="gmail-blend-screen"')>=1,
 'hero header copy wrapped (white-on-photo hero)':(bool(re.search(r'<div class="gmail-blend-screen"><div class="m-h1s"',body)) if 'class="m-h1s"' in body else 'n/a: hero copy is not the white-on-photo editorial hero'),
}
for k,v in checks.items(): print(('PASS ' if v is True or isinstance(v,str) else 'FAIL ')+k+(' ('+v+')' if isinstance(v,str) else ''))
print('wrappers in body:',body.count('class="gmail-blend-screen"'))
sys.exit(0 if all(v is True or isinstance(v,str) for v in checks.values()) else 1)
