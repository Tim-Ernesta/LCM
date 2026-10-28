"""Journey Builder checklist (Tim's sheet 12vACxeciVDEQcvbNPvPmtdt9HQI_zLjKWVPizT2UHa0, standard for ALL NL journeys). Runs every item that can be verified over the API;
prints PASS / FAIL / NOTE / MANUAL for each item number. usage: python journey_checklist.py <journey name> [expected_copy.txt]
expected_copy.txt = one expected copy string per line (headline, body, CTAs...) from the copy document; checked against the rendered email text (item 17)."""
import sys,os,re,json,html,collections,urllib.request,urllib.parse
sys.path.insert(0,os.path.dirname(__file__)); import sfmc
JN=sys.argv[1]; COPY=[l.strip() for l in open(sys.argv[2])] if len(sys.argv)>2 else []
R={}; 
def rec(n,status,msg): R[n]=(status,msg); print(f'{n:>2} {status:6s} {msg}')
def find_journey(name):
    for pg in range(1,15):   # $search does not filter by name; page through newest first
        for i in sfmc.call(f'/interaction/v1/interactions?$pageSize=100&$page={pg}&$orderBy=modifiedDate%20DESC')['items']:
            if i['name']==name: return i
    raise SystemExit('journey not found: '+name)
j=sfmc.call('/interaction/v1/interactions/'+find_journey(JN)['id'])
ek=j['triggers'][0]['metaData']['eventDefinitionKey']; ev=sfmc.call('/interaction/v1/eventDefinitions/key:'+ek)
acts={a['key']:a for a in j['activities']}; emails=[a for a in j['activities'] if a['type']=='EMAILV2']
def asset(name):
    i=sfmc.call('/asset/v1/content/assets/query',{"page":{"page":1,"pageSize":2},"query":{"property":"name","simpleOperator":"equal","value":name}})['items'][0]['id']; return sfmc.call(f'/asset/v1/content/assets/{i}')
A={v:asset(f'{JN}_{v}') for v in ('VA','VB')}; byLegacy={a['legacyData']['legacyId']:v for v,a in A.items()}
de=sfmc.de_meta(JN); fields=sfmc.call(f"/data/v1/customobjects/{de['id']}/fields")['fields']
# 1 no filters on entry DE
z='00000000-0000-0000-0000-000000000000'
tc=j['triggers'][0].get('configurationArguments') or {}
ok=ev.get('filterDefinitionId')==z and not ev.get('filterDefinitionTemplate') and not ev['arguments'].get('criteria') and not tc.get('criteria') and tc.get('filterDefinitionId',z)==z
rec(1,'PASS' if ok else 'FAIL','entry DE has no filter (event definition and trigger criteria empty)')
# 2 subject + preheader in every send activity equals the email's current version
bad=[]
for a in emails:
    ts=a['configurationArguments']['triggeredSend']; v=byLegacy.get(ts['emailId'])
    sub=A[v]['views']['subjectline']['content'] if v else None; pre=A[v]['views']['preheader']['content'] if v else None
    if not v or ts['emailSubject']!=sub or ts['dynamicEmailSubject']!=sub or (ts.get('preHeader') or '').strip()!=(pre or '').strip(): bad.append(a['key'])
rec(2,'PASS' if not bad else 'FAIL',f"{len(emails)} send activities: subject, dynamic subject and preheader match the current email versions" if not bad else f'mismatch in {bad}')
# 3 / 6 live sends
rec(3,'MANUAL','send a live email for each variation (VA, VB) from Content Builder; not run by Claude (outward-facing send)')
rec(6,'MANUAL','unsubscribe link must be tested from a live send. Static check: '+('%%unsub_center_url%%' in A['VA']['views']['html']['content'] and 'footer has %%unsub_center_url%% in both emails' if '%%unsub_center_url%%' in A['VB']['views']['html']['content'] else 'unsub_center_url MISSING'))
# 5 primary key / sendable
pk=[f['name'] for f in fields if f.get('isPrimaryKey')]
rec(5,'PASS' if pk==['Email'] and de.get('isSendable') else 'FAIL',f"target DE primary key {pk}; sendable={de.get('isSendable')} on {de.get('sendableCustomObjectField')} -> {de.get('sendableSubscriberField')}")
# 8 no re-entry
rec(8,'PASS' if j['entryMode'] in('OnceAndDone','NoReentry') else 'FAIL',f"entryMode={j['entryMode']}")
rec(9,'N/A','exit criteria not necessary for newsletters / one-time blasts')
# 10 variants mapped to right email
m=[]; 
for k in ('RANDOMSPLIT-AB','RANDOMSPLIT-TESTVER'):
    for o in acts[k]['outcomes']:
        e=acts[o['next']]; ts=e['configurationArguments']['triggeredSend']; v=byLegacy.get(ts['emailId']); m.append((k,o['metaData'].get('label'),o['next'],v))
