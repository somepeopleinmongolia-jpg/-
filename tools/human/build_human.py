"""
架空の人物の全身3Dモデル(GLB)を組み立てる。

素材:MakeHuman / MPFB2 のアセット(CC0)。PyPI の anny パッケージ同梱の data/mpfb2 を使う。
使い方(Blender の Python モジュール bpy が入った Python で実行):
  python tools/human/build_human.py --mpfb <.../anny/data/mpfb2> --char professor --out assets/people/professor.glb

やること
  1. base.obj を読み、体型ターゲット(性別・年齢・筋肉・体重・身長・民族)を混ぜる
  2. 体・目・まつげ・歯・舌を1つのメッシュにし、頂点カラーで肌・唇・眉・頬を塗る
  3. 服(シャツ/上着・ズボン・靴)と髪は、体や補助メッシュを法線方向に少し膨らませた殻で作る
  4. ゲームエンジン用の骨(53本)と重みを付け、まばたき・口の開閉をシェイプキーにする
  5. 簡単なアニメーション(待機・歩き・会釈・うなずき 等)を付けて GLB に書き出す
"""
import argparse, gzip, json, math, os, sys
import numpy as np

def C(**k):
    base = dict(gender=1.0, age=0.7, muscle=0.5, weight=0.5, height=0.5,
                race=dict(asian=0.88, caucasian=0.12, african=0.0),
                skin=(0.82, 0.64, 0.51), hair=(0.05, 0.045, 0.045), hair_gray=0.0, hair_style='short',
                top=(0.5, 0.5, 0.5), pants=(0.22, 0.23, 0.26), shoes=(0.12, 0.09, 0.07), brow=0.55)
    base.update(k)
    return base

# 登場人物(すべて架空)。age: 0.5=25歳, 0.75≒57歳, 1.0=90歳
CHARS = {
    'prof_normal': C(age=0.74, muscle=0.42, weight=0.62, height=0.45, hair_gray=0.12, top=(0.93, 0.93, 0.91),
                     outer=(0.18, 0.19, 0.22), outer_kind='suit', tie=(0.12, 0.17, 0.36), pants=(0.17, 0.18, 0.21)),
    'prof_hotoke': C(age=0.84, muscle=0.35, weight=0.8, height=0.4, hair_gray=0.75, skin=(0.84, 0.66, 0.53),
                     top=(0.95, 0.93, 0.88), outer=(0.70, 0.60, 0.44), outer_kind='suit', tie=(0.46, 0.14, 0.16), pants=(0.24, 0.19, 0.15)),
    'prof_oni': C(age=0.66, muscle=0.5, weight=0.3, height=0.62, hair_gray=0.05, brow=0.85,
                  top=(0.96, 0.96, 0.95), outer=(0.07, 0.07, 0.09), outer_kind='suit', tie=(0.45, 0.06, 0.08),
                  pants=(0.07, 0.07, 0.09), shoes=(0.04, 0.04, 0.04)),
    'prof_taiiku': C(age=0.62, muscle=0.95, weight=0.55, height=0.58, hair_style='buzz', skin=(0.74, 0.54, 0.40),
                     top=(0.62, 0.12, 0.13), pants=(0.10, 0.12, 0.26), shoes=(0.90, 0.90, 0.88)),
    'prof_core': C(gender=0.0, age=0.7, muscle=0.45, weight=0.42, height=0.5, hair_style='bob', hair_gray=0.2,
                   top=(0.94, 0.94, 0.95), outer=(0.28, 0.30, 0.36), outer_kind='suit', pants=(0.22, 0.24, 0.30), brow=0.45),
    'prof_absent': C(age=0.72, muscle=0.45, weight=0.5, height=0.55, hair_gray=0.4,
                     top=(0.55, 0.44, 0.30), pants=(0.62, 0.56, 0.44)),
    'prof_yuru': C(age=0.58, muscle=0.45, weight=0.5, height=0.52, top=(0.40, 0.44, 0.31),
                   pants=(0.20, 0.27, 0.42), shoes=(0.88, 0.88, 0.86)),
    'clerk': C(gender=0.0, age=0.6, muscle=0.45, weight=0.45, height=0.42, hair_style='bob', skin=(0.86, 0.68, 0.56),
               top=(0.70, 0.78, 0.90), outer=(0.12, 0.16, 0.28), outer_kind='suit', pants=(0.12, 0.16, 0.28), shoes=(0.06, 0.05, 0.05), brow=0.45),
    'friend': C(age=0.52, muscle=0.55, weight=0.5, height=0.56, top=(0.52, 0.54, 0.50),
                pants=(0.18, 0.24, 0.36), shoes=(0.86, 0.86, 0.84), brow=0.6),
    'lover': C(gender=0.0, age=0.51, muscle=0.45, weight=0.42, height=0.45, hair_style='bob', skin=(0.87, 0.69, 0.57),
               hair=(0.12, 0.08, 0.06), top=(0.86, 0.66, 0.68), outer=(0.93, 0.89, 0.81), outer_kind='open', pants=(0.70, 0.64, 0.55), shoes=(0.85, 0.82, 0.78), brow=0.4),
    'mother': C(gender=0.0, age=0.8, muscle=0.4, weight=0.66, height=0.38, hair_style='bob', hair_gray=0.3,
                top=(0.72, 0.56, 0.26), outer=(0.80, 0.36, 0.34), outer_kind='apron', pants=(0.36, 0.30, 0.25), brow=0.4),
}
CHARS['professor'] = CHARS['prof_normal']

