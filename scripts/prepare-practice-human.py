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

# The painted textures and backdrops come from generated watercolor
# originals kept in OUTPUT/source (provenance.json there): each swatch is
# moved to the style target's palette, made to tile without a seam and
# sized for phones.
SWATCHES = {'skin': ('#efbe96', 0.45), 'tunic': ('#7aa46a', 0.9), 'trousers': ('#4e5090', 0.85),
            'hair': ('#7a4a2a', 1.0), 'sash': ('#ecd6a2', 0.6)}
BACKDROPS = ('tai-chi', 'sun-salutation', 'workout', 'astral')

def prepare_textures(folder):
    from PIL import Image
    source = folder/'source'
    for name, (target, contrast) in SWATCHES.items():
        picture = np.asarray(Image.open(source/f'{name}.webp').convert('RGB').resize((512, 512), Image.LANCZOS),
                             dtype=np.float64)
        mean = picture.reshape(-1, 3).mean(axis=0)
        goal = np.array([int(target[at:at+2], 16) for at in (1, 3, 5)], dtype=np.float64)
        light = picture @ np.array([0.30, 0.59, 0.11])
        # Keep the brushwork's light and dark, painted in the target colour,
        # with a little of the swatch's own colour variation.
        shade = (light-light.mean())*contrast
        tinted = goal+shade[:, :, None]+(picture-mean-(light-light.mean())[:, :, None])*0.45
        # A copy offset by half covers the seam at the edges.
        shifted = np.roll(tinted, (256, 256), axis=(0, 1))
        ramp = 1-np.abs(np.arange(512)/511*2-1)
        weight = np.clip(np.minimum.outer(ramp, ramp)*3, 0, 1)[:, :, None]
        tiled = tinted*weight+shifted*(1-weight)
        Image.fromarray(np.clip(tiled, 0, 255).astype(np.uint8)).save(folder/f'{name}.webp', quality=88, method=6)
    # The face painting takes the skin swatch's colour on its cheeks and
    # brow, keeping its own eyes, brows, lips and blush.
    face = np.asarray(Image.open(source/'face.webp').convert('RGB').resize((512, 512), Image.LANCZOS), dtype=np.float64)
    skin = face[118:155, 230:285].reshape(-1, 3).mean(axis=0)
    goal = np.array([int(SWATCHES['skin'][0][at:at+2], 16) for at in (1, 3, 5)], dtype=np.float64)
    face = face*goal/skin
    # Outside the painted face (its paper, hair and ears) the painting
    # becomes plain skin, so wherever the mesh's face reaches past it the
    # skin goes on.
    y, x = np.mgrid[0:512, 0:512]
    oval = np.sqrt(((x-256)/150)**2+((y-262)/190)**2)
    keep = np.clip((1.0-oval)/0.18, 0, 1)[:, :, None]
    face = face*keep+goal*(1-keep)
    Image.fromarray(np.clip(face, 0, 255).astype(np.uint8)).save(folder/'face.webp', quality=90, method=6)
    (folder/'backdrops').mkdir(exist_ok=True)
    for name in BACKDROPS:
        picture = Image.open(source/f'backdrop-{name}.webp').convert('RGB')
        picture.thumbnail((1280, 1280), Image.LANCZOS)
        # Richer washes; the near-white paper barely moves.
        pixels = np.asarray(picture, dtype=np.float64)
        light = (pixels @ np.array([0.30, 0.59, 0.11]))[:, :, None]
        pixels = np.clip(light+(pixels-light)*1.3, 0, 255)
        Image.fromarray(pixels.astype(np.uint8)).save(folder/'backdrops'/f'{name}.webp', quality=85, method=6)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--textures-only', action='store_true',
                    help='only rebuild the painted textures and backdrops from OUTPUT/source')
args = parser.parse_args()
if args.textures_only:
    prepare_textures(args.output.resolve())
    raise SystemExit(0)
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
# MakeHuman's base mesh is its gender-neutral average. Her body and face take
# MakeHuman's own CC0 young-adult female macro shape: the three ethnic
# female-young targets in equal shares, as MakeHuman mixes them by default.
# She is slender: MakeHuman's weight slider at 0.25, muscle at 0.35, height
# at 0.85 and ideal proportions, mixed as MakeHuman mixes its macro targets
# (each weight-and-muscle pair by the product of their shares).
def apply_target(name, share):
    target = ROOT / f'design/astral-projection/three/assets/makehuman-{name}.target.gz'
    for line in gzip.open(target, 'rt'):
        if line.strip() and not line.startswith('#'):
            index, dx, dy, dz = line.split()
            all_vertices[int(index)] += np.array([float(dx), float(dy), float(dz)])*share

for race in ('african', 'asian', 'caucasian'):
    apply_target(f'{race}-female-young', 1/3)
