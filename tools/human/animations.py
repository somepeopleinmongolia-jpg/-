"""
骨のアニメーションを手付けで作る。
回転は「アーマチュア空間(Z上、正面 -Y)」で指定し、各ボーンのローカル回転に変換して打つ。
  前屈 = +X 回転 / 左を向く = +Z 回転 / 体の左(+X)側の腕を下ろす = +Y 回転
"""
import math
import bpy
from mathutils import Quaternion, Vector, Matrix

FPS = 30

def q(axis, deg):
    return Quaternion(Vector(axis).normalized(), math.radians(deg))

def to_local(pb, qa):
    m = pb.bone.matrix_local.to_3x3()
    return (m.inverted() @ qa.to_matrix() @ m).to_quaternion()

class Pose:
    """
    base: ボーン -> 休止姿勢での「親に対する」回転(armature 軸)
    extra: そのフレームで足す「親に対する」回転(armature 軸)。親の動きには自動で追従する
    """
    def __init__(self, rig, base):
        self.rig = rig
        self.base = base

    def key(self, frame, extra):
        for pb in self.rig.pose.bones:
            pb.rotation_mode = 'QUATERNION'
            qa = extra.get(pb.name, Quaternion()) @ self.base.get(pb.name, Quaternion())
            pb.rotation_quaternion = to_local(pb, qa)
            pb.keyframe_insert('rotation_quaternion', frame=frame)
        loc = extra.get('_loc')
        root = self.rig.pose.bones['pelvis']
        root.location = loc if loc is not None else (0, 0, 0)
        root.keyframe_insert('location', frame=frame)

def rest_pose(rig, bones):
    """A ポーズの腕を体の横に下ろした姿勢(親に対する回転で返す)"""
    base = {}
    for side, s in (('l', 1), ('r', -1)):
        b = bones[f'upperarm_{side}']
        d = Vector((b['tail'] - b['head']).tolist()).normalized()
        want = Vector((s * 0.16, 0.04, -1)).normalized()
        A = d.rotation_difference(want)
        base[f'upperarm_{side}'] = A
        # 肘を少し前に曲げる(下ろした腕の向きで見て X 回転)
        base[f'lowerarm_{side}'] = A.inverted() @ q((1, 0, 0), 10) @ A
        # 指を軽く曲げる
        lo = q((1, 0, 0), 10) @ A
        for f in ('index', 'middle', 'ring', 'pinky'):
            base[f'{f}_01_{side}'] = lo.inverted() @ q((1, 0, 0), 12) @ lo
            for k in (2, 3):
                base[f'{f}_0{k}_{side}'] = lo.inverted() @ q((1, 0, 0), 14) @ lo
    return base

def new_action(rig, name):
    act = bpy.data.actions.new(name)
    rig.animation_data_create()
    rig.animation_data.action = act
    return act

def finish(rig, act, start, end):
    act.frame_range = (start, end)
    act.use_frame_range = True
    tr = rig.animation_data.nla_tracks.new()
    tr.name = act.name
    st = tr.strips.new(act.name, start, act)
    tr.mute = True
    rig.animation_data.action = None

def wave(t, period, a):
    return a * math.sin(2 * math.pi * t / period)