GROIN = (2.2, 0.2, 62)   # 骨盤の下(dm)の範囲と、基準にする前方位置のパーセンタイル
GROUND = [0.0]  # 足裏を z=0 に合わせるためのずらし量(位置にだけ足す)

def obj2bl(p):
    """MakeHuman の obj(Y上・デシメートル)→ Blender(Z上・メートル)。差分(ベクトル)用"""
    p = np.asarray(p, dtype=np.float64)
    return np.stack([p[..., 0], -p[..., 2], p[..., 1]], -1) * 0.1

def pos2bl(p):
    """位置用:obj2bl + 床合わせ"""
    return obj2bl(p) + np.array([0, 0, GROUND[0]])

# ---------------------------------------------------------------- obj / targets
def load_obj(path):
    V, VT, faces = [], [], []
    grp = None
    for line in open(path):
        if line.startswith('v '):
            V.append([float(x) for x in line.split()[1:4]])
        elif line.startswith('vt '):
            VT.append([float(x) for x in line.split()[1:3]])
        elif line.startswith('g '):
            grp = line.split()[1]
        elif line.startswith('f '):
            vi, ti = [], []
            for t in line.split()[1:]:
                a = t.split('/')
                vi.append(int(a[0]) - 1)
                ti.append(int(a[1]) - 1 if len(a) > 1 and a[1] else -1)
            faces.append((grp, vi, ti))
    return np.array(V), np.array(VT), faces

_tcache = {}
def load_target(path, n):
    if path in _tcache:
        return _tcache[path]
    d = np.zeros((n, 3))
    if os.path.exists(path):
        for line in gzip.open(path, 'rt'):
            if not line.strip() or line.startswith('#'):
                continue
            a = line.split()
            d[int(a[0])] = [float(a[1]), float(a[2]), float(a[3])]
    else:
        print('  (missing target)', os.path.basename(path))
    _tcache[path] = d
    return d

def two(v, lo, hi):
    """0..1 の値を lo/hi の重みに"""
    return {lo: 1 - v, hi: v}

def macro_weights(c):
    g = two(c['gender'], 'female', 'male')
    a = c['age']
    if a < 0.1875:
        t = a / 0.1875; age = {'baby': 1 - t, 'child': t}
    elif a < 0.5:
        t = (a - 0.1875) / (0.5 - 0.1875); age = {'child': 1 - t, 'young': t}
    else:
        t = (a - 0.5) / 0.5; age = {'young': 1 - t, 'old': t}
    m = c['muscle']
    mus = {'minmuscle': 1 - m / 0.5, 'averagemuscle': m / 0.5} if m < 0.5 else {'averagemuscle': 1 - (m - 0.5) / 0.5, 'maxmuscle': (m - 0.5) / 0.5}
    w = c['weight']
    wei = {'minweight': 1 - w / 0.5, 'averageweight': w / 0.5} if w < 0.5 else {'averageweight': 1 - (w - 0.5) / 0.5, 'maxweight': (w - 0.5) / 0.5}
    return g, age, mus, wei

def shape_body(V, mpfb, c):
    n = len(V)
    td = os.path.join(mpfb, 'targets', 'macrodetails')
    g, age, mus, wei = macro_weights(c)
    out = V.copy()
    for gk, gw in g.items():
        for ak, aw in age.items():
            for mk, mw in mus.items():
                for wk, ww in wei.items():
                    k = gw * aw * mw * ww
                    if k > 1e-4:
                        out += k * load_target(os.path.join(td, f'universal-{gk}-{ak}-{mk}-{wk}.target.gz'), n)
                    h = c['height']
                    hk, hw = ('minheight', (0.5 - h) * 2) if h < 0.5 else ('maxheight', (h - 0.5) * 2)
                    if k * hw > 1e-4:
                        out += k * hw * load_target(os.path.join(td, 'height', f'{gk}-{ak}-{mk}-{wk}-{hk}.target.gz'), n)
            for rk, rw in c['race'].items():
                k = rw * gw * aw
                if k > 1e-4:
                    out += k * load_target(os.path.join(td, f'{rk}-{gk}-{ak}.target.gz'), n)
    return out

def expr_delta(mpfb, name, n, race):
    d = np.zeros((n, 3))
    for rk, rw in race.items():
        if rw > 0:
            d += rw * load_target(os.path.join(mpfb, 'targets', 'expression', 'units', rk, name + '.target.gz'), n)
    return d

