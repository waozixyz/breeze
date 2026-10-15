// Exports the course for Inner Breeze: the key poses and timing the app
// samples and solves itself, the two painted characters, the words to
// translate, and a reference for the app's parity test.
//
//   node tools/export-app.mjs
//
// Writes (paths from the Inbe repository root):
//   assets/practices/taichi/course.bin        keys, course outline, rigs, parts
//   assets/practices/taichi/<character>/*.png  painted parts, scaled down
//   design/tai-chi/text/en.txt                 course words as locale entries
//   tests/fixtures/tai-chi-reference.json      sampled poses, joints, pieces
//
// course.bin is little-endian. Every string is a u16 byte length and UTF-8
// bytes; a string index of -1 means none. Sections in order:
//   "TCH2"
//   strings: u32 count, strings (locale keys and asset paths)
//   key sets: u32 count; each u32 key count, then per key:
//     f32 t, s32 cue, f32 seconds the cue's words need on screen (0 without
//     a cue), u8 look kind (0 ahead, 1 left hand, 2 right hand, 3 angles
//     only), 3 pad bytes, f32 look yaw (degrees), f32 look pitch (degrees),
//     f32[CHANNELS.length] channels
//   characters: u32 count; each s32 id, s32 name, f32[RIG_FIELDS.length] rig,
//     u32 image count; per image s32 role, s32 path, f32 width, f32 height,
//     f32[16] points (8 named points by role, see IMAGE_POINTS), f32[4]
//     values (anterior, thickness, sign, across thumb)
//   outline: u32 module count; each s32 title, u32 lesson count; each s32
//     title, s32 subtitle, s32 summary, u32 item count; each s32 id,
//     s32 title, s32 version, u8 kind, u8 view, u8 mirror, u8 source
//     (0 a slice of key set 0, the form; 1 a whole key set), u8 words (0
//     the movement's name, 1 each step's words, slowed to be read), s32 first,
//     s32 last (key indices of the slice, or the key set and -1), f32 scale,
//     f32 hold after each cue, f32 duration, u32 mark count; each s32
//     title, f32 start, f32 end

import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { buildCourse, readingTime, timelineFor } from '../src/course.js'
import { createPaintedLayout, imageFromSpec, pieceVertices, pieceImage } from '../src/painted/layout.js'
import { makeRig } from '../src/rig.js'
import { solvePose } from '../src/solve.js'
import { STUDIO_ROOT } from './serve.mjs'

const INBE_ROOT = resolve(STUDIO_ROOT, '..', '..')
const ASSET_DIR = join(INBE_ROOT, 'assets', 'practices', 'taichi')
const TEXT_FILE = join(STUDIO_ROOT, 'text', 'en.txt')
const REFERENCE_FILE = join(INBE_ROOT, 'tests', 'fixtures', 'tai-chi-reference.json')
// Painted parts are drawn about two thirds of their painted size on a
// phone. Smaller copies with 256-colour palettes keep the package small;
// at that size the palette is not visible.
const PART_SCALE = 0.65

const CHARACTERS = [
    { id: 'monk', dir: 'monk', name: 'Tibetan monk' },
    { id: 'tibetanWoman', dir: 'tibetan-woman', name: 'Tibetan woman' },
]

const KINDS = ['drill', 'lesson', 'demo', 'breakdown', 'follow', 'full']
const VIEWS = ['front', 'behind', 'side', 'threeQuarter']

export const RIG_FIELDS = ['scale', 'height', 'ankleHeight', 'heelBack', 'ball', 'toeTip', 'footHalfWidth', 'shin',
    'thigh', 'hipHalfWidth', 'hipDrop', 'spine0', 'spine1', 'spine2', 'neck', 'headHeight', 'shoulderHalfWidth',
    'shoulderDrop', 'upperArm', 'foreArm', 'palmOffset', 'handLength', 'legLength', 'armLength', 'hipHeight',
    'pelvisHeight']

// The pose channels in the order the app reads them: the timeline's body
// channels, then its hand channels.
export const CHANNELS = ['facing', 'load', 'sink', 'hips', 'chest', 'lean', 'bend', 'shiftF', 'shiftS']
for (const side of ['L', 'R']) {
    for (const field of ['yaw', 'pitch', 'lift', 'x', 'z']) {
        CHANNELS.push(`foot${side}.${field}`)
    }
    for (let index = 0; index < 3; index += 1) {
        CHANNELS.push(`shape${side}${index}`)
    }
}
for (const side of ['L', 'R']) {
    for (const field of ['at', 'palm', 'fingers', 'elbow']) {
        for (let index = 0; index < 3; index += 1) {
            CHANNELS.push(`${side}.${field}${index}`)
        }
    }
}

