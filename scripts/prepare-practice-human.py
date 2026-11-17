#!/usr/bin/env python3
"""Bake the pinned CC0 MakeHuman surface for the native practice skin rig."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
source_file = ROOT / 'design/astral-projection/three/assets/makehuman-base.obj.gz'
vertices, groups, group = [], {}, ''
for line in gzip.open(source_file, 'rt'):
    if line.startswith('v '):
        vertices.append(list(map(float, line.split()[1:4])))
    elif line.startswith('g '):
        group = line.strip()[2:]
        groups[group] = []
    elif line.startswith('f '):
        groups[group].append([int(item.split('/')[0]) - 1 for item in line.split()[1:]])
all_vertices = np.asarray(vertices, dtype=np.float64)
ids = sorted({index for face in groups['body'] for index in face})
lookup = {old: index for index, old in enumerate(ids)}
body = all_vertices[ids]
scale = 1.7 / np.ptp(body[:, 1])
origin = np.array([0, body[:, 1].min(), 0])
positions = (body - origin) * scale

def joint(name):
    indices = sorted({index for face in groups['joint-' + name] for index in face})
    return (all_vertices[indices].mean(axis=0) - origin) * scale

bones = []

def bone(role, side, start, end, parent=-1, finger=0, segment=0):
    index = len(bones)
    bones.append(dict(role=role, side=side, origin=np.array(start), tip=np.array(end),
                      parent=parent, finger=finger, segment=segment))
    return index

# The arm and finger chains match the preview's anatomical joints; native
# standing and floor practices also need the pelvis, spine, head and legs.
bone(0, 0, joint('pelvis'), joint('spine-3'))
bone(1, 0, joint('spine-3'), joint('spine-1'), 0)
bone(2, 0, joint('spine-1'), joint('neck'), 1)
bone(3, 0, joint('neck'), joint('head-2'), 2)
arm_sets, leg_sets = [], []
for side, prefix in enumerate(('l', 'r')):
    arm = []
    parent = 2
    for role, start, end in [(4, 'shoulder', 'elbow'), (5, 'elbow', 'hand'),
                             (6, 'hand', 'finger-3-1')]:
        parent = bone(role, side, joint(prefix+'-'+start), joint(prefix+'-'+end), parent)
        arm.append(parent)
    hand = parent
    for finger in range(1, 6):
        parent = hand
        for segment in range(3):
            parent = bone(7, side, joint(f'{prefix}-finger-{finger}-{segment+1}'),
                          joint(f'{prefix}-finger-{finger}-{segment+2}'), parent, finger, segment)
            arm.append(parent)
    arm_sets.append(arm)
    leg = []
    parent = 0
    for role, start, end in [(8, 'upper-leg', 'knee'), (9, 'knee', 'ankle'),
                             (10, 'ankle', 'toe-3-3')]:
        parent = bone(role, side, joint(prefix+'-'+start), joint(prefix+'-'+end), parent)
        leg.append(parent)
    leg_sets.append(leg)

weights = np.zeros((len(ids), 4), dtype=np.float64)
joints = np.zeros((len(ids), 4), dtype=np.uint8)
for index, point in enumerate(positions):
    side = 0 if point[0] >= 0 else 1
    shoulder = joint(('l' if side == 0 else 'r') + '-shoulder')
    hip = joint(('l' if side == 0 else 'r') + '-upper-leg')
    candidates = list(range(4)) + arm_sets[side]
    # Blend branch eligibility across the torso instead of cutting the mesh
    # at an X/Y line: adjacent elbow/finger vertices must move together.
    arm_gain = max(np.clip((abs(point[0])-0.25)/0.08, 0, 1),
                   np.clip((point[1]-joint('spine-3')[1])/0.15, 0, 1))
    if point[1] < hip[1] + 0.06:
        candidates = [0, 1] + leg_sets[side]
        arm_gain = 1.0
    distances = []
    for at in candidates:
        start, end = bones[at]['origin'], bones[at]['tip']
        delta = end-start
        along = np.clip(np.dot(point-start, delta) / np.dot(delta, delta), 0, 1)
        distances.append(np.linalg.norm(point-start-along*delta))
    scores = 1 / np.maximum(np.asarray(distances), 0.008)**4
    for candidate, at in enumerate(candidates):
        if at >= 4 and bones[at]['role'] <= 7:
            scores[candidate] *= arm_gain*arm_gain
    order = np.argsort(-scores)[:4]
    raw = scores[order]
    raw /= raw.sum()
    joints[index, :len(order)] = np.asarray(candidates)[order]
    weights[index, :len(order)] = raw

# MakeHuman's own CC0 rig weights for this mesh, folded onto these 46 bones.
# The procedural weights above remain only for vertices the rig leaves out.
weights_file = ROOT / 'design/astral-projection/three/assets/makehuman-default-weights.mhw.gz'
rig = json.loads(gzip.open(weights_file, 'rt').read())
assert rig['license'] == 'CC0'

def rig_bones(name):
    side = 0 if name.endswith('.L') else 1
    base = 4 + side*21
    stem = name.split('.')[0]
    if stem in ('root', 'pelvis', 'spine05', 'spine04'):
        return [(0, 1.0)]
    if stem in ('spine03', 'spine02'):
        return [(1, 1.0)]
    if stem in ('spine01', 'breast', 'clavicle'):
        return [(2, 1.0)]
    if stem == 'shoulder01':
        return [(2, 0.5), (base, 0.5)]
    if stem.startswith('upperarm'):
        return [(base, 1.0)]
    if stem.startswith('lowerarm'):
        return [(base+1, 1.0)]
    if stem in ('wrist',) or stem.startswith('metacarpal'):
        return [(base+2, 1.0)]
    if stem.startswith('finger'):
        finger, segment = map(int, stem[6:].split('-'))
        return [(base+3+(finger-1)*3+segment-1, 1.0)]
    if stem.startswith('upperleg'):
        return [(base+18, 1.0)]
    if stem.startswith('lowerleg'):
        return [(base+19, 1.0)]
    if stem == 'foot' or stem.startswith('toe'):
        return [(base+20, 1.0)]
    return [(3, 1.0)]  # neck, head, jaw, eyes and face

for index, (at, side) in enumerate(((0, 0), (0, 1))):
    assert bones[4+side*21]['role'] == 4 and bones[4+side*21+18]['role'] == 8
gathered = [dict() for _ in ids]
for name, entries in rig['weights'].items():
    targets = rig_bones(name)
    for vertex, weight in entries:
        if vertex in lookup:
            for target, share in targets:
                gathered[lookup[vertex]][target] = gathered[lookup[vertex]].get(target, 0.0)+weight*share
for index, influence in enumerate(gathered):
    strongest = sorted(((target, weight) for target, weight in influence.items() if weight > 0.004),
                       key=lambda item: -item[1])[:4]
    total = sum(weight for _, weight in strongest)
    if total < 0.5:
        continue
    joints[index] = 0
    weights[index] = 0.0
    for slot, (target, weight) in enumerate(strongest):
        joints[index, slot] = target
        weights[index, slot] = weight/total

# The middle waist belongs to the trunk even when a hand passes near it.
waist = (positions[:, 1] > joint('pelvis')[1]+0.06) & (positions[:, 1] < joint('spine-3')[1]) & (np.abs(positions[:, 0]) < 0.25)
arm_roles = np.array([4 <= item['role'] <= 7 for item in bones])
assert not np.any(arm_roles[joints[waist]] & (weights[waist] > 0)), 'Waist cannot follow an arm'
# Distal fingers must never cross back into the trunk-only region. The
# shoulder's outward slope is capped before the hand and thumb surface.
hands = (np.abs(positions[:, 0]) > 0.40) & (positions[:, 2] > 0.20)
assert np.all(np.sum(weights[hands] * (joints[hands] < 4), axis=1) < 0.1), 'Fingers cannot follow the trunk'

triangles = []
for face in groups['body']:
    for index in range(1, len(face)-1):
        triangles.append([lookup[face[0]], lookup[face[index]], lookup[face[index+1]]])
triangles = np.array(triangles, dtype=np.int64)
normals = np.zeros_like(positions)
face_normals = np.cross(positions[triangles[:, 1]]-positions[triangles[:, 0]],
                        positions[triangles[:, 2]]-positions[triangles[:, 0]])
for corner in range(3):
    np.add.at(normals, triangles[:, corner], face_normals)
normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
uvs = np.column_stack((positions[:, 0]*3+0.5, positions[:, 1]*3))
# Regions keep the same surface and skin weights: skin, tunic, trousers, hair.
hip_height = joint('pelvis')[1]
neck_height = joint('neck')[1]
head = joint('head')
cuffs = [abs(joint(prefix+'-hand')[0])-0.025 for prefix in ('l', 'r')]
ankles = [joint(prefix+'-ankle')[1]+0.02 for prefix in ('l', 'r')]

def region_of(points):
    points = np.atleast_2d(points)
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    regions = np.zeros(len(points), dtype=np.uint8)
    # Sleeves continue over the shoulder cap. A horizontal collar cutoff alone
    # leaves isolated bare patches where the arm rises above the neck cutoff.
    regions[(y > hip_height-0.09) & ((y < neck_height-0.04) |
            ((np.abs(x) > 0.115) & (y < neck_height+0.025)))] = 1
    regions[y <= hip_height-0.04] = 2
    for cuff, ankle in zip(cuffs, ankles):
        # Hands hang below the hips in the bind pose; only arms reach this wide.
        regions[(np.abs(x) > cuff) & (y > 0.5)] = 0
        regions[y < ankle] = 0
    regions[(y > head[1]+0.055) | ((y > head[1]-0.015) & (z < head[2]-0.015))] = 3
    return regions

# Clean painted hems: split each triangle that crosses a region boundary
# exactly along the boundary's plane, then give every region its own copy
# of the shared hem vertices. Surface and skin stay continuous.
cuts = [(1, hip_height-0.04), (1, neck_height-0.04), (1, neck_height+0.025),
        (0, 0.115), (0, -0.115), (1, head[1]+0.055), (1, head[1]-0.015), (2, head[2]-0.015)]
cuts += [(0, cuff) for cuff in cuffs] + [(0, -cuff) for cuff in cuffs] + [(1, ankle) for ankle in ankles]
points, skin_joints, skin_weights = list(positions), list(joints), list(weights)
surface_normals = list(normals)
edges = {}

def hem_point(a, b, axis, value):
    key = (min(a, b), max(a, b), axis, value)
    if key not in edges:
        da, db = points[a][axis]-value, points[b][axis]-value
        t = da/(da-db)
        points.append(points[a]+(points[b]-points[a])*t)
        normal = surface_normals[a]*(1-t)+surface_normals[b]*t
        surface_normals.append(normal/max(np.linalg.norm(normal), 1e-12))
        mixed = {}
        for chain, share in ((a, 1-t), (b, t)):
            for at, weight in zip(skin_joints[chain], skin_weights[chain]):
                mixed[int(at)] = mixed.get(int(at), 0.0)+weight*share
        strongest = sorted(mixed.items(), key=lambda item: -item[1])[:4]
        total = sum(weight for _, weight in strongest)
        skin_joints.append(np.array([at for at, _ in strongest]+[0]*(4-len(strongest)), dtype=np.uint8))
        skin_weights.append(np.array([weight/total for _, weight in strongest]+[0.0]*(4-len(strongest))))
        edges[key] = len(points)-1
    return edges[key]

faces = [list(face) for face in triangles]
for axis, value in cuts:
    split = []
    for face in faces:
        corners = np.array([points[at] for at in face])
        distance = corners[:, axis]-value
        if len(set(region_of(corners))) == 1 or not (np.any(distance > 1e-7) and np.any(distance < -1e-7)):
            split.append(face)
            continue
        side = np.where(np.abs(distance) <= 1e-7, 0, np.sign(distance)).astype(int)
        if 0 in side:
            # One corner lies on the plane: cut the opposite edge once.
            on = int(np.where(side == 0)[0][0])
            a, b, c = face[on], face[(on+1) % 3], face[(on+2) % 3]
            middle = hem_point(b, c, axis, value)
            split += [[a, b, middle], [a, middle, c]]
            continue
        lone = int([at for at in range(3) if list(side).count(side[at]) == 1][0])
        a, b, c = face[lone], face[(lone+1) % 3], face[(lone+2) % 3]
        ab, ac = hem_point(a, b, axis, value), hem_point(a, c, axis, value)
        split += [[a, ab, ac], [ab, b, c], [ab, c, ac]]
    faces = split
points = np.array(points)
face_regions = region_of(np.array([points[face].mean(axis=0) for face in faces]))
# Thumbs sit inside the cuff plane in the bind pose: whatever the hand and
# fingers carry is skin.
hand_bones = np.array([item['role'] in (6, 7) for item in bones])
hand_share = [float(np.sum(skin_weights[at][hand_bones[skin_joints[at]]])) for at in range(len(points))]
for at, face in enumerate(faces):
    if min(hand_share[corner] for corner in face) > 0.5:
        face_regions[at] = 0
copies = {}
order = []
for face, region in zip(faces, face_regions):
    for corner, at in enumerate(face):
        key = (at, int(region))
        if key not in copies:
            copies[key] = len(order)
            order.append(key)
        face[corner] = copies[key]
source = np.array([at for at, _ in order])
regions = np.array([region for _, region in order], dtype=np.uint8)
positions = points[source]
normals = np.array(surface_normals)[source]
joints = np.array(skin_joints)[source]
weights = np.array(skin_weights)[source]
uvs = np.column_stack((positions[:, 0]*3+0.5, positions[:, 1]*3))
triangles = np.array(faces, dtype=np.int64)
quantized = np.rint(weights*65535).astype(np.int64)
quantized[:, 0] += 65535-quantized.sum(axis=1)
assert np.all(quantized >= 0) and np.all(quantized <= 65535)
assert np.isfinite(positions).all() and np.isfinite(normals).all()
assert np.max(joints) < len(bones) < 256
assert np.max(triangles) < len(positions) < 65536
assert np.all(quantized.sum(axis=1) == 65535)
assert len(bones) == 46
blob = bytearray(struct.pack('<8sIIIf', b'PFIG0001', len(positions), triangles.size, len(bones), 1.7))
for item in bones:
    blob.extend(struct.pack('<4Bi6f', item['role'], item['side'], item['finger'], item['segment'],
                            item['parent'], *item['origin'], *item['tip']))
for point, normal, uv, influence, weight, region in zip(positions, normals, uvs, joints, quantized, regions):
    blob.extend(struct.pack('<3f3h2f4B4HBB', *point, *np.rint(normal*32767).astype(int),
                            *uv, *influence, *weight, int(region), 0))
blob.extend(triangles.astype('<u2').tobytes())
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
(output/'anatomy.bin').write_bytes(blob)
metadata = {'format':'PFIG0001', 'vertices':len(positions), 'triangles':len(triangles),
            'bones':len(bones), 'bytes':len(blob), 'sha256':hashlib.sha256(blob).hexdigest(),
            'source':'https://github.com/makehumancommunity/makehuman/blob/a8bc2d54ff0ac92e78ff71431b1023eda42bf482/makehuman/data/3dobjs/base.obj',
            'license':'CC0-1.0', 'bone_names':[f"{b['role']}/{b['side']}/{b['finger']}/{b['segment']}" for b in bones]}
(output/'anatomy.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(f"Prepared {len(positions)} vertices, {len(triangles)} triangles, {len(bones)} bones; {len(blob)} bytes")
