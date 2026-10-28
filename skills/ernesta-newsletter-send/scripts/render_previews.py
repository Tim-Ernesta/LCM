"""Real recipient previews of the LIVE Content Builder emails (VA, VB) for actual audience rows. Static-fallback / placeholder renders do not count.
usage: python render_previews.py Newsletter_216_TextureSizing_102826 <outdir> [featured,styles]
Picks a rug customer with no offer, a Lead with the offer and a Sample customer with the offer (each with recs, a review and a RevUgc photo),
renders with the AMPscript interpreter, masks promo codes, adds a subject/preheader bar, screenshots at 640px x1.5 and scales images taller than 8000px."""
import sys,os,re,json,html,subprocess
sys.path.insert(0,os.path.dirname(__file__)); import sfmc; from amp import Amp
JN,OUT=sys.argv[1],os.path.abspath(sys.argv[2]); FEAT={x.lower() for x in (sys.argv[3] if len(sys.argv)>3 else '').split(',') if x}
os.makedirs(OUT,exist_ok=True); lc=lambda s:(s or '').strip().lower()
live={}
for v in ('VA','VB'):
    a=sfmc.call('/asset/v1/content/assets/query',{"page":{"page":1,"pageSize":2},"query":{"property":"name","simpleOperator":"equal","value":f'{JN}_{v}'}})['items'][0]
    a=sfmc.call(f"/asset/v1/content/assets/{a['id']}"); live[v]=(a['views']['html']['content'],a['views']['preheader']['content'],a['views']['subjectline']['content'])
aud=sfmc.rows(JN); ugc=sfmc.rows(JN+'_RevUgc'); rc=sfmc.rows('Lead_IntroOffer15_Recurring'); so=sfmc.rows('SampleOffer15_Day12')
hold={lc(r['email address']) for r in sfmc.rows('WeeklyHoldout_5K')}; seeds={lc(r['email']) for r in sfmc.rows('Test-TF-Newsletter')}
hrlv={lc(r['email']) for r in sfmc.rows('Sample_Customer_Reduce_Frequency') if r.get('risk_tier')=='High' and r.get('value_tier')=='Low'}
photo={(lc(r['revstyle']),lc(r['revcolor'])) for r in ugc}
def ok(r,offer):
    e=lc(r['email'])
    if e in hold or e in seeds or e in hrlv or r['hasrecs']!='Yes' or r['hasreview']!='Yes': return False
    if (lc(r['revstyle']),lc(r['revcolor'])) not in photo: return False
    if FEAT&({lc(r[f'rec{i}style']) for i in (1,2,3)}|{lc(r['revstyle'])}): return False
    return offer==(bool(r['promo_code']) and r['creative_variant']=='15OFF')
pick={}
for r in aud:
    for k,c in (('rug_nooffer',r['segment']=='Consumer Rug Customers' and ok(r,False)),('lead_offer',r['segment']=='Lead' and ok(r,True)),('sample_offer',r['segment']=='Sample Customers' and ok(r,True))):
        if c and k not in pick: pick[k]=r
jobs=[('VA','rug_nooffer','VA-rug-customer-no-offer'),('VB','rug_nooffer','VB-rug-customer-no-offer'),('VB','lead_offer','VB-lead-with-15-off'),('VA','sample_offer','VA-sample-customer-with-15-off')]
for v,who,name in jobs:
    row=pick[who]; e=lc(row['email'])
    data={JN:[row],JN+'_RevUgc':ugc,'Lead_IntroOffer15_Recurring':[r for r in rc if lc(r['email'])==e],'SampleOffer15_Day12':[r for r in so if lc(r['email'])==e]}
    tpl,pre,sub=live[v]; out=Amp(data,row['email']).render(tpl); pre=Amp(data,row['email']).render(pre).strip()
    out=re.sub(r'%%Member_\w+%%','',out).replace('%%unsub_center_url%%','#').replace('%%profile_center_url%%','#')
    code=row.get('promo_code') or ''
    if code: out=out.replace(code,'XXXXXXXXXX').replace(code.upper(),'XXXXXXXXXX')
    assert not re.findall(r'%%[^%]{1,60}%%',out)
    bar=f'<div style="font-family:Arial,sans-serif;font-size:13px;line-height:1.5;background:#fff;border-bottom:1px solid #ccc;padding:10px 16px;max-width:600px;margin:0 auto;color:#222"><b>Subject:</b> {html.escape(sub)}<br><b>Preheader:</b> {html.escape(pre)}<br><span style="color:#777">{v} &middot; {html.escape(row["segment"])} &middot; recs {html.escape(row["rec1style"])}, {html.escape(row["rec2style"])}, {html.escape(row["rec3style"])} &middot; review {html.escape(row["revstyle"])} {html.escape(row["revcolor"])} &middot; offer {"yes" if code else "no"}</span></div>'
    open(f'{OUT}/{name}.html','w').write(re.sub(r'(<body[^>]*>)',lambda m:m.group(1)+bar,out,count=1))
    print(name,'|',row['segment'],'|',row['rec1style'],row['rec2style'],row['rec3style'],'| review',row['revstyle'],'| offer shown','Exclusive offer' in re.sub(r'<[^>]+>',' ',out))
subprocess.run(['node',os.path.join(os.path.dirname(__file__),'shot.js'),OUT],check=True)
from PIL import Image
for f in os.listdir(OUT):
    if f.endswith('.png'):
        im=Image.open(f'{OUT}/{f}')
        if im.size[1]>8000: s=7900/im.size[1]; im.resize((int(im.size[0]*s),7900)).save(f'{OUT}/{f}')