BODY_WEIGHT, BODY_MUSCLE, BODY_HEIGHT, BODY_PROPORTIONS = 0.25, 0.35, 0.65, 1.0
for muscle, muscle_share in (('minmuscle', 1-BODY_MUSCLE/0.5), ('averagemuscle', BODY_MUSCLE/0.5)):
    for weight, weight_share in (('minweight', 1-BODY_WEIGHT/0.5), ('averageweight', BODY_WEIGHT/0.5)):
        pair = muscle_share*weight_share
        if (muscle, weight) != ('averagemuscle', 'averageweight'):
            apply_target(f'universal-female-young-{muscle}-{weight}', pair)
        apply_target(f'proportions-female-young-{muscle}-{weight}-idealproportions', pair*BODY_PROPORTIONS)
# MakeHuman's four maxheight targets for these pairs are the same file.
apply_target('height-female-young-maxheight', (BODY_HEIGHT-0.5)/0.5)

# MakeHuman's own CC0 rig weights for this mesh (folded onto this figure's
# bones further on).
weights_file = ROOT / 'design/astral-projection/three/assets/makehuman-default-weights.mhw.gz'
rig = json.loads(gzip.open(weights_file, 'rt').read())
assert rig['license'] == 'CC0'

def rig_share(accept):
    share = np.zeros(len(all_vertices))
    for name, entries in rig['weights'].items():
        if accept(name):
            for vertex, weight in entries:
                share[vertex] += weight
    return np.clip(share, 0, 1)

def helpers(prefix):
    return sorted({index for group, faces in groups.items() if group.startswith(prefix) for face in faces
                   for index in face})

def group_centre(name):
    return all_vertices[sorted({index for face in groups['joint-'+name] for index in face})].mean(axis=0)

# Graceful hands and feet: each a little smaller about the wrist or ankle,
# with its finger and toe joints, so the rig still fits.
metres = 1.7/np.ptp(all_vertices[sorted({i for f in groups['body'] for i in f})][:, 1])
for side in ('L', 'R'):
    prefix = 'l' if side == 'L' else 'r'
    for pivot_name, stems, joint_prefix, factor in (
            ('hand', ('wrist', 'metacarpal', 'finger'), f'joint-{prefix}-finger', 0.90),
            ('ankle', ('foot', 'toe'), f'joint-{prefix}-toe', 0.92)):
        pivot = group_centre(f'{prefix}-{pivot_name}')
        share = rig_share(lambda name: name.endswith('.'+side) and name.split('.')[0].startswith(stems))
        all_vertices += (pivot-all_vertices)*((1-factor)*share)[:, None]
        tips = helpers(joint_prefix)
        all_vertices[tips] = pivot+(all_vertices[tips]-pivot)*factor
# A longer neck: everything the head carries rises a little, fading in up
# the neck and away from the shoulders.
neck_base, skull = group_centre('neck'), group_centre('head')
rise = np.clip((all_vertices[:, 1]-neck_base[1])/(skull[1]-neck_base[1]), 0, 1)
rise = rise*rise*(3-2*rise)*np.clip(1-(np.abs(all_vertices[:, 0])-0.05/metres)/(0.05/metres), 0, 1)
all_vertices[:, 1] += rise*0.014/metres
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

# MakeHuman hands the groin and buttock from pelvis to thigh within a few
# millimetres, which tears the surface open in a forward fold or a deep
# stance. Diffuse that hand-over across the surface around the hips, and the
# shoulder's chest-to-arm hand-over the same way for arms raised overhead;
# other bones' shares, the hands and the fingers stay as rigged.
face_triangles = np.array([[lookup[face[0]], lookup[face[at]], lookup[face[at+1]]]
                           for face in groups['body'] for at in range(1, len(face)-1)], dtype=np.int64)
pairs = np.concatenate([face_triangles[:, [0, 1]], face_triangles[:, [1, 2]], face_triangles[:, [2, 0]]])
pairs = np.unique(np.concatenate([pairs, pairs[:, ::-1]]), axis=0)
degree = np.bincount(pairs[:, 0], minlength=len(ids)).astype(np.float64)
dense = np.zeros((len(ids), len(bones)))
for slot in range(4):
    np.add.at(dense, (np.arange(len(ids)), joints[:, slot]), weights[:, slot])
arm_share = dense[:, [at for at, item in enumerate(bones) if 5 <= item['role'] <= 7]].sum(axis=1)

def diffuse(members, zone, steps):
    shares = dense[:, members]
    mass = shares.sum(axis=1)
    active = zone & (mass > 0.02)
    for _ in range(steps):
        total = np.zeros_like(shares)
        np.add.at(total, pairs[:, 0], shares[pairs[:, 1]])
        mean = total/np.maximum(degree, 1)[:, None]
        mixed = shares*0.5+mean*0.5
        scale = mass/np.maximum(mixed.sum(axis=1), 1e-12)
        shares[active] = mixed[active]*scale[active, None]
    dense[:, members] = shares

