"""Print the Snowflake stock-check SQL for every style/colour pair that can appear. Run it with the Snowflake tool; 0 rows back = all pass.
usage: python stock_check_sql.py <ByStyle DE> <RevUgc DE> "Fleur:Champagne,Tallulah:Silver,Marks:Teal" "Cormac:Oatmeal,..."   (static fallback pairs, featured pairs)
Rule (Tim): custom rows only (is_sample false, is_custom true, is_published 'true', status active); pass = inventory > 0 and (no out_of_stock_on, or restocked_on >= out_of_stock_on)."""
import sys,os
sys.path.insert(0,os.path.dirname(__file__)); import sfmc
bs=sfmc.rows(sys.argv[1]); ru=sfmc.rows(sys.argv[2]); extra=[tuple(p.split(':')) for a in sys.argv[3:] for p in a.split(',') if p]
pairs=set(extra)
for r in bs:
    if not r['rec3style']: continue
    for i in (1,2,3): pairs.add((r[f'rec{i}style'],r[f'rec{i}color']))
    if r['revstyle']: pairs.add((r['revstyle'],r['revcolor']))
for r in ru: pairs.add((r['revstyle'],r['revcolor']))
vals=','.join("('%s','%s')"%(a.replace("'","''"),b.replace("'","''")) for a,b in sorted(pairs))
print(f"""with p(style,color) as (select * from values {vals}),
c as (select line_list_style_name s, product_variant_color_name col, inventory_quantity inv, out_of_stock_on oos, restocked_on rs from PROD_DW.MAIN.PRODUCTS_VARIANTS where is_sample=false and is_published='true' and product_status='active' and is_custom=true)
select p.style, p.color, count(c.s) as rows_found, max(c.inv) as inv, max(c.oos) as oos, max(c.rs) as rs,
 case when count(c.s)=0 then 'NO_ROW' when max(c.inv)<=0 then 'ZERO_INV' when max(c.oos) is not null and max(c.oos)<>'' and (max(c.rs) is null or max(c.rs)='' or max(c.rs)<max(c.oos)) then 'OPEN_STOCKOUT' else 'OK' end as status
from p left join c on lower(c.s)=lower(p.style) and lower(c.col)=lower(p.color) group by p.style,p.color having status<>'OK' order by 1,2""")
