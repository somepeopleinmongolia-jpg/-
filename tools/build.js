// 公開用フォルダ public/ に、公開するファイルだけをコピーする。
// firebase deploy の前に自動で実行される(firebase.json の predeploy)。
// 人物の3Dデータ(.glb)は、Firebaseが自動で圧縮してくれる JSON 形式(データは base64 埋め込み)に変換して置く。
// そのままの .glb は圧縮されず、1体約1.5MBがそのまま配信されるため。
const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'..'),out=path.join(root,'public');
fs.rmSync(out,{recursive:true,force:true});fs.mkdirSync(out);
for(const f of ['index.html','og.png'])fs.copyFileSync(path.join(root,f),path.join(out,f));
fs.cpSync(path.join(root,'vendor'),path.join(out,'vendor'),{recursive:true});
// cine.js:読み込む拡張子を .json に切り替える
const cine=fs.readFileSync(path.join(root,'cine.js'),'utf8');
if(!cine.includes("const MODEL_EXT = '.glb';"))throw new Error('cine.js の MODEL_EXT が見つかりません');
fs.writeFileSync(path.join(out,'cine.js'),cine.replace("const MODEL_EXT = '.glb';","const MODEL_EXT = '.json';"));
// 人物データ:.glb → .json
const src=path.join(root,'assets','people'),dst=path.join(out,'assets','people');
fs.mkdirSync(dst,{recursive:true});
let n=0,bytes=0;
for(const f of fs.readdirSync(src).filter(x=>x.endsWith('.glb'))){
  const b=fs.readFileSync(path.join(src,f));
  const jl=b.readUInt32LE(12),json=JSON.parse(b.slice(20,20+jl).toString('utf8'));
  const o=20+jl,bl=b.readUInt32LE(o),bin=b.slice(o+8,o+8+bl);
  json.buffers[0].uri='data:application/octet-stream;base64,'+bin.toString('base64');
  const s=JSON.stringify(json);
  fs.writeFileSync(path.join(dst,f.replace(/\.glb$/,'.json')),s);n++;bytes+=s.length;
}
console.log('public/ を用意しました(人物データ '+n+'体、'+(bytes/1048576).toFixed(1)+'MB。配信時に圧縮されます)');
