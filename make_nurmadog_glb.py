import json
import struct
import math

FLOAT = 5126
USHORT = 5123

buf = bytearray()      # single binary chunk (BIN)
bviews = []            # buffer views
accs = []              # accessors


def push(b):
    off = len(buf)
    buf.extend(b)
    return off, len(b)


def acc(ctype, atype, count, b, mn=None, mx=None):
    off, ln = push(b)
    bviews.append({'buffer': 0, 'byteOffset': off, 'byteLength': ln})
    a = {'bufferView': len(bviews) - 1, 'componentType': ctype,
         'type': atype, 'count': count}
    if mn is not None:
        a['min'] = mn
    if mx is not None:
        a['max'] = mx
    accs.append(a)
    return len(accs) - 1


def f32(vals):
    return struct.pack('<%df' % len(vals), *vals)


def u16(vals):
    return struct.pack('<%dH' % len(vals), *vals)


def quat_z(angle):
    """Quaternion for rotation around Z axis, glTF order (x, y, z, w)."""
    return (0.0, 0.0, math.sin(angle / 2), math.cos(angle / 2))


def cube(lo, hi):
    """Box from lo to hi: 24 vertices, 36 indices, outward normals."""
    lx, ly, lz = lo
    hx, hy, hz = hi
    faces = [
        ([(lx, hy, lz), (hx, hy, lz), (hx, ly, lz), (lx, ly, lz)], (0, 0, -1)),
        ([(lx, ly, hz), (hx, ly, hz), (hx, hy, hz), (lx, hy, hz)], (0, 0, 1)),
        ([(lx, ly, lz), (lx, ly, hz), (lx, hy, hz), (lx, hy, lz)], (-1, 0, 0)),
        ([(hx, hy, lz), (hx, hy, hz), (hx, ly, hz), (hx, ly, lz)], (1, 0, 0)),
        ([(lx, ly, hz), (lx, ly, lz), (hx, ly, lz), (hx, ly, hz)], (0, -1, 0)),
        ([(lx, hy, lz), (hx, hy, lz), (hx, hy, hz), (lx, hy, hz)], (0, 1, 0)),
    ]
    pos = []
    norm = []
    ind = []
    base = 0
    for corners, n in faces:
        for c in corners:
            pos.extend(c)
            norm.extend(n)
        ind += [base + 0, base + 1, base + 2, base + 0, base + 2, base + 3]
        base += 4
    return pos, norm, ind


# Joints (bones): name and global bind-pose translation
joints = [
    ("Hips", (0.0, 0.10, 0.0)),
    ("Spine", (0.0, 0.15, 0.0)),
    ("Head", (0.35, 0.22, 0.0)),
    ("FrontLeft", (0.28, 0.15, 0.10)),
    ("FrontRight", (0.28, 0.15, -0.10)),
    ("BackLeft", (-0.28, 0.15, 0.10)),
    ("BackRight", (-0.28, 0.15, -0.10)),
]

# Scene graph nodes; node 7 is the skinned mesh
nodes = [
    {"name": "Hips", "translation": [0.0, 0.10, 0.0], "children": [1, 3, 4, 5, 6]},
    {"name": "Spine", "translation": [0.0, 0.05, 0.0], "children": [2]},
    {"name": "Head", "translation": [0.35, 0.07, 0.0]},
    {"name": "FrontLeftLeg", "translation": [0.28, 0.05, 0.10]},
    {"name": "FrontRightLeg", "translation": [0.28, 0.05, -0.10]},
    {"name": "BackLeftLeg", "translation": [-0.28, 0.05, 0.10]},
    {"name": "BackRightLeg", "translation": [-0.28, 0.05, -0.10]},
    {"name": "Body", "mesh": 0, "skin": 0},
]

# Geometry parts: (lo, hi, joint index it is rigidly skinned to)
parts = [
    ((-0.30, 0.00, -0.12), (0.30, 0.30, 0.12), 1),   # body -> Spine
    ((0.30, 0.15, 0.00), (0.55, 0.35, 0.24), 2),     # head -> Head
    ((0.22, -0.25, 0.04), (0.34, 0.15, 0.16), 3),    # front left leg
    ((0.22, -0.25, -0.16), (0.34, 0.15, -0.04), 4),  # front right leg
    ((-0.34, -0.25, 0.04), (-0.22, 0.15, 0.16), 5),  # back left leg
    ((-0.34, -0.25, -0.16), (-0.22, 0.15, -0.04), 6),# back right leg
]