hips_y = (joint('l-upper-leg')[1]+joint('r-upper-leg')[1])/2
hip_zone = (positions[:, 1] > hips_y-0.24) & (positions[:, 1] < hips_y+0.07) & (arm_share < 0.01)
thighs = [4+18, 4+21+18]
diffuse([0]+thighs, hip_zone, 120)
# The thighs never reach above the hip crease: a lifted or spread leg must
# not drag the waist out with it.
fade = np.clip((hips_y+0.07-positions[:, 1])/0.09, 0, 1)
for thigh in thighs:
    removed = dense[:, thigh]*(1-fade)
    dense[:, thigh] -= removed
    dense[:, 0] += removed
for side in (0, 1):
    shoulder = joint(('l' if side == 0 else 'r')+'-shoulder')
    near = np.linalg.norm(positions-shoulder, axis=1) < 0.16
    diffuse([1, 2, 4+side*21], near & (arm_share < 0.01), 40)
for index in range(len(ids)):
    strongest = np.argsort(-dense[index])[:4]
    shares = dense[index, strongest]
    shares[shares < 0.004] = 0.0
    joints[index] = strongest
    weights[index] = shares/shares.sum()

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

eye_height = joint('l-eye')[1]

def hairline(points):
    """Positive on the hair: a hairline high on the forehead, lower over
    the temples, behind the ears and down to the nape; the ears stay bare."""
    points = np.atleast_2d(points)
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    turn = np.degrees(np.arctan2(np.abs(x), z-0.02))
    height = eye_height+np.interp(turn, [0, 20, 45, 65, 85, 105, 125, 180],
                                  [0.064, 0.062, 0.052, 0.034, 0.012, 0.002, -0.022, -0.045])
    value = y-height
    ears = (y < eye_height+0.002) & (np.abs(x) > 0.070)
    value = np.where(ears, np.minimum(value, 0.070-np.abs(x)), value)
    return np.where(y < 1.44, -1.0, value)

def neckline(points):
    """Positive below the wrap top's collar: level over the shoulders, then
    a V down the breastbone in front."""
    points = np.atleast_2d(points)
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    v = 0.075*np.clip(1-np.abs(x)/0.085, 0, 1)*np.clip((z-0.02)/0.04, 0, 1)
    return (neck_height-0.04-v)-y

def region_of(points):
    points = np.atleast_2d(points)
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    regions = np.zeros(len(points), dtype=np.uint8)
    # Sleeves continue over the shoulder cap. A horizontal collar cutoff alone
    # leaves isolated bare patches where the arm rises above the neck cutoff.
    regions[(y > hip_height-0.09) & ((neckline(points) > 0) |
            ((np.abs(x) > 0.115) & (y < neck_height+0.025)))] = 1
    regions[y <= hip_height-0.04] = 2
    for cuff, ankle in zip(cuffs, ankles):
        # Hands hang below the hips in the bind pose; only arms reach this wide.
        regions[(np.abs(x) > cuff) & (y > 0.5)] = 0
        regions[y < ankle] = 0
    regions[hairline(points) > 0] = 3
    return regions

# Clean painted hems: split each triangle that crosses a region boundary
# exactly along the boundary's plane, then give every region its own copy
# of the shared hem vertices. Surface and skin stay continuous.
def plane(axis, value):
    return lambda points: np.atleast_2d(points)[:, axis]-value

planes = [(1, hip_height-0.04), (1, neck_height+0.025), (0, 0.115), (0, -0.115)]
planes += [(0, cuff) for cuff in cuffs] + [(0, -cuff) for cuff in cuffs] + [(1, ankle) for ankle in ankles]
cuts = [(('plane',)+item, plane(*item)) for item in planes] + [(('neckline',), neckline), (('hairline',), hairline)]
points, skin_joints, skin_weights = list(positions), list(joints), list(weights)
surface_normals = list(normals)
edges = {}

def hem_point(a, b, name, cut):
    key = (min(a, b), max(a, b), name)
    if key not in edges:
        da, db = float(cut(points[a])[0]), float(cut(points[b])[0])
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
for name, cut in cuts:
    split = []
    for face in faces:
        corners = np.array([points[at] for at in face])
        distance = cut(corners)
        if len(set(region_of(corners))) == 1 or not (np.any(distance > 1e-7) and np.any(distance < -1e-7)):
            split.append(face)
            continue
        side = np.where(np.abs(distance) <= 1e-7, 0, np.sign(distance)).astype(int)
        if 0 in side:
            # One corner lies on the plane: cut the opposite edge once.
            on = int(np.where(side == 0)[0][0])
            a, b, c = face[on], face[(on+1) % 3], face[(on+2) % 3]
            middle = hem_point(b, c, name, cut)
            split += [[a, b, middle], [a, middle, c]]
            continue
        lone = int([at for at in range(3) if list(side).count(side[at]) == 1][0])
        a, b, c = face[lone], face[(lone+1) % 3], face[(lone+2) % 3]
        ab, ac = hem_point(a, b, name, cut), hem_point(a, c, name, cut)
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
triangles = np.array(faces, dtype=np.int64)
# The head. MakeHuman's own eyeballs sit in the sockets under painted lids;
# a hair shell rises from nothing at the hairline to a centimetre over the
# crown; a low bun sits at the back. All follow the head bone alone.
def outward_faces(vertices, faces, center):
    faces = np.array(faces, dtype=np.int64)
    normal = np.cross(vertices[faces[:, 1]]-vertices[faces[:, 0]], vertices[faces[:, 2]]-vertices[faces[:, 0]])
    flip = np.einsum('ij,ij->i', normal, vertices[faces].mean(axis=1)-center) < 0
    faces[flip] = faces[flip][:, ::-1]
    return faces

