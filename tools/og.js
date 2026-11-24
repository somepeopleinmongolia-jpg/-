// tools/og.html を 1200x630 の og.png に書き出す
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1200,height:630},deviceScaleFactor:1});
await p.goto('file://'+path.resolve(__dirname,'og.html'));await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(500);
await p.screenshot({path:path.resolve(__dirname,'..','og.png')});await b.close()})();
