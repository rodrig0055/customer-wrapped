// Stage 2: deterministic, resumable, concurrent card renderer.
// out/customers.jsonl -> out/pngs/<cid>_<NN>_<key>.png  (retina, full 9:16, no crop)
// Resumable: a customer whose PNGs all already exist is skipped. Concurrency via a page pool.
const puppeteer=require('puppeteer');
const fs=require('fs'), path=require('path');
const HERE=__dirname, OUT=path.join(HERE,'out'), PNG=path.join(OUT,'pngs');
const TEMPLATE='file://'+path.join(HERE,'template.html');
const CONCURRENCY=parseInt(process.env.RENDER_CONCURRENCY||'6',10);
fs.mkdirSync(PNG,{recursive:true});

const customers=fs.readFileSync(path.join(OUT,'customers.jsonl'),'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);

function expectedNames(c){ // deterministic filenames without rendering
  const keys=['archetype',...c.cards.map(x=>x.key),'summary'];
  return keys.map((k,i)=>`${c.cid}_${String(i+1).padStart(2,'0')}_${k}.png`);
}
function done(c){ return expectedNames(c).every(n=>fs.existsSync(path.join(PNG,n))); }

(async()=>{
  const limit=parseInt(process.env.LIMIT||'0',10);
  const todo=customers.filter(c=>!done(c)).slice(0, limit||undefined);
  console.log(`${customers.length} customers, ${todo.length} to render now, concurrency ${CONCURRENCY}`);
  if(!todo.length){ console.log('nothing to do'); return; }
  const browser=await puppeteer.launch({headless:'shell',
    executablePath: process.env.PUPPETEER_EXEC,   // optional: use an installed Chrome
    args:['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage'],
    protocolTimeout:120000, timeout:90000});
  let idx=0, rendered=0;
  async function worker(wid){
    const page=await browser.newPage();
    await page.setViewport({width:1000,height:1400,deviceScaleFactor:2});
    await page.goto(TEMPLATE,{waitUntil:'networkidle0'});
    await page.evaluate(async()=>{ if(document.fonts&&document.fonts.ready) await document.fonts.ready; });
    while(true){
      const c=todo[idx++]; if(!c) break;
      // fonts load lazily, on first use: wait for them after every render
      const keys=await page.evaluate(async x=>{ const k=window.renderCards(x); await document.fonts.ready; return k; }, c);
      await new Promise(r=>setTimeout(r,120));
      const cards=await page.$$('#stage .card');
      for(let i=0;i<cards.length;i++){
        const name=`${c.cid}_${String(i+1).padStart(2,'0')}_${keys[i]}.png`;
        await cards[i].screenshot({path:path.join(PNG,name),omitBackground:true});
      }
      rendered++; if(rendered%200===0) console.log(`  rendered ${rendered}/${todo.length}`);
    }
    await page.close();
  }
  await Promise.all(Array.from({length:CONCURRENCY},(_,w)=>worker(w)));
  await browser.close();
  console.log(`done. rendered ${rendered} customers. total pngs: ${fs.readdirSync(PNG).length}`);
})();