def vertex_normals(vertices, faces):
    result = np.zeros_like(vertices)
    face = np.cross(vertices[faces[:, 1]]-vertices[faces[:, 0]], vertices[faces[:, 2]]-vertices[faces[:, 0]])
    for corner in range(3):
        np.add.at(result, faces[:, corner], face)
    return result/np.maximum(np.linalg.norm(result, axis=1)[:, None], 1e-12)

extras = []
hair_faces = triangles[np.all(regions[triangles] == 3, axis=1)]
used = np.unique(hair_faces)
depth = hairline(positions[used])
# Neat swept-back hair: close over the ears and at the hairline, fuller
# towards the back of the crown where it gathers into the bun.
top = np.clip((positions[used, 1]-eye_height-0.03)/0.07, 0, 1)
back = np.clip((joint('head')[2]+0.01-positions[used, 2])/0.08, 0, 1)
sides = np.clip(np.abs(positions[used, 0])/0.07, 0, 1)
above = np.clip((positions[used, 1]-eye_height)/0.03, 0, 1)
thickness = (0.005+0.008*top+0.010*top*back+0.008*sides*above)*np.clip(depth/0.04, 0, 1)**0.9
shell = positions[used]+normals[used]*thickness[:, None]
remap = np.full(len(positions), -1, dtype=np.int64)
remap[used] = np.arange(len(used))
shell_faces = remap[hair_faces]
extras.append((shell, vertex_normals(shell, shell_faces), np.full(len(shell), 3), shell_faces))
rings, segments = 10, 18
# A low, round bun at the back of the head.
nape = positions[used][np.abs(positions[used, 1]-(eye_height+0.045)) < 0.01]
bun_center = np.array([0.0, eye_height+0.045, nape[:, 2].min()-0.016])
bun_radii = np.array([0.046, 0.040, 0.036])
units = np.array([[np.sin(np.pi*ring/rings)*np.cos(2*np.pi*at/segments), np.cos(np.pi*ring/rings),
                   np.sin(np.pi*ring/rings)*np.sin(2*np.pi*at/segments)]
                  for ring in range(rings+1) for at in range(segments)])
bun = bun_center+units*bun_radii
bun_faces = []
for ring in range(rings):
    for at in range(segments):
        a, b = ring*segments+at, ring*segments+(at+1) % segments
        c, d = a+segments, b+segments
        if ring > 0:
            bun_faces.append([a, b, d])
        if ring < rings-1:
            bun_faces.append([a, d, c])
bun_faces = outward_faces(bun, bun_faces, bun_center)
extras.append((bun, vertex_normals(bun, bun_faces), np.full(len(bun), 3), bun_faces))
for prefix in ('l', 'r'):
    indices = sorted({index for face in groups[f'helper-{prefix}-eye'] for index in face})
    eye_lookup = {old: at for at, old in enumerate(indices)}
    eye = (all_vertices[indices]-origin)*scale
    center = eye.mean(axis=0)
    eye_faces = outward_faces(eye, [[eye_lookup[face[0]], eye_lookup[face[at]], eye_lookup[face[at+1]]]
                                    for face in groups[f'helper-{prefix}-eye'] for at in range(1, len(face)-1)], center)
    extras.append((eye, vertex_normals(eye, eye_faces), np.zeros(len(eye)), eye_faces))
head_index = [at for at, item in enumerate(bones) if item['role'] == 3][0]
body_count = len(positions)
for vertices, vertex_normal, vertex_region, faces_of in extras:
    base = len(positions)
    positions = np.vstack([positions, vertices])
    normals = np.vstack([normals, vertex_normal])
    joints = np.vstack([joints, np.tile(np.array([head_index, 0, 0, 0], dtype=np.uint8), (len(vertices), 1))])
    weights = np.vstack([weights, np.tile(np.array([1.0, 0.0, 0.0, 0.0]), (len(vertices), 1))])
    regions = np.concatenate([regions, np.asarray(vertex_region, dtype=np.uint8)])
    triangles = np.vstack([triangles, np.asarray(faces_of, dtype=np.int64)+base])

