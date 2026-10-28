const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const urls=JSON.parse(fs.readFileSync(process.argv[2]));const b=await chromium.launch();const ctx=await b.newContext({userAgent:'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'});
const out=[];for(const u of urls){const p=await ctx.newPage();let st='ERR',fin='',title='';try{const r=await p.goto(u,{waitUntil:'domcontentloaded',timeout:30000});st=r.status();fin=p.url();title=(await p.title()).slice(0,50);}catch(e){st='ERR '+String(e).slice(0,40)}await p.close();out.push({u,st,fin:fin===u?'':fin,title});}
fs.writeFileSync(process.argv[3],JSON.stringify(out,null,1));await b.close()})()
