"""
NURMADOG — процедурная 3D-модель бойца (бойцовый пёс) в формате GLB (glTF 2.0).

Содержит:
  * одну сетку (~1.5 тыс. вершин, 2 материала: тело и экипировка),
  * скелет из 17 костей (armature) с иерархией,
  * skinning-веса JOINTS_0 / WEIGHTS_0 с плавными переходами в суставах,
  * inverseBindMatrices,
  * Idle-анимацию (подскоки, работа рук / ног / головой).

Готовая модель на GitHub не найдена, поэтому построена процедурно в коде.
Запуск: python3 build_nurmadog.py  ->  nurmadog.glb
"""
import math

import numpy as np
import pygltflib
from pygltflib import (
    GLTF2, Accessor, Animation, AnimationChannel, AnimationChannelTarget,
    AnimationSampler, Asset, Buffer, BufferView, Material, Mesh, Node,
    PbrMetallicRoughness, Primitive, Scene, Skin,
)

ACC_FLOAT = 5126
ACC_USHORT = 5123
ACC_UINT = 5125
ARRAY_BUFFER = 34962
ELEMENT_ARRAY_BUFFER = 34963

# -----------------------------------------------------------------------------
# Скелет: имя, индекс родителя, локальный перевод (м) в bind-позе.
# Стопы на y = 0, таз (Root) на y = 0.92.
# -----------------------------------------------------------------------------
BONES = [
    ("Root",               -1, (0.000, 0.920, 0.000)),
    ("Spine",               0, (0.000, 0.400, 0.000)),
    ("Head",                1, (0.000, 0.460, 0.000)),
    ("L_Ear",               2, (-0.085, 0.080, 0.035)),
    ("R_Ear",               2, (0.085,  0.080, 0.035)),
    ("L_UpperArm",          1, (-0.300, 0.155, 0.000)),
    ("L_LowerArm",          5, (-0.300, -0.155, 0.000)),
    ("L_Glove",             6, (-0.190, -0.055, 0.000)),
    ("R_UpperArm",          1, (0.300,  0.155, 0.000)),
    ("R_LowerArm",          8, (0.300,  -0.155, 0.000)),
    ("R_Glove",             9, (0.190, -0.055, 0.000)),
    ("L_UpperLeg",          0, (-0.115, -0.120, 0.000)),
    ("L_LowerLeg",          11, (0.000, -0.470, 0.000)),
    ("L_Foot",              12, (0.000, -0.280, 0.065)),
    ("R_UpperLeg",          0, (0.115,  -0.120, 0.000)),
    ("R_LowerLeg",          14, (0.000,  -0.470, 0.000)),
    ("R_Foot",              15, (0.000,  -0.280, 0.065)),
]
BONE_NAMES = [b[0] for b in BONES]
N_BONES = len(BONES)
BONE_INDEX = {name: i for i, name in enumerate(BONE_NAMES)}
PARENTS = [b[1] for b in BONES]
MESH_NODE = N_BONES  # узел сетки (ребёнок Root)
N_NODES = N_BONES + 1

BODY, GEAR = 0, 1


def T(x, y, z):
    M = np.eye(4)
    M[0:3, 3] = (x, y, z)
    return M


def Rx(a):
    c, s = math.cos(a), math.sin(a)
    M = np.eye(4)
    M[1, 1] = c; M[1, 2] = -s
    M[2, 1] = s; M[2, 2] = c
    return M


def align_y_to(direction):
    """Поворот, накладывающий локальную ось Y на заданный вектор."""
    a = np.array([0.0, 1.0, 0.0])
    b = np.array(direction, dtype=float)
    b = b / np.linalg.norm(b)
    c = float(np.dot(a, b))
    if c > 0.99999:
        return np.eye(4)
    if c < -0.99999:
        M = np.eye(4)
        M[0, 0] = -1.0
        M[2, 2] = -1.0
        return M
    v = np.cross(a, b)
    kmat = np.array([
        [0.0, -v[2], v[1]],
        [v[2], 0.0, -v[0]],
        [-v[1], v[0], 0.0],
    ])
    R = np.eye(4)
    R[0:3, 0:3] = np.eye(3) + kmat + kmat @ kmat * ((1.0 - c) / float(np.linalg.norm(v) ** 2))
    return R


