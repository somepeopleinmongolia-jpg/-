// 卒論ギリギリシミュレーター:3D人物のカットシーン
// ゲーム本体から import('./cine.js') で遅延読み込みする。Three.js と人物モデル(assets/people/*.glb)を使う。
// 失敗(WebGLなし・読み込み失敗・視差効果を減らす設定)のときは何も表示せずに終わる。
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const BASE = new URL('.', import.meta.url).href;
const cache = new Map();          // model名 -> Promise<gltf>
let R = null;                     // 使い回すレンダラー
const loader = new GLTFLoader();

export function preload(names) {
  for (const n of names) load(n).catch(() => {});
}
const MODEL_EXT = '.glb';
function load(name) {
  if (!cache.has(name)) {
    const p = fetchModel(BASE + 'assets/people/' + name + MODEL_EXT);
    p.catch(() => cache.delete(name));
    cache.set(name, p);
  }
  return cache.get(name);
}

// モデルを取ってきて、メモリ上で読み込む。
// .glb はそのまま。.json(glTF の JSON 形式、データは base64 埋め込み)は、data: URL を使わずに
// 自分でデコードして GLB に組み直す(data: URL の取得を禁じるページでも読めるように)
async function fetchModel(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error('HTTP ' + res.status);
  const buf = await res.arrayBuffer();
  const head = new Uint8Array(buf, 0, 4);
  if (head[0] === 0x67 && head[1] === 0x6c && head[2] === 0x54 && head[3] === 0x46) return loader.parseAsync(buf, '');
  const json = JSON.parse(new TextDecoder().decode(buf));
  const uri = json.buffers && json.buffers[0] && json.buffers[0].uri || '';
  const b64 = uri.slice(uri.indexOf(',') + 1);
  const raw = atob(b64), bin = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) bin[i] = raw.charCodeAt(i);
  delete json.buffers[0].uri;
  json.buffers[0].byteLength = bin.length;
  return loader.parseAsync(toGLB(json, bin), '');
}
function toGLB(json, bin) {
  const enc = new TextEncoder().encode(JSON.stringify(json));
  const jl = Math.ceil(enc.length / 4) * 4, bl = Math.ceil(bin.length / 4) * 4;
  const out = new ArrayBuffer(12 + 8 + jl + 8 + bl), dv = new DataView(out), u8 = new Uint8Array(out);
  dv.setUint32(0, 0x46546c67, true); dv.setUint32(4, 2, true); dv.setUint32(8, out.byteLength, true);
  dv.setUint32(12, jl, true); dv.setUint32(16, 0x4e4f534a, true);
  u8.set(enc, 20); for (let i = enc.length; i < jl; i++) u8[20 + i] = 0x20;
  dv.setUint32(20 + jl, bl, true); dv.setUint32(24 + jl, 0x004e4942, true);
  u8.set(bin, 28 + jl);
  return out;
}

