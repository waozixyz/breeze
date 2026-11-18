#!/usr/bin/env python3
"""Bake a practice character from the pinned CC0 MakeHuman surface: its
shape, rig, clothes, hair and clean texture maps, for practices' figure.

    prepare-practice-human.py --output practices/shared/figure --character female
    prepare-practice-human.py --output practices/shared/figure --character male
    prepare-practice-human.py --output practices/shared/figure --backdrops

Each character goes to OUTPUT/CHARACTER: anatomy.bin (PFIG0002), its texture
maps and anatomy.json. The backdrops come from OUTPUT/source."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'design/astral-projection/three/assets'
BACKDROPS = ('tai-chi', 'sun-salutation', 'workout', 'astral')

CHARACTERS = {
    # A petite young Chinese woman, slim and toned: narrow shoulders, small
    # hands and feet and a small soft jaw. A fitted jade top with cap sleeves,
    # a stand-up collar and frog knots, slim navy trousers, bare feet; sleek
    # black hair parted in the middle and drawn back into a high bun.
    'female': dict(gender='female', races=(('asian', 0.9), ('caucasian', 0.1)),
                   weight=0.10, muscle=0.45, height=0.60, hands=0.86, feet=0.88, neck=0.006,
                   shoulders=0.012, jaw=0.08, eyes=0.22, mouth=0.10, chin=0.07, outfit='fitted', hair='bun',
                   colours=dict(skin='#f5d7c3', top='#2aa385', trousers='#283b70', hair='#231f27',
                                knot='#f4e8cc', iris='#3b2418', lashes='#140f0e', brows='#3d2c25',
                                lips='#e3788a', blush='#f4a3a5')),
    # A young Chinese man, athletic. A loose indigo kung fu jacket with a
    # stand-up collar and frog knots down the front, wide black trousers
    # gathered at the ankle, bare feet; short black hair.
    'male': dict(gender='male', races=(('asian', 0.9), ('caucasian', 0.1)),
                 weight=0.40, muscle=0.65, height=0.60, hands=0.98, feet=0.98, neck=0.004,
                 shoulders=0.0, jaw=0.0, eyes=0.04, mouth=0.0, chin=0.0, outfit='kungfu', hair='short',
                 colours=dict(skin='#ecc7a9', top='#36508f', trousers='#25252d', hair='#1e1b20',
                              knot='#f0e3c6', iris='#2e1d14', lashes='#1a1311', brows='#211813',
                              lips='#c98b85', blush=None)),
}


def colour(text):
    return np.array([int(text[at:at+2], 16) for at in (1, 3, 5)], dtype=np.float64)


def prepare_backdrops(folder):
    from PIL import Image
    (folder/'backdrops').mkdir(exist_ok=True)
    for name in BACKDROPS:
        picture = Image.open(folder/'source'/f'backdrop-{name}.webp').convert('RGB')
        picture.thumbnail((1280, 1280), Image.LANCZOS)
        # Richer colour; the near-white sky barely moves.
        pixels = np.asarray(picture, dtype=np.float64)
        light = (pixels @ np.array([0.30, 0.59, 0.11]))[:, :, None]
        pixels = np.clip(light+(pixels-light)*1.3, 0, 255)
        Image.fromarray(pixels.astype(np.uint8)).save(folder/'backdrops'/f'{name}.webp', quality=85, method=6)


parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--character', choices=sorted(CHARACTERS))
parser.add_argument('--backdrops', action='store_true', help='only rebuild the backdrops from OUTPUT/source')
args = parser.parse_args()
if args.backdrops:
    prepare_backdrops(args.output.resolve())
    raise SystemExit(0)
if args.character is None:
    parser.error('--character is required unless --backdrops')
spec = CHARACTERS[args.character]
gender = spec['gender']

source_file = ASSETS/'makehuman-base.obj.gz'
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


# MakeHuman's base mesh is its gender-neutral average. Each character is
# MakeHuman's own CC0 young-adult macro shape for its gender, mostly its
# Asian target, at its weight, muscle and height with ideal proportions,
# mixed as MakeHuman mixes its macro targets (each weight-and-muscle pair by
# the product of their shares).
def apply_target(name, share):
    if share == 0.0:
        return
    for line in gzip.open(ASSETS/f'makehuman-{name}.target.gz', 'rt'):
        if line.strip() and not line.startswith('#'):
            index, dx, dy, dz = line.split()
            all_vertices[int(index)] += np.array([float(dx), float(dy), float(dz)])*share


def bracket(value):
    if value <= 0.5:
        return (('min', 1-value/0.5), ('average', value/0.5))
    return (('average', 1-(value-0.5)/0.5), ('max', (value-0.5)/0.5))


for race, share in spec['races']:
    apply_target(f'{race}-{gender}-young', share)
for muscle, muscle_share in bracket(spec['muscle']):
    for weight, weight_share in bracket(spec['weight']):
        pair = muscle_share*weight_share
        if (muscle, weight) != ('average', 'average'):
            apply_target(f'universal-{gender}-young-{muscle}muscle-{weight}weight', pair)
        apply_target(f'proportions-{gender}-young-{muscle}muscle-{weight}weight-idealproportions', pair)
# MakeHuman's four maxheight targets for these pairs are the same file.
apply_target(f'height-{gender}-young-maxheight', max(spec['height']-0.5, 0.0)/0.5)

# MakeHuman's own CC0 rig weights for this mesh (folded onto this figure's
# bones further on). They cover its joint helpers too, so a shape change
# weighted by them carries the rig along.
rig = json.loads(gzip.open(ASSETS/'makehuman-default-weights.mhw.gz', 'rt').read())
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


def smooth(value):
    value = np.clip(value, 0, 1)
    return value*value*(3-2*value)


metres = 1.7/np.ptp(all_vertices[sorted({i for f in groups['body'] for i in f})][:, 1])
for side in ('L', 'R'):
    prefix = 'l' if side == 'L' else 'r'
    # Graceful hands and feet: each a little smaller about the wrist or ankle.
    for pivot_name, stems, factor in (('hand', ('wrist', 'metacarpal', 'finger'), spec['hands']),
                                      ('ankle', ('foot', 'toe'), spec['feet'])):
        pivot = group_centre(f'{prefix}-{pivot_name}')
        share = rig_share(lambda name: name.endswith('.'+side) and name.split('.')[0].startswith(stems))
        all_vertices += (pivot-all_vertices)*((1-factor)*share)[:, None]
    # Narrower shoulders: each arm moves in towards her, the collarbone half
    # as far.
    if spec['shoulders']:
        arm = rig_share(lambda name: name.endswith('.'+side) and name.split('.')[0].startswith(
            ('shoulder01', 'upperarm', 'lowerarm', 'wrist', 'metacarpal', 'finger')))
        collar_bone = rig_share(lambda name: name == 'clavicle.'+side)
        inward = 1.0 if side == 'L' else -1.0
        all_vertices[:, 0] -= inward*np.clip(arm+0.5*collar_bone, 0, 1)*spec['shoulders']/metres
# A longer neck: everything the head carries rises a little, fading in up
# the neck and away from the shoulders.
neck_base, skull = group_centre('neck'), group_centre('head')
rise = np.clip((all_vertices[:, 1]-neck_base[1])/(skull[1]-neck_base[1]), 0, 1)
rise = rise*rise*(3-2*rise)*np.clip(1-(np.abs(all_vertices[:, 0])-0.05/metres)/(0.05/metres), 0, 1)
all_vertices[:, 1] += rise*spec['neck']/metres
# A small soft jaw: the face narrows a little from the cheekbones to the
# chin, and the neck under it with it.
if spec['jaw']:
    eye_level = group_centre('l-eye')[1]
    down = smooth((eye_level-all_vertices[:, 1])/(0.075/metres))
    above_shoulders = smooth((all_vertices[:, 1]-(eye_level-0.135/metres))/(0.03/metres))
    near = np.abs(all_vertices[:, 0]) < 0.1/metres
    all_vertices[:, 0] *= 1-spec['jaw']*down*above_shoulders*near
eye_level = group_centre('l-eye')[1]
for prefix in ('l', 'r'):
    # Larger eyes, opened a little more than widened, fading out round each
    # eye; the eyeball itself grows evenly.
    centre = group_centre(f'{prefix}-eye')
    offset = all_vertices-centre
    reach = np.linalg.norm(offset, axis=1)/(0.026/metres)
    grow = spec['eyes']*smooth(1-reach)**2
    ball = helpers(f'helper-{prefix}-eye')
    factor = np.column_stack((1+0.8*grow, 1+1.3*grow, 1+0.6*grow))
    factor[ball] = 1+spec['eyes']*0.75
    all_vertices = centre+offset*factor
mouth_centre = group_centre('mouth')
if spec['mouth']:
    # A smaller mouth: the lips draw in towards their middle.
    offset = all_vertices-mouth_centre
    near = smooth(1-np.linalg.norm(offset[:, :2], axis=1)/(0.035/metres))*(offset[:, 2] > -0.01/metres)
    all_vertices[:, 0] -= offset[:, 0]*spec['mouth']*near
if spec['chin']:
    # A shorter lower face: from below the nose to the chin it rises a
    # little towards the eyes, the neck under it following less and less.
    below = smooth((eye_level-0.035/metres-all_vertices[:, 1])/(0.04/metres))
    above_neck = smooth((all_vertices[:, 1]-(eye_level-0.16/metres))/(0.035/metres))
    near = np.abs(all_vertices[:, 0]) < 0.1/metres
    all_vertices[:, 1] += (eye_level-0.035/metres-all_vertices[:, 1])*spec['chin']*below*above_neck*near
ids = sorted({index for face in groups['body'] for index in face})
lookup = {old: index for index, old in enumerate(ids)}
body = all_vertices[ids]
scale = 1.7 / np.ptp(body[:, 1])
origin = np.array([0, body[:, 1].min(), 0])
positions = (body - origin) * scale


def joint(name):
    indices = sorted({index for face in groups['joint-' + name] for index in face})
    return (all_vertices[indices].mean(axis=0) - origin) * scale


def helper_points(name):
    return (all_vertices[sorted({index for face in groups[name] for index in face})]-origin)*scale


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

triangles = face_triangles.copy()


def vertex_normals(vertices, faces):
    result = np.zeros_like(vertices)
    face = np.cross(vertices[faces[:, 1]]-vertices[faces[:, 0]], vertices[faces[:, 2]]-vertices[faces[:, 0]])
    for corner in range(3):
        np.add.at(result, faces[:, corner], face)
    return result/np.maximum(np.linalg.norm(result, axis=1)[:, None], 1e-12)


normals = vertex_normals(positions, triangles)
# Regions keep the same surface and skin weights: skin, top, trousers, hair.
hip_height = joint('pelvis')[1]
neck_height = joint('neck')[1]
hips_joint = (joint('l-upper-leg')+joint('r-upper-leg'))/2
cuffs = [abs(joint(prefix+'-hand')[0])-0.025 for prefix in ('l', 'r')]
ankles = [joint(prefix+'-ankle')[1]+0.02 for prefix in ('l', 'r')]
eye_height = joint('l-eye')[1]
head_centre_z = joint('head')[2]
fitted = spec['outfit'] == 'fitted'
# Her fitted top ends just over the hips; his jacket's body region ends at
# the trouser waist and its skirt hangs on below.
top_hem = hips_joint[1]+0.01 if fitted else hip_height-0.04
HAIRLINES = {'bun': [0.050, 0.050, 0.045, 0.031, 0.012, 0.000, -0.022, -0.045],
             'short': [0.056, 0.063, 0.060, 0.036, 0.012, 0.000, -0.022, -0.042]}


def head_turn(points):
    return np.degrees(np.arctan2(np.abs(points[:, 0]), points[:, 2]-0.02))


def hairline(points):
    """Positive on the hair: from the hairline over the forehead, the temples,
    behind the ears and down to the nape; the ears stay bare."""
    points = np.atleast_2d(points)
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    turn = head_turn(points)
    height = eye_height+np.interp(turn, [0, 20, 45, 65, 85, 105, 125, 180], HAIRLINES[spec['hair']])
    value = y-height
    ears = (y < eye_height+0.002) & (np.abs(x) > 0.070)
    value = np.where(ears, np.minimum(value, 0.070-np.abs(x)), value)
    return np.where(y < 1.44, -1.0, value)


def neckline(points):
    """Positive below the mandarin top's round neckline, a little lower in
    front, where its stand-up collar begins."""
    points = np.atleast_2d(points)
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    front = 0.012*np.clip(1-np.abs(x)/0.07, 0, 1)*np.clip((z-0.02)/0.04, 0, 1)
    return (neck_height-0.008-front)-y


def arm_points(points):
    """The arms in the bind pose: near the shoulder-elbow-hand line, out from
    the trunk."""
    points = np.atleast_2d(points)
    result = np.zeros(len(points), dtype=bool)
    for prefix in ('l', 'r'):
        s, e, h = joint(prefix+'-shoulder'), joint(prefix+'-elbow'), joint(prefix+'-hand')
        mine = (points[:, 0] >= 0) == (prefix == 'l')
        for a, b in ((s, e), (e, h)):
            t = np.clip((points-a) @ (b-a)/np.dot(b-a, b-a), 0, 1)
            near = np.linalg.norm(points-(a+t[:, None]*(b-a)), axis=1) < 0.075
            result |= mine & near & (np.abs(points[:, 0]) > 0.10)
    return result


def sleeve_end(points):
    """Positive on the arm past her cap sleeves, a third of the way down the
    upper arm, across the arm."""
    points = np.atleast_2d(points)
    value = np.full(len(points), -1.0)
    for prefix in ('l', 'r'):
        s, e = joint(prefix+'-shoulder'), joint(prefix+'-elbow')
        axis = (e-s)/np.linalg.norm(e-s)
        mine = arm_points(points) & ((points[:, 0] >= 0) == (prefix == 'l'))
        value[mine] = ((points[mine]-s) @ axis)-0.33*np.linalg.norm(e-s)
    return value


def region_of(points):
    points = np.atleast_2d(points)
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    regions = np.zeros(len(points), dtype=np.uint8)
    # Sleeves continue over the shoulder cap. A horizontal collar cutoff alone
    # leaves isolated bare patches where the arm rises above the neck cutoff.
    covered = (y > top_hem) & ((neckline(points) > 0) | ((np.abs(x) > 0.115) & (y < neck_height+0.025)))
    if fitted:
        arms = arm_points(points)
        regions[covered & ~(arms & (sleeve_end(points) > 0))] = 1
        regions[(y <= top_hem) & ~arms] = 2
    else:
        regions[covered] = 1
        regions[y <= top_hem] = 2
        for cuff in cuffs:
            # Hands hang below the hips in the bind pose; only arms reach this wide.
            regions[(np.abs(x) > cuff) & (y > 0.5)] = 0
    for ankle in ankles:
        regions[y < ankle] = 0
    regions[hairline(points) > 0] = 3
    return regions


# Clean hems: split each triangle that crosses a region boundary exactly
# along the boundary, then give every region its own copy of the shared hem
# vertices. Surface and skin stay continuous.
def plane(axis, value):
    return lambda points: np.atleast_2d(points)[:, axis]-value


planes = [(1, top_hem), (1, neck_height+0.025), (0, 0.115), (0, -0.115)] + [(1, ankle) for ankle in ankles]
if not fitted:
    planes += [(0, cuff) for cuff in cuffs] + [(0, -cuff) for cuff in cuffs]
cuts = [(('plane',)+item, plane(*item)) for item in planes] + [(('neckline',), neckline), (('hairline',), hairline)]
if fitted:
    cuts.append((('sleeve',), sleeve_end))
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
role_of = np.array([item['role'] for item in bones])
head_index = [at for at, item in enumerate(bones) if item['role'] == 3][0]


def outward_faces(vertices, faces, center):
    faces = np.array(faces, dtype=np.int64)
    normal = np.cross(vertices[faces[:, 1]]-vertices[faces[:, 0]], vertices[faces[:, 2]]-vertices[faces[:, 0]])
    flip = np.einsum('ij,ij->i', normal, vertices[faces].mean(axis=1)-center) < 0
    faces[flip] = faces[flip][:, ::-1]
    return faces


def neighbours(faces, count):
    edge = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edge = np.unique(np.concatenate([edge, edge[:, ::-1]]), axis=0)
    return edge, np.maximum(np.bincount(edge[:, 0], minlength=count), 1).astype(np.float64)


def relax(base, normal, lift, faces, steps, pinned=None):
    """Cloth or hair LIFT off the surface BASE, smoothed the way cloth lies:
    it bridges hollows (between the breasts, the small of the back, the
    crotch) but never sinks below LIFT or slides along the surface. PINNED
    vertices keep their lift, so an edge stays on the surface."""
    edge, count = neighbours(faces, len(base))
    height = lift.copy()
    for _ in range(steps):
        shell = base+normal*height[:, None]
        total = np.zeros_like(shell)
        np.add.at(total, edge[:, 0], shell[edge[:, 1]])
        towards = np.einsum('ij,ij->i', total/count[:, None]-shell, normal)
        height = np.maximum(height+0.5*towards, lift)
        if pinned is not None:
            height[pinned] = lift[pinned]
    return base+normal*height[:, None]


# The head. MakeHuman's own eyeballs sit in the sockets under the lids; a
# hair shell rises from nothing at the hairline over the crown.
extras = []
body_count = len(positions)
hair_faces = triangles[np.all(regions[triangles] == 3, axis=1)]
used = np.unique(hair_faces)
p = positions[used]
depth = hairline(p)
top = np.clip((p[:, 1]-eye_height-0.03)/0.07, 0, 1)
back = np.clip((head_centre_z+0.01-p[:, 2])/0.08, 0, 1)
sides = np.clip(np.abs(p[:, 0])/0.07, 0, 1)
above = np.clip((p[:, 1]-eye_height)/0.03, 0, 1)
if spec['hair'] == 'bun':
    # Sleek, a little fuller towards the crown where it gathers into the bun.
    thickness = (0.004+0.006*top+0.005*top*back+0.002*sides*above)*np.clip(depth/0.02, 0, 1)**0.7
else:
    thickness = (0.0035+0.004*top+0.002*back)*np.clip(depth/0.015, 0, 1)**0.8
remap = np.full(len(positions), -1, dtype=np.int64)
remap[used] = np.arange(len(used))
shell_faces = remap[hair_faces]
# Its edge stays on the skin at the hairline, with no crack between them.
shell = relax(p, normals[used], thickness, shell_faces, 12, depth <= 0.0005)
if spec['hair'] == 'bun':
    # A centre parting from the hairline back over the crown: the hair dips
    # to the scalp along a narrow line.
    height = np.einsum('ij,ij->i', shell-p, normals[used])
    front = smooth((p[:, 2]-(head_centre_z-0.05))/0.03)*smooth((p[:, 1]-eye_height-0.035)/0.01)
    height *= 1-0.8*np.exp(-(p[:, 0]/0.0045)**2)*front
    shell = p+normals[used]*height[:, None]
extras.append((shell, vertex_normals(shell, shell_faces), np.full(len(shell), 3), shell_faces))
# A soft hairline: the first few millimetres of hair fade into the skin.
hair_edge = np.clip(1-depth/0.007, 0, 1)**1.5
bun_center = None
if spec['hair'] == 'bun':
    # A neat high bun on the back of the crown.
    rings, segments = 14, 24
    crown_ring = shell[np.abs(shell[:, 1]-(eye_height+0.100)) < 0.008]
    bun_center = np.array([0.0, eye_height+0.100, crown_ring[:, 2].min()+0.006])
    bun_radii = np.array([0.043, 0.037, 0.041])
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
crown = positions[:, 1].max()
for vertices, vertex_normal, vertex_region, faces_of in extras:
    base = len(positions)
    positions = np.vstack([positions, vertices])
    normals = np.vstack([normals, vertex_normal])
    joints = np.vstack([joints, np.tile(np.array([head_index, 0, 0, 0], dtype=np.uint8), (len(vertices), 1))])
    weights = np.vstack([weights, np.tile(np.array([1.0, 0.0, 0.0, 0.0]), (len(vertices), 1))])
    regions = np.concatenate([regions, np.asarray(vertex_region, dtype=np.uint8)])
    triangles = np.vstack([triangles, np.asarray(faces_of, dtype=np.int64)+base])
head_count = len(positions)
softs = np.zeros(len(positions))
softs[body_count:body_count+len(hair_edge)] = hair_edge

# The clothes: shells over the body, skinned by the same rig.
# Regions: 0 skin, 1 top, 2 trousers, 3 hair, 4 trim (the placket's frog knots).


def share(rows, shares, roles):
    return np.sum(shares*np.isin(role_of[rows], roles), axis=1)


arm = share(joints, weights, [4, 5, 6, 7])
trunk_points = (np.arange(len(positions)) < body_count) & (arm < 0.15)
armpit_y = (joint('l-shoulder')[1]+joint('r-shoulder')[1])/2-0.09
hem_y = hips_joint[1]-0.05


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


def nearest_weights(points, near=8, low=None, high=None):
    """Skin weights for cloth away from the surface: the weights of the
    nearest trunk and leg vertices between LOW and HIGH, closer ones counting
    more."""
    low = hem_y-0.12 if low is None else low
    high = waist_y+0.15 if high is None else high
    candidates = np.where(trunk_points[:body_count] & (positions[:body_count, 1] > low) &
                          (positions[:body_count, 1] < high))[0]
    result = np.zeros((len(points), len(bones)))
    for at, point in enumerate(points):
        distance = np.linalg.norm(positions[candidates]-point, axis=1)
        order = np.argsort(distance)[:near]
        share_of = 1/np.maximum(distance[order], 0.005)**2
        result[at] = share_of @ dense_body[candidates[order]]/share_of.sum()
    return result


def strongest_of(dense):
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


def body_shell(faces_of, lift, steps):
    """The body's own triangles FACES_OF, lifted by LIFT (one per vertex of
    the body) and relaxed like cloth; returns the shell and its vertices."""
    used = np.unique(faces_of)
    remap = np.full(len(positions), -1, dtype=np.int64)
    remap[used] = np.arange(len(used))
    shell_faces = remap[faces_of]
    # Lifted along smoothed normals, so sharp creases (the crotch, the
    # armpits) do not fan the cloth out into thin folds that tear in a pose.
    edge, count = neighbours(shell_faces, len(used))
    direction = normals[used].copy()
    for _ in range(8):
        total = np.zeros_like(direction)
        np.add.at(total, edge[:, 0], direction[edge[:, 1]])
        direction = 0.5*direction+0.5*total/count[:, None]
        direction /= np.maximum(np.linalg.norm(direction, axis=1)[:, None], 1e-12)
    q = relax(positions[used], direction, lift[used], shell_faces, steps)
    return used, q, shell_faces


cloth = []  # (points, normals, joints, weights, region, faces, source positions or None, hang, UVs or None)
body_faces = np.all(triangles < body_count, axis=1)
down = np.clip((top_hem-positions[:, 1])/(top_hem-np.mean(ankles)), 0, 1)
if fitted:
    trouser_lift = 0.005+0.012*smooth(down)
    # The fitted top: the body's own surface lifted a little and smoothed
    # the way silk lies, over the chest, the waist and the hips to just
    # below the hip bones, and down a third of each upper arm. Its hem laps
    # over the trousers' waist.
    lap = body_faces & np.all(regions[triangles] == 2, axis=1) & np.all(positions[triangles][:, :, 1] > top_hem-0.025, axis=1)
    top_faces = triangles[(body_faces & np.all(regions[triangles] == 1, axis=1)) | lap]
    lift = np.full(len(positions), 0.0035)
    lift[positions[:, 1] < top_hem+0.002] = trouser_lift[positions[:, 1] < top_hem+0.002]+0.0025
    used, q, faces_of = body_shell(top_faces, lift, 14)
    top_shell = q
    cloth.append((q, vertex_normals(q, faces_of), joints[used], weights[used], 1, faces_of, positions[used],
                  np.zeros(len(q)), None))
    placket_low = (waist_y+armpit_y)/2-0.02
else:
    hang = np.zeros((len(grid_y), K))
    for j, h in enumerate(grid_y):
        s = slab(h)
        hang[j] = (np.column_stack((s[:, 0], s[:, 2]-trunk_z(h))) @ directions.T).max(axis=0)
    # Cloth falls straight from the widest place above it, under the armpits.
    top_row = int(np.searchsorted(grid_y, armpit_y))
    for j in range(top_row-1, -1, -1):
        hang[j] = np.maximum(hang[j], hang[j+1])
    # Soft cloth settles part of the way back onto him below the widest place.
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

    # The jacket: the body's own surface lifted off it over the chest and
    # along the long sleeves, falling wider towards the wrist.
    top_faces = triangles[body_faces & np.all(regions[triangles] == 1, axis=1)]
    top_faces = top_faces[(positions[top_faces][:, :, 1].min(axis=1) > waist_y-0.03) | (arm[top_faces].mean(axis=1) > 0.5)]
    used = np.unique(top_faces)
    p, n = positions[used], normals[used]
    bust_y = slab((waist_y+armpit_y)/2, half=0.06)[:, 1][np.argmax(slab((waist_y+armpit_y)/2, half=0.06)[:, 2])]
    sleeve = smooth((arm[used]-0.2)/0.6)
    lift = np.interp(p[:, 1], [waist_y, bust_y, neck_height-0.04], [0.010, 0.007, 0.005])*(1-sleeve)
    lift += (0.007+0.016*arm_progress(p)**1.5)*sleeve
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
    # Loose cloth hides the muscles under it: smooth the jacket, never
    # letting it sink back towards him.
    q = relax(q, vertex_normals(q, faces_of), np.zeros(len(q)), faces_of, 30)
    top_shell = q
    cloth.append((q, vertex_normals(q, faces_of), joints[used], weights[used], 1, faces_of, p, np.zeros(len(q)), None))

    # The jacket's skirt, from just above the waist to below the hip bones,
    # slit at both sides for its lower third.
    rows_y = np.linspace(waist_y+0.035, hem_y, 12)
    fall = (rows_y[0]-rows_y)/(rows_y[0]-rows_y[-1])
    skirt = []
    for y, f in zip(rows_y, fall):
        r = hanging_radius(angles, np.full(K, y))+0.010+0.012*f**1.5
        skirt.append(np.column_stack((np.sin(angles)*r, np.full(K, y), trunk_z(y)+np.cos(angles)*r)))
    skirt = np.vstack(skirt)
    faces_of = grid_faces(len(rows_y), K, True)
    side_of = np.abs(np.sin(angles[faces_of[:, 0] % K]+np.pi/K)) > 0.97
    faces_of = facing_out(skirt, faces_of[~(side_of & (faces_of[:, 0]//K >= 2*len(rows_y)//3))], trunk_axis)
    dense = nearest_weights(skirt).reshape(len(rows_y), K, len(bones))
    for _ in range(2):
        dense = 0.5*dense+0.25*np.roll(dense, 1, axis=1)+0.25*np.roll(dense, -1, axis=1)
    # The hand-over from the pelvis to the thighs spreads down the whole hem,
    # so a lifted leg draws it out gradually instead of tearing a band.
    for _ in range(12):
        dense[1:-1] = 0.5*dense[1:-1]+0.25*dense[:-2]+0.25*dense[2:]
        dense[-1] = 0.5*dense[-1]+0.5*dense[-2]
    rows, shares = strongest_of(dense.reshape(-1, len(bones)))
    cloth.append((skirt, vertex_normals(skirt, faces_of), rows, shares, 1, faces_of, None, np.repeat(fall, K), None))
    placket_low = hem_y+0.004

# The stand-up mandarin collar round the base of the neck, leaning in a
# little at its top.
collar_y = neck_height+np.array([-0.012, 0.006, 0.022])
collar_angles = np.arange(48)*2*np.pi/48
dip = 0.013*np.maximum(np.cos(collar_angles), 0)**2
collar = []
neck_points = positions[:body_count][arm[:body_count] < 0.15]
for y, give, follow in zip(collar_y, (0.006, 0.004, 0.002), (1.0, 0.6, 0.35)):
    ring = []
    for angle, low in zip(collar_angles, dip*follow):
        at = y-low
        s = neck_points[np.abs(neck_points[:, 1]-at) < 0.006]
        middle = (s[:, 2].min()+s[:, 2].max())/2
        reach = (np.column_stack((s[:, 0], s[:, 2]-middle)) @ np.array([np.sin(angle), np.cos(angle)])).max()
        ring.append([np.sin(angle)*(reach+give), at, middle+np.cos(angle)*(reach+give)])
    collar.append(np.array(ring))
collar = np.vstack(collar)
faces_of = facing_out(collar, grid_faces(3, 48, True), lambda m: np.column_stack((np.zeros(len(m)), m[:, 1], np.full(len(m), collar[:, 2].mean()))))
rows, shares = strongest_of(nearest_weights(collar, low=neck_height-0.05, high=neck_height+0.05))
cloth.append((collar, vertex_normals(collar, faces_of), rows, shares, 1, faces_of, None, np.zeros(len(collar)), None))

# The placket down the front with its frog-knot buttons, just over the top:
# to the middle of her chest, all the way down his jacket.
front = top_shell[np.abs(top_shell[:, 0]) < 0.01]
if not fitted:
    front = np.vstack([front, skirt[np.abs(skirt[:, 0]) < 0.01]])
placket_y = np.arange(neck_height-0.012, placket_low, -0.01)
reach = np.array([front[np.abs(front[:, 1]-y) < 0.012][:, 2].max() for y in placket_y])
placket = np.vstack([[[side*0.015, y, z+0.0025] for side in (-1, 1)] for y, z in zip(placket_y, reach)])
faces_of = facing_out(placket, grid_faces(len(placket_y), 2, False), trunk_axis)
rows, shares = strongest_of(nearest_weights(placket, low=placket_low-0.12, high=neck_height+0.02))
if fitted:
    placket_hang = np.zeros(len(placket))
else:
    placket_hang = np.repeat(np.clip((rows_y[0]-placket_y)/(rows_y[0]-rows_y[-1]), 0, 1), 2)
placket_uv = np.column_stack((np.tile([0.0, 1.0], len(placket_y)), np.repeat((placket_y[0]-placket_y)/0.045, 2)))
cloth.append((placket, vertex_normals(placket, faces_of), rows, shares, 4, faces_of, None, placket_hang, placket_uv))

# The trousers: the legs' surface lifted off them. Hers are slim and fall
# straight to the ankle; his fall wide and gather again at the ankle.
leg_faces = triangles[body_faces & np.all(regions[triangles] == 2, axis=1)]
if fitted:
    used, q, faces_of = body_shell(leg_faces, trouser_lift, 30)
else:
    # Smoothed like the rest, so the crotch is bridged rather than lifted
    # into thin folds that tear when he folds forward.
    lift = 0.010+0.028*smooth(down/0.75)-0.020*smooth((down-0.85)/0.15)
    lift *= 0.4+0.6*smooth((np.abs(positions[:, 0])-0.02)/0.05)
    used, q, faces_of = body_shell(leg_faces, lift, 30)
cloth.append((q, vertex_normals(q, faces_of), joints[used], weights[used], 2, faces_of, positions[used],
              np.zeros(len(q)), None))

# Texture coordinates follow the form: the trunk and the head are wrapped
# about the vertical, each arm and leg about its own length.
CLOTH_TILE = 0.30
HAIR_TILE = 0.18


def trunk_uv(points):
    turn = np.abs(np.arctan2(points[:, 0], points[:, 2]-trunk_z(points[:, 1])))/np.pi
    return np.column_stack((turn*0.45/CLOTH_TILE, points[:, 1]/CLOTH_TILE))


def head_uv(points):
    turn = np.abs(np.arctan2(points[:, 0], points[:, 2]-head_centre_z))/np.pi
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
# Hair runs from the hairline back to the bun, or from the crown's whorl.
hair = regions == 3
sweep = bun_center if bun_center is not None else np.array([0.0, eye_height+0.105, head_centre_z-0.045])
swept = positions[hair]-sweep
uvs[hair] = np.column_stack((np.abs(np.arctan2(swept[:, 0], swept[:, 1]))/np.pi*0.25/HAIR_TILE,
                             np.linalg.norm(swept, axis=1)/HAIR_TILE))
for points_of, vertex_normal, rows, shares, region, faces_of, source_of, hanging, given_uv in cloth:
    base = len(positions)
    if given_uv is not None:
        uv = given_uv
    elif source_of is None:
        uv = trunk_uv(points_of)
    else:
        uv = wrapped_uv(source_of, rows, shares)
    positions = np.vstack([positions, points_of])
    normals = np.vstack([normals, vertex_normal])
    joints = np.vstack([joints, np.asarray(rows, dtype=np.uint8)])
    weights = np.vstack([weights, shares])
    regions = np.concatenate([regions, np.full(len(points_of), region, dtype=np.uint8)])
    triangles = np.vstack([triangles, faces_of+base])
    uvs = np.vstack([uvs, uv])
    hangs = np.concatenate([hangs, hanging])
    softs = np.concatenate([softs, np.zeros(len(points_of))])

# The face is drawn in face.webp, which lies on the head as seen from the
# front: FACE_SIZE metres square about the middle of the face. Its features
# are drawn on the mesh's own: the lids' lash lines, the eyeballs and the
# mouth between the teeth.
FACE_SIZE = 0.22
face_low = np.array([-FACE_SIZE/2, eye_height-0.14])
details = (positions[:, :2]-face_low)/FACE_SIZE
x, y = positions[:, 0], positions[:, 1]
oval = ((x/0.080)**2+((y-eye_height+0.02)/0.105)**2)**0.5
mask = smooth((normals[:, 2]-0.10)/0.4)*smooth((1.0-oval)/0.25)*smooth(-hairline(positions)/0.006)
mask *= (role_of[joints[:, 0]] == 3) & (regions == 0)
details[mask <= 0] = 0.0
# Cloth's detail is how freely it hangs from the waist: 0 at the waist, 1
# at the jacket's hem; the hair's is how far it fades into the skin.
details[regions != 0] = np.column_stack((hangs, np.zeros(len(hangs))))[regions != 0]
details[regions == 3] = np.column_stack((softs, np.zeros(len(softs))))[regions == 3]
masks = np.rint(np.clip(mask, 0, 1)*255).astype(np.int64)


def draw_face(path):
    """Draws the face as a clean, flat colour map over the skin colour."""
    from PIL import Image, ImageDraw, ImageFilter
    size, over = 1024, 2
    canvas = size*over
    skin = colour(spec['colours']['skin'])

    def pixel(point):
        return ((point[0]-face_low[0])/FACE_SIZE*canvas, (1-(point[1]-face_low[1])/FACE_SIZE)*canvas)

    def metres(value):
        return value/FACE_SIZE*canvas

    layers = []

    def layer(fill, alpha, draw_with, blur=0.0):
        mask_image = Image.new('L', (canvas, canvas), 0)
        draw_with(ImageDraw.Draw(mask_image))
        if blur:
            mask_image = mask_image.filter(ImageFilter.GaussianBlur(metres(blur)))
        layers.append((colour(fill) if isinstance(fill, str) else fill, alpha, np.asarray(mask_image, dtype=np.float64)/255))

    def stroke(points, widths):
        def draw_with(draw):
            for at in range(len(points)-1):
                a, b = pixel(points[at]), pixel(points[at+1])
                w = metres((widths[at]+widths[at+1])/2)
                draw.line([a, b], fill=255, width=max(1, int(round(w))))
                draw.ellipse([b[0]-w/2, b[1]-w/2, b[0]+w/2, b[1]+w/2], fill=255)
        return draw_with

    female = spec['gender'] == 'female'
    for prefix, sign in (('l', 1.0), ('r', -1.0)):
        eye = helper_points(f'helper-{prefix}-eye')
        centre = eye.mean(axis=0)
        margins = []
        for strip in (f'helper-{prefix}-eyelashes-2', f'helper-{prefix}-eyelashes-1'):
            lashes = helper_points(strip)
            root = lashes[np.argsort(np.linalg.norm(lashes-centre, axis=1))[:len(lashes)//2]]
            # The lid's edge: a smooth curve through the lash roots.
            across = np.linspace(root[:, 0].min(), root[:, 0].max(), 24)
            line = np.column_stack([across]+[np.polyval(np.polyfit(root[:, 0], root[:, axis], 3), across)
                                             for axis in (1, 2)])
            margins.append(line if sign > 0 else line[::-1])
        upper, lower = margins
        # The opening between the lids, closed at both corners.
        inner = min(upper[:, 0].min(), lower[:, 0].min()) if sign > 0 else max(upper[:, 0].max(), lower[:, 0].max())
        outline = list(upper)+list(lower[::-1])
        opening = [pixel(point) for point in outline]
        layer('#f6f1ec', 1.0, lambda draw: draw.polygon(opening, fill=255), 0.0002)
        iris_centre = np.array([centre[0]+sign*0.0004, (upper[:, 1].max()+lower[:, 1].min())/2+0.0006])
        iris = 0.0056 if female else 0.0052

        def disc(point, radius):
            c = pixel(point)
            r = metres(radius)
            return lambda draw: draw.ellipse([c[0]-r, c[1]-r, c[0]+r, c[1]+r], fill=255)

        clip = Image.new('L', (canvas, canvas), 0)
        ImageDraw.Draw(clip).polygon(opening, fill=255)
        clip = np.asarray(clip.filter(ImageFilter.GaussianBlur(metres(0.0002))), dtype=np.float64)/255
        for fill, radius, alpha in ((spec['colours']['iris'], iris, 1.0), ('#5c3a27', iris*0.72, 0.55),
                                    ('#0c0908', 0.0024, 1.0)):
            start = len(layers)
            layer(fill, alpha, disc(iris_centre, radius), 0.0002)
            fill_of, alpha_of, mask_of = layers[start]
            layers[start] = (fill_of, alpha_of, mask_of*clip)
        for offset, radius in (((-0.0016*sign, 0.0018), 0.0009), ((0.0017*sign, -0.0014), 0.00045)):
            start = len(layers)
            layer('#ffffff', 0.9, disc(iris_centre+np.array(offset), radius), 0.0001)
            fill_of, alpha_of, mask_of = layers[start]
            layers[start] = (fill_of, alpha_of, mask_of*clip)
        # Lash lines: the upper thick and dark, flicking up a little past the
        # outer corner; the lower soft.
        span = np.abs(upper[:, 0]-inner)/max(np.ptp(upper[:, 0]), 1e-6)
        thick = (0.0008+0.0007*span) if female else (0.0006+0.0003*span)
        line = list(upper)
        if female:
            outer = upper[np.argmax(np.abs(upper[:, 0]-inner))]
            line.append(outer+np.array([sign*0.0028, 0.0013, 0.0]))
            thick = np.append(thick, 0.0004)
        layer(spec['colours']['lashes'], 1.0, stroke(line, thick), 0.00012)
        lower_span = np.abs(lower[:, 0]-inner)/max(np.ptp(lower[:, 0]), 1e-6)
        layer('#6b4a3e', 0.55, stroke(list(lower), 0.00025+0.0002*lower_span), 0.00015)
        # A soft fold over the upper lid.
        crease = upper[1:-1]+np.array([0.0, 0.0024, 0.0])
        layer('#b98c7a', 0.35 if female else 0.25, stroke(list(crease), np.full(len(crease), 0.0003)), 0.0003)
        # The brow.
        top = upper[:, 1].max()
        brow = np.array([[inner-sign*0.0025, top+0.0080], [centre[0]+sign*0.002, top+0.0108],
                         [centre[0]+sign*0.0115, top+0.0108], [centre[0]+sign*0.0185, top+0.0070]])
        brow = np.array([np.interp(t, [0, 1, 2, 3], brow[:, 0]) for t in np.linspace(0, 3, 16)]), \
            np.array([np.interp(t, [0, 1, 2, 3], brow[:, 1]) for t in np.linspace(0, 3, 16)])
        brow = np.column_stack(brow)
        widths = np.linspace(0.0021, 0.0008, len(brow)) if female else np.linspace(0.0034, 0.0020, len(brow))
        layer(spec['colours']['brows'], 0.85 if female else 0.92, stroke(list(brow), widths), 0.0005)
        if female and spec['colours']['blush']:
            cheek = pixel(np.array([centre[0]+sign*0.006, centre[1]-0.026]))
            rx, ry = metres(0.016), metres(0.010)
            layer(spec['colours']['blush'], 0.30,
                  lambda draw: draw.ellipse([cheek[0]-rx, cheek[1]-ry, cheek[0]+rx, cheek[1]+ry], fill=255), 0.006)
    # The lips, on the line where the teeth meet.
    upper_teeth, lower_teeth = helper_points('helper-upper-teeth'), helper_points('helper-lower-teeth')
    mouth = (upper_teeth[:, 1].min()+lower_teeth[:, 1].max())/2+0.001
    half = 0.0205 if female else 0.0235

    def lips(draw):
        upper_lip = [(-half, 0.0), (-half*0.55, 0.0032), (-0.0035, 0.0052), (0.0, 0.0040), (0.0035, 0.0052),
                     (half*0.55, 0.0032), (half, 0.0)]
        lower_lip = [(half, 0.0), (half*0.55, -0.0050), (0.0, -0.0066), (-half*0.55, -0.0050)]
        draw.polygon([pixel(np.array([x, mouth+y])) for x, y in upper_lip+lower_lip], fill=255)

    layer(spec['colours']['lips'], 0.85 if female else 0.45, lips, 0.0005)
    layer('#9c4b56' if female else '#8f5c55', 0.6,
          stroke([np.array([x, mouth+0.0006*(1-(x/half)**2)]) for x in np.linspace(-half*0.95, half*0.95, 15)],
                 np.full(15, 0.0005)), 0.0002)
    if female:
        shine = pixel(np.array([0.003, mouth-0.0035]))
        rx, ry = metres(0.0045), metres(0.0012)
        layer('#ffffff', 0.25, lambda draw: draw.ellipse([shine[0]-rx, shine[1]-ry, shine[0]+rx, shine[1]+ry],
                                                         fill=255), 0.0008)
    picture = np.tile(skin, (canvas, canvas, 1))
    for fill, alpha, mask_of in layers:
        weight = (mask_of*alpha)[:, :, None]
        picture = picture*(1-weight)+fill*weight
    image = Image.fromarray(np.clip(picture, 0, 255).astype(np.uint8)).resize((size, size), Image.LANCZOS)
    image.save(path, quality=92, method=6)


def draw_trim(path):
    """The placket: a strip of the top's colour edged with fine piping, one
    frog knot to each repeat."""
    from PIL import Image, ImageDraw, ImageFilter
    size = 512
    background = colour(spec['colours']['top'])*0.92
    knot = colour(spec['colours']['knot'])
    mask_image = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask_image)
    draw.rounded_rectangle([size*0.10, size*0.44, size*0.90, size*0.56], radius=size*0.06, fill=255)
    for at in (0.30, 0.70):
        draw.ellipse([size*(at-0.10), size*0.38, size*(at+0.10), size*0.62], outline=255, width=int(size*0.045))
    draw.ellipse([size*0.41, size*0.41, size*0.59, size*0.59], fill=255)
    draw.line([(size*0.04, 0), (size*0.04, size)], fill=255, width=int(size*0.025))
    draw.line([(size*0.96, 0), (size*0.96, size)], fill=255, width=int(size*0.025))
    weight = np.asarray(mask_image.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float64)[:, :, None]/255
    picture = background*(1-weight)+knot*weight
    Image.fromarray(np.clip(picture, 0, 255).astype(np.uint8)).resize((256, 256), Image.LANCZOS).save(
        path, quality=92, method=6)


def draw_hair(path):
    """Hair: its colour with soft, faint lighter and darker strands along
    the texture's height."""
    from PIL import Image
    size = 256
    across = np.arange(size)/size
    random = np.random.default_rng(7)
    shade = np.zeros(size)
    for cycles, amount in ((5, 0.05), (11, 0.04), (19, 0.03), (31, 0.025), (47, 0.02)):
        shade += amount*np.sin(2*np.pi*(cycles*across+random.random()))
    picture = colour(spec['colours']['hair'])[None, None, :]*(1+shade)[None, :, None]
    Image.fromarray(np.clip(np.repeat(picture, size, axis=0), 0, 255).astype(np.uint8)).save(path, lossless=True)