# Loose clothes: shells over the body, skinned by the same rig. The wrap
# top hangs from the bust and the shoulder blades, its skirt hangs over the
# hips and both thighs, a sash with two tails covers the seam at the waist,
# the sleeves open into bells and the trousers balloon to a gathered hem.
# Regions: 0 skin, 1 tunic, 2 trousers, 3 hair, 4 sash.
role_of = np.array([item['role'] for item in bones])

def share(rows, shares, roles):
    return np.sum(shares*np.isin(role_of[rows], roles), axis=1)

def smooth(value):
    value = np.clip(value, 0, 1)
    return value*value*(3-2*value)

arm = share(joints, weights, [4, 5, 6, 7])
trunk_points = (np.arange(len(positions)) < body_count) & (arm < 0.15)
hips_joint = (joint('l-upper-leg')+joint('r-upper-leg'))/2
armpit_y = (joint('l-shoulder')[1]+joint('r-shoulder')[1])/2-0.09
hem_y = hips_joint[1]-0.15

def slab(height, mask=trunk_points, half=0.012):
    return positions[mask & (np.abs(positions[:, 1]-height) < half)]

heights = np.arange(hip_height+0.02, joint('spine-1')[1], 0.005)
waist_y = heights[int(np.argmin([np.ptp(slab(h, half=0.006)[:, 0]) for h in heights]))]
grid_y = np.arange(hem_y-0.04, neck_height+0.0001, 0.01)
centre_z = np.array([(lambda s: (s[:, 2].min()+s[:, 2].max())/2)(slab(h)) for h in grid_y])
centre_z = np.convolve(np.pad(centre_z, 2, mode='edge'), np.ones(5)/5, mode='valid')

def trunk_z(y):
    return np.interp(y, grid_y, centre_z)

K = 72
angles = np.arange(K)*2*np.pi/K
directions = np.column_stack((np.sin(angles), np.cos(angles)))
hang = np.zeros((len(grid_y), K))
for j, h in enumerate(grid_y):
    s = slab(h)
    hang[j] = (np.column_stack((s[:, 0], s[:, 2]-trunk_z(h))) @ directions.T).max(axis=0)
# Cloth falls straight from the widest place above it, under the armpits.
top = int(np.searchsorted(grid_y, armpit_y))
for j in range(top-1, -1, -1):
    hang[j] = np.maximum(hang[j], hang[j+1])
# Soft cloth settles part of the way back onto her below the widest place.
hang = 0.65*hang+0.35*np.array([(np.column_stack((s[:, 0], s[:, 2]-trunk_z(h))) @ directions.T).max(axis=0)
                                 for h, s in ((h, slab(h)) for h in grid_y)])
for _ in range(3):
    hang = 0.5*hang+0.25*np.roll(hang, 1, axis=1)+0.25*np.roll(hang, -1, axis=1)
hang[1:-1] = 0.5*hang[1:-1]+0.25*hang[:-2]+0.25*hang[2:]

def hanging_radius(theta, y):
    fj = np.clip((y-grid_y[0])/0.01, 0, len(grid_y)-1.001)
    j = fj.astype(int)
    tj = fj-j
    fk = (theta % (2*np.pi))/(2*np.pi)*K
    k = np.floor(fk).astype(int) % K
    tk = fk-np.floor(fk)
    k1 = (k+1) % K
    a = hang[j, k]*(1-tk)+hang[j, k1]*tk
    b = hang[j+1, k]*(1-tk)+hang[j+1, k1]*tk
    return a*(1-tj)+b*tj

def arm_progress(points):
    result = np.zeros(len(points))
    for side, prefix in enumerate(('l', 'r')):
        s, e, h = joint(prefix+'-shoulder'), joint(prefix+'-elbow'), joint(prefix+'-hand')
        upper, lower = np.linalg.norm(e-s), np.linalg.norm(h-e)
        mine = (points[:, 0] >= 0) == (side == 0)
        p = points[mine]
        a = np.clip((p-s) @ (e-s)/upper**2, 0, 1)
        b = np.clip((p-e) @ (h-e)/lower**2, 0, 1)
        da = np.linalg.norm(p-(s+a[:, None]*(e-s)), axis=1)
        db = np.linalg.norm(p-(e+b[:, None]*(h-e)), axis=1)
        result[mine] = np.where(da < db, a*upper, upper+b*lower)/(upper+lower)
    return result

dense_body = np.zeros((body_count, len(bones)))
for slot in range(4):
    np.add.at(dense_body, (np.arange(body_count), joints[:body_count, slot]), weights[:body_count, slot])

def nearest_weights(points, near=8):
    """Skin weights for cloth away from the surface: the weights of the
    nearest trunk and leg vertices, closer ones counting more."""
    candidates = np.where(trunk_points[:body_count] & (positions[:body_count, 1] > hem_y-0.12) &
                          (positions[:body_count, 1] < waist_y+0.15))[0]
    result = np.zeros((len(points), len(bones)))
    for at, point in enumerate(points):
        distance = np.linalg.norm(positions[candidates]-point, axis=1)
        order = np.argsort(distance)[:near]
        share_of = 1/np.maximum(distance[order], 0.005)**2
        result[at] = share_of @ dense_body[candidates[order]]/share_of.sum()
    return result

