# 卒論ギリギリシミュレーター

卒論を書き上げる10日間を遊ぶ、スマホ向けのブラウザゲーム。`index.html` 1枚で動く(ビルド不要、外部依存はGoogle Fontsのみ)。

公開URL(Firebase Hosting):https://sotsuron-girigiri.web.app/

## ファイル
- `index.html` … ゲーム本体。単体でも遊べる(カットシーンなし)。
- `cine.js` … 3D人物のカットシーン。`vendor/three/`(Three.js r170, MIT)と `assets/people/` を使う。
- `og.png` … シェア用の画像(1200×630)。OGPタグから参照する。
- `firebase.json` / `.firebaserc` … Firebase Hosting の設定。デプロイ前に `tools/build.js` が、公開するファイル(`index.html`・`og.png`・`cine.js`・`vendor/`・`assets/`)だけを `public/` にコピーする。
- `.github/workflows/firebase-hosting.yml` … push時に自動で公開するワークフロー。
- `tools/set-url.js` … 公開URL(OGP・シェア文・FirebaseのプロジェクトID)を一括で差し替える。
- `tools/balance.js` … 自動プレイでエンディングの出現率を測る(Playwright)。`node tools/balance.js 300`
- `tools/og.html`, `tools/og.js` … `og.png` の元と書き出しスクリプト。`node tools/og.js`

## 3Dの人物カットシーン
- 配属(研究室タイプ別7種)、提出(エンディング別の窓口の反応)、イベント4種(教授のメール・同期の飲みの誘い・恋人・母のビデオ通話)で、3DCGの人物が出てくる。
- 再生は `cine.js`(Three.js を `vendor/three/` から遅延読み込み)。人物モデルは `assets/people/*.glb`(1人約1.5MB、場面ごとに必要な人だけ読む)。
- 読み込めない環境(WebGLなし、`file://` で開いた、claude.ai 上など)や「視差効果を減らす」設定では、カットシーンを飛ばしてゲームだけが進む。
- 人物は架空。素材は MakeHuman/MPFB2 の CC0 アセットで、`tools/human/` のスクリプトで作る(作り方は `tools/human/README.md`)。
- `window.__noCine = true` にするとカットシーンを全部飛ばす(自動プレイ・テスト用)。

## 公開(Firebase Hosting / `○○.web.app`)
公開URLは `https://<FirebaseのプロジェクトID>.web.app/`。いまの設定は `sotsuron-girigiri`。

### 初回だけ
1. https://console.firebase.google.com/ で「プロジェクトを追加」。プロジェクトIDがそのままURLになる(全世界で一意。取られていたら別のIDにする)。Google アナリティクスは不要。
2. IDが `sotsuron-girigiri` と違う場合は、`node tools/set-url.js https://<ID>.web.app/` を実行してコミットする(index.html のOGP・シェアURL、`.firebaserc`、ワークフローを一括で書き換える)。

### 手元のPCから公開する場合
```
npx firebase-tools login
npx firebase-tools deploy --only hosting
```

### GitHubにpushしたら自動で公開する場合
1. Firebaseコンソール → プロジェクトの設定 → サービスアカウント → 「新しい秘密鍵を生成」でJSONをダウンロード。
2. GitHubのリポジトリ → Settings → Secrets and variables → Actions に `FIREBASE_SERVICE_ACCOUNT` という名前でJSONの中身を登録。
3. 以後、pushすると `.github/workflows/firebase-hosting.yml` が公開する。
   - 作業ブランチへのpush → 確認用の一時URL(`sotsuron-girigiri--preview-xxxx.web.app`、30日で消える)。URLはActionsの実行結果の「Summary」に出る。本番は変わらない。
   - `main` へのpush(またはマージ) → 本番 `https://sotsuron-girigiri.web.app/`。
   - 本番で問題が出たら、Firebaseコンソールの Hosting → リリース履歴 から前の版に戻せる。

(`npx firebase-tools init hosting:github` を使うと、1と2を自動でやってくれる。その場合、既存の `firebase.json` は上書きしないこと。)

GitHub Pages など別の場所でも、`index.html` をそのまま置けば動く。その場合も `tools/set-url.js` でURLを合わせる。

## メモ
- 最初にラボ配属ガチャを引く。研究室(7タイプ、名字はランダム)で先生の厳しさや初期値、各種倍率が変わる。定義は `LABS` / `LAB_BASE`。
- 正気度が0になっても1回目は倒れてその日が終わるだけ。2回目で燃え尽き。
- 通常エンディングは12個(`ENDINGS` の `hidden` なし)。判定は `judge()`。追加分:`barely`(字数9,200以上で信頼が低い)、`getaway`(疑惑ありで1万字達成)、`faint`(一度倒れて1万字達成)。
- 優秀卒論賞と早期提出は、「被弾」(`HARM`:データ消失・コーヒー・倒れる・抜き打ち訪問・最終日の目次崩壊)がゼロのときだけ。ハプニングは `INCIDENTS` の `avoid()` で備えていれば避けられる(保存済み、正気度40以上、研究の質40以上)。HUDの「無傷/被弾」で確認できる。
- 隠しエンディングは7つ(`HIDDEN_RULES`)。提出まで進んだとき `rollHidden()` で、条件を満たしたものだけが各1%の抽選に入る。
  - `neko` 猫が卒業:猫の入力を採用した / `uchu` 星間査読:午前2時に乗った / `letter` ラブレター受理:ラブレターを書いた
  - `okan` 母が代理提出:母に長文を返信した / `aigrad` AIが首席卒業:AIに全部書かせた / `nobel` 世紀の大発見(誤):実験で予想と真逆の結果が出た
  - `nature` ネイチャー掲載:「新規性がある」ことにして、研究の質も60以上
  - 確認用に、URLの末尾へ `#preview-neko` などを付けると結果画面だけ見られる(図鑑には記録されない)。公開時に消すなら、`index.html` 末尾の `#preview-` の即時関数を削除。
- 模擬卒論はゲーム内のテンプレートと語彙だけで作る(AI不要)。内容・数値・文献はすべて架空。
- プレイ中の事件(猫の入力、AIに丸投げ、先輩の卒論、徹夜、エナドリ、Wordフリーズなど)は `mark()` で記録され、模擬卒論に痕跡として残る。痕跡の量が「カオス度」(0〜5)になり、3以上で誤字、4以上で章の入れ替わり、5でタイトル崩壊。処理は `chaosify()`。
- 恋人・親とのトークやラブレターも、イベントの選択(またはカオス度4以上のクリップボード事故)で卒論に紛れ込む。文面は `TH_LOVER` / `TH_PARENT` / `TH_LETTER`。
- claude.ai上で開いたときだけ、「Claudeに書き直してもらう」ボタンが追加で出る。
- テスト用フック:`window.__sotsu`(`judge`, `endGame`, `newGame`, `state`)。
