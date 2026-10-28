"""Net audience, offer counts and QA lines for a send. Read-only.  usage: python net_audience.py Newsletter_216_TextureSizing_102826 cormac,nora,gemma
Rule (Tim, 2026-10-27): net = audience table rows - WeeklyHoldout_5K - seeds (Test-TF-Newsletter) - HRLV samples
(Sample_Customer_Reduce_Frequency risk High + value Low, by email) - 40% of disengaged leads (Lead, not in Active_Subscribers_Deduped_6Months, after HRLV).
Check the cloned journey's decision activities first; drop an off-ramp here if the journey does not have it."""
import sys,json,collections,os
sys.path.insert(0,os.path.dirname(__file__)); import sfmc
JN=sys.argv[1]; FEAT={x.strip().lower() for x in (sys.argv[2] if len(sys.argv)>2 else '').split(',') if x.strip()}
lc=lambda s:(s or '').strip().lower()
aud=sfmc.rows(JN); hold={lc(r['email address']) for r in sfmc.rows('WeeklyHoldout_5K')}; seeds={lc(r['email']) for r in sfmc.rows('Test-TF-Newsletter')}
hrlv={lc(r['email']) for r in sfmc.rows('Sample_Customer_Reduce_Frequency') if r.get('risk_tier')=='High' and r.get('value_tier')=='Low'}
active={lc(r['email']) for r in sfmc.rows('Active_Subscribers_Deduped_6Months')}
io={lc(r['email']):r for r in sfmc.rows('Lead_IntroOffer15_091026')}; rc={lc(r['email']):r for r in sfmc.rows('Lead_IntroOffer15_Recurring')}
order=['Lead','Sample Customers','Consumer Rug Customers','Trade']; st=collections.Counter(); c=collections.Counter()
for r in aud:
    e=lc(r['email']); seg=r['segment']
    if e in hold: st['holdout']+=1; continue
    if e in seeds: st['seeds']+=1; continue
    st['main_'+seg]+=1
    if e in hrlv: st['hrlv_'+seg]+=1; st['hrlv']+=1; continue
    w=0.6 if (seg=='Lead' and e not in active) else 1.0
    if seg=='Lead' and e not in active: st['disengaged']+=1
    v=r['creative_variant']; coded=bool(r['promo_code']) and v=='15OFF'
    if seg=='Lead':
        src='Sept10' if (e in io and io[e].get('creative_variant')=='15OFF') else ('Recurring' if e in rc else 'Sept10')
        if coded: c['lead_offer_'+src]+=w
        if v in('CONTROL','FREESHIP','SUPPRESSED'): c[f'lead_{v}_{src}']+=w
    if seg=='Sample Customers':
        if coded: c['sample_offer']+=w
        if v=='CONTROL': c['sample_control']+=w
net={s:round(st['main_'+s]-st['hrlv_'+s]-(0.4*st['disengaged'] if s=='Lead' else 0)) for s in order}; T=sum(net.values())
print(f"table rows {len(aud):,} - holdout {st['holdout']:,} - seeds {st['seeds']:,} - HRLV {st['hrlv']:,} - 40% of {st['disengaged']:,} disengaged leads (~{round(0.4*st['disengaged']):,}) = {T:,}\n")
print('Segment | Contacts | Share')
for s in order: print(f'{s} | {net[s]:,} | {net[s]/T*100:.1f}%')
print(f'TOTAL | {T:,} | 100.0%\n'); print('offer counts (net, est.):',{k:round(v) for k,v in sorted(c.items())})
q=collections.Counter()
for r in aud:
    e=lc(r['email'])
    if r['hasrecs']=='Yes':
        recs=[lc(r[f'rec{i}style']) for i in (1,2,3)]
        if FEAT&set(recs): q['featured_in_recs']+=1
        if len(set(recs))<3: q['duplicate_in_grid']+=1
        if r['hasreview']=='Yes' and lc(r['revstyle']) not in recs: q['review_not_in_grid']+=1
        if r['hasreview']=='Yes' and lc(r['revstyle']) in FEAT: q['featured_in_review']+=1
    if r['promo_code'] and not (r['segment'] in('Lead','Sample Customers') and r['creative_variant']=='15OFF'): q['codes_on_ineligible']+=1
    if e in seeds: q['seeds_in_table']+=1
q['hasrecs_yes']=sum(1 for r in aud if r['hasrecs']=='Yes'); print('QA lines (internal):',dict(q))
