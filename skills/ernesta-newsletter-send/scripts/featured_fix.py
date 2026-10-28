"""Build the new send's Recs_ByStyle from the NEWEST send's table with featured styles removed from every rec slot.
usage: python featured_fix.py Newsletter_214_..._Recs_ByStyle cormac,nora,gemma out.json
Refill from the same class ranked by clicks; if a class runs short the slot is left blank so the query sets HasRecs=No and the static fallback shows.
Then upsert with sfmc.upsert_rows(<new>_Recs_ByStyle, rows) and copy the newest send's RevUgc rows the same way."""
import sys,json,collections,re,os
sys.path.insert(0,os.path.dirname(__file__)); import sfmc
src,feat,out=sys.argv[1],{x.strip().lower() for x in sys.argv[2].split(',')},sys.argv[3]
base=sfmc.rows(src); pool=collections.defaultdict(dict)
for r in base:
    for i in (1,2,3):
        s=r[f'rec{i}style']
        if s:
            rec={'style':s,'color':r[f'rec{i}color'],'url':r[f'rec{i}url'],'img':r[f'rec{i}img'],'clicks':float(r[f'rec{i}clicks'] or 0)}
            cur=pool[r['sourceclass']].get(s)
            if not cur or rec['clicks']>cur['clicks']: pool[r['sourceclass']][s]=rec
new=[];short=[]
for r in base:
    r=dict(r); recs=[{'style':r[f'rec{i}style'],'color':r[f'rec{i}color'],'url':r[f'rec{i}url'],'img':r[f'rec{i}img'],'clicks':float(r[f'rec{i}clicks'] or 0)} for i in (1,2,3)]
    if any(x['style'].lower() in feat for x in recs):
        keep=[x for x in recs if x['style'].lower() not in feat]; have={x['style'].lower() for x in keep}|{r['sourcestyle'].lower()}|feat
        add=[dict(c) for c in sorted([c for c in pool[r['sourceclass']].values() if c['style'].lower() not in have],key=lambda c:-c['clicks'])[:3-len(keep)]]
        recs=sorted(keep+add,key=lambda x:-x['clicks'])
        if len(recs)<3: short.append(r['sourcestyle'])
        for i in (1,2,3):
            x=recs[i-1] if i<=len(recs) else {'style':'','color':'','url':'','img':'','clicks':0}
            r[f'rec{i}style'],r[f'rec{i}color'],r[f'rec{i}img'],r[f'rec{i}clicks']=x['style'],x['color'],x['img'],str(int(x['clicks'])) if x['style'] else ''
            r[f'rec{i}url']=re.sub(r'element=rec\d',f'element=rec{i}',x['url']) if x['url'] else ''
    new.append(r)
json.dump(new,open(out,'w')); print(len(new),'rows; short (static fallback):',short)
