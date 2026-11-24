# 3D人物の生成(試作)

架空の人物の全身3Dモデル(GLB)を作るスクリプト。素材は MakeHuman / MPFB2 のアセット(CC0)。

- 素材の入手:PyPI の `anny` パッケージ(Apache-2.0)に `data/mpfb2`(CC0)が同梱されている。
  `pip download --no-deps anny==0.6.2` で wheel を取り、`anny/data/mpfb2/` を展開して使う。
- 実行環境:Blender の Python モジュール `bpy`(5.2系、Python 3.13)と numpy, pillow。
- 実行:`python tools/human/build_human.py --mpfb <展開先>/anny/data/mpfb2 --char professor --out assets/people/professor.glb`

中身
- `build_human.py`:体型(性別・年齢・筋肉・体重・身長・民族)を混ぜ、肌・唇・眉・頬・髪の生え際を頂点カラーで塗る。
  服(上着・ズボン)と髪は体を膨らませた殻を Taubin 平滑化して作り、服の下に隠れる体の面は消す。靴は角の丸い箱。
  ゲームエンジン用の骨(53本)、まばたき・口の開閉のシェイプキー付き。
- `animations.py`:待機・歩き・会釈・うなずき・腕組み・手渡しを手付けで作る。
- 人物の設定は `CHARS`(professor / clerk / student)。
