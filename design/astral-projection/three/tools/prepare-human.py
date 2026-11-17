#!/usr/bin/env python3
"""Repose the CC0 MakeHuman surface and bake a compact four-weight arm rig."""
from pathlib import Path
import json
import gzip
import numpy as np

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
vertices, groups, group = [], {}, ''
for line in gzip.open(ASSETS / 'makehuman-base.obj.gz', 'rt'):
    if line.startswith('v '):
        vertices.append(list(map(float, line.split()[1:4])))
    elif line.startswith('g '):
        group = line.strip()[2:]
        groups[group] = []
    elif line.startswith('f '):
        groups[group].append([int(x.split('/')[0]) - 1 for x in line.split()[1:]])
original = np.array(vertices) * 0.16
original[:, 1] += 0.10

def joint(name):
    ids = sorted({i for face in groups['joint-' + name] for i in face})
    return original[ids].mean(axis=0)

def rotation(a, b):
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = np.dot(a, b)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / max(1e-8, 1 + c)

def distances(points, a, b):
    delta = b - a
    t = np.clip(((points-a) @ delta) / np.dot(delta, delta), 0, 1)
    return np.linalg.norm(points - (a + t[:, None] * delta), axis=1)

ids = sorted({i for face in groups['body'] for i in face})
lookup = {old: n for n, old in enumerate(ids)}
source = original[ids].copy()
posed = source.copy()
# Close the eyelids in the neutral rest pose, retaining the actual face topology.
for side in ['l', 'r']:
    eye = joint(side + '-eye')
    near = (np.abs(source[:, 0]-eye[0]) < 0.055) & (np.abs(source[:, 1]-eye[1]) < 0.035) & (source[:, 2] > eye[2]-0.025)
    posed[near, 1] = eye[1] + (posed[near, 1]-eye[1]) * 0.12

bones = [{'name': 'body', 'parent': -1, 'position': [0, 0, 0]}]
weights = np.zeros((len(ids), 4), dtype=np.float32)
weights[:, 0] = 1
skin = np.zeros((len(ids), 4), dtype=np.uint16)
arm_data = []
for side, sign in [('l', 1), ('r', -1)]:
    shoulder, elbow, wrist = [joint(side+'-'+name) for name in ['shoulder', 'elbow', 'hand']]
    upper_length, fore_length = np.linalg.norm(elbow-shoulder), np.linalg.norm(wrist-elbow)
    new_shoulder = shoulder.copy()
    new_elbow = shoulder + np.array([sign*0.045, -np.sqrt(upper_length**2-0.045**2), 0])
    new_wrist = new_elbow + np.array([sign*0.018, -np.sqrt(fore_length**2-0.018**2-0.01**2), 0.01])
    upper_rotation = rotation(elbow-shoulder, new_elbow-new_shoulder)
    lower_rotation = rotation(wrist-elbow, new_wrist-new_elbow)
    shoulder_index = len(bones)
    bones.append({'name': side+'-shoulder', 'parent': 0, 'position': new_shoulder.tolist()})
    elbow_index = len(bones)
    bones.append({'name': side+'-elbow', 'parent': shoulder_index, 'position': (new_elbow-new_shoulder).tolist()})
    wrist_index = len(bones)
    bones.append({'name': side+'-hand', 'parent': elbow_index, 'position': (new_wrist-new_elbow).tolist()})
    segments = [(shoulder_index, shoulder, elbow, upper_rotation, new_shoulder),
                (elbow_index, elbow, wrist, lower_rotation, new_elbow)]
    middle = joint(side+'-finger-3-1')
    segments.append((wrist_index, wrist, middle, lower_rotation, new_wrist))
    finger_indices = []
    for finger in range(1, 6):
        points = [joint(f'{side}-finger-{finger}-{n}') for n in range(1, 5)]
        parent, previous = wrist_index, new_wrist
        chain = []
        for n in range(3):
            new_point = new_wrist + lower_rotation @ (points[n]-wrist)
            index = len(bones)
            bones.append({'name': f'{side}-finger-{finger}-{n}', 'parent': parent, 'position': (new_point-previous).tolist()})
            segments.append((index, points[n], points[n+1], lower_rotation, new_point))
            parent, previous = index, new_point
            chain.append(index)
        finger_indices.append(chain)
    # Restrict each anatomical branch. Shoulder weights blend smoothly into
    # the body; the same bound skin is used for the sleeper and the double.
    mask = (source[:, 0]*sign > 0.22) & (source[:, 1] < 1.08) & ((source[:, 1] > 0.35) | (source[:, 0]*sign > 0.45))
    points = source[mask]
    d = np.stack([distances(points, a, b) for _, a, b, _, _ in segments], axis=1)
    # Body anchor at shoulder; avoids pulling chest surface into the upper arm.
    body_distance = np.maximum(0, points[:, 0]*sign-0.18) + 0.015
    d = np.column_stack([body_distance, d])
    order = np.argsort(d, axis=1)[:, :4]
    influence = 1 / np.maximum(np.take_along_axis(d, order, axis=1), 0.008)**5
    influence /= influence.sum(axis=1)[:, None]
    transforms = [points]
    indices = [0]
    for index, a, _, rot, new_a in segments:
        transforms.append((points-a) @ rot.T + new_a)
        indices.append(index)
    transformed = np.stack(transforms, axis=1)
    posed[mask] = (np.take_along_axis(transformed, order[:, :, None], axis=1)*influence[:, :, None]).sum(axis=1)
    weights[mask] = influence
    skin[mask] = np.array(indices)[order]
    arm_data.append({'shoulder': shoulder_index, 'elbow': elbow_index, 'wrist': wrist_index, 'fingers': finger_indices})