def strongest(dense):
    rows = np.argsort(-dense, axis=1)[:, :4]
    shares = np.take_along_axis(dense, rows, axis=1)
    shares[shares < 0.004] = 0.0
    return rows.astype(np.uint8), shares/shares.sum(axis=1)[:, None]

def grid_faces(rows, columns, wrap):
    faces = []
    span = columns if wrap else columns-1
    for j in range(rows-1):
        for k in range(span):
            a, b = j*columns+k, j*columns+(k+1) % columns
            faces += [[a, b, b+columns], [a, b+columns, a+columns]]
    return np.array(faces, dtype=np.int64)

def facing_out(points, faces, centre_of):
    normal = np.cross(points[faces[:, 1]]-points[faces[:, 0]], points[faces[:, 2]]-points[faces[:, 0]])
    middle = points[faces].mean(axis=1)
    out = middle-centre_of(middle)
    flip = np.einsum('ij,ij->i', normal, out) < 0
    faces[flip] = faces[flip][:, ::-1]
    return faces

def trunk_axis(points):
    return np.column_stack((np.zeros(len(points)), points[:, 1], trunk_z(points[:, 1])))

cloth = []  # (points, normals, joints, weights, region, faces, source positions or None, hang)

# The top: the body's own tunic surface lifted off it, above the waist and
# along the sleeves.
top_faces = triangles[np.all(regions[triangles] == 1, axis=1) & np.all(triangles < body_count, axis=1)]
top_faces = top_faces[(positions[top_faces][:, :, 1].min(axis=1) > waist_y-0.03) | (arm[top_faces].mean(axis=1) > 0.5)]
used = np.unique(top_faces)
p, n = positions[used], normals[used]
bust_y = slab((waist_y+armpit_y)/2, half=0.06)[:, 1][np.argmax(slab((waist_y+armpit_y)/2, half=0.06)[:, 2])]
sleeve = smooth((arm[used]-0.2)/0.6)
lift = np.interp(p[:, 1], [waist_y, bust_y, neck_height-0.04], [0.016, 0.010, 0.005])*(1-sleeve)
lift += (0.008+0.040*arm_progress(p)**1.6)*sleeve
q = p+n*lift[:, None]
rel = np.column_stack((q[:, 0], q[:, 2]-trunk_z(p[:, 1])))
theta = np.arctan2(rel[:, 0], rel[:, 1])
push = np.maximum(hanging_radius(theta, p[:, 1])+lift-np.linalg.norm(rel, axis=1), 0)
push *= (1-sleeve)*np.clip((armpit_y-p[:, 1])/0.06, 0, 1)
q[:, 0] += np.sin(theta)*push
q[:, 2] += np.cos(theta)*push
remap = np.full(len(positions), -1, dtype=np.int64)
remap[used] = np.arange(len(used))
faces_of = remap[top_faces]
cloth.append((q, vertex_normals(q, faces_of), joints[used], weights[used], 1, faces_of, p, np.zeros(len(q))))

# The skirt of the top, from just above the waist to the upper thigh, with
# a gently uneven hem.
rows_y = np.linspace(waist_y+0.035, hem_y, 16)
fall = (rows_y[0]-rows_y)/(rows_y[0]-rows_y[-1])
skirt = []
for y, f in zip(rows_y, fall):
    hem = 0.012*np.sin(3*angles+0.7)*f**4
    r = hanging_radius(angles, np.full(K, y))+0.016+0.028*f**1.5
    skirt.append(np.column_stack((np.sin(angles)*r, np.full(K, y)+hem, trunk_z(y)+np.cos(angles)*r)))
skirt = np.vstack(skirt)
faces_of = facing_out(skirt, grid_faces(len(rows_y), K, True), trunk_axis)
dense = nearest_weights(skirt).reshape(len(rows_y), K, len(bones))
for _ in range(2):
    dense = 0.5*dense+0.25*np.roll(dense, 1, axis=1)+0.25*np.roll(dense, -1, axis=1)
# The hand-over from the pelvis to the thighs spreads down the whole skirt,
# so a lifted leg draws the hem out gradually instead of tearing a band.
for _ in range(12):
    dense[1:-1] = 0.5*dense[1:-1]+0.25*dense[:-2]+0.25*dense[2:]
    dense[-1] = 0.5*dense[-1]+0.5*dense[-2]
rows, shares = strongest(dense.reshape(-1, len(bones)))
cloth.append((skirt, vertex_normals(skirt, faces_of), rows, shares, 1, faces_of, None, np.repeat(fall, K)))