function channelValue(pose, name) {
    if (name === 'shiftF') {
        return pose.shift[0]
    }
    if (name === 'shiftS') {
        return pose.shift[1]
    }
    let match = /^foot([LR])\.(\w+)$/.exec(name)
    if (match) {
        return pose.feet[match[1]][match[2]]
    }
    match = /^shape([LR])(\d)$/.exec(name)
    if (match) {
        return pose.hands[match[1]].shape[Number(match[2])]
    }
    match = /^([LR])\.(at|palm|fingers|elbow)(\d)$/.exec(name)
    if (match) {
        return pose.hands[match[1]][match[2]][Number(match[3])]
    }
    return pose[name]
}

// Named points per image role, in slot order.
const IMAGE_POINTS = {
    head: ['neck', 'crown'],
    torso: ['neck', 'hip', 'shoulder0', 'shoulder1'],
    limb: ['root', 'end'],
    hand: ['wrist', 'tip'],
    shoeSide: ['heel', 'toe'],
    shoe: ['ankle'],
}

// --- Strings ---------------------------------------------------------------

const strings = []
const stringIndex = new Map()
function stringId(value) {
    if (value === null || value === undefined) {
        return -1
    }
    if (!stringIndex.has(value)) {
        stringIndex.set(value, strings.length)
        strings.push(value)
    }
    return stringIndex.get(value)
}

// Course words become locale keys named after their English text.
const words = new Map()
function textKey(english) {
    if (english === null || english === undefined) {
        return -1
    }
    const key = `tai_chi_text_${createHash('sha1').update(english).digest('hex').slice(0, 8)}`
    const known = words.get(key)
    if (known !== undefined && known !== english) {
        throw new Error(`Text key collision: "${known}" and "${english}"`)
    }
    words.set(key, english)
    return stringId(key)
}

// --- Binary writer -----------------------------------------------------------

class Writer {
    constructor() {
        this.parts = []
    }

    bytes(buffer) {
        this.parts.push(buffer)
    }

    u8(value) {
        const buffer = Buffer.alloc(1)
        buffer.writeUInt8(value)
        this.bytes(buffer)
    }

    u16(value) {
        const buffer = Buffer.alloc(2)
        buffer.writeUInt16LE(value)
        this.bytes(buffer)
    }

    u32(value) {
        const buffer = Buffer.alloc(4)
        buffer.writeUInt32LE(value)
        this.bytes(buffer)
    }

    s32(value) {
        const buffer = Buffer.alloc(4)
        buffer.writeInt32LE(value)
        this.bytes(buffer)
    }

    f32(value) {
        if (!Number.isFinite(value)) {
            throw new Error(`Not a finite number: ${value}`)
        }
        const buffer = Buffer.alloc(4)
        buffer.writeFloatLE(value)
        this.bytes(buffer)
    }

    string(value) {
        const encoded = Buffer.from(value, 'utf8')
        if (encoded.length > 65535) {
            throw new Error('String too long')
        }
        this.u16(encoded.length)
        this.bytes(encoded)
    }

    finish() {
        return Buffer.concat(this.parts)
    }
}

// --- Course ------------------------------------------------------------------

const course = buildCourse()
const form = course.form
const keySets = [form.keys]
const narrationWords = new Set()

function lookFields(look) {
    if (!look || look === 'fwd') {
        return { kind: 0, yaw: 0, pitch: 0 }
    }
    if (look === 'L' || look === 'R') {
        return { kind: look === 'L' ? 1 : 2, yaw: 0, pitch: 0 }
    }
    if (look.hand) {
        return { kind: look.hand === 'L' ? 1 : 2, yaw: look.yaw ?? 0, pitch: look.pitch ?? 0 }
    }
    return { kind: 3, yaw: look.yaw ?? 0, pitch: look.pitch ?? 0 }
}