# Relax the splayed standing legs to a supported parallel rest pose. These
# vertices remain on the root bone: exit/roll moves the entire resting body.
for side, sign in [('l', 1), ('r', -1)]:
    hip, knee, ankle = [joint(side+'-'+name) for name in ['upper-leg', 'knee', 'ankle']]
    mask = (source[:, 0]*sign > 0) & (source[:, 1] < hip[1])
    points = source[mask]
    new_knee = hip + np.array([0, -np.linalg.norm(knee-hip), 0.025])
    new_ankle = new_knee + np.array([0, -np.linalg.norm(ankle-knee), -0.01])
    upper = rotation(knee-hip, new_knee-hip)
    lower = rotation(ankle-knee, new_ankle-new_knee)
    u = (points-hip) @ upper.T + hip
    lo = (points-knee) @ lower.T + new_knee
    blend = np.clip((knee[1]+0.09-points[:, 1])/0.18, 0, 1)
    posed[mask] = u*(1-blend[:, None])+lo*blend[:, None]
    pelvic_blend = np.clip((hip[1]-points[:, 1])/0.18, 0, 1)
    posed[mask] = posed[mask]*pelvic_blend[:, None]+points*(1-pelvic_blend[:, None])

triangles = []
for face in groups['body']:
    for n in range(1, len(face)-1):
        triangles.extend([lookup[face[0]], lookup[face[n]], lookup[face[n+1]]])
# Reject spikes or torn anatomical edges before shipping the rigged surface.
faces = np.array(triangles).reshape(-1, 3)
edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
lengths = np.linalg.norm(posed[edges[:, 0]]-posed[edges[:, 1]], axis=1)
assert np.isfinite(posed).all()
assert np.max(lengths) < 0.23, f'Stretched mesh edge: {np.max(lengths):.4f}'
assert np.max(np.abs(posed[:, 0])) < 0.55, 'Hands did not reach the resting pose'
assert np.max(np.abs(weights.sum(axis=1)-1)) < 0.00001
print(f'Maximum anatomical edge: {np.max(lengths):.4f}')
arrays = [('position', posed.astype('<f4')), ('bodyCoordinate', source.astype('<f4')),
          ('skinWeight', weights.astype('<f4')), ('skinIndex', skin.astype('<u2')),
          ('index', np.array(triangles, dtype='<u2'))]
metadata = {'vertices': len(ids), 'bones': bones, 'arms': arm_data, 'attributes': {}}
blob = bytearray()
for name, data in arrays:
    while len(blob) % 4:
        blob.append(0)
    metadata['attributes'][name] = {'offset': len(blob), 'length': data.size, 'type': 'uint16' if data.dtype.itemsize == 2 else 'float32'}
    blob.extend(data.tobytes())
(ASSETS / 'human.bin').write_bytes(blob)
(ASSETS / 'human.json').write_text(json.dumps(metadata, indent=2)+'\n')
print(f'Prepared {len(ids)} anatomical vertices, {len(triangles)//3} triangles, {len(bones)} bones; {len(blob)} bytes.')