def draw_plain(path, text):
    from PIL import Image
    Image.fromarray(np.tile(colour(text), (32, 32, 1)).astype(np.uint8)).save(path, lossless=True)


# The body under the clothes never shows: drop it, keeping the skin near
# the cuffs, the collar and the hems, where it can be seen inside. Fewer
# triangles to skin, upload and draw every frame.
corners = positions[triangles]
body_face = np.all(triangles < body_count, axis=1)
face_arm = share(joints, weights, [4, 5, 6, 7])[triangles].mean(axis=1)
leg_down = np.clip((top_hem-corners[:, :, 1].min(axis=1))/(top_hem-np.mean(ankles)), 0, 1)
hidden_legs = (regions[triangles[:, 0]] == 2) & (leg_down < 0.8)
if fitted:
    near_sleeve = sleeve_end(corners.reshape(-1, 3)).reshape(-1, 3).max(axis=1) > -0.03
    hidden_top = (regions[triangles[:, 0]] == 1) & ~near_sleeve & \
        (corners[:, :, 1].max(axis=1) < neck_height-0.05) & (corners[:, :, 1].min(axis=1) > top_hem+0.03)
else:
    progress = arm_progress(corners.reshape(-1, 3)).reshape(-1, 3).max(axis=1)
    hidden_top = (regions[triangles[:, 0]] == 1) & ((face_arm < 0.5) | (progress < 0.8)) & \
        (corners[:, :, 1].max(axis=1) < neck_height-0.05) & ((face_arm >= 0.5) | (corners[:, :, 1].min(axis=1) > waist_y))