const CSS = `
.cine{position:fixed;inset:0;z-index:60;background:#0b0b0d;overflow:hidden;font-family:var(--f-body,sans-serif);-webkit-user-select:none;user-select:none;animation:cineIn .3s ease-out both}
.cine.out{animation:cineOut .35s ease-in forwards}
@keyframes cineIn{from{opacity:0}to{opacity:1}}
@keyframes cineOut{to{opacity:0}}
.cine-bg{position:absolute;inset:-48px;filter:blur(7px) saturate(.92);transform-origin:50% 42%}
.cine canvas{position:absolute;inset:0;width:100%!important;height:100%!important}
.cine-bar{position:absolute;left:0;right:0;height:8.5%;background:#000;z-index:2}
.cine-bar.t{top:0}.cine-bar.b{bottom:0}
.cine-sub{position:absolute;left:18px;right:18px;bottom:calc(8.5% + 20px);z-index:3;text-align:center;color:#fff;font-weight:900;font-size:18px;line-height:1.5;
  text-shadow:0 2px 4px rgba(0,0,0,.9),0 0 12px rgba(0,0,0,.6);opacity:0;transform:translateY(6px);transition:opacity .2s,transform .2s}
.cine-sub.on{opacity:1;transform:none}
.cine-sub small{display:block;font-size:12px;font-weight:700;opacity:.8;margin-bottom:2px}
.cine-skip{position:absolute;right:12px;top:calc(8.5% + 10px);z-index:4;border:1.5px solid rgba(255,255,255,.6);background:rgba(0,0,0,.35);color:#fff;font:inherit;font-size:12px;font-weight:900;border-radius:99px;padding:4px 12px}
.cine-load{position:absolute;inset:0;display:grid;place-items:center;color:rgba(255,255,255,.7);font-size:13px;font-weight:700;z-index:3}
.cine-flash{position:absolute;inset:0;background:#fff;z-index:3;pointer-events:none;animation:cineFlash .18s ease-out forwards}
@keyframes cineFlash{from{opacity:.85}to{opacity:0}}
.cine-stamp{position:absolute;left:50%;top:36%;z-index:3;width:132px;height:132px;margin:-66px 0 0 -66px;border:7px solid #e23a2e;border-radius:50%;color:#e23a2e;display:grid;place-items:center;
  font-family:var(--f-display,sans-serif);font-size:44px;background:rgba(255,255,251,.82);transform:rotate(-12deg);animation:cineSlam .45s cubic-bezier(.2,1.4,.4,1) both}
@keyframes cineSlam{from{opacity:0;transform:rotate(-30deg) scale(2.6)}to{opacity:1;transform:rotate(-12deg) scale(1)}}
.cine-phone .cine-bar.t,.cine-phone .cine-bar.b{background:#101418}
.cine-call{position:absolute;left:0;right:0;top:calc(8.5% + 10px);z-index:3;text-align:center;color:#fff;text-shadow:0 1px 3px rgba(0,0,0,.7)}
.cine-call b{display:block;font-size:20px}
.cine-call span{font-size:12px;font-weight:700;opacity:.85}
.cine-hang{position:absolute;left:50%;bottom:calc(8.5% + 78px);z-index:3;width:56px;height:56px;margin-left:-28px;border-radius:50%;background:#e5484d;display:grid;place-items:center;color:#fff;font-size:24px;box-shadow:0 2px 8px rgba(0,0,0,.4)}
.cine-self{position:absolute;right:14px;top:calc(8.5% + 64px);z-index:3;width:74px;height:104px;border-radius:12px;border:2px solid rgba(255,255,255,.8);background:linear-gradient(#3a3f47,#1c1f24);display:grid;place-items:center;color:rgba(255,255,255,.7);font-size:11px;font-weight:700}
`;