def vertex_normals(P, faces):
    N = np.zeros_like(P)
    for f in faces:
        p = P[f]
        nrm = np.cross(p[1] - p[0], p[2] - p[0])
        if len(f) == 4:
            nrm = nrm + np.cross(p[2] - p[0], p[3] - p[0])
        N[f] += nrm
    l = np.linalg.norm(N, axis=1, keepdims=True)
    return N / np.maximum(l, 1e-9)

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mpfb', required=True)
    ap.add_argument('--char', default='professor')
    ap.add_argument('--out', required=True)
    args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    c = CHARS[args.char]
    mp = args.mpfb

    V0, VT, faces = load_obj(os.path.join(mp, '3dobjs', 'base.obj'))
    n = len(V0)
    print('verts', n, 'faces', len(faces))
    V = shape_body(V0, mp, c)
    if c['gender'] < 0.5:
        # 服の上から体の線が出すぎないよう、胸の張り出しを控えめにする
        for t in ('breast-point-decr', 'nipple-point-decr'):
            V = V + load_target(os.path.join(mp, 'targets', 'breast', t + '.target.gz'), n)
    GROUND[0] = -obj2bl(V[:13380])[:, 2].min()
    blink = (expr_delta(mp, 'eye-left-closure', n, c['race']) + expr_delta(mp, 'eye-right-closure', n, c['race']))
    mouth = expr_delta(mp, 'mouth-open', n, c['race'])

    groups = {}
    for gname, vi, ti in faces:
        groups.setdefault(gname, []).append((vi, ti))
    def gverts(name):
        return sorted({i for vi, _ in groups.get(name, []) for i in vi})

    # 股間の膨らみをなくす:体そのものの前方への張り出しを、まわりの面にならす(服も肌も同じ体に沿うので穴は出ない)
    ypel = float(V[gverts('joint-pelvis')].mean(0)[1])
    zone = (np.abs(V[:, 0]) < 1.0) & (V[:, 1] > ypel - GROIN[0]) & (V[:, 1] < ypel - GROIN[1]) & (V[:, 2] > 0)
    zone[13380:] = False
    if zone.any():
        ref = float(np.percentile(V[zone, 2], GROIN[2]))
        wxg = np.clip(1 - (np.abs(V[:, 0]) - 0.6) / 0.4, 0, 1)
        wyg = np.clip((V[:, 1] - (ypel - GROIN[0])) / 0.25, 0, 1) * np.clip(((ypel - GROIN[1]) - V[:, 1]) / 0.25, 0, 1)
        wg = wxg * wyg * zone
        print('groin zone', int(zone.sum()), 'ref', round(ref, 3), 'max z', round(float(V[zone, 2].max()), 3))
        V[:, 2] -= np.maximum(0, V[:, 2] - ref) * wg * 0.9

    # 骨の位置
    rig = json.load(open(os.path.join(mp, 'rigs', 'standard', 'rig.game_engine.json')))
    W = json.load(open(os.path.join(mp, 'rigs', 'standard', 'weights.game_engine.json')))['weights']
    def joint(spec):
        if spec['strategy'] == 'CUBE':
            return V[gverts(spec['cube_name'])].mean(0)
        return V[spec['vertex_indices']].mean(0)
    bones = {b: dict(head=pos2bl(joint(d['head'])), tail=pos2bl(joint(d['tail'])), roll=d['roll'], parent=d['parent']) for b, d in rig.items()}

    # 支配的な骨(服の領域分けに使う)
    wmat = {}
    for b, lst in W.items():
        for i, w in lst:
            if w > wmat.get(i, (None, 0))[1]:
                wmat[i] = (b, w)
    dom = np.array([wmat.get(i, ('Root', 0))[0] for i in range(n)], dtype=object)

    # 体メッシュ(体+目+まつげ+歯+舌)
    keep = ['body', 'helper-l-eye', 'helper-r-eye', 'helper-upper-teeth', 'helper-lower-teeth', 'helper-tongue']
    mat_of = lambda g: 'skin' if g == 'body' else 'eye' if g.endswith('-eye') else 'lash' if 'eyelashes' in g else 'teeth' if 'teeth' in g else 'tongue'
    body_faces = [(vi, ti, mat_of(g)) for g in keep for vi, ti in groups.get(g, [])]

    # 頂点カラー(肌・唇・眉・頬・目)
    from PIL import Image
    lips_mask = np.asarray(Image.open(os.path.join(mp, 'textures', 'mpfb_lips.jpg')).convert('L'), dtype=np.float32) / 255
    vuv = np.zeros((n, 2)); has = np.zeros(n, bool)
    for vi, ti, _ in body_faces:
        for a, t in zip(vi, ti):
            if t >= 0 and not has[a]:
                vuv[a] = VT[t]; has[a] = True
    H, Wd = lips_mask.shape
    px = np.clip((vuv[:, 0] * (Wd - 1)).astype(int), 0, Wd - 1)
    py = np.clip(((1 - vuv[:, 1]) * (H - 1)).astype(int), 0, H - 1)
    lip = lips_mask[py, px] * has
    P = pos2bl(V)
    skin = np.array(c['skin'])
    rng = np.random.default_rng(7)
    col = np.tile(skin, (n, 1)) * (0.97 + 0.06 * rng.random((n, 1)))
    lipc = skin * np.array([0.86, 0.55, 0.52])
    col = col * (1 - lip[:, None] * 0.85) + lipc * lip[:, None] * 0.85
    # 眉:目の関節の少し上、額の帯
    eyeL = P[gverts('joint-l-eye')].mean(0); eyeR = P[gverts('joint-r-eye')].mean(0)
    head_front = P[:13380][:, 1].min()
    for e in (eyeL, eyeR):
        d = P - e
        # x方向に眉の幅、z方向に目の 1.8〜3.0cm 上、前面のみ
        bx = np.clip(1 - (np.abs(d[:, 0] - np.sign(e[0]) * 0.005) / 0.021) ** 2, 0, 1)
        bz = np.clip(1 - ((d[:, 2] - 0.026) / 0.0085) ** 2, 0, 1)
        front = (d[:, 1] < 0.0).astype(float) * (np.abs(d[:, 1]) < 0.05)
        b = np.clip(bx * bz * front * c['brow'] * 1.7, 0, 0.95)
        b[13380:] = 0
        hc = np.array(c['hair']) * 1.1
        col = col * (1 - b[:, None]) + hc * b[:, None]
        # 頬:目の下外側
        ch = np.exp(-(((d[:, 0] - np.sign(e[0]) * 0.012) / 0.02) ** 2 + ((d[:, 2] + 0.03) / 0.018) ** 2)) * front * 0.12
        ch[13380:] = 0
        col = col * (1 - ch[:, None]) + np.array([0.85, 0.45, 0.42]) * ch[:, None]
    # 目:白目+前方の頂点を虹彩・瞳孔に
    for side in ('l', 'r'):
        ev = gverts(f'helper-{side}-eye')
        cen = P[ev].mean(0)
        fwd = (P[ev] - cen) / np.maximum(np.linalg.norm(P[ev] - cen, axis=1, keepdims=True), 1e-9)
        f = -fwd[:, 1]  # -Y が正面
        ec = np.where(f[:, None] > 0.985, [0.04, 0.03, 0.03], np.where(f[:, None] > 0.90, [0.30, 0.19, 0.12], [0.93, 0.91, 0.88]))
        col[ev] = ec

    # 髪:なめらかな重み。肌に塗って生え際をぼかし、内側だけ殻で厚みを出す
    eyeC = (eyeL + eyeR) / 2
    sig = lambda x: 1 / (1 + np.exp(-x))
    dy = P[:, 1] - eyeC[1]; dz = P[:, 2] - eyeC[2]
    dx = np.abs(P[:, 0] - eyeC[0])
    thr = 0.043 - 0.013 * np.clip(dx / 0.075, 0, 1) ** 1.5      # 中央が高く、こめかみで低い(前髪は額の近くまで)
    hw = np.maximum.reduce([
        sig((dz - thr) / 0.0055) * sig((dy + 0.02) / 0.006),
        sig((dz - 0.030) / 0.004) * sig((dy - 0.034) / 0.004),
        sig((dy - 0.068) / 0.005) * sig((dz + 0.072) / 0.006),
    ])
    hw[13380:] = 0
    hw *= np.isin(dom, ['head', 'neck_01'])
    ear = sig((dx - 0.058) / 0.006) * sig((dz + 0.062) / 0.005) * sig((0.034 - dz) / 0.005) * sig((dy - 0.0) / 0.006) * sig((0.092 - dy) / 0.006)
    hw *= (1 - ear)
    hair_rgb = np.array(c['hair']) * (1 - c['hair_gray']) + np.array([0.62, 0.62, 0.62]) * c['hair_gray']
    col = col * (1 - hw[:, None]) + hair_rgb * hw[:, None]

    # ---------------- Blender
    import bpy, bmesh
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.render.fps = 30

    def make_mat(name, rgb, rough=0.6, vcol=False, metal=0.0):
        m = bpy.data.materials.new(name)
        m.use_backface_culling = name not in ('Bob', 'Hair')
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = (*rgb, 1)
        bsdf.inputs['Roughness'].default_value = rough
        bsdf.inputs['Metallic'].default_value = metal
        if vcol:
            ca = nt.nodes.new('ShaderNodeVertexColor')
            ca.layer_name = 'Col'
            nt.links.new(ca.outputs['Color'], bsdf.inputs['Base Color'])
        return m

    def build_mesh(name, face_list, positions, mats, vcolors=None, keys=None, vweights_src=None):
        """face_list: [(vi, ti, matname)], positions: n×3 (Blender座標)。使う頂点だけ詰めて作る"""
        used = sorted({i for vi, _, _ in face_list for i in vi})
        remap = {o: k for k, o in enumerate(used)}
        me = bpy.data.meshes.new(name)
        verts = positions[used].tolist()
        polys = [[remap[i] for i in vi] for vi, _, _ in face_list]
        me.from_pydata(verts, [], polys)
        me.update()
        mnames = list(mats)
        for mn in mnames:
            me.materials.append(mats[mn])
        for p, (_, _, mn) in zip(me.polygons, face_list):
            p.material_index = mnames.index(mn)
            p.use_smooth = True
        # UV
        uvl = me.uv_layers.new(name='UVMap')
        li = 0
        for p, (vi, ti, _) in zip(me.polygons, face_list):
            for k in range(p.loop_total):
                t = ti[k]
                uvl.data[p.loop_start + k].uv = VT[t].tolist() if t >= 0 else (0, 0)
        if vcolors is not None:
            ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
            for k, o in enumerate(used):
                ca.data[k].color = (*vcolors[o], 1)
        ob = bpy.data.objects.new(name, me)
        scn.collection.objects.link(ob)
        if keys:
            ob.shape_key_add(name='Basis')
            for kn, delta in keys.items():
                sk = ob.shape_key_add(name=kn, from_mix=False)
                sk.value = 0.0
                d = obj2bl(delta)  # 差分も同じ変換(スケールのみ・平行移動なし)
                for k, o in enumerate(used):
                    sk.data[k].co = (positions[o] + d[o]).tolist()
        # 重み
        src = vweights_src if vweights_src is not None else {o: o for o in used}
        vg = {}
        for b, lst in W.items():
            for i, w in lst:
                vg.setdefault(i, []).append((b, w))
        groups_ = {}
        for k, o in enumerate(used):
            for b, w in vg.get(src[o], []):
                if b not in groups_:
                    groups_[b] = ob.vertex_groups.new(name=b)
                groups_[b].add([k], w, 'REPLACE')
        return ob

    M = dict(
        skin=make_mat('skin', (1, 1, 1), 0.55, vcol=True),
        eye=make_mat('eye', (1, 1, 1), 0.15, vcol=True),
        lash=make_mat('lash', (0.03, 0.03, 0.03), 0.8),
        teeth=make_mat('teeth', (0.92, 0.9, 0.84), 0.3),
        tongue=make_mat('tongue', (0.62, 0.28, 0.28), 0.5),
    )

    # ---------------- 服・髪の殻
    Nrm = vertex_normals(P, [vi for vi, _, _ in body_faces])
    def shell(name, face_list, push, rgb, rough=0.8, smooth=2, src_positions=None, taper=0, pmul=None, drape=False, hem=None, crotch=None):
        pos = (src_positions if src_positions is not None else P).copy()
        if drape:
            # 胸の一番前の点から下は、布がまっすぐ垂れる(谷間やアンダーバストに沿わない)。左右の端へは徐々に弱める
            used = sorted({i for vi, _, _ in face_list for i in vi})
            chest = [i for i in used if dom[i] == 'spine_03' and abs(pos[i, 0]) < 0.2]
            ap = min(chest, key=lambda i: pos[i, 1])
            az = pos[ap, 2]
            # 基準の面:胸まわりの中央値(いちばん前の点ではなく)。張り出しはここまで押し戻される
            band = [pos[i, 1] for i in chest if abs(pos[i, 0]) < 0.12 and az - 0.16 < pos[i, 2] < az + 0.05]
            ay = float(np.median(band)) if band else pos[ap, 1]
            for i in used:
                x, y, z = pos[i]
                if dom[i] not in ('spine_01', 'spine_02', 'spine_03', 'pelvis') or y >= 0:
                    continue
                wx = min(1.0, max(0.0, 1 - (abs(x) - (0.14 if drape is True else 0.20)) / 0.10))
                span = 0.21 if drape is True else 0.62
                wz = min(1.0, max(0.0, (z - (az - span)) / 0.07)) * min(1.0, max(0.0, (az + 0.10 - z) / 0.05))
                front = ay + max(0.0, az - z) * 0.10
                pos[i, 1] = y + (front - y) * wx * wz * 0.92
        if crotch:
            # 股まわりの膨らみを平らにする(正面側の頂点を、帯の中の背面寄りの値へ寄せる)
            z0_, z1_ = crotch
            usedc = sorted({i for vi, _, _ in face_list for i in vi})
            band_ = [i for i in usedc if abs(pos[i, 0]) < 0.075 and z0_ < pos[i, 2] < z1_ and pos[i, 1] < 0]
            if band_:
                ref = float(np.percentile([pos[i, 1] for i in band_], 80))
                for i in band_:
                    w = max(0.0, 1 - abs(pos[i, 0]) / 0.075) ** 0.5
                    if pos[i, 1] < ref:
                        pos[i, 1] += (ref - pos[i, 1]) * 0.95 * w
        Nl = vertex_normals(pos, [vi for vi, _, _ in face_list])
        pw = np.full(len(pos), 1.0)
        if taper:
            # 縁から taper リング分だけ厚みを 0 → 1 に
            nb0 = {}; ec0 = {}
            for vi, _, _ in face_list:
                for k in range(len(vi)):
                    a, b = vi[k], vi[(k + 1) % len(vi)]
                    nb0.setdefault(a, set()).add(b); nb0.setdefault(b, set()).add(a)
                    e = (min(a, b), max(a, b)); ec0[e] = ec0.get(e, 0) + 1
            ring = {i for e, k in ec0.items() if k == 1 for i in e}
            seen = set(ring)
            for r in range(taper + 1):
                for i in ring:
                    pw[i] = r / (taper + 1)
                ring = {j for i in ring for j in nb0[i]} - seen
                seen |= ring
        if pmul is not None:
            pw = pw * pmul
        newpos = pos + Nl * push * pw[:, None]
        # 布っぽく:細かい凹凸(指・乳首・あばら)をならす。境界の頂点は動かさない
        nb = {}
        edge_count = {}
        for vi, _, _ in face_list:
            for k in range(len(vi)):
                a, b = vi[k], vi[(k + 1) % len(vi)]
                nb.setdefault(a, set()).add(b); nb.setdefault(b, set()).add(a)
                e = (min(a, b), max(a, b)); edge_count[e] = edge_count.get(e, 0) + 1
        border = {i for e, k in edge_count.items() if k == 1 for i in e}
        idx = [i for i in nb if i not in border]
        # Taubin 平滑化(縮まずに細かい凹凸だけ消す)
        nbl = [list(nb[i]) for i in idx]
        for it in range(smooth * 2 if idx else 0):
            lam = 0.5 if it % 2 == 0 else -0.53
            avg = np.array([newpos[l].mean(0) for l in nbl])
            newpos[idx] = newpos[idx] + lam * (avg - newpos[idx])
        # 縁(襟・袖口・裾)のギザギザを、縁に沿ってならす
        bn = {i: [j for j in nb[i] if j in border and (min(i, j), max(i, j)) in edge_count and edge_count[(min(i, j), max(i, j))] == 1] for i in border}
        bl = [i for i in border if len(bn[i]) == 2]
        for _ in range(smooth if bl else 0):
            avg = np.array([newpos[bn[i]].mean(0) for i in bl])
            newpos[bl] = newpos[bl] * 0.5 + avg * 0.5
        if hem is not None:
            # 裾の縁をまっすぐに:縁の頂点のうち裾の高さ付近のものを、同じ高さにそろえる
            low = [i for i in border if newpos[i, 2] < hem + 0.07]
            if low:
                zz = float(np.mean([newpos[i, 2] for i in low]))
                for i in low:
                    newpos[i, 2] = zz
        return build_mesh(name, face_list, newpos, {name: make_mat(name, rgb, rough)})

    body_only = [(vi, ti) for vi, ti in groups['body']]
    def region(bset, need_all=True):
        out = []
        for vi, ti in body_only:
            ok = [dom[i] in bset for i in vi]
            if (all(ok) if need_all else any(ok)):
                out.append((vi, ti))
        return out

    upper = {'spine_01', 'spine_02', 'spine_03', 'clavicle_l', 'clavicle_r', 'upperarm_l', 'upperarm_r', 'lowerarm_l', 'lowerarm_r'}
    # 首の付け根:neck_01 のうち低い頂点
    neck_low = {i for i in range(13380) if dom[i] == 'neck_01' and P[i, 2] < P[gverts('joint-neck')].mean(0)[2] - 0.01} if 'joint-neck' in groups else set()
    pz = bones['pelvis']['head'][2]
    neck_cut = max(bones['clavicle_l']['head'][2], bones['clavicle_r']['head'][2]) + 0.035
    legs_hands_head = {'thigh_l', 'thigh_r', 'calf_l', 'calf_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r', 'head', 'hand_l', 'hand_r'}
    is_suit = c.get('outer_kind') == 'suit'
    shirt_hem = pz + (0.02 if is_suit else 0.075)       # シャツ・トップスの裾の高さ(まっすぐ)
    def top_ok(vi, hz=None):
        hz = shirt_hem if hz is None else hz
        cz = P[vi, 2].mean()
        doms = [dom[i] for i in vi]
        if any(d in legs_hands_head or d.startswith(('index', 'middle', 'ring', 'pinky', 'thumb')) for d in doms):
            return False
        if any(d == 'neck_01' for d in doms):
            return cz < neck_cut
        return P[vi, 2].min() > hz - 0.012
    top_faces = [(vi, ti) for vi, ti in body_only if top_ok(vi)]
    shell('Top', [(vi, ti, 'Top') for vi, ti in top_faces], 0.018, c['top'], 0.9, smooth=60, drape='full' if is_suit else True, hem=shirt_hem)
    # 羽織りもの:前開きの上着(open)/エプロン(apron)
    ok = c.get('outer_kind')
    if ok:
        def cen(vi):
            return P[vi].mean(0)
        if ok == 'suit':
            # 上着:腰より少し下まで。胸の前だけV字に開けて、シャツとネクタイを見せる
            hipset = {'pelvis', 'spine_01', 'thigh_l', 'thigh_r'}
            jhem = pz - 0.045
            def jacket_ok(vi):
                if top_ok(vi, jhem): return True
                return all(dom[i] in hipset for i in vi) and P[vi, 2].min() > jhem - 0.012
            v0 = pz + 0.16
            def in_v(vi):
                m = cen(vi)
                return m[1] < 0 and m[2] > v0 and abs(m[0]) < 0.008 + (m[2] - v0) * 0.30
            jk = [(vi, ti, 'Outer') for vi, ti in body_only if jacket_ok(vi) and not in_v(vi)]
            shell('Outer', jk, 0.036, c['outer'], 0.9, smooth=80, drape='full', hem=jhem)
            if c.get('tie'):
                # ネクタイ:V字の中、シャツの前に貼る細長い板(結び目+剣先)
                tie_mat = make_mat('Tie', c['tie'], 0.55); tie_mat.use_backface_culling = False
                z0, z1 = neck_cut - 0.015, pz + 0.10
                rows = 9; vs, fs = [], []
                def front_y(zz):
                    near = [i for i in range(13380) if abs(P[i, 0]) < 0.035 and abs(P[i, 2] - zz) < 0.012 and P[i, 1] < 0]
                    return (min(P[i, 1] for i in near) if near else -0.13) - 0.028
                for k in range(rows):
                    t = k / (rows - 1); zz = z0 + (z1 - z0) * t
                    w = 0.013 if t < 0.12 else (0.026 + 0.012 * t if t < 0.9 else 0.005)
                    yy = front_y(zz)
                    vs += [(-w, yy, zz), (w, yy, zz)]
                for k in range(rows - 1):
                    a_, b_ = 2 * k, 2 * k + 1
                    fs.append([a_, b_, b_ + 2, a_ + 2])
                me = bpy.data.meshes.new('Tie'); me.from_pydata(vs, [], fs); me.materials.append(tie_mat); me.update()
                for pg in me.polygons: pg.use_smooth = True
                ob = bpy.data.objects.new('Tie', me); scn.collection.objects.link(ob)
                g3 = ob.vertex_groups.new(name='spine_03'); g2 = ob.vertex_groups.new(name='spine_02')
                for k, v in enumerate(vs):
                    t = (v[2] - z1) / (z0 - z1)
                    g3.add([k], float(t), 'REPLACE'); g2.add([k], float(1 - t), 'REPLACE')
        elif ok == 'open':
            outer = [(vi, ti, 'Outer') for vi, ti in top_faces
                     if not (abs(cen(vi)[0]) < 0.05 and cen(vi)[1] < 0 and cen(vi)[2] < neck_cut - 0.02)]
            shell('Outer', outer, 0.032, c['outer'], 0.85, smooth=40, drape=True)
        else:
            apron = [(vi, ti, 'Outer') for vi, ti in body_only
                     if dom[vi[0]] in ('spine_01', 'spine_02', 'spine_03', 'pelvis', 'thigh_l', 'thigh_r')
                     and abs(cen(vi)[0]) < 0.14 and cen(vi)[1] < -0.02 and pz - 0.06 < cen(vi)[2] < neck_cut - 0.1]
            shell('Outer', apron, 0.045, c['outer'], 0.8, smooth=30, drape=True)
    # ズボン:タイツ補助メッシュのうち足首より上
    ank = min(bones['foot_l']['head'][2], bones['foot_r']['head'][2])
    waist = bones['pelvis']['head'][2] + 0.09
    legset = {'pelvis', 'thigh_l', 'thigh_r', 'calf_l', 'calf_r', 'spine_01'}
    pants = [(vi, ti) for vi, ti in body_only if all(dom[i] in legset for i in vi) and ank + 0.02 < P[vi, 2].mean() < ((pz - 0.045 + 0.025) if is_suit else (shirt_hem + 0.06))]
    suit = c.get('outer_kind') == 'suit'
    shell('Pants', [(vi, ti, 'Pants') for vi, ti in pants], 0.016 if suit else 0.012, c['pants'], 0.85, smooth=30 if suit else 8)

    # 服の下に隠れる体の面は消す(突き抜け防止)。開口部のまわり 2 リングは残す
    def interior(fl, rings=2):
        nb0 = {}; ec0 = {}
        for vi, _ in fl:
            for k in range(len(vi)):
                a, b = vi[k], vi[(k + 1) % len(vi)]
                nb0.setdefault(a, set()).add(b); nb0.setdefault(b, set()).add(a)
                e = (min(a, b), max(a, b)); ec0[e] = ec0.get(e, 0) + 1
        near = {i for e, k in ec0.items() if k == 1 for i in e}
        for _ in range(rings):
            near |= {j for i in near for j in nb0[i]}
        return {tuple(vi) for vi, _ in fl if not any(i in near for i in vi)}
    hidden = interior(top_faces) | interior(pants)
    hidden |= {tuple(vi) for vi, _ in body_only if all(dom[i] in ('foot_l', 'foot_r', 'ball_l', 'ball_r') for i in vi) and P[vi, 2].max() < ank + 0.015}
    visible_body = [(vi, ti, m) for vi, ti, m in body_faces if not (m == 'skin' and tuple(vi) in hidden)]
    print('hidden body faces', len(body_faces) - len(visible_body))
    body = build_mesh('Body', visible_body, P, M, vcolors=col, keys={'blink': blink, 'mouth': mouth})
    feet = region({'foot_l', 'foot_r', 'ball_l', 'ball_r'}, need_all=False)
    # 靴:足の範囲を包む角の丸い箱(スーパー楕円体)を足とつま先の骨に付ける
    shoe_mat = make_mat('Shoes', c['shoes'], 0.4)
    for side in ('l', 'r'):
        fv = [i for i in range(13380) if dom[i] in (f'foot_{side}', f'ball_{side}') and P[i, 2] < ank + 0.035]
        lo = P[fv].min(0) - 0.009; hi = P[fv].max(0) + 0.009
        lo[2] = max(lo[2], -0.004)
        hi[2] = ank + 0.03
        cen = (lo + hi) / 2; half = (hi - lo) / 2
        nu, nv = 28, 16
        vs, fs = [], []
        for j in range(nv + 1):
            ph = -math.pi / 2 + math.pi * j / nv
            for i in range(nu):
                th = 2 * math.pi * i / nu
                cx, sx, cp, sp = math.cos(th), math.sin(th), math.cos(ph), math.sin(ph)
                e = 0.45
                fx = np.sign(cp * cx) * abs(cp * cx) ** e
                fy = np.sign(cp * sx) * abs(cp * sx) ** e
                fz = np.sign(sp) * abs(sp) ** e
                pnt = cen + half * np.array([fx, fy, fz])
                # つま先側を少し低く、かかとを少し高く
                pnt[2] = min(pnt[2], cen[2] + half[2] * (0.35 if pnt[1] < cen[1] - half[1] * 0.3 else 1.0))
                vs.append(pnt)
        for j in range(nv):
            for i in range(nu):
                a = j * nu + i; b = j * nu + (i + 1) % nu
                fs.append([a, b, b + nu, a + nu])
        me = bpy.data.meshes.new(f'Shoe_{side}')
        me.from_pydata([v.tolist() for v in vs], [], fs)
        me.materials.append(shoe_mat)
        for pg in me.polygons:
            pg.use_smooth = True
        me.update()
        ob = bpy.data.objects.new(f'Shoe_{side}', me)
        scn.collection.objects.link(ob)
        gf = ob.vertex_groups.new(name=f'foot_{side}'); gb = ob.vertex_groups.new(name=f'ball_{side}')
        by = bones[f'ball_{side}']['head'][1]
        for k, v in enumerate(vs):
            t = np.clip((by - v[1]) / 0.03 + 0.5, 0, 1)  # つま先(-Y)ほど ball
            gb.add([k], float(t), 'REPLACE'); gf.add([k], float(1 - t), 'REPLACE')
    style = c.get('hair_style', 'short')
    if style != 'buzz':
        hair_faces = [(vi, ti, 'Hair') for vi, ti in body_only if all(hw[i] > 0.9 for i in vi)]
        crown = 1 + 1.2 * sig((dz - 0.08) / 0.015) + 0.5 * sig((dy - 0.06) / 0.015)
        shell('Hair', hair_faces, 0.0045, tuple(hair_rgb), 0.75, smooth=8, taper=5, pmul=crown)
    if style == 'bob':
        # 補助メッシュの長髪を肩の上で切り、顔の前にかからない部分だけ使う
        shoulder = max(bones['clavicle_l']['head'][2], bones['clavicle_r']['head'][2]) + 0.07
        bob = [(vi, ti, 'Bob') for vi, ti in groups['helper-hair'] if P[vi, 2].mean() > shoulder and P[vi, 1].mean() > eyeC[1] + 0.045 and abs(P[vi, 0].mean() - eyeC[0]) < 0.115]
        if bob:
            shell('Bob', bob, 0.012, tuple(hair_rgb), 0.75, smooth=6, taper=1)

    # ---------------- 骨
    arm = bpy.data.armatures.new('Rig')
    rigob = bpy.data.objects.new('Rig', arm)
    scn.collection.objects.link(rigob)
    bpy.context.view_layer.objects.active = rigob
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for b, d in bones.items():
        e = arm.edit_bones.new(b)
        e.head = d['head'].tolist(); e.tail = d['tail'].tolist(); e.roll = d['roll']
        eb[b] = e
    for b, d in bones.items():
        if d['parent']:
            eb[b].parent = eb[d['parent']]
    bpy.ops.object.mode_set(mode='OBJECT')
    for ob in [o for o in scn.objects if o.type == 'MESH']:
        ob.parent = rigob
        md = ob.modifiers.new('Armature', 'ARMATURE')
        md.object = rigob

    # ---------------- アニメーション
    import animations
    animations.add_all(rigob, body, bones)

    # ---------------- 書き出し
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=args.out, export_format='GLB', export_animations=True,
                              export_animation_mode='ACTIONS', export_morph=True, export_skins=True,
                              export_vertex_color='ACTIVE', export_all_vertex_colors=False,
                              export_yup=True, export_apply=False, export_force_sampling=True)
    print('wrote', args.out, os.path.getsize(args.out) // 1024, 'KB')

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
