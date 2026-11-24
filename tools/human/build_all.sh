#!/bin/sh
# 全員分の GLB を assets/people/ に書き出す。
# 使い方: tools/human/build_all.sh <bpy の入った python> <.../anny/data/mpfb2>
set -e
PY=${1:?python with bpy}; MPFB=${2:?mpfb2 dir}
cd "$(dirname "$0")/../.."
for c in prof_normal prof_hotoke prof_oni prof_taiiku prof_core prof_absent prof_yuru clerk friend lover mother; do
  "$PY" tools/human/build_human.py --mpfb "$MPFB" --char "$c" --out "assets/people/$c.glb" 2>&1 | grep -E "wrote|Error|Traceback" || true
done