def quat_from_axis_angle(axis, angle):
    axis = np.array(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    h = angle / 2.0
    s = math.sin(h)
    return (float(axis[0] * s), float(axis[1] * s), float(axis[2] * s), float(math.cos(h)))


# world-матрицы суставов в bind-позе
LOCALS_REST = [T(*b[2]) for b in BONES]
WORLD_REST = [None] * N_BONES


def solve_world(i):
    if WORLD_REST[i] is not None:
        return WORLD_REST[i]
    p = PARENTS[i]
    WORLD_REST[i] = LOCALS_REST[i] if p < 0 else np.dot(solve_world(p), LOCALS_REST[i])
    return WORLD_REST[i]


for i in range(N_BONES):
    solve_world(i)

JOINT_POS = [tuple(WORLD_REST[i][0:3, 3]) for i in range(N_BONES)]

# -----------------------------------------------------------------------------
# Геометрия примитивов
# -----------------------------------------------------------------------------
def box(sx, sy, sz):
    hs = (sx / 2, sy / 2, sz / 2)
    intended = [(0, 0, -1), (0, 0, 1), (0, -1, 0), (0, 1, 0), (-1, 0, 0), (1, 0, 0)]
    quads = [
        # back, (0,0,-1)
        [(-hs[0], -hs[1], -hs[2]), (-hs[0], hs[1], -hs[2]),
         (hs[0], hs[1], -hs[2]), (hs[0], -hs[1], -hs[2])],
        # front, (0,0,1)
        [(hs[0], -hs[1], hs[2]), (hs[0], hs[1], hs[2]),
         (-hs[0], hs[1], hs[2]), (-hs[0], -hs[1], hs[2])],
        # bottom, (0,-1,0)
        [(-hs[0], -hs[1], -hs[2]), (hs[0], -hs[1], -hs[2]),
         (hs[0], -hs[1], hs[2]), (-hs[0], -hs[1], hs[2])],
        # top, (0,1,0)
        [(-hs[0], hs[1], hs[2]), (-hs[0], hs[1], -hs[2]),
         (hs[0], hs[1], -hs[2]), (hs[0], hs[1], hs[2])],
        # left, (-1,0,0)
        [(-hs[0], -hs[1], hs[2]), (-hs[0], hs[1], hs[2]),
         (-hs[0], hs[1], -hs[2]), (-hs[0], -hs[1], -hs[2])],
        # right, (1,0,0)
        [(hs[0], -hs[1], -hs[2]), (hs[0], hs[1], -hs[2]),
         (hs[0], hs[1], hs[2]), (hs[0], -hs[1], hs[2])],
    ]
    verts, norms, faces = [], [], []
    for fi, quad in enumerate(quads):
        n = np.array(intended[fi], float)
        v0, v1, v2 = quad[0], quad[1], quad[2]
        c = np.cross(np.array(v1) - np.array(v0), np.array(v2) - np.array(v0))
        if np.dot(c, n) < 0:
            quad[1], quad[3] = quad[3], quad[1]  # развернуть обход
        base = len(verts)
        verts.extend(quad)
        norms.extend([tuple(n)] * 4)
        faces += [base, base + 1, base + 2, base, base + 2, base + 3]
    return (np.array(verts, float), np.array(norms, float),
            np.array(faces, np.uint32).reshape(-1))


def uv_sphere(radius, lat=10, lon=14):
    verts, norms = [], []
    for i in range(lat + 1):
        la = math.pi * i / lat - math.pi / 2
        y = math.sin(la)
        r = math.cos(la)
        for j in range(lon + 1):
            a = 2 * math.pi * j / lon
            x = math.cos(a)
            z = math.sin(a)
            verts.append((radius * x, radius * y, radius * z))
            norms.append((x, y, z))
    faces = []
    for i in range(lat):
        for j in range(lon):
            v1 = i * (lon + 1) + j
            v2 = v1 + 1
            v3 = (i + 1) * (lon + 1) + j
            v4 = v3 + 1
            faces.append((v1, v3, v2))
            faces.append((v2, v3, v4))
    return (np.array(verts, float), np.array(norms, float),
            np.array(faces, np.uint32).reshape(-1))


def cylinder(radius_top, radius_bottom, height, segs=10):
    n_side = segs + 1
    verts, norms = [], []
    for side in (0, 1):
        r = radius_top if side == 0 else radius_bottom
        y = height / 2 if side == 0 else -height / 2
        for j in range(segs + 1):
            a = 2 * math.pi * j / segs
            x = math.cos(a)
            z = math.sin(a)
            verts.append((r * x, y, r * z))
            norms.append((x, 0.0, z))
    faces = []
    for j in range(segs):
        a0, a1 = j, j + 1
        b0, b1 = n_side + j, n_side + j + 1
        faces.append((a0, b0, b1))
        faces.append((a0, b1, a1))
    for side in (0, 1):
        r = radius_top if side == 0 else radius_bottom
        y = height / 2 if side == 0 else -height / 2
        base = len(verts)
        verts.append((0.0, y, 0.0))
        norms.append((0.0, 1.0 if side == 0 else -1.0, 0.0))
        for j in range(segs + 1):
            a = 2 * math.pi * j / segs
            verts.append((r * math.cos(a), y, r * math.sin(a)))
            norms.append((0.0, 1.0 if side == 0 else -1.0, 0.0))
        for j in range(segs):
            if side == 0:
                faces.append((base, base + j + 1, base + j + 2))
            else:
                faces.append((base, base + j + 2, base + j + 1))
    return (np.array(verts, float), np.array(norms, float),
            np.array(faces, np.uint32).reshape(-1))


def apply_M(verts, norms, M):
    R = M[0:3, 0:3]
    t = M[0:3, 3]
    new_verts = (verts @ R.T) + t
    new_norms = norms @ R.T
    nrm = np.linalg.norm(new_norms, axis=1, keepdims=True)
    new_norms = new_norms / np.where(nrm > 0, nrm, 1.0)
    return new_verts, new_norms


# -----------------------------------------------------------------------------
# Части тела: (геометрия, параметры, мировая матрица, {кость: базовый вес}, материал)
# -----------------------------------------------------------------------------
PARTS = [
    # шорты / таз
    (box, dict(sx=0.44, sy=0.32, sz=0.24), T(0, 0.87, 0), {"Root": 1.0}, BODY),
    # торс
    (box, dict(sx=0.36, sy=0.52, sz=0.22), T(0, 1.28, 0), {"Spine": 1.0}, BODY),
    # шея
    (cylinder, dict(radius_top=0.05, radius_bottom=0.05, height=0.16, segs=10),
     T(0, 1.615, 0), {"Spine": 0.5, "Head": 0.5}, BODY),
    # голова
    (uv_sphere, dict(radius=0.13, lat=10, lon=14), T(0, 1.81, 0), {"Head": 1.0}, BODY),
    # уши
    (uv_sphere, dict(radius=0.042, lat=8, lon=10),
     T(-0.078, 1.895, 0.032), {"Head": 1.0}, BODY),
    (uv_sphere, dict(radius=0.042, lat=8, lon=10),
     T(0.078, 1.895, 0.032), {"Head": 1.0}, BODY),
    # конечности — матрицы заполняются ниже (цилиндр по направлению кости)
    (cylinder, dict(radius_top=0.055, radius_bottom=0.048, height=1.0, segs=8),
     None, {"L_UpperArm": 1.0}, BODY),
    (cylinder, dict(radius_top=0.048, radius_bottom=0.042, height=1.0, segs=8),
     None, {"L_LowerArm": 1.0}, BODY),
    (box, dict(sx=0.15, sy=0.10, sz=0.17), T(-0.885, 1.25, 0.0), {"L_Glove": 1.0}, GEAR),
    (cylinder, dict(radius_top=0.055, radius_bottom=0.048, height=1.0, segs=8),
     None, {"R_UpperArm": 1.0}, BODY),
    (cylinder, dict(radius_top=0.048, radius_bottom=0.042, height=1.0, segs=8),
     None, {"R_LowerArm": 1.0}, BODY),
    (box, dict(sx=0.15, sy=0.10, sz=0.17), T(0.885, 1.25, 0.0), {"R_Glove": 1.0}, GEAR),
    (cylinder, dict(radius_top=0.075, radius_bottom=0.066, height=1.0, segs=8),
     None, {"L_UpperLeg": 1.0}, BODY),
    (cylinder, dict(radius_top=0.066, radius_bottom=0.056, height=1.0, segs=8),
     None, {"L_LowerLeg": 1.0}, BODY),
    (box, dict(sx=0.21, sy=0.05, sz=0.16), T(-0.115, 0.02, 0.05), {"L_Foot": 1.0}, BODY),
    (cylinder, dict(radius_top=0.075, radius_bottom=0.066, height=1.0, segs=8),
     None, {"R_UpperLeg": 1.0}, BODY),
    (cylinder, dict(radius_top=0.066, radius_bottom=0.056, height=1.0, segs=8),
     None, {"R_LowerLeg": 1.0}, BODY),
    (box, dict(sx=0.21, sy=0.05, sz=0.16), T(0.115, 0.02, 0.05), {"R_Foot": 1.0}, BODY),
]

# индексы частей -> (начальная кость, конечная кость) для выравнивания цилиндра
LIMB_MAP = {
    6: ("L_UpperArm", "L_LowerArm"),
    7: ("L_LowerArm", None),
    9: ("R_UpperArm", "R_LowerArm"),
    10: ("R_LowerArm", None),
    12: ("L_UpperLeg", "L_LowerLeg"),
    13: ("L_LowerLeg", None),
    15: ("R_UpperLeg", "R_LowerLeg"),
    16: ("R_LowerLeg", None),
}
for idx, (bone, child) in LIMB_MAP.items():
    p0 = np.array(JOINT_POS[BONE_INDEX[bone]])
    p1 = np.array(JOINT_POS[BONE_INDEX[child]]) if child else p0 + np.array([0.0, 0.1, 0.0])
    mid = (p0 + p1) / 2.0
    height = max(float(np.linalg.norm(p1 - p0)), 0.25)
    M = T(*mid) @ align_y_to(p1 - p0)
    kw = dict(PARTS[idx][1], height=height, segs=8)
    PARTS[idx] = (PARTS[idx][0], kw, M, PARTS[idx][3], PARTS[idx][4])

# зоны плавного перехода весов у суставов: (центр, радиус, {кость: вес})
BLEND_ZONES = [
    ((-0.305, 1.455, 0.0), 0.105, {"Spine": 0.5, "L_UpperArm": 0.5}),
    ((0.305, 1.455, 0.0), 0.105, {"Spine": 0.5, "R_UpperArm": 0.5}),
    ((-0.595, 1.315, 0.0), 0.090, {"L_UpperArm": 0.5, "L_LowerArm": 0.5}),
    ((0.595, 1.315, 0.0), 0.090, {"R_UpperArm": 0.5, "R_LowerArm": 0.5}),
    ((-0.815, 1.265, 0.0), 0.070, {"L_LowerArm": 0.5, "L_Glove": 0.5}),
    ((0.815, 1.265, 0.0), 0.070, {"R_LowerArm": 0.5, "R_Glove": 0.5}),
    ((-0.115, 0.805, 0.0), 0.095, {"Root": 0.5, "L_UpperLeg": 0.5}),
    ((0.115, 0.805, 0.0), 0.095, {"Root": 0.5, "R_UpperLeg": 0.5}),
    ((-0.115, 0.335, 0.0), 0.080, {"L_UpperLeg": 0.5, "L_LowerLeg": 0.5}),
    ((0.115, 0.335, 0.0), 0.080, {"R_UpperLeg": 0.5, "R_LowerLeg": 0.5}),
    ((-0.115, 0.060, 0.0), 0.070, {"L_LowerLeg": 0.5, "L_Foot": 0.5}),
    ((0.115, 0.060, 0.0), 0.070, {"R_LowerLeg": 0.5, "R_Foot": 0.5}),
    ((0.0, 1.620, 0.0), 0.075, {"Spine": 0.5, "Head": 0.5}),
]


def build_mesh():
    all_pos, all_nrm, all_w, all_mat = [], [], [], []
    faces_by_mat = {BODY: [], GEAR: []}
    voff = 0

    for geom, kw, M, weights, mat_idx in PARTS:
        verts, norms, faces = geom(**kw)
        verts, norms = apply_M(verts, norms, M)
        base = [(BONE_INDEX[b], w) for b, w in weights.items()]
        all_pos.append(verts)
        all_nrm.append(norms)
        all_w.extend([list(base) for _ in range(len(verts))])
        all_mat.extend([mat_idx] * len(verts))
        for tri in faces.reshape(-1, 3):
            faces_by_mat[mat_idx].append(tuple(int(v) + voff for v in tri))
        voff += len(verts)

    positions = np.concatenate(all_pos, axis=0).astype(np.float32)
    normals = np.concatenate(all_nrm, axis=0).astype(np.float32)
    n_vert = positions.shape[0]

    for vi in range(n_vert):
        p = positions[vi]
        wdict = dict(all_w[vi])
        for center, radius, zweights in BLEND_ZONES:
            d = float(np.linalg.norm(p - np.array(center)))
            if d < radius:
                f = 1.0 - d / radius
                for b, w in zweights.items():
                    bi = BONE_INDEX[b]
                    wdict[bi] = wdict.get(bi, 0.0) * (1.0 - f) + w * f
        all_w[vi] = sorted(wdict.items())

    joints = np.zeros((n_vert, 4), dtype=np.uint16)
    weights = np.zeros((n_vert, 4), dtype=np.float32)
    for vi, wlist in enumerate(all_w):
        wlist = sorted(wlist, key=lambda x: -x[1])[:4]
        total = sum(w for _, w in wlist) or 1.0
        for k, (bi, w) in enumerate(wlist):
            joints[vi, k] = bi
            weights[vi, k] = np.float32(w / total)

    index_sets = {}
    for mat_idx, flist in faces_by_mat.items():
        index_sets[mat_idx] = np.array(flist, dtype=np.uint32).reshape(-1)

    return positions, normals, joints, weights, index_sets


# -----------------------------------------------------------------------------
# Сборка glTF -> GLB
# -----------------------------------------------------------------------------
def build_gltf(positions, normals, joints, weights, index_sets):
    n_vert = positions.shape[0]
    gltf = GLTF2()
    gltf.asset = Asset(version="2.0", generator="NURMADOG procedural builder")
    gltf.scene = 0

    # материалы
    gltf.materials = [
        Material(name="body",
                 pbrMetallicRoughness=PbrMetallicRoughness(
                     baseColorFactor=[0.84, 0.60, 0.46, 1.0],
                     metallicFactor=0.0, roughnessFactor=0.90)),
        Material(name="gear",
                 pbrMetallicRoughness=PbrMetallicRoughness(
                     baseColorFactor=[0.15, 0.17, 0.21, 1.0],
                     metallicFactor=0.10, roughnessFactor=0.55)),
    ]

    # ----- анимация (Idle, 3 секунды, 30 fps) -----
    fps = 30.0
    duration = 3.0
    n_frames = int(duration * fps) + 1
    times = np.linspace(0.0, duration, n_frames, dtype=np.float32)

    def sinv(freq=1.0):
        return np.sin(2.0 * math.pi * freq * times / duration)

    root_tr = np.stack([
        np.zeros(n_frames, np.float32),
        (0.92 + 0.018 * sinv()).astype(np.float32),
        np.zeros(n_frames, np.float32),
    ], axis=1)

    def quat_tracks(axis, angles):
        axis = np.array(axis, dtype=float)
        axis = axis / np.linalg.norm(axis)
        h = np.asarray(angles, dtype=float) / 2.0
        s = np.sin(h)[:, None]
        c = np.cos(h)[:, None]
        return np.concatenate([axis[None, :] * s, c], axis=1).astype(np.float32)

    def quat_track(axis, angles):
        return quat_tracks(axis, angles).tobytes()

    # (узел, путь, байты данных, тип аксессора)
    anim_specs = [
        (0, "translation", root_tr.tobytes(), "VEC3"),
        (2, "rotation", quat_track((0, 0, 1), 0.05 * sinv()), "VEC4"),
        (5, "rotation", quat_track((0, 0, 1), 0.30 * sinv()), "VEC4"),
        (6, "rotation", quat_track((1, 0, 0), -0.35 + 0.12 * sinv(0.5)), "VEC4"),
        (8, "rotation", quat_track((0, 0, 1), -0.30 * sinv()), "VEC4"),
        (9, "rotation", quat_track((1, 0, 0), -0.35 + 0.12 * sinv(0.5)), "VEC4"),
        (11, "rotation", quat_track((0, 0, 1), -0.25 * sinv()), "VEC4"),
        (12, "rotation", quat_track((1, 0, 0), 0.10 * sinv(0.5)), "VEC4"),
        (14, "rotation", quat_track((0, 0, 1), 0.25 * sinv()), "VEC4"),
        (15, "rotation", quat_track((1, 0, 0), 0.10 * sinv(0.5)), "VEC4"),
        (13, "rotation", quat_track((0, 0, 1), 0.225 * sinv()), "VEC4"),
        (16, "rotation", quat_track((0, 0, 1), -0.225 * sinv()), "VEC4"),
    ]

    # ----- один общий бинарный буфер -----
    pos_bytes = positions.tobytes()
    nrm_bytes = normals.tobytes()
    jnt_bytes = joints.tobytes()
    wgt_bytes = weights.tobytes()

    ibm_bytes = b"".join(
        np.linalg.inv(WORLD_REST[i]).astype(np.float32).T.tobytes()
        for i in range(N_BONES)
    )

    time_bytes = times.tobytes()
    anim_out_bytes = [s[2] for s in anim_specs]

    all_chunks = [(time_bytes, None),
                  (pos_bytes, ARRAY_BUFFER), (nrm_bytes, ARRAY_BUFFER),
                  (jnt_bytes, ARRAY_BUFFER), (wgt_bytes, ARRAY_BUFFER),
                  (ibm_bytes, None)]
    all_chunks += [(index_sets[BODY].tobytes(), ELEMENT_ARRAY_BUFFER),
                   (index_sets[GEAR].tobytes(), ELEMENT_ARRAY_BUFFER)]
    all_chunks += [(b, None) for b in anim_out_bytes]

    gltf.buffers = [Buffer(byteLength=0)]
    buf = bytearray()
    buffer_views = []

    def emit(data, target):
        pad = (-len(buf)) % 4
        if pad:
            buf.extend(b"\x00" * pad)
        off = len(buf)
        buf.extend(data)
        bv = BufferView(buffer=0, byteOffset=off, byteLength=len(data), target=target)
        gltf.bufferViews.append(bv)
        return len(gltf.bufferViews) - 1

    bv_time = emit(time_bytes, None)
    bv_pos = emit(pos_bytes, ARRAY_BUFFER)
    bv_nrm = emit(nrm_bytes, ARRAY_BUFFER)
    bv_jnt = emit(jnt_bytes, ARRAY_BUFFER)
    bv_wgt = emit(wgt_bytes, ARRAY_BUFFER)
    bv_ibm = emit(ibm_bytes, None)
    bv_idx_body = emit(index_sets[BODY].tobytes(), ELEMENT_ARRAY_BUFFER)
    bv_idx_gear = emit(index_sets[GEAR].tobytes(), ELEMENT_ARRAY_BUFFER)
    bv_anims = [emit(b, None) for b in anim_out_bytes]

    def add_accessor(buffer_view, component_type, count, atype, minv=None, maxv=None):
        a = Accessor(bufferView=buffer_view, componentType=component_type,
                     count=count, type=atype)
        if minv is not None:
            a.min = list(minv)
            a.max = list(maxv)
        gltf.accessors.append(a)
        return len(gltf.accessors) - 1

    acc_time = add_accessor(bv_time, ACC_FLOAT, n_frames, "SCALAR", [0.0], [duration])
    acc_pos = add_accessor(bv_pos, ACC_FLOAT, n_vert, "VEC3",
                           positions.min(axis=0).tolist(), positions.max(axis=0).tolist())
    acc_nrm = add_accessor(bv_nrm, ACC_FLOAT, n_vert, "VEC3")
    acc_jnt = add_accessor(bv_jnt, ACC_USHORT, n_vert, "VEC4")
    acc_wgt = add_accessor(bv_wgt, ACC_FLOAT, n_vert, "VEC4")
    acc_idx_body = add_accessor(bv_idx_body, ACC_UINT, index_sets[BODY].size, "SCALAR",
                                [int(index_sets[BODY].min())], [int(index_sets[BODY].max())])
    acc_idx_gear = add_accessor(bv_idx_gear, ACC_UINT, index_sets[GEAR].size, "SCALAR",
                                [int(index_sets[GEAR].min())], [int(index_sets[GEAR].max())])
    acc_ibm = add_accessor(bv_ibm, ACC_FLOAT, N_BONES, "MAT4")
    acc_anims = [add_accessor(bv, ACC_FLOAT, n_frames, atype)
                 for (_, _, _, atype), bv in zip(anim_specs, bv_anims)]

    # ----- узлы и иерархия -----
    nodes = []
    for i in range(N_BONES):
        nodes.append(Node(name=BONES[i][0],
                          translation=LOCALS_REST[i][0:3, 3].tolist(),
                          children=[]))
    nodes.append(Node(name="Mesh", mesh=0, skin=0,
                      translation=[0.0, -0.92, 0.0], children=[]))

    children = {
        0: [1, 5, 8, 11, 14, MESH_NODE],
        1: [2],
        2: [3, 4],
        5: [6], 6: [7],
        8: [9], 9: [10],
        11: [12], 12: [13],
        14: [15], 15: [16],
        3: [], 4: [], 7: [], 10: [], 13: [], 16: [], MESH_NODE: [],
    }
    for i, ch in children.items():
        nodes[i].children = ch

    # ----- меш (2 примитива по материалам) -----
    shared_attrs = {"POSITION": acc_pos, "NORMAL": acc_nrm,
                    "JOINTS_0": acc_jnt, "WEIGHTS_0": acc_wgt}
    primitives = [
        Primitive(attributes=dict(shared_attrs), indices=acc_idx_body,
                  material=BODY, mode=4),
        Primitive(attributes=dict(shared_attrs), indices=acc_idx_gear,
                  material=GEAR, mode=4),
    ]
    gltf.meshes = [Mesh(name="NURMADOG_body", primitives=primitives)]

    # ----- скин -----
    gltf.skins = [Skin(name="NURMADOG_armature", skeleton=0,
                       joints=list(range(N_BONES)),
                       inverseBindMatrices=acc_ibm)]

    # ----- анимация -----
    samplers = []
    channels = []
    for ai, (node, path, _, _) in enumerate(anim_specs):
        samplers.append(AnimationSampler(input=acc_time, output=acc_anims[ai],
                                         interpolation="LINEAR"))
        channels.append(AnimationChannel(sampler=ai,
                                         target=AnimationChannelTarget(node=node, path=path)))
    gltf.animations = [Animation(name="Idle", samplers=samplers, channels=channels)]

    gltf.nodes = nodes
    gltf.scenes = [Scene(name="Scene", nodes=[0])]

    gltf.buffers[0].byteLength = len(buf)
    gltf.set_binary_blob(bytes(buf))
    return gltf


def main():
    positions, normals, joints, weights, index_sets = build_mesh()
    print(f"vertices: {positions.shape[0]}, "
          f"triangles body: {index_sets[BODY].size // 3}, "
          f"triangles gear: {index_sets[GEAR].size // 3}, bones: {N_BONES}")

    gltf = build_gltf(positions, normals, joints, weights, index_sets)
    gltf.save_binary("nurmadog/nurmadog.glb")
    print("saved nurmadog/nurmadog.glb")

    # валидация: перечитаем файл
    back = GLTF2().load("nurmadog/nurmadog.glb")
    print("nodes:", len(back.nodes), "meshes:", len(back.meshes),
          "skins:", len(back.skins), "anims:", len(back.animations),
          "accessors:", len(back.accessors), "bufferViews:", len(back.bufferViews))
    skin = back.skins[0]
    print("skin joints:", list(skin.joints), "skeleton:", skin.skeleton,
          "inverseBindMatrices:", skin.inverseBindMatrices)
    anim = back.animations[0]
    print("animation channels:", len(anim.channels))
    for ch in anim.channels:
        print("  node", ch.target.node, ch.target.path, "sampler", ch.sampler)


if __name__ == "__main__":
    main()