def add_all(rig, body, bones):
    bpy.context.view_layer.objects.active = rig
    base = rest_pose(rig, bones)
    P = Pose(rig, base)

    # idle:呼吸と重心のゆれ(4秒ループ)
    act = new_action(rig, 'idle')
    for f in range(0, 121, 5):
        t = f / FPS
        P.key(f, {
            'spine_02': q((1, 0, 0), wave(t, 4, 1.2)),
            'spine_03': q((1, 0, 0), wave(t, 4, 0.8)),
            'neck_01': q((0, 0, 1), wave(t, 4, 2.0)) @ q((1, 0, 0), 2),
            'head': q((0, 1, 0), wave(t + 1, 4, 1.5)),
            'pelvis': q((0, 1, 0), wave(t, 4, 1.0)),
            '_loc': (0, 0, 0),
        })
    finish(rig, act, 0, 120)

    # walk:その場歩き(1秒で2歩)。前進はゲーム側で動かす
    act = new_action(rig, 'walk')
    for f in range(0, 31, 2):
        t = f / FPS
        ph = 2 * math.pi * t / 1.0
        sw = math.sin(ph)
        P.key(f, {
            'thigh_l': q((1, 0, 0), -24 * sw),
            'thigh_r': q((1, 0, 0), 24 * sw),
            'calf_l': q((1, 0, 0), -max(0, 38 * math.sin(ph - 1.2))),
            'calf_r': q((1, 0, 0), -max(0, 38 * math.sin(ph + math.pi - 1.2))),
            'foot_l': q((1, 0, 0), 10 * math.sin(ph - 0.6)),
            'foot_r': q((1, 0, 0), 10 * math.sin(ph + math.pi - 0.6)),
            'upperarm_l': q((1, 0, 0), 16 * sw),
            'upperarm_r': q((1, 0, 0), -16 * sw),
            'pelvis': q((0, 0, 1), 4 * sw),
            'spine_03': q((0, 0, 1), -5 * sw) @ q((1, 0, 0), 3),
            '_loc': (0, 0, 0.012 * abs(math.cos(ph))),
        })
    finish(rig, act, 0, 30)

    # bow:会釈(2秒)
    act = new_action(rig, 'bow')
    for f in range(0, 61, 3):
        t = f / 60
        k = math.sin(math.pi * min(1, t / 0.75)) if t < 0.75 else 0
        k = (1 - math.cos(math.pi * min(t / 0.35, 1))) / 2 if t < 0.35 else (1 if t < 0.55 else (1 + math.cos(math.pi * (t - 0.55) / 0.45)) / 2)
        P.key(f, {
            'spine_01': q((1, 0, 0), 10 * k), 'spine_02': q((1, 0, 0), 10 * k),
            'spine_03': q((1, 0, 0), 8 * k), 'neck_01': q((1, 0, 0), 8 * k), 'head': q((1, 0, 0), 6 * k),
        })
    finish(rig, act, 0, 60)

    # nod:うなずき(1.2秒)
    act = new_action(rig, 'nod')
    for f in range(0, 37, 2):
        t = f / 36
        k = math.sin(math.pi * 2 * t) * (1 - t)
        P.key(f, {'neck_01': q((1, 0, 0), 9 * max(0, k)), 'head': q((1, 0, 0), 7 * max(0, k))})
    finish(rig, act, 0, 36)

    # armsfold:腕組み(保持)
    act = new_action(rig, 'armsfold')
    fold = {}
    for side, s in (('l', 1), ('r', -1)):
        fold[f'upperarm_{side}'] = q((1, 0, 0), 40) @ q((0, 0, 1), -s * 25)
        fold[f'lowerarm_{side}'] = q((0, 0, 1), -s * 95)
    for f in (0, 60):
        x = dict(fold); x['neck_01'] = q((1, 0, 0), -3)
        P.key(f, x)
    finish(rig, act, 0, 60)

    # handover:両手で差し出す(2秒、最後は差し出したまま)
    act = new_action(rig, 'handover')
    for f in range(0, 61, 3):
        t = min(1, f / 40)
        k = (1 - math.cos(math.pi * t)) / 2
        x = {}
        for side, s in (('l', 1), ('r', -1)):
            x[f'upperarm_{side}'] = q((1, 0, 0), 55 * k) @ q((0, 0, 1), -s * 8 * k)
            x[f'lowerarm_{side}'] = q((1, 0, 0), 35 * k)
        x['spine_03'] = q((1, 0, 0), 6 * k)
        P.key(f, x)
    finish(rig, act, 0, 60)