// How an item's keys come from the form or from its own key set.
function itemSource(item) {
    const id = item.id
    if (item.kind === 'drill' || item.kind === 'follow') {
        keySets.push(timelineFor(item).keys)
        return { source: 1, first: keySets.length - 1, last: -1, scale: 1, hold: 0 }
    }
    if (item.kind === 'full') {
        return { source: 0, first: 0, last: form.keys.length - 1, scale: id === 'full/slow' ? 1.5 : 1, hold: 0 }
    }
    const lessonNumber = Number(/^lesson-(\d+)\//.exec(id)[1])
    const moves = form.moves.filter((move) => move.lesson === lessonNumber)
    if (item.kind === 'lesson') {
        return { source: 0, first: moves[0].startIndex, last: moves[moves.length - 1].endIndex, scale: 1, hold: 0 }
    }
    const moveId = id.split('/')[1]
    const move = moves.find((candidate) => candidate.id === moveId)
    if (item.kind === 'breakdown') {
        return { source: 0, first: move.startIndex, last: move.endIndex, scale: 1.7, hold: 1.6 }
    }
    return { source: 0, first: move.startIndex, last: move.endIndex, scale: 1, hold: 0 }
}

const outline = course.modules.map((module) => ({
    title: textKey(module.title),
    lessons: module.lessons.map((lesson) => ({
        title: textKey(lesson.title),
        subtitle: textKey(lesson.subtitle ?? null),
        summary: textKey(lesson.summary ?? null),
        items: lesson.items.map((item) => {
            const { timeline, marks, keys } = timelineFor(item)
            if (item.cues === 'steps') {
                for (const key of keys) {
                    if (key.cue) narrationWords.add(key.cue)
                }
            } else {
                for (const mark of marks) {
                    if (mark.title) narrationWords.add(mark.title)
                }
            }
            return {
                id: stringId(item.id),
                title: textKey(item.title),
                version: textKey(item.version ?? null),
                kind: KINDS.indexOf(item.kind),
                view: VIEWS.indexOf(item.view ?? 'behind'),
                mirror: item.mirror ? 1 : 0,
                stepWords: item.cues === 'steps' ? 1 : 0,
                ...itemSource(item),
                duration: timeline.duration,
                marks: marks.map((mark) => ({ title: textKey(mark.title), start: mark.start, end: mark.end })),
            }
        }),
    })),
}))
for (const set of keySets) {
    for (const key of set) {
        if (key.cue) {
            textKey(key.cue)
        }
    }
}

// --- Characters ----------------------------------------------------------------

function pngSize(path) {
    const data = readFileSync(path)
    return { width: data.readUInt32BE(16), height: data.readUInt32BE(20) }
}

function loadCharacter(entry) {
    const base = join(STUDIO_ROOT, 'characters', entry.dir)
    const definition = JSON.parse(readFileSync(join(base, 'character.json'), 'utf8'))
    const images = []
    const image = (role, kind, spec) => {
        const size = pngSize(join(base, spec.file))
        const { file, ...points } = spec
        const described = imageFromSpec(points, size.width, size.height)
        images.push({ role, kind, file, size, described })
        return described
    }
    const group = (prefix, kind, specs) => Object.fromEntries(Object.entries(specs)
        .filter(([, spec]) => spec && typeof spec === 'object' && spec.file)
        .map(([name, spec]) => [name, image(`${prefix}.${name}`, kind(name), spec)]))
    const character = {
        head: group('head', () => 'head', definition.head.views),
        torso: group('torso', () => 'torso', definition.torso.views),
        arm: image('arm', 'limb', definition.arm),
        leg: image('leg', 'limb', definition.leg),
        hands: group('hands', () => 'hand', definition.hands),
        shoes: group('shoes', (name) => (name === 'outer' || name === 'inner' ? 'shoeSide' : 'shoe'), definition.shoes),
    }
    return { definition, base, character, images }
}

const characters = CHARACTERS.map((entry) => ({ ...entry, ...loadCharacter(entry), rig: makeRig(entry.id) }))

// Scaled copies of the painted parts.
for (const entry of characters) {
    const target = join(ASSET_DIR, entry.dir)
    mkdirSync(target, { recursive: true })
    const script = `
import sys
from PIL import Image
scale = float(sys.argv[1])
for source, target in zip(sys.argv[2::2], sys.argv[3::2]):
    image = Image.open(source).convert('RGBA')
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    small = image.resize(size, Image.LANCZOS)
    small.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.FLOYDSTEINBERG).save(target, optimize=True)
`
    const pairs = entry.images.flatMap((image) => [join(entry.base, image.file), join(target, image.file.replace(/^parts\//, ''))])
    execFileSync('python3', ['-I', '-c', script, String(PART_SCALE), ...pairs])
}

// The soft floor shadow, as the studio paints it on a canvas: warm brown
// fading out from the middle.
const shadowScript = `
import sys
from PIL import Image
size = 128
image = Image.new('RGBA', (size, size), (60, 45, 30, 0))
pixels = image.load()
for y in range(size):
    for x in range(size):
        r = ((x + 0.5 - size / 2) ** 2 + (y + 0.5 - size / 2) ** 2) ** 0.5 / (size / 2)
        if r < 0.55:
            a = 0.42 + (0.2 - 0.42) * r / 0.55
        elif r < 1:
            a = 0.2 * (1 - (r - 0.55) / 0.45)
        else:
            a = 0
        pixels[x, y] = (60, 45, 30, round(a * 255))
image.save(sys.argv[1], optimize=True)
`
execFileSync('python3', ['-I', '-c', shadowScript, join(ASSET_DIR, 'shadow.png')])

function rigValue(rig, field) {
    const match = /^spine(\d)$/.exec(field)
    return match ? rig.spine[Number(match[1])] : rig[field]
}

function imageRecord(image, entry) {
    const described = image.described
    const slots = new Array(16).fill(0)
    const names = IMAGE_POINTS[image.kind]
    names.forEach((name, slot) => {
        let point = described[name]
        if (name.startsWith('shoulder')) {
            point = described.shoulders[Number(name.slice('shoulder'.length))]
        }
        if (name === 'crown' && !point) {
            point = { x: 0, y: 0.02 * image.size.height }
        }
        slots[slot * 2] = point.x
        slots[slot * 2 + 1] = point.y
    })
    return {
        role: stringId(image.role),
        path: stringId(`assets/practices/taichi/${entry.dir}/${image.file.replace(/^parts\//, '')}`),
        width: image.size.width,
        height: image.size.height,
        slots,
        values: [described.anterior ?? 1, described.thickness ?? 1, described.sign ?? 1, described.across === 'thumb' ? 1 : 0],
    }
}

// --- Write course.bin --------------------------------------------------------

const characterRecords = characters.map((entry) => ({
    id: stringId(entry.id),
    name: textKey(entry.name),
    rig: RIG_FIELDS.map((field) => rigValue(entry.rig, field)),
    images: entry.images.map((image) => imageRecord(image, entry)),
}))

const writer = new Writer()
writer.bytes(Buffer.from('TCH2', 'ascii'))
writer.u32(strings.length)
for (const value of strings) {
    writer.string(value)
}
writer.u32(keySets.length)
for (const set of keySets) {
    writer.u32(set.length)
    for (const key of set) {
        writer.f32(key.t)
        writer.s32(key.cue ? stringIndex.get(`tai_chi_text_${createHash('sha1').update(key.cue).digest('hex').slice(0, 8)}`) : -1)
        writer.f32(key.cue ? readingTime(key.cue) : 0)
        const look = lookFields(key.pose.look)
        writer.u8(look.kind)
        writer.u8(0)
        writer.u8(0)
        writer.u8(0)
        writer.f32(look.yaw)
        writer.f32(look.pitch)
        for (const channel of CHANNELS) {
            writer.f32(channelValue(key.pose, channel))
        }
    }
}
writer.u32(characterRecords.length)
for (const record of characterRecords) {
    writer.s32(record.id)
    writer.s32(record.name)
    for (const value of record.rig) {
        writer.f32(value)
    }
    writer.u32(record.images.length)
    for (const image of record.images) {
        writer.s32(image.role)
        writer.s32(image.path)
        writer.f32(image.width)
        writer.f32(image.height)
        for (const value of image.slots) {
            writer.f32(value)
        }
        for (const value of image.values) {
            writer.f32(value)
        }
    }
}
writer.u32(outline.length)
for (const module of outline) {
    writer.s32(module.title)
    writer.u32(module.lessons.length)
    for (const lesson of module.lessons) {
        writer.s32(lesson.title)
        writer.s32(lesson.subtitle)
        writer.s32(lesson.summary)
        writer.u32(lesson.items.length)
        for (const item of lesson.items) {
            writer.s32(item.id)
            writer.s32(item.title)
            writer.s32(item.version)
            writer.u8(item.kind)
            writer.u8(item.view)
            writer.u8(item.mirror)
            writer.u8(item.source)
            writer.u8(item.stepWords)
            writer.s32(item.first)
            writer.s32(item.last)
            writer.f32(item.scale)
            writer.f32(item.hold)
            writer.f32(item.duration)
            writer.u32(item.marks.length)
            for (const mark of item.marks) {
                writer.s32(mark.title)
                writer.f32(mark.start)
                writer.f32(mark.end)
            }
        }
    }
}
const binary = writer.finish()
mkdirSync(ASSET_DIR, { recursive: true })
writeFileSync(join(ASSET_DIR, 'course.bin'), binary)

// --- Words ---------------------------------------------------------------------

mkdirSync(dirname(TEXT_FILE), { recursive: true })
const entries = [...words.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
writeFileSync(TEXT_FILE, entries.map(([key, value]) => `[${key}]\n${value}\n---\n`).join(''))
const narrationKeys = [...narrationWords].map((text) =>
    `tai_chi_text_${createHash('sha1').update(text).digest('hex').slice(0, 8)}`).sort()
writeFileSync(join(STUDIO_ROOT, 'narration-lines.json'), `${JSON.stringify(narrationKeys, null, 2)}\n`)

// --- Parity reference ------------------------------------------------------------

// For a handful of items and times: the sampled channels, solved joints and
// the painted pieces seen from a fixed camera, laid out with no memory of
// earlier frames, so the app's port can be checked number for number.
const REFERENCE_ITEMS = ['foundations/hook', 'lesson-2/brush-knee/breakdown', 'lesson-6/snake-left/follow', 'full/normal']
const REFERENCE_JOINTS = ['pelvis', 'neckBase', 'shoulderCenter', 'shoulderL', 'elbowR', 'wristL', 'wristR', 'kneeL', 'kneeR',
    'ankleL', 'heelR', 'toeL', 'headTop', 'com']
const REFERENCE_PIECES = ['shadowL', 'shadowBody', 'torso', 'head', 'armL', 'armR', 'handL', 'handR', 'legL', 'legR', 'shoeL', 'shoeR']
const reference = { channels: CHANNELS, joints: REFERENCE_JOINTS, pieces: REFERENCE_PIECES, grid: [2, 6], samples: [] }
const itemIds = []
for (const module of course.modules) {
    for (const lesson of module.lessons) {
        for (const item of lesson.items) {
            itemIds.push(item.id)
        }
    }
}
for (const entry of characters) {
    const imageGroups = { ...entry.character }
    for (const id of REFERENCE_ITEMS) {
        const item = course.items.get(id)
        const { timeline } = timelineFor(item)
        for (const fraction of [0, 0.137, 0.41, 0.73, 1]) {
            const time = timeline.duration * fraction
            const pose = timeline.sample(timeline.start + time).pose
            const solved = solvePose(pose, entry.rig)
            const camera = { yaw: 0.6 + fraction, tilt: 0.12, center: solved.joints.pelvis.clone().setY(0) }
            const placement = createPaintedLayout(imageGroups, entry.rig)
            const frame = placement.layout(solved, camera)
            reference.samples.push({
                character: entry.id,
                item: itemIds.indexOf(id),
                time,
                look: pose.look,
                channels: CHANNELS.map((channel) => channelValue(pose, channel)),
                joints: REFERENCE_JOINTS.map((name) => [solved.joints[name].x, solved.joints[name].y, solved.joints[name].z]),
                camera: { yaw: camera.yaw, tilt: camera.tilt, center: [camera.center.x, camera.center.z] },
                order: frame.order,
                pieces: REFERENCE_PIECES.map((name) => {
                    const piece = frame.pieces[name]
                    const image = pieceImage({ ...imageGroups, shadow: { width: 128, height: 128 } }, piece.image)
                    return {
                        name,
                        image: piece.image,
                        points: pieceVertices(piece, image, reference.grid[0], reference.grid[1]).map((point) => [point.x, point.y]),
                    }
                }),
            })
        }
    }
}
mkdirSync(dirname(REFERENCE_FILE), { recursive: true })
const roundDeep = (value) => (typeof value === 'number' ? Math.round(value * 1e6) / 1e6
    : Array.isArray(value) ? value.map(roundDeep)
        : value && typeof value === 'object' ? Object.fromEntries(Object.entries(value).map(([key, item]) => [key, roundDeep(item)]))
            : value)
writeFileSync(REFERENCE_FILE, `${JSON.stringify(roundDeep(reference))}\n`)

const keyCount = keySets.reduce((sum, set) => sum + set.length, 0)
console.log(`course.bin: ${(binary.length / 1024).toFixed(0)} KB, ${keySets.length} key sets, ${keyCount} keys, ${strings.length} strings, ${words.size} words to translate`)
console.log(`items: ${itemIds.length}; reference samples: ${reference.samples.length}`)