primitives = []
for lo, hi, jid in parts:
    pos, norm, ind = cube(lo, hi)
    nv = len(pos) // 3
    pmin = [min(pos[i::3]) for i in range(3)]
    pmax = [max(pos[i::3]) for i in range(3)]
    jbytes = b''.join(struct.pack('<4H', jid, 0, 0, 0) for _ in range(nv))
    wbytes = b''.join(struct.pack('<4f', 1.0, 0.0, 0.0, 0.0) for _ in range(nv))
    pos_id = acc(FLOAT, 'VEC3', nv, f32(pos), pmin, pmax)
    norm_id = acc(FLOAT, 'VEC3', nv, f32(norm))
    j_id = acc(USHORT, 'VEC4', nv, jbytes)
    w_id = acc(FLOAT, 'VEC4', nv, wbytes)
    i_id = acc(USHORT, 'SCALAR', len(ind), u16(ind))
    primitives.append({
        'attributes': {
            'POSITION': pos_id,
            'NORMAL': norm_id,
            'JOINTS_0': j_id,
            'WEIGHTS_0': w_id,
        },
        'indices': i_id,
        'material': 0,
        'mode': 4,
    })

# Inverse bind matrices (pure translations -> negated translation)
ibm = []
for _, p in joints:
    x, y, z = p
    ibm += [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -x, -y, -z, 1]
ibm_acc = acc(FLOAT, 'MAT4', len(joints), f32(ibm))

mesh = {'name': 'Nurmadog', 'primitives': primitives}
skin = {'name': 'Armature', 'skeleton': 0,
        'joints': list(range(len(joints))),
        'inverseBindMatrices': ibm_acc}

# Animation: legs trot in diagonal pairs, body bobs up and down
times = [0.0, 0.25, 0.5, 0.75, 1.0]
inp = acc(FLOAT, 'SCALAR', 5, f32(times), [0.0], [1.0])


def qseq(angles):
    return [v for a in angles for v in quat_z(a)]


rotA = acc(FLOAT, 'VEC4', 5, f32(qseq([0.0, -0.9, 0.0, 0.9, 0.0])))
rotB = acc(FLOAT, 'VEC4', 5, f32(qseq([0.0, 0.9, 0.0, -0.9, 0.0])))
trans = acc(FLOAT, 'VEC3', 5,
            f32([v for t in
                 [(0, 0, 0), (0, 0.04, 0), (0, 0, 0), (0, 0.04, 0), (0, 0, 0)]
                 for v in t]))

samplers = [
    {'input': inp, 'output': rotA, 'interpolation': 'LINEAR'},  # FrontLeft
    {'input': inp, 'output': rotB, 'interpolation': 'LINEAR'},  # FrontRight
    {'input': inp, 'output': rotB, 'interpolation': 'LINEAR'},  # BackLeft
    {'input': inp, 'output': rotA, 'interpolation': 'LINEAR'},  # BackRight
    {'input': inp, 'output': trans, 'interpolation': 'LINEAR'}, # Body bob
]
channels = [
    {'sampler': 0, 'target': {'node': 3, 'path': 'rotation'}},
    {'sampler': 1, 'target': {'node': 4, 'path': 'rotation'}},
    {'sampler': 2, 'target': {'node': 5, 'path': 'rotation'}},
    {'sampler': 3, 'target': {'node': 6, 'path': 'rotation'}},
    {'sampler': 4, 'target': {'node': 7, 'path': 'translation'}},
]
animation = {'name': 'Walk', 'samplers': samplers, 'channels': channels}

gltf = {
    'asset': {'version': '2.0', 'minVersion': '2.0',
              'generator': 'NURMADOG GLB builder'},
    'scene': 0,
    'scenes': [{'nodes': [0, 7]}],
    'nodes': nodes,
    'meshes': [mesh],
    'skins': [skin],
    'accessors': accs,
    'bufferViews': bviews,
    'buffers': [{'byteLength': len(buf)}],
    'materials': [{'name': 'BodyMat',
                   'pbrMetallicRoughness': {
                       'baseColorFactor': [0.7, 0.5, 0.35, 1.0],
                       'metallicFactor': 0.0,
                       'roughnessFactor': 0.9}}],
    'animations': [animation],
}

json_bytes = json.dumps(gltf).encode('utf-8')


def pad4(b, fill):
    n = (-len(b)) % 4
    return b + fill * n


json_pad = pad4(json_bytes, b' ')
bin_pad = pad4(bytes(buf), b'\x00')

total = 12 + 8 + len(json_pad) + 8 + len(bin_pad)
out = bytearray()
out += b'glTF'
out += struct.pack('<II', 2, total)            # magic + version + total length
out += struct.pack('<II', len(json_pad), 0x4E4F534A)  # JSON chunk
out += json_pad
out += struct.pack('<II', len(bin_pad), 0x004E4942)   # BIN chunk
out += bin_pad

with open('nurmadog.glb', 'wb') as f:
    f.write(out)

print('GLB written: nurmadog.glb, bytes:', len(out))
print('accessors:', len(accs), '| bufferViews:', len(bviews))
print('joints:', [j[0] for j in joints])
print('animation channels:', len(channels))
