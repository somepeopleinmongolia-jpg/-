// 公開URLをまとめて差し替える。
// 使い方: node tools/set-url.js https://<プロジェクトID>.web.app/
// index.html の CANON_URL・OGP・canonical、README、Firebaseの設定(プロジェクトID)を書き換える。
const fs=require('fs'),path=require('path');
let url=process.argv[2];
if(!url||!/^https:\/\/[^/]+\/?/.test(url)){console.error('使い方: node tools/set-url.js https://<id>.web.app/');process.exit(1)}
if(!url.endsWith('/'))url+='/';
const root=path.resolve(__dirname,'..');
const html=path.join(root,'index.html');
let s=fs.readFileSync(html,'utf8');
const old=s.match(/var CANON_URL='([^']+)'/)[1];
s=s.split(old).join(url);
fs.writeFileSync(html,s);
const rd=path.join(root,'README.md');
fs.writeFileSync(rd,fs.readFileSync(rd,'utf8').split(old).join(url));
const m=url.match(/^https:\/\/([a-z0-9-]+)\.(web\.app|firebaseapp\.com)\//);
if(m){
  const id=m[1];
  const rc=path.join(root,'.firebaserc');
  fs.writeFileSync(rc,JSON.stringify({projects:{default:id}},null,2)+'\n');
  const wf=path.join(root,'.github/workflows/firebase-hosting.yml');
  fs.writeFileSync(wf,fs.readFileSync(wf,'utf8').replace(/projectId: .*/,'projectId: '+id));
  console.log('Firebase プロジェクトID: '+id);
}
console.log(old+' → '+url);
