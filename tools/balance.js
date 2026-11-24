// 自動プレイでエンディングの出現率を測る。
// 使い方: node tools/balance.js [1戦略あたりの回数=300] [戦略をカンマ区切り。例 casual,sensible]
// タイマーを早送りするので「書く」の5秒は待たない。
const {chromium}=require('playwright');
const path=require('path');
const N=+process.argv[2]||300;

const SHIM=`(()=>{
  const st=window.setTimeout.bind(window);let vt=0;
  window.__realTimeout=st;
  window.setTimeout=(fn,ms,...a)=>st(fn,0,...a);
  performance.now=()=>(vt+=100);
  window.requestAnimationFrame=cb=>st(()=>cb(performance.now()),0);
  window.cancelAnimationFrame=()=>{};
  window.AudioContext=window.webkitAudioContext=undefined;
  navigator.vibrate=()=>true;
  window.__noCine=true; // 3Dのカットシーンは飛ばす
})();`;

const BOT=`window.__play=async function(strategy){
  const R=Math.random, pick=a=>a[Math.floor(R()*a.length)], rnd=(a,b)=>a+Math.floor(R()*(b-a+1));
  const ch=new MessageChannel(),q=[];ch.port1.onmessage=()=>q.shift()();
  const tick=()=>new Promise(r=>{q.push(r);ch.port2.postMessage(0)});
  const S=()=>window.__sotsu.state;
  const click=b=>b.dispatchEvent(new MouseEvent('click',{bubbles:true}));
  const taps={random:[18,40],casual:[22,36],sensible:[28,40],grinder:[30,42]}[strategy];
  const t0=Date.now();
  while(Date.now()-t0<20000){
    await tick();
    const res=document.querySelector('.result');
    if(res){const s=S();return {chaos:(()=>{let p=0;for(const k in s.marks)p+=s.marks[k];p+=Math.floor((s.crazyN||0)/10)+(s.san<20?1:0)+s.sus*2;return Math.min(5,Math.floor(p*0.8))})(),lab:s.lab,down:s.down,title:document.querySelector('.sc-title').textContent,score:+document.querySelector('.sc-rank').textContent.match(/(\\d+)点/)[1],day:s.day,chars:s.chars,q:s.q,t:s.trust,san:s.san,sus:s.sus}}
    const roll=document.getElementById('roll'),go=document.getElementById('labgo');
    if(go){click(go);continue}
    if(roll){click(roll);continue}
    if(document.querySelector('.gacha'))continue;
    const st=document.getElementById('stage');const c=st&&st.firstElementChild;if(!c)continue;
    const tap=document.getElementById('tap');
    if(tap){if(!tap.disabled&&!tap.dataset.done){tap.dataset.done=1;const n=rnd(...taps);for(let k=0;k<n;k++)tap.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,cancelable:true}))}continue}
    if(c.querySelector('.res-text')){click(c.querySelector('.btn.primary'));continue}
    if(c.querySelector('.ev-title')&&!c.querySelector('.res-text')){
      const bs=[...c.querySelectorAll('.stack .btn')].filter(b=>!b.disabled);
      if(/バックアップ/.test(c.textContent)&&bs.length){ // 夜の保存:慎重な戦略ほど保存する
        const save={random:0.5,casual:0.6,sensible:1,grinder:0.3}[strategy];click(R()<save?bs[0]:bs[1]);continue}
      if(bs.length)click(pick(bs));continue}
    const acts=c.querySelectorAll('.actions .btn');
    if(acts.length){
      const s=S(), sub=c.querySelector('.btn.marker');
      const by=id=>acts[['write','read','exp','ask','sleep'].indexOf(id)];
      let a;
      if(strategy==='random'){ if(sub&&R()<0.5){click(sub);continue} a=pick(['write','read','exp','ask','sleep']); }
      else if(strategy==='casual'){ // ふつうの人:疲れたら寝る、たまに調べる
        if(sub){click(sub);continue}
        a=s.san<25?'sleep':R()<0.55?'write':pick(['read','exp','ask','sleep']);
      }else if(strategy==='sensible'){
        if(sub&&((s.q>=70&&s.trust>=60)||s.day>=9)){click(sub);continue}
        if(s.san<35)a='sleep';
        else if(s.q<45&&R()<0.45)a=pick(['read','exp']);
        else if(s.trust<55&&R()<0.25)a='ask';
        else a=s.chars<10000?'write':pick(['read','exp','ask']);
      }else{ // grinder: 書き続ける
        if(sub){click(sub);continue}
        a=s.san<20?'sleep':'write';
      }
      click(by(a));continue;
    }
  }
  return {title:'STUCK'};
};`;

(async()=>{
  const b=await chromium.launch();const p=await b.newPage();
  await p.addInitScript(SHIM);
  await p.route(/^https?:/,r=>r.abort()); // フォントなど外部は読まない
  const url='file://'+path.resolve(__dirname,'..','index.html');
  const out={};
  const STRATS=(process.argv[3]||'random,casual,sensible,grinder').split(',');
  for(const strat of STRATS){
    const tally={},sc=[],byLab={};let chars=0,downs=0;const ch=[0,0,0,0,0,0];
    for(let i=0;i<N;i++){
      if(i===0&&strat===STRATS[0]){await p.goto(url);await p.evaluate(BOT)}
      else await p.evaluate(()=>document.getElementById('again').click());
      await p.evaluate(()=>document.getElementById('start').click());
      const r=await p.evaluate(s=>window.__play(s),strat);
      if(r.title==='STUCK'){console.log('STUCK');await p.goto(url);await p.evaluate(BOT);i--;continue}
      tally[r.title]=(tally[r.title]||0)+1;sc.push(r.score);chars+=r.chars;if(r.down)downs++;ch[r.chaos]++;
      const B=byLab[r.lab]=byLab[r.lab]||{n:0,good:0,bad:0};B.n++;
      if(/早期|優秀|無事|字数|温情/.test(r.title))B.good++;else B.bad++;
    }
    sc.sort((a,b)=>a-b);
    out[strat]={tally,median:sc[N>>1],avgChars:Math.round(chars/N)};
    console.log('\n['+strat+'] n='+N+' 中央値スコア '+sc[N>>1]+' 平均字数 '+Math.round(chars/N)+' 一度倒れた '+(downs/N*100).toFixed(0)+'%');
    Object.entries(tally).sort((a,b)=>b[1]-a[1]).forEach(([k,v])=>console.log('  '+k.padEnd(14,'　')+(v/N*100).toFixed(1).padStart(5)+'%'));
    console.log('  カオス度の分布(0〜5): '+ch.map(v=>(v/N*100).toFixed(0)+'%').join(' / '));
    console.log('  研究室別 卒業できた率: '+Object.entries(byLab).map(([k,v])=>k+' '+(v.good/v.n*100).toFixed(0)+'%(n='+v.n+')').join(' / '));
  }
  await b.close();
})();