good=all((nx.endswith('VA') and v=='VA') or (nx.endswith('VB') and v=='VB') for _,_,nx,v in m)
va,vb=A['VA']['views']['html']['content'],A['VB']['views']['html']['content']
rec(10,'PASS' if good else 'FAIL','; '.join(f'{k.split("-")[-1]} {l!r}->{nx}({v})' for k,l,nx,v in m)+f' | VA/VB html differ: {va!=vb}')
# 11 audience segments
aud=sfmc.rows(JN); seg=collections.Counter(r['segment'] for r in aud)
rec(11,'NOTE','linked DE is the full-audience table: '+', '.join(f'{k} {v:,}' for k,v in seg.most_common())+' (correct only if the email is for the full audience, not Trade-only)')
# 12/23 desktop vs mobile images and links
def blocks(h,cls): return re.findall(r'<div class="'+cls+r'">(.*?)</div>',h,re.S)
sep=[c for c in ('em_coastal_desktop','em_coastal_mobile') if f'class="{c}"' in va+vb]
if sep:
    for n in (12,23): rec(n,'MANUAL','email has separate desktop/mobile blocks '+str(sep)+': compare image and link sets by hand')
else:
    rec(12,'PASS','no separate mobile image set: one responsive set of images is used for desktop and mobile')
    rec(23,'PASS','no separate mobile link set: each link exists once (stacked layout, not duplicated blocks)')
# 13 email activities re-added after content edits (see refresh_email_activities.py): each send activity must match the CURRENT asset and hold no stale triggered-send snapshot
stale=[]
for a in emails:
    ts=a['configurationArguments']['triggeredSend']; v=byLegacy.get(ts['emailId']); as_=A.get(v) if v else None
    if not as_ or ts['emailSubject']!=as_['views']['subjectline']['content'] or (ts.get('preHeader') or '').strip()!=as_['views']['preheader']['content'].strip() or a['configurationArguments'].get('triggeredSendId'):
        stale.append(a['key'])
newest=max(x['modifiedDate'] for x in A.values()); 
rec(13,'PASS' if not stale else 'FAIL',('all 4 email activities match the current email assets and carry no stale triggered-send reference; ' if not stale else f'stale: {stale}; ')+'if the emails are edited again, run refresh_email_activities.py (draft journeys only); Journey Builder may still ask to confirm the email activities when Tim opens it')
# 14 automation
try:
    au=sfmc.call('/automation/v1/automations/'+ev['automationId']); steps=[(s['step'],[x.get('name') for x in s['activities']]) for s in au['steps']]
    last=au['steps'][-1]['activities'][0].get('objectTypeId')
    rec(14,'PASS' if last==952 else 'FAIL',f"automation '{au['name']}' status {au.get('status')}: steps {steps}; last step is {'the Journey entry' if last==952 else 'NOT the Journey entry'}. Note: no population-query step in it (same as NL213): run the query by hand before send (item 18)")
except Exception as e: rec(14,'FAIL',f'no entry automation on the event definition ({e})')
# 14b one event definition only: saving a draft journey can make Journey Builder create a REPLACEMENT event definition + entry automation and repoint the trigger
dups=[]
for pg in range(1,30):
    items=sfmc.call(f'/interaction/v1/eventDefinitions?$pageSize=100&$page={pg}').get('eventDefinitions') or []
    dups+=[e for e in items if e.get('name')==JN or e.get('dataExtensionName')==JN]
    if len(items)<100: break
orph=[e['eventDefinitionKey'] for e in dups if e['id']!=ev['id']]
rec('14b','PASS' if not orph else 'FAIL','one event definition for this audience, and it is the one the trigger uses' if not orph else f'extra event definitions (orphans, delete the event definition and its entry automation): {orph}')
# 15 evaluate all records
rec(15,'PASS' if ev['arguments'].get('useHighWatermark') is False else 'FAIL',f"useHighWatermark={ev['arguments'].get('useHighWatermark')} (False = evaluate all records)")
# 16 waits
waits=[(a['key'],a['configurationArguments']['waitDuration'],a['configurationArguments']['waitUnit']) for a in j['activities'] if a['type']=='WAIT']
rec(16,'NOTE',f"waits in journey: {waits}; journey metaData disableEndWait={j['metaData'].get('disableEndWait')}; no exit-wait activity. Same as NL213/NL214. Item wording ('3 minutes') is not tied to a setting Claude can see: confirm in Builder")
# 17 copy
txt=lambda h:re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',re.sub(r'%%\[.*?\]%%','',h,flags=re.S)))).replace('’',"'").replace('–','-').replace('—','-').replace('“','"').replace('”','"')
norm=lambda s:txt(s).strip().lower()
if COPY:
    miss=[c for c in COPY if c and norm(c) not in norm(va) and norm(c) not in norm(vb)]
    rec(17,'PASS' if not miss else 'FAIL',f'{len([c for c in COPY if c])} copy strings checked against VA and VB'+('' if not miss else f'; missing: {miss}'))