# The sash round the waist and its two tails hanging in front.
band_y = waist_y+np.array([0.035, 0.012, -0.012, -0.035])
band = np.vstack([np.column_stack((np.sin(angles)*r, np.full(K, y), trunk_z(y)+np.cos(angles)*r))
                  for y, r in ((y, hanging_radius(angles, np.full(K, y))+0.016+bulge)
                               for y, bulge in zip(band_y, (0.005, 0.010, 0.010, 0.005)))])
faces_of = facing_out(band, grid_faces(len(band_y), K, True), trunk_axis)
rows, shares = strongest(nearest_weights(band))
cloth.append((band, vertex_normals(band, faces_of), rows, shares, 4, faces_of, None, np.zeros(len(band))))
for tail, (turn, length) in enumerate(((0.30, 0.30), (0.46, 0.25))):
    strip = []
    for step in np.linspace(0, 1, 9):
        y = waist_y-0.02-step*length
        f = np.clip((rows_y[0]-y)/(rows_y[0]-rows_y[-1]), 0, 1)
        for side in (-1, 1):
            angle = turn+0.12*step+side*0.022/0.15
            r = hanging_radius(np.array([angle]), np.array([y]))[0]+0.016+0.028*f**1.5+0.008+0.004*tail
            strip.append([np.sin(angle)*r, y, trunk_z(y)+np.cos(angle)*r])
    strip = np.array(strip)
    faces_of = facing_out(strip, grid_faces(9, 2, False), trunk_axis)
    rows, shares = strongest(nearest_weights(strip))
    cloth.append((strip, vertex_normals(strip, faces_of), rows, shares, 4, faces_of, None,
                  np.repeat(0.25+0.75*np.linspace(0, 1, 9), 2)))

# The trousers: the legs' surface lifted off them, ballooning below the
# knee and gathered again at the ankle.
leg_faces = triangles[np.all(regions[triangles] == 2, axis=1) & np.all(triangles < body_count, axis=1)]
used = np.unique(leg_faces)
p, n = positions[used], normals[used]
down = np.clip((hip_height-0.04-p[:, 1])/(hip_height-0.04-np.mean(ankles)), 0, 1)
lift = 0.010+0.030*smooth(down/0.7)-0.018*smooth((down-0.86)/0.14)
q = p+n*lift[:, None]
remap = np.full(len(positions), -1, dtype=np.int64)
remap[used] = np.arange(len(used))
faces_of = remap[leg_faces]
cloth.append((q, vertex_normals(q, faces_of), joints[used], weights[used], 2, faces_of, p, np.zeros(len(q))))

# Painted textures follow the form: the trunk and the head are wrapped
# about the vertical, each arm and leg about its own length, so brush
# strokes run down the body and along the limbs. Each wrap is mirrored at
# its back and front, so it has no seam.
CLOTH_TILE = 0.30
HAIR_TILE = 0.18

def trunk_uv(points):
    turn = np.abs(np.arctan2(points[:, 0], points[:, 2]-trunk_z(points[:, 1])))/np.pi
    return np.column_stack((turn*0.45/CLOTH_TILE, points[:, 1]/CLOTH_TILE))

def head_uv(points):
    turn = np.abs(np.arctan2(points[:, 0], points[:, 2]-joint('head')[2]))/np.pi
    return np.column_stack((turn*0.28/HAIR_TILE, points[:, 1]/HAIR_TILE))

def limb_uv(points, start, end, half_round):
    axis = (end-start)/np.linalg.norm(end-start)
    forward = np.array([0.0, 0.0, 1.0])-axis*axis[2]
    forward /= np.linalg.norm(forward)
    across = np.cross(axis, forward)
    rel = points-start
    turn = np.abs(np.arctan2(rel @ across, rel @ forward))/np.pi
    return np.column_stack((turn*half_round/CLOTH_TILE, -(rel @ axis)/CLOTH_TILE))

def wrapped_uv(points, rows, shares):
    dominant = rows[np.arange(len(rows)), np.argmax(shares, axis=1)]
    roles = role_of[dominant]
    sides = np.array([item['side'] for item in bones])[dominant]
    result = trunk_uv(points)
    head = roles == 3
    result[head] = head_uv(points[head])
    for side, prefix in enumerate(('l', 'r')):
        limb = (roles >= 4) & (roles <= 7) & (sides == side)
        result[limb] = limb_uv(points[limb], joint(prefix+'-shoulder'), joint(prefix+'-hand'), 0.13)
        limb = (roles >= 8) & (sides == side)
        result[limb] = limb_uv(points[limb], joint(prefix+'-upper-leg'), joint(prefix+'-ankle'), 0.25)
    return result

uvs = wrapped_uv(positions, joints, weights)
hangs = np.zeros(len(positions))
hair = regions == 3
# Hair strokes run from the hairline back into the bun.
swept = positions[hair]-bun_center
uvs[hair] = np.column_stack((np.abs(np.arctan2(swept[:, 0], swept[:, 1]))/np.pi*0.25/HAIR_TILE,
                             np.linalg.norm(swept, axis=1)/HAIR_TILE))
