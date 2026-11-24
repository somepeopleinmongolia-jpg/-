# 卒論ギリギリシミュレーター

卒論を書き上げる10日間を遊ぶ、スマホ向けのブラウザゲーム。`index.html` 1枚で動く(ビルド不要、外部依存はGoogle Fontsのみ)。

公開URL(GitHub Pages):https://somepeopleinmongolia-jpg.github.io/-/

## ファイル
- `index.html` … ゲーム本体。これだけで遊べる。
- `og.png` … シェア用の画像(1200×630)。OGPタグから参照する。
- `.nojekyll` … GitHub PagesでJekyll処理をしない。
- `tools/balance.js` … 自動プレイでエンディングの出現率を測る(Playwright)。`node tools/balance.js 300`
- `tools/og.html`, `tools/og.js` … `og.png` の元と書き出しスクリプト。`node tools/og.js`

## 公開(GitHub Pages)
1. リポジトリの Settings → Pages を開く。
2. Source を「Deploy from a branch」にし、公開したいブランチと `/ (root)` を選んで保存。
3. 数分後に上の公開URLで開ける。

別の場所(Vercel / Netlify など)に置く場合は、`index.html` の `CANON_URL` と、`<head>` の `og:url` / `og:image` / `twitter:image` / `canonical` のURLを書き換える。

## メモ
- 最初にラボ配属ガチャを引く。研究室(7タイプ、名字はランダム)で先生の厳しさや初期値、各種倍率が変わる。定義は `LABS` / `LAB_BASE`。
- 正気度が0になっても1回目は倒れてその日が終わるだけ。2回目で燃え尽き。
- 模擬卒論はゲーム内のテンプレートと語彙だけで作る(AI不要)。内容・数値・文献はすべて架空。
- プレイ中の事件(猫の入力、AIに丸投げ、先輩の卒論、徹夜、エナドリ、Wordフリーズなど)は `mark()` で記録され、模擬卒論に痕跡として残る。痕跡の量が「カオス度」(0〜5)になり、3以上で誤字、4以上で章の入れ替わり、5でタイトル崩壊。処理は `chaosify()`。
- claude.ai上で開いたときだけ、「Claudeに書き直してもらう」ボタンが追加で出る。
- テスト用フック:`window.__sotsu`(`judge`, `endGame`, `newGame`, `state`)。
