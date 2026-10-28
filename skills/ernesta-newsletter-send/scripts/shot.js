// node shot.js <dir>  -> screenshots every .html in dir at 640px wide, scale 1.5, full page; prints broken-image counts
const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const D=process.argv[2];
for(const f of fs.readdirSync(D).filter(x=>x.endsWith('.html'))){const n=f.replace('.html','');
const ctx=await b.newContext({viewport:{width:640,height:900},deviceScaleFactor:1.5});const p=await ctx.newPage();
await p.goto(`file://${D}/${f}`,{waitUntil:'networkidle'});
const r=await p.evaluate(()=>({broken:[...document.images].filter(i=>!i.naturalWidth).map(i=>i.src.slice(-50)),total:document.images.length}));
console.log(n,JSON.stringify(r));await p.screenshot({path:`${D}/${n}.png`,fullPage:true});await ctx.close();}
await b.close()})()
