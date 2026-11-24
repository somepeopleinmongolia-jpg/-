// 公開用フォルダ public/ に、公開するファイル(index.html と og.png)だけをコピーする。
// firebase deploy の前に自動で実行される(firebase.json の predeploy)。
const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'..'),out=path.join(root,'public');
fs.rmSync(out,{recursive:true,force:true});fs.mkdirSync(out);
for(const f of ['index.html','og.png'])fs.copyFileSync(path.join(root,f),path.join(out,f));
console.log('public/ に index.html と og.png を用意しました');