# The scalp lies under the hair shell, which starts on it at the hairline.
hidden_scalp = np.all(regions[triangles] == 3, axis=1)
triangles = triangles[~(body_face & (hidden_top | hidden_legs | hidden_scalp))]
kept = np.unique(triangles)
renumber = np.full(len(positions), -1, dtype=np.int64)
renumber[kept] = np.arange(len(kept))
triangles = renumber[triangles]
positions, normals, uvs, details = positions[kept], normals[kept], uvs[kept], details[kept]
joints, weights, regions, masks = joints[kept], weights[kept], regions[kept], masks[kept]
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
output = args.output.resolve()/args.character
output.mkdir(parents=True, exist_ok=True)
(output/'anatomy.bin').write_bytes(blob)
for name in ('skin', 'top', 'trousers'):
    draw_plain(output/f'{name}.webp', spec['colours'][name])
draw_hair(output/'hair.webp')
draw_trim(output/'trim.webp')
draw_face(output/'face.webp')
metadata = {'format': 'PFIG0002', 'character': args.character, 'vertices': len(positions),
            'triangles': len(triangles), 'bones': len(bones), 'bytes': len(blob),
            'sha256': hashlib.sha256(blob).hexdigest(), 'regions': ['skin', 'top', 'trousers', 'hair', 'trim'],
            'shape': {key: spec[key] for key in ('races', 'weight', 'muscle', 'height', 'hands', 'feet', 'neck',
                                                  'shoulders', 'jaw', 'outfit', 'hair')},
            'face': {'size_metres': FACE_SIZE, 'low': [round(float(v), 5) for v in face_low]},
            'source': 'https://github.com/makehumancommunity/makehuman/blob/a8bc2d54ff0ac92e78ff71431b1023eda42bf482/makehuman/data/3dobjs/base.obj',
            'license': 'CC0-1.0', 'bone_names': [f"{b['role']}/{b['side']}/{b['finger']}/{b['segment']}" for b in bones]}
(output/'anatomy.json').write_text(json.dumps(metadata, indent=2)+'\n')
print(f"{args.character}: {len(positions)} vertices, {len(triangles)} triangles, {len(bones)} bones; {len(blob)} bytes")
# The eyes sit halfway down the head.
print(f"waist {waist_y:.3f} armpit {armpit_y:.3f} top hem {top_hem:.3f}; "
      f"{1.7/(2*(crown-eye_height)):.2f} heads tall; shoulders {joint('l-shoulder')[0]-joint('r-shoulder')[0]:.3f} m apart")