// 背景(CSSで描いて、ぼかして奥行きを出す)
const BG = {
  lab: `radial-gradient(ellipse 38% 50% at 80% 28%,rgba(255,255,245,.95),rgba(255,255,245,0) 70%),
        linear-gradient(90deg,transparent 7%,#8a7a68 7% 24%,transparent 24%) 0 0/100% 62% no-repeat,
        repeating-linear-gradient(180deg,#6d5f50 0 4px,#b9ab95 4px 44px) 9% 8%/20% 56% no-repeat,
        linear-gradient(90deg,transparent 58%,#4b5a63 58% 66%,transparent 66%) 0 30%/100% 30% no-repeat,
        linear-gradient(#d2d6d1,#bcc0b9 61%,#8f8b82 61.5%,#6f6a62)`,
  night: `radial-gradient(ellipse 30% 22% at 30% 46%,rgba(140,190,255,.9),rgba(140,190,255,0) 70%),
        radial-gradient(circle at 78% 20%,rgba(255,214,150,.55),rgba(255,214,150,0) 22%),
        repeating-linear-gradient(180deg,#2a2622 0 4px,#4c443b 4px 42px) 84% 8%/18% 52% no-repeat,
        linear-gradient(#1f2430,#262a33 60%,#17191e 60.5%,#121316)`,
  counter: `linear-gradient(90deg,transparent 12%,#c9c3b4 12% 13%,transparent 13% 87%,#c9c3b4 87% 88%,transparent 88%) 0 0/100% 60% no-repeat,
        radial-gradient(ellipse 60% 30% at 50% 0,rgba(255,255,255,.9),rgba(255,255,255,0) 70%),
        repeating-linear-gradient(90deg,#d9d6cd 0 120px,#cfccc2 120px 122px),
        linear-gradient(#e7e5df,#dcd9d1)`,
  izakaya: `radial-gradient(circle at 18% 22%,rgba(255,120,60,.95),rgba(255,120,60,0) 9%),
        radial-gradient(circle at 34% 16%,rgba(255,170,80,.9),rgba(255,170,80,0) 8%),
        radial-gradient(circle at 70% 24%,rgba(255,90,70,.9),rgba(255,90,70,0) 10%),
        radial-gradient(circle at 86% 30%,rgba(255,200,110,.85),rgba(255,200,110,0) 8%),
        radial-gradient(circle at 56% 12%,rgba(255,220,150,.7),rgba(255,220,150,0) 7%),
        linear-gradient(#3a2217,#5b3522 58%,#2d1a12 58.5%,#20130d)`,
  room: `radial-gradient(ellipse 40% 40% at 25% 30%,rgba(255,236,200,.95),rgba(255,236,200,0) 70%),
        linear-gradient(90deg,transparent 64%,#9c7c5c 64% 80%,transparent 80%) 0 20%/100% 40% no-repeat,
        linear-gradient(#e9dccb,#d8c7b1 62%,#a8896a 62.5%,#8a6e55)`,
};
// ショット:カメラ位置と注視点を、人物の足元 c と頭 h からの相対で決める
const SHOT = {
  wide:   (c, h) => ({ pos: [0.35, 1.3, 5.6], at: [0, 0.9, -0.6], fov: 30, zoom: 1.0, blur: 6 }),   // 部屋に固定
  full:   (c, h) => ({ pos: [c.x + 0.45, 1.2, c.z + 4.1], at: [c.x, 1.0, c.z], fov: 32, zoom: 1.1, blur: 7 }),
  medium: (c, h) => ({ pos: [h.x + 0.5, h.y - 0.25, h.z + 2.5], at: [h.x, h.y - 0.35, h.z], fov: 30, zoom: 1.2, blur: 9 }),
  close:  (c, h) => ({ pos: [h.x + 0.35, h.y - 0.05, h.z + 1.55], at: [h.x, h.y - 0.1, h.z], fov: 30, zoom: 1.4, blur: 12 }),
  low:    (c, h) => ({ pos: [c.x + 0.5, 0.55, c.z + 1.9], at: [h.x, h.y - 0.2, h.z], fov: 34, zoom: 1.3, blur: 9 }),
  side:   (c, h) => ({ pos: [h.x + 1.3, h.y - 0.1, h.z + 0.9], at: [h.x, h.y - 0.2, h.z], fov: 30, zoom: 1.3, blur: 10 }),
};

const lerp = (a, b, t) => a + (b - a) * t;
const ease = t => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
const text = (tag, cls, t) => { const e = el(tag, cls); e.textContent = t; return e; };

function renderer() {
  if (R) return R;
  const r = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
  r.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  r.outputColorSpace = THREE.SRGBColorSpace;
  r.toneMapping = THREE.ACESFilmicToneMapping;
  r.toneMappingExposure = 1.05;
  R = r;
  return r;
}

function propBox(w, h, d, color) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), new THREE.MeshStandardMaterial({ color, roughness: 0.75 }));
  return m;
}

// 窓口のセット(カウンター・書類・シャッター)
function counterSet(scene) {
  const g = new THREE.Group();
  const top = propBox(2.4, 0.05, 0.6, 0xd8d2c4); top.position.set(0, 1.0, 0.55); g.add(top);
  const front = propBox(2.4, 1.0, 0.05, 0x9aa3a8); front.position.set(0, 0.5, 0.83); g.add(front);
  const paper = new THREE.Group();
  const pages = propBox(0.21, 0.03, 0.297, 0xfbfaf4); paper.add(pages);
  const cover = propBox(0.215, 0.006, 0.30, 0x2e4a7a); cover.position.y = 0.018; paper.add(cover);
  paper.position.set(0.05, 1.04, 0.95); g.add(paper);
  const shutter = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 1.3), new THREE.MeshStandardMaterial({ map: shutterTex(), roughness: 0.5, metalness: 0.3 }));
  shutter.position.set(0, 2.9, 0.88); g.add(shutter);
  scene.add(g);
  return { paper, shutter };
}
function shutterTex() {
  const c = document.createElement('canvas'); c.width = 64; c.height = 256;
  const x = c.getContext('2d');
  for (let y = 0; y < 256; y += 16) { x.fillStyle = '#b7bcc0'; x.fillRect(0, y, 64, 12); x.fillStyle = '#8c9297'; x.fillRect(0, y + 12, 64, 4); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1, 3);
  return t;
}