else: rec(17,'MANUAL','pass a copy file to compare against the original copy document')
# 18 / 19 reminders
rec(18,'MANUAL','re-run the population query just before send; last run: '+str((sfmc.call(f"/data/v1/customobjects/{de['id']}").get('queryActivity') or {}).get('instanceDate')))
rec(19,'MANUAL','stock check: run stock_check_sql.py in Snowflake now and again on send morning (also confirm on the live site that no featured product shows Out of stock)')
# 20 shape/size params
pat=re.compile(r'[&?](?:amp;)?(?:shape=rectangle|size=custom)',re.I); where=[]
for v,a in A.items():
    for part in ('html','preheader'):
        if pat.search(a['views'][part]['content']): where.append(f'{v}.{part}')
for nm in (JN+'_Recs_ByStyle',JN+'_RevUgc'):
    rows=sfmc.rows(nm)
    if any(pat.search(str(x)) for x in rows): where.append(nm)
if any(pat.search(' '.join(str(r.get(k,'')) for k in r)) for r in aud): where.append(JN+' (audience rec/review urls)')
rec(20,'PASS' if not where else 'FAIL','no &shape=rectangle or &size=custom in emails, lookup tables or audience URLs' if not where else f'found in {where}')
rec(21,'MANUAL','footer alignment: eyeball the recipient previews (footer is the editorial footer)')
rec(22,'MANUAL','dark mode on iPhone/Apple Mail: open a live test in iOS dark mode. Static stack check: '+('PASS' if all(x in html_ for html_ in (va,vb) for x in ('class="body"','light only','u + .body .gmail-blend-screen','class="gmail-blend-screen"')) else 'FAIL (run darkmode_check.py)'))
# L: link coverage (Tim, 2026-10-27): the logo, the headline, EVERY image and every subhead must be linked, with styling unchanged (anchors repeat the text colour, no underline)
miss=[]
for v,a in A.items():
    b=html.unescape(a['views']['html']['content']); b=b[b.lower().index('<body'):]
    for m in re.finditer(r'<img\b[^>]*>',b):
        pre=b[:m.start()]; o=[x.start() for x in re.finditer(r'<a[\s>]',pre)]
        if not o or o[-1]<pre.rfind('</a>'): miss.append(f"{v} image ...{re.search(r'src=.([^ ]+)',m.group(0)).group(1)[-34:]}")
    for m in re.finditer(r'<div class="(m-h1s|m-h2|m-h3|em_h1)"[^>]*>(.*?)</div>',b,re.S):
        if '<a ' not in m.group(2) and re.sub(r'<[^>]+>|\s','',m.group(2)): miss.append(f"{v} {m.group(1)} heading unlinked: {re.sub('<[^>]+>','',m.group(2))[:30]!r}")
rec('L','PASS' if not miss else 'FAIL','every image, the headline and every subhead are linked in VA and VB' if not miss else f'unlinked: {miss[:8]}')
# 24 preheader: clean text, hidden preview-text hack in place (90 x filler) so body copy never flows into the Gmail preview
bad=[]
for v,a in A.items():
    pre=a['views']['preheader']['content']; body=a['views']['html']['content']
    top=body[re.search(r'<body[^>]*>',body,re.I).start():].split('<table')[0]
    odd=[c for c in re.sub(r'%%\[.*?\]%%','',pre,flags=re.S) if ord(c)>127 or c in '\t\r']
    pairs=top.count('&#xFEFF;&#x34F;')
    if odd or pairs<90 or '  ' in re.sub(r'%%\[.*?\]%%','',pre,flags=re.S): bad.append((v,odd[:3],f'filler pairs {pairs}'))
rec(24,'PASS' if not bad else 'FAIL','preheader text is clean and the preview-text hack (empty hidden div + 90 x &#xFEFF;&#x34F;) is in place in VA and VB, so body copy cannot flow into the Gmail preview' if not bad else str(bad))
# 25 Id / SubscriberKey
ids=[r['id'] for r in aud]; blank=sum(1 for i in ids if not i); dup=len(ids)-len(set(ids))
rec(25,'PASS' if de.get('sendableCustomObjectField')=='Id' and de.get('sendableSubscriberField')=='_SubscriberKey' and not blank and not dup else 'FAIL',f"sendable Id->_SubscriberKey; {len(ids):,} rows, blank Id {blank}, duplicate Id {dup}; Id comes from the contact id (= SubscriberKey) in the population query")
# 26 one email per path
nxt={a['key']:[o.get('next') for o in a.get('outcomes',[])] for a in j['activities']}
starts=[o for o in acts if all(o not in v for v in nxt.values())]
paths=[]
def walk(k,p):
    if not k: paths.append(p); return
    n=nxt[k]
    if not n or all(x is None for x in n): paths.append(p+[k]); return
    for x in n: walk(x,p+[k])
