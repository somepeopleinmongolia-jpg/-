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
        # 素体は肘が前に約45度曲がっているので、上腕の延長にそろえてから 10 度だけ前に曲げる
        lb = bones[f'lowerarm_{side}']
        dlo = Vector((lb['tail'] - lb['head']).tolist()).normalized()
        R = (A @ dlo).rotation_difference(q((1, 0, 0), -10) @ want)
        base[f'lowerarm_{side}'] = A.inverted() @ R @ A
        # 指を軽く曲げる
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

    def gait(name, period, frames, thigh, calf, arm, lean, bob, elbow=0):
        act = new_action(rig, name)
        for f in range(0, frames + 1, 2):
            t = f / FPS
            ph = 2 * math.pi * t / period
            sw = math.sin(ph)
            x = {
                'thigh_l': q((1, 0, 0), -thigh * sw),
                'thigh_r': q((1, 0, 0), thigh * sw),
                'calf_l': q((1, 0, 0), max(0, calf * math.sin(ph - 1.3))),
                'calf_r': q((1, 0, 0), max(0, calf * math.sin(ph + math.pi - 1.3))),
                'foot_l': q((1, 0, 0), -8 * math.sin(ph - 0.6)),
                'foot_r': q((1, 0, 0), -8 * math.sin(ph + math.pi - 0.6)),
                'upperarm_l': q((1, 0, 0), arm * sw),
                'upperarm_r': q((1, 0, 0), -arm * sw),
                'pelvis': q((0, 0, 1), 4 * sw),
                'spine_01': q((1, 0, 0), lean),
                'spine_03': q((0, 0, 1), -5 * sw),
                '_loc': (0, 0, bob * abs(math.cos(ph))),
            }
            if elbow:
                x['lowerarm_l'] = q((1, 0, 0), -elbow); x['lowerarm_r'] = q((1, 0, 0), -elbow)
            P.key(f, x)
        finish(rig, act, 0, frames)

    # walk:その場歩き(1秒で2歩)/ run:小走り。前進はゲーム側で動かす
    gait('walk', 1.0, 30, 24, 40, 16, 2, 0.012)
    gait('run', 0.6, 18, 38, 80, 40, 10, 0.03, elbow=70)

    def ease(t):
        t = max(0.0, min(1.0, t))
        return (1 - math.cos(math.pi * t)) / 2

    def hold(t, a, b, c):
        """0→1(a秒まで)→保持(bまで)→0(cまで)"""
        if t < a: return ease(t / a)
        if t < b: return 1.0
        return 1 - ease((t - b) / (c - b))

    # bow:会釈(2秒)
    act = new_action(rig, 'bow')
    for f in range(0, 61, 3):
        k = hold(f / FPS, 0.7, 1.1, 2.0)
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

    # tilt:首をかしげる(2秒、保持して戻る)
    act = new_action(rig, 'tilt')
    for f in range(0, 61, 3):
        k = hold(f / FPS, 0.5, 1.5, 2.0)
        P.key(f, {'neck_01': q((0, 1, 0), -9 * k), 'head': q((0, 1, 0), -10 * k) @ q((0, 0, 1), 6 * k)})
    finish(rig, act, 0, 60)

    # shake:首を横に振る(1.4秒)
    act = new_action(rig, 'shake')
    for f in range(0, 43, 2):
        t = f / 42
        a = 22 * math.sin(2 * math.pi * 2 * t) * math.sin(math.pi * t)
        P.key(f, {'neck_01': q((0, 0, 1), a * 0.45), 'head': q((0, 0, 1), a * 0.55)})
    finish(rig, act, 0, 42)

    # armsfold:腕組み(保持)
    act = new_action(rig, 'armsfold')
    for f in (0, 30, 60):
        x = {'neck_01': q((1, 0, 0), -3)}
        for side, s in (('l', 1), ('r', -1)):
            x[f'upperarm_{side}'] = q((1, 0, 0), -38) @ q((0, 1, 0), -s * 6)
            x[f'lowerarm_{side}'] = q((0, 0, 1), -s * 100) @ q((1, 0, 0), -55)
        P.key(f, x)
    finish(rig, act, 0, 60)

    # handover:両手で差し出す/受け取る(2秒、最後は差し出したまま)
    act = new_action(rig, 'handover')
    for f in range(0, 61, 3):
        k = ease(f / 40)
        x = {'spine_03': q((1, 0, 0), 6 * k)}
        for side, s in (('l', 1), ('r', -1)):
            x[f'upperarm_{side}'] = q((1, 0, 0), -45 * k) @ q((0, 1, 0), s * 6 * k)
            x[f'lowerarm_{side}'] = q((1, 0, 0), -40 * k)
        P.key(f, x)
    finish(rig, act, 0, 60)

    # wave:右手を挙げて振る(2.4秒)
    act = new_action(rig, 'wave')
    for f in range(0, 73, 2):
        t = f / FPS
        k = hold(t, 0.4, 2.0, 2.4)
        w = math.sin(2 * math.pi * 2.2 * t) * k
        P.key(f, {
            'upperarm_r': q((0, 1, 0), 75 * k) @ q((1, 0, 0), -15 * k),
            'lowerarm_r': q((0, 1, 0), 75 * k + 18 * w),
            'head': q((0, 1, 0), -4 * k),
        })
    finish(rig, act, 0, 72)

    # beckon:「ちょっと来て」の手招き(2.4秒)
    act = new_action(rig, 'beckon')
    for f in range(0, 73, 2):
        t = f / FPS
        k = hold(t, 0.4, 2.0, 2.4)
        w = (math.sin(2 * math.pi * 1.6 * t) * 0.5 + 0.5) * k
        P.key(f, {
            'upperarm_r': q((1, 0, 0), -50 * k) @ q((0, 1, 0), 10 * k),
            'lowerarm_r': q((1, 0, 0), -(40 + 40 * w)),
            'hand_r': q((1, 0, 0), -30 * w),
            'neck_01': q((1, 0, 0), 4 * k),
        })
    finish(rig, act, 0, 72)

    # cheer:両手を挙げる(2秒、保持)
    act = new_action(rig, 'cheer')
    for f in range(0, 61, 3):
        k = ease(f / 15)
        b = 0.02 * abs(math.sin(2 * math.pi * 1.5 * f / FPS)) * k
        P.key(f, {
            'upperarm_l': q((0, 1, 0), -150 * k), 'upperarm_r': q((0, 1, 0), 150 * k),
            'lowerarm_l': q((0, 1, 0), -15 * k), 'lowerarm_r': q((0, 1, 0), 15 * k),
            'neck_01': q((1, 0, 0), -8 * k), '_loc': (0, 0, b),
        })
    finish(rig, act, 0, 60)