/**
 * spec = {
 *   model, bg, frame:'cinema'|'phone', call:{name}, set:'counter',
 *   at:[x,z], face:度, dur:秒,
 *   keys:[[秒,'shot',名前], [秒,'anim',名前], [秒,'say',文,秒,話者], [秒,'move',[x,z],秒,'walk'|'run'],
 *         [秒,'face',度,秒], [秒,'show'|'hide'], [秒,'stamp',文字], [秒,'paper',[x,y,z],秒], [秒,'shutter',秒], [秒,'flash']]
 * }
 */
export function play(spec) {
  return new Promise(resolve => {
    let calm = false; // 視差効果を減らす設定:シーンは見せるが、カメラは動かさない
    try { calm = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches); } catch (e) {}
    let done = false, raf = 0, why = '';
    if (!document.getElementById('cine-css')) { const s = el('style'); s.id = 'cine-css'; s.textContent = CSS; document.head.appendChild(s); }
    const ov = el('div', 'cine' + (spec.frame === 'phone' ? ' cine-phone' : ''));
    ov.setAttribute('role', 'dialog'); ov.setAttribute('aria-label', spec.label || 'ムービー');
    const bg = el('div', 'cine-bg'); bg.style.background = BG[spec.bg] || BG.lab; ov.appendChild(bg);
    const loading = text('div', 'cine-load', '読み込み中…'); ov.appendChild(loading);
    ov.appendChild(el('div', 'cine-bar t')); ov.appendChild(el('div', 'cine-bar b'));
    const sub = el('div', 'cine-sub'); ov.appendChild(sub);
    if (spec.frame === 'phone') {
      const call = el('div', 'cine-call'); call.appendChild(text('b', '', spec.call && spec.call.name || ''));
      const tm = text('span', '', 'ビデオ通話 00:00'); call.appendChild(tm); ov.appendChild(call);
      ov.appendChild(el('div', 'cine-hang', '✕')); ov.appendChild(text('div', 'cine-self', 'あなた'));
      spec._timer = tm;
    }
    const skip = text('button', 'cine-skip', 'スキップ ▶▶'); skip.type = 'button'; ov.appendChild(skip);
    document.body.appendChild(ov);

    function finish() {
      if (done) return; done = true;
      cancelAnimationFrame(raf);
      ov.classList.add('out');
      setTimeout(() => { if (ov.parentNode) ov.parentNode.removeChild(ov); resolve(why ? { why } : { ok: true }); }, 330);
    }
    skip.addEventListener('click', e => { e.stopPropagation(); finish(); });
    ov.addEventListener('click', () => { if (ov.dataset.ready) finish(); });
    const giveUp = setTimeout(() => { if (!ov.dataset.ready) { why = '人物データの読み込みに時間がかかりすぎた'; finish(); } }, 25000);

    let r;
    try { r = renderer(); } catch (e) { clearTimeout(giveUp); why = 'この端末では3D表示(WebGL)が使えない'; return finish(); }
    load(spec.model).then(gltf => {
      if (done) return;
      clearTimeout(giveUp);
      loading.remove();
      start(gltf);
    }).catch(e => { clearTimeout(giveUp); why = '人物データを読み込めなかった(' + String(e && e.message || e).slice(0, 80) + ')'; finish(); });

    function start(gltf) {
      const W = ov.clientWidth, H = ov.clientHeight;
      r.setSize(W, H, false);
      ov.insertBefore(r.domElement, ov.querySelector('.cine-bar'));
      const scene = new THREE.Scene();
      const warm = spec.bg === 'izakaya' || spec.bg === 'room';
      scene.add(new THREE.HemisphereLight(warm ? 0xfff0dc : 0xf4f1ea, 0x6b6258, spec.bg === 'night' ? 0.7 : 1.25));
      const key = new THREE.DirectionalLight(spec.bg === 'night' ? 0xb8d4ff : 0xfff6e8, spec.bg === 'night' ? 1.6 : 2.4); key.position.set(2.5, 3.2, 2.2); scene.add(key);
      const rim = new THREE.DirectionalLight(warm ? 0xffb070 : 0xdfe8ff, 1.2); rim.position.set(-2, 2.5, -2.5); scene.add(rim);
      const shadow = new THREE.Mesh(new THREE.CircleGeometry(0.42, 32), new THREE.MeshBasicMaterial({ color: 0, transparent: true, opacity: 0.28, depthWrite: false }));
      shadow.rotation.x = -Math.PI / 2; shadow.scale.set(1, 0.6, 1); scene.add(shadow);
      const set = spec.set === 'counter' ? counterSet(scene) : null;

      // 同じモデルを何度も使えるよう、シーンごとに複製する
      const man = cloneSkinned(gltf.scene);
      scene.add(man);
      let body = null; man.traverse(o => { if (o.morphTargetDictionary && o.morphTargetDictionary.blink != null) body = o; });
      const mixer = new THREE.AnimationMixer(man);
      const acts = {}; gltf.animations.forEach(c => { acts[c.name] = mixer.clipAction(c); });
      ['bow', 'nod', 'tilt', 'shake', 'handover', 'wave', 'beckon', 'cheer', 'armsfold'].forEach(n => { if (acts[n]) { acts[n].setLoop(THREE.LoopOnce); acts[n].clampWhenFinished = true; } });
      let cur = null;
      const playAnim = (n, fade = 0.3) => { const a = acts[n]; if (!a || a === cur) return; a.reset().play(); if (cur) cur.crossFadeTo(a, fade, false); cur = a; };
      playAnim('idle', 0);

      const at = spec.at || [0, 0];
      man.position.set(at[0], 0, at[1]);
      man.rotation.y = THREE.MathUtils.degToRad(spec.face || 0);
      man.updateMatrixWorld(true);
      // 目の高さ:モデルの頭頂から 11.5cm 下(骨の位置は人によってずれるので形から測る)
      const box = new THREE.Box3().setFromObject(man);
      const headY = box.max.y - 0.115;
      const hb = man.getObjectByName('head'), hw = new THREE.Vector3();
      if (hb) hb.getWorldPosition(hw); else hw.copy(man.position);
      const hoff = new THREE.Vector3(hw.x - man.position.x, 0, hw.z - man.position.z);
      if (spec.hidden) man.visible = false;

      const cam = new THREE.PerspectiveCamera(30, W / H, 0.05, 60);
      let shot = SHOT.full, shotT = 0;
      let move = null, turn = null, talkUntil = 0, paperMove = null, shutterMove = null;
      const keys = (spec.keys || []).slice().sort((a, b) => a[0] - b[0]);
      let ki = 0;
      const blinks = [0.8, 2.6, 4.1, 5.9, 7.6, 9.2];
      const t0 = performance.now(); let last = t0;
      ov.dataset.ready = '1';

      function doKey(k, t) {
        const [, type, a, b, c] = k;
        if (type === 'shot') { shot = SHOT[a] || SHOT.full; shotT = t; }
        else if (type === 'anim') playAnim(a);
        else if (type === 'say') {
          sub.innerHTML = '';
          if (c) sub.appendChild(text('small', '', c));
          sub.appendChild(document.createTextNode(a));
          sub.classList.add('on');
          talkUntil = t + Math.min(b || 2, String(a).length * 0.11 + 0.3);
          const end = t + (b || 2);
          keys.push([end, '_unsay', a]); keys.sort((x, y) => x[0] - y[0]);
        } else if (type === '_unsay') { if (sub.lastChild && sub.lastChild.textContent === a) sub.classList.remove('on'); }
        else if (type === 'move') {
          move = { from: [man.position.x, man.position.z], to: a, t0: t, dur: b, anim: c || 'walk' };
          playAnim(move.anim, 0.2);
        } else if (type === 'face') turn = { from: man.rotation.y, to: THREE.MathUtils.degToRad(a), t0: t, dur: b || 0.5 };
        else if (type === 'show') man.visible = true;
        else if (type === 'hide') man.visible = false;
        else if (type === 'flash') ov.appendChild(el('div', 'cine-flash'));
        else if (type === 'stamp') { const s = text('div', 'cine-stamp', a); ov.appendChild(s); ov.appendChild(el('div', 'cine-flash')); try { navigator.vibrate && navigator.vibrate(40); } catch (e) {} }
        else if (type === 'paper' && set) paperMove = { from: set.paper.position.clone(), to: new THREE.Vector3(...a), t0: t, dur: b || 0.8 };
        else if (type === 'shutter' && set) shutterMove = { t0: t, dur: a || 1.2 };
      }

      function frame(now) {
        if (done) return;
        const dt = Math.min(0.05, (now - last) / 1000); last = now;
        const t = (now - t0) / 1000;
        while (ki < keys.length && keys[ki][0] <= t) doKey(keys[ki++], t);
        if (move) {
          const k = Math.min(1, (t - move.t0) / move.dur);
          const x = lerp(move.from[0], move.to[0], k), z = lerp(move.from[1], move.to[1], k);
          const dx = move.to[0] - move.from[0], dz = move.to[1] - move.from[1];
          if (Math.hypot(dx, dz) > 0.01) man.rotation.y = Math.atan2(dx, dz);
          man.position.set(x, 0, z);
          if (k >= 1) { move = null; playAnim('idle', 0.35); turn = { from: man.rotation.y, to: 0, t0: t, dur: 0.5 }; }
        }
        if (turn) { const k = Math.min(1, (t - turn.t0) / turn.dur); man.rotation.y = lerp(turn.from, turn.to, ease(k)); if (k >= 1) turn = null; }
        if (paperMove) { const k = Math.min(1, (t - paperMove.t0) / paperMove.dur); set.paper.position.lerpVectors(paperMove.from, paperMove.to, ease(k)); if (k >= 1) paperMove = null; }
        if (shutterMove) { const k = Math.min(1, (t - shutterMove.t0) / shutterMove.dur); set.shutter.position.y = lerp(2.9, 1.65, k * k); if (k >= 1) shutterMove = null; }
        shadow.position.set(man.position.x, 0.002, man.position.z); shadow.visible = man.visible;
        mixer.update(dt);
        if (body) {
          const d = body.morphTargetDictionary, inf = body.morphTargetInfluences;
          inf[d.blink] = blinks.some(b => t > b && t < b + 0.14) ? 1 : 0;
          if (d.mouth != null) inf[d.mouth] = t < talkUntil ? 0.12 + 0.12 * Math.abs(Math.sin(t * 17)) : 0;
        }
        // カメラ:ショットの基準位置から、ゆっくり寄る
        const c = man.position, h = new THREE.Vector3(c.x + hoff.x, headY, c.z + hoff.z);
        const s = shot(c, h), k = t - shotT;
        cam.fov = s.fov; cam.aspect = W / H; cam.updateProjectionMatrix();
        const dir = new THREE.Vector3(s.at[0] - s.pos[0], s.at[1] - s.pos[1], s.at[2] - s.pos[2]).normalize();
        const dolly = calm ? 0 : 0.04;
        cam.position.set(s.pos[0] + dir.x * k * dolly, s.pos[1] + dir.y * k * dolly, s.pos[2] + dir.z * k * dolly);
        cam.lookAt(s.at[0], s.at[1], s.at[2]);
        bg.style.transform = `scale(${s.zoom + k * 0.012}) translateX(${-cam.position.x * 18}px)`;
        bg.style.filter = `blur(${s.blur}px) saturate(.92)`;
        if (spec._timer) spec._timer.textContent = 'ビデオ通話 00:' + String(Math.floor(t + 12)).padStart(2, '0');
        r.render(scene, cam);
        if (t >= spec.dur) return finish();
        raf = requestAnimationFrame(frame);
      }
      raf = requestAnimationFrame(frame);
    }
  });
}

// SkinnedMesh を含むシーンの複製(骨の対応を付け直す)
function cloneSkinned(src) {
  const map = new Map();
  const dst = src.clone(true);
  const srcList = [], dstList = [];
  src.traverse(o => srcList.push(o)); dst.traverse(o => dstList.push(o));
  srcList.forEach((o, i) => map.set(o, dstList[i]));
  dst.traverse(o => {
    if (o.isSkinnedMesh) {
      const sk = o.skeleton;
      const bones = sk.bones.map(b => map.get(b));
      o.bind(new THREE.Skeleton(bones, sk.boneInverses), o.bindMatrix);
      o.morphTargetInfluences = o.morphTargetInfluences ? o.morphTargetInfluences.slice() : o.morphTargetInfluences;
    }
  });
  return dst;
}