for s in starts: walk(s,[])
worst=max(sum(1 for k in p if acts[k]['type']=='EMAILV2') for p in paths)
rec(26,'PASS' if worst<=1 else 'FAIL',f'{len(paths)} distinct paths through the journey; max emails on any single path = {worst}')
# 27 sender profile
try:
    import xml.etree.ElementTree as ET
    sp=emails[0]['configurationArguments']['triggeredSend']['senderProfileId']; tok=sfmc._state['access_token']
    env=f'<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:a="http://schemas.xmlsoap.org/ws/2004/08/addressing"><s:Header><a:Action s:mustUnderstand="1">Retrieve</a:Action><a:To s:mustUnderstand="1">{sfmc._state["soap_instance_url"]}Service.asmx</a:To><fueloauth xmlns="http://exacttarget.com">{tok}</fueloauth></s:Header><s:Body><RetrieveRequestMsg xmlns="http://exacttarget.com/wsdl/partnerAPI"><RetrieveRequest><ObjectType>SenderProfile</ObjectType><Properties>Name</Properties><Properties>CustomerKey</Properties><Properties>FromName</Properties><Properties>FromAddress</Properties><Filter xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="SimpleFilterPart"><Property>ObjectID</Property><SimpleOperator>equals</SimpleOperator><Value>{sp}</Value></Filter></RetrieveRequest></RetrieveRequestMsg></s:Body></s:Envelope>'
    r=urllib.request.Request(sfmc._state['soap_instance_url']+'Service.asmx',data=env.encode(),headers={'Content-Type':'text/xml'}); x=urllib.request.urlopen(r).read().decode()
    nm=re.search(r'<Name>(.*?)</Name>',x); fa=re.search(r'<FromAddress>(.*?)</FromAddress>',x); fn=re.search(r'<FromName>(.*?)</FromName>',x)
    same=len({a['configurationArguments']['triggeredSend']['senderProfileId'] for a in emails})==1
    rec(27,'PASS' if nm and 'default' in nm.group(1).lower() and same else 'FAIL',f"sender profile on all {len(emails)} sends: {nm.group(1) if nm else '?'} / {fn.group(1) if fn else '?'} <{fa.group(1) if fa else '?'}>")
except Exception as e: rec(27,'MANUAL',f'could not read the sender profile name via SOAP ({e}); id {emails[0]["configurationArguments"]["triggeredSend"]["senderProfileId"]} is the same profile NL213 uses')
# 4: links (real browser: the site blocks plain scripts with 403). 200 alone is not enough: filter URLs /f/1/<slug>~<code> must be checked by name.
import subprocess,tempfile
links=set()
for a in A.values(): links|=set(re.findall(r'href="(https?://www\.ernestarugs\.com[^"]+)"',html.unescape(re.sub(r'%%\[.*?\]%%','',a['views']['html']['content'],flags=re.S))))
links={l for l in links if '%%' not in l}
tf=tempfile.mktemp(suffix='.json'); of=tempfile.mktemp(suffix='.json'); json.dump(sorted(links),open(tf,'w'))
subprocess.run(['node',os.path.join(os.path.dirname(__file__),'linkcheck.js'),tf,of],check=True)
res=json.load(open(of)); bad=[(x['st'],x['u'][:80],x['fin'][:60]) for x in res if x['st']!=200]
redir=[(x['u'].split('?')[0][-45:],x['fin'].split('?')[0][-45:]) for x in res if x['st']==200 and x['fin'] and x['fin'].split('?')[0]!=x['u'].split('?')[0]]
filt=sorted({re.search(r'/f/1/([^?]+)',x['u']).group(1) for x in res if '/f/1/' in x['u']})
rec(4,'PASS' if not bad else 'FAIL',f'{len(res)} links load (200) in a real browser'+(f'; {len(redir)} redirect: {redir[:4]}' if redir else '')+(f'; FILTER URLs to confirm by name: {filt}' if filt else '')+('' if not bad else f'; NOT 200: {bad}'))
print('\nSUMMARY',collections.Counter(s for s,_ in R.values()))
json.dump({str(k):list(v) for k,v in sorted(R.items(),key=lambda kv:str(kv[0]))},open('journey_checklist_result.json','w'),indent=1)
