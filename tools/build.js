// 公開用フォルダ public/ に、公開するファイルだけをコピーする。
// firebase deploy の前に自動で実行される(firebase.json の predeploy)。
const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'..'),out=path.join(root,'public');
fs.rmSync(out,{recursive:true,force:true});fs.mkdirSync(out);
const files=['index.html','og.png','cine.js'];
for(const f of files)fs.copyFileSync(path.join(root,f),path.join(out,f));
for(const d of ['vendor','assets'])fs.cpSync(path.join(root,d),path.join(out,d),{recursive:true});
console.log('public/ に '+files.join(', ')+' と vendor/, assets/ を用意しました');
