"""Send-readiness check for Content Builder emails: the things Marketing Cloud's subscriber preview / send validation rejects.
usage: python send_readiness_check.py <asset name> [<asset name> ...]   (run on VA and VB, and on a known-good send as a baseline)
There is NO validation API reachable from here (/guide/v1/emails/validate etc. return 404); Tim's Subscriber Preview in Content Builder is the final test.
Learned on NL216 (2026-10-27): the editorial template has no profile center link and no open-tracking tag, so a build from it failed Subscriber Preview with
'A profile center link is missing' (HTML + text) and 'does not include the code to track opens' (text). Camille and NL214 carry both."""
import sys,re,os
sys.path.insert(0,os.path.dirname(__file__)); import sfmc
def asset(name):
    i=sfmc.call('/asset/v1/content/assets/query',{"page":{"page":1,"pageSize":2},"query":{"property":"name","simpleOperator":"equal","value":name}})['items'][0]['id']; return sfmc.call(f'/asset/v1/content/assets/{i}')

def preview_ok(h,pre):
    """What Gmail shows after the subject: preheader text, then body text in DOM order INCLUDING display:none. Visible body copy must not start before 150 preview chars."""
    import html as _h
    pre=re.sub(r'%%\[.*?\]%%','',pre,flags=re.S); pre=re.sub(r'%%.*?%%','',pre); b=h[re.search(r'<body[^>]*>',h,re.I).start():]
    b=re.sub(r'%%\[.*?\]%%','',b,flags=re.S); b=re.sub(r'<style.*?</style>|<!--.*?-->','',b,flags=re.S)
    txt=_h.unescape(re.sub(r'<[^>]+>',' ',b)); txt=re.sub(r'[\ufeff\u034f\u2007\u200c\u00a0\s]+',' ',txt)  # invisible filler collapses to spaces
    first=re.search(r'[A-Za-z0-9]',txt); lead=(pre.strip()+' ').strip()
    # filler chars (before collapsing) that sit between the preheader and the first visible word
    raw=_h.unescape(re.sub(r'<[^>]+>','',b)); m=re.search(r'[A-Za-z0-9]',raw); filler=len(re.findall(r'[\ufeff\u034f\u2007\u200c\u00a0]',raw[:m.start()])) if m else 0
    return len(lead)+filler>=150
bad=0
for name in sys.argv[1:]:
    a=asset(name); h=a['views']['html']['content']; t=a['views'].get('text',{})
    ifs=ends=0
    for blk in re.findall(r'%%\[(.*?)\]%%',h,re.S):
        for line in [l.strip() for l in re.sub(r'/\*.*?\*/','',blk,flags=re.S).splitlines() if l.strip()]:
            if re.match(r'IF .* THEN$',line,re.I): ifs+=1
            elif line.upper()=='ENDIF': ends+=1
    checks=[
     ('profile center link (%%profile_center_url%% in an <a href>)',bool(re.search(r'<a[^>]+href="%%profile_center_url%%"',h))),
     ('unsubscribe link (%%unsub_center_url%% in an <a href>)',bool(re.search(r'<a[^>]+href="%%unsub_center_url%%"',h))),
     ('open tracking tag <custom name="opencounter" type="tracking"',bool(re.search(r'<custom name="opencounter" type="tracking"',h))),
     ('physical address merge fields (Member_Addr, Member_City)','%%Member_Addr%%' in h and '%%Member_City%%' in h),
     ('text version generated from html',t.get('generateFrom')=='html' and t.get('data',{}).get('email',{}).get('options',{}).get('generateFrom')=='html'),
     ('subject line and preheader set',bool(a['views']['subjectline']['content'].strip()) and bool(a['views']['preheader']['content'].strip())),
     (f'preview-text hack: >=90 x &#xFEFF;&#x34F; filler in the hidden div before the first table ({h[re.search(r"<body[^>]*>",h,re.I).start():].split("<table")[0].count("&#xFEFF;&#x34F;")} found)',h[re.search(r"<body[^>]*>",h,re.I).start():].split("<table")[0].count("&#xFEFF;&#x34F;")>=90),
     ('Gmail preview flow: preheader then filler, no visible copy within the first 150 preview characters',preview_ok(h,a['views']['preheader']['content'])),
     ('<title> present',bool(re.search(r'<title>[^<]+</title>',h))),
     (f'AMPscript IF/ENDIF balanced ({ifs} IF, {ends} ENDIF)',ifs==ends),
     ('html is ASCII only',all(ord(c)<128 for c in h)),
     ('size under 100 KB',len(h.encode())<100_000)]
    print('==',name,f'({len(h):,} bytes)')
    for k,v in checks:
        print(('  PASS ' if v else '  FAIL ')+k); bad+=0 if v else 1
sys.exit(1 if bad else 0)