for points, vertex_normal, rows, shares, region, faces_of, source, hanging in cloth:
    base = len(positions)
    if source is None:
        uv = trunk_uv(points)
    else:
        uv = wrapped_uv(source, rows, shares)
    positions = np.vstack([positions, points])
    normals = np.vstack([normals, vertex_normal])
    joints = np.vstack([joints, np.asarray(rows, dtype=np.uint8)])
    weights = np.vstack([weights, shares])
    regions = np.concatenate([regions, np.full(len(points), region, dtype=np.uint8)])
    triangles = np.vstack([triangles, faces_of+base])
    uvs = np.vstack([uvs, uv])
    hangs = np.concatenate([hangs, hanging])

# The face is painted by face.webp, projected from the front onto the
# head: its eyes, mouth and the mesh's own match exactly, and the painting
# fades out towards the ears, the hairline and under the chin.
FACE = dict(size=(1254, 1254), right_eye=(430, 576), left_eye=(826, 576), mouth=(630, 858))
face_ready = FACE['right_eye'] != (0, 0)
mouth_point = np.array([0.0, joint('mouth')[1]-0.027])
mesh_marks = np.array([joint('r-eye')[:2], joint('l-eye')[:2], mouth_point])
picture = np.array([FACE['right_eye'], FACE['left_eye'], FACE['mouth']], dtype=np.float64)
picture = np.column_stack((picture[:, 0]/FACE['size'][0], 1-picture[:, 1]/FACE['size'][1]))
mapping = np.linalg.solve(np.column_stack((mesh_marks, np.ones(3))), picture)
details = np.column_stack((positions[:, :2], np.ones(len(positions)))) @ mapping
x, y = positions[:, 0], positions[:, 1]
oval = ((x/0.078)**2+((y-eye_height+0.02)/0.115)**2)**0.5
mask = smooth((normals[:, 2]-0.12)/0.4)*smooth((1.0-oval)/0.25)*smooth(-hairline(positions)/0.012)
mask *= (role_of[joints[:, 0]] == 3) & (regions == 0) & face_ready
details[mask <= 0] = 0.0
# Cloth's detail is how freely it hangs from the waist: 0 at the waist, 1
# at the skirt's hem and the sash tails' ends.
details[regions != 0] = np.column_stack((hangs, np.zeros(len(hangs))))[regions != 0]
masks = np.rint(np.clip(mask, 0, 1)*255).astype(np.int64)

quantized = np.rint(weights*65535).astype(np.int64)
quantized[:, 0] += 65535-quantized.sum(axis=1)
assert np.all(quantized >= 0) and np.all(quantized <= 65535)
assert np.isfinite(positions).all() and np.isfinite(normals).all() and np.isfinite(uvs).all()
assert np.max(joints) < len(bones) < 256
assert np.max(triangles) < len(positions) < 65536
assert np.all(quantized.sum(axis=1) == 65535)
assert len(bones) == 46 and np.max(regions) <= 4
blob = bytearray(struct.pack('<8sIIIf', b'PFIG0002', len(positions), triangles.size, len(bones), 1.7))
for item in bones:
    blob.extend(struct.pack('<4Bi6f', item['role'], item['side'], item['finger'], item['segment'],
                            item['parent'], *item['origin'], *item['tip']))
for point, normal, uv, detail, influence, weight, region, face in zip(positions, normals, uvs, details, joints,
                                                                     quantized, regions, masks):
    blob.extend(struct.pack('<3f3h2f2f4B4HBB', *point, *np.rint(normal*32767).astype(int),
                            *uv, *detail, *influence, *weight, int(region), int(face)))
blob.extend(triangles.astype('<u2').tobytes())
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
(output/'anatomy.bin').write_bytes(blob)
metadata = {'format':'PFIG0002', 'vertices':len(positions), 'triangles':len(triangles),
            'bones':len(bones), 'bytes':len(blob), 'sha256':hashlib.sha256(blob).hexdigest(),
            'regions':['skin', 'tunic', 'trousers', 'hair', 'sash'],
            'source':'https://github.com/makehumancommunity/makehuman/blob/a8bc2d54ff0ac92e78ff71431b1023eda42bf482/makehuman/data/3dobjs/base.obj',
            'license':'CC0-1.0', 'bone_names':[f"{b['role']}/{b['side']}/{b['finger']}/{b['segment']}" for b in bones]}
(output/'anatomy.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(f"Prepared {len(positions)} vertices, {len(triangles)} triangles, {len(bones)} bones; {len(blob)} bytes")
crown = positions[:body_count, 1].max()
# The eyes sit halfway down the head.
print(f"waist {waist_y:.3f} bust {bust_y:.3f} armpit {armpit_y:.3f} hem {hem_y:.3f}; "
      f"{1.7/(2*(crown-eye_height)):.2f} heads tall")
