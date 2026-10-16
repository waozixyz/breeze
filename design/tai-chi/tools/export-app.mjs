// Exports the course for Inner Breeze: the key poses and timing the app
// samples and solves itself, the two flat characters (src/flat/shapes.js),
// the words to translate, and a reference for the app's parity test.
//
//   node tools/export-app.mjs
//
// Writes (paths from the Inbe repository root):
//   assets/practices/taichi/course.bin        keys, course outline, rigs
//   assets/practices/taichi/flat-edge.png      soft edges of the figure's shapes
//   design/tai-chi/text/en.txt                 course words as locale entries
//   tests/fixtures/tai-chi-reference.json      sampled poses, joints, shapes
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
//     u32 image count (0: the flat characters are drawn, not painted); per
//     image s32 role, s32 path, f32 width, f32 height, f32[16] points (8
//     named points by role), f32[4] values (anterior, thickness, sign,
//     across thumb)
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
import { FLAT_LOOKS, createFlatShapes } from '../src/flat/shapes.js'
import { FlatView } from '../src/painted/layout.js'
import { makeRig } from '../src/rig.js'
import { solvePose } from '../src/solve.js'
import { STUDIO_ROOT } from './serve.mjs'

const INBE_ROOT = resolve(STUDIO_ROOT, '..', '..')
const ASSET_DIR = join(INBE_ROOT, 'assets', 'practices', 'taichi')
const TEXT_FILE = join(STUDIO_ROOT, 'text', 'en.txt')
const REFERENCE_FILE = join(INBE_ROOT, 'tests', 'fixtures', 'tai-chi-reference.json')
// The app's characters, in the order it lists them; the men speak with the
// male voice (the app keeps each look's details in tai_chi_flat.zi).
const CHARACTERS = [
    { id: 'jadeWoman', name: 'Jade woman' },
    { id: 'indigoMan', name: 'Indigo man' },
    { id: 'tibetanWoman', name: 'Tibetan woman' },
    { id: 'monk', name: 'Tibetan monk' },
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

const characters = CHARACTERS.map((entry) => ({ ...entry, rig: makeRig(entry.id), look: FLAT_LOOKS[entry.id] }))

// Shapes and lines are drawn as tinted meshes over this one-row image,
// clear at both ends and opaque between: a fan from a shape's middle out
// past its edge, a strip across a line. With smooth scaling the fade gives
// every edge a soft, even border.
const edgeScript = `
import sys
from PIL import Image
alphas = (0, 255, 255, 255, 255, 0)
image = Image.new('RGBA', (len(alphas), 1))
for x, alpha in enumerate(alphas):
    image.putpixel((x, 0), (255, 255, 255, alpha))
image.save(sys.argv[1], optimize=True)
`
mkdirSync(ASSET_DIR, { recursive: true })
execFileSync('python3', ['-I', '-c', edgeScript, join(ASSET_DIR, 'flat-edge.png')])

function rigValue(rig, field) {
    const match = /^spine(\d)$/.exec(field)
    return match ? rig.spine[Number(match[1])] : rig[field]
}

// --- Write course.bin --------------------------------------------------------

const characterRecords = characters.map((entry) => ({
    id: stringId(entry.id),
    name: textKey(entry.name),
    rig: RIG_FIELDS.map((field) => rigValue(entry.rig, field)),
    images: [],
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
// the flat figure's paint operations seen from a fixed camera, so the app's
// port can be checked number for number. A fill is compared by its area,
// centroid and bounds (hull corners may differ where points are in line),
// a line by its ends and its number of points.
const REFERENCE_ITEMS = ['foundations/hook', 'lesson-1/wild-horse/demo', 'lesson-2/brush-knee/breakdown', 'lesson-6/snake-left/follow', 'full/normal']
const REFERENCE_JOINTS = ['pelvis', 'neckBase', 'shoulderCenter', 'shoulderL', 'elbowR', 'wristL', 'wristR', 'kneeL', 'kneeR',
    'ankleL', 'heelR', 'toeL', 'headTop', 'com']
const reference = { channels: CHANNELS, joints: REFERENCE_JOINTS, samples: [] }
const itemIds = []
for (const module of course.modules) {
    for (const lesson of module.lessons) {
        for (const item of lesson.items) {
            itemIds.push(item.id)
        }
    }
}

function fillSummary(points) {
    let area = 0
    let cx = 0
    let cy = 0
    for (let index = 0; index < points.length; index += 1) {
        const a = points[index]
        const b = points[(index + 1) % points.length]
        const cross = a.x * b.y - b.x * a.y
        area += cross
        cx += (a.x + b.x) * cross
        cy += (a.y + b.y) * cross
    }
    area /= 2
    const xs = points.map((point) => point.x)
    const ys = points.map((point) => point.y)
    return {
        area,
        center: Math.abs(area) > 1e-12 ? [cx / (6 * area), cy / (6 * area)] : [xs[0], ys[0]],
        box: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)],
    }
}

for (const entry of characters) {
    const shapes = createFlatShapes(entry.look, entry.rig)
    for (const id of REFERENCE_ITEMS) {
        const item = course.items.get(id)
        const { timeline } = timelineFor(item)
        for (const fraction of [0, 0.41, 0.73]) {
            const time = timeline.duration * fraction
            const pose = timeline.sample(timeline.start + time).pose
            const solved = solvePose(pose, entry.rig)
            const camera = { yaw: 0.6 + fraction * 3.4, tilt: 0.12, center: solved.joints.pelvis.clone().setY(0) }
            const view = new FlatView()
            view.set(camera.yaw, camera.tilt, camera.center)
            const ops = shapes.paint(solved, view)
            reference.samples.push({
                character: entry.id,
                item: itemIds.indexOf(id),
                time,
                channels: CHANNELS.map((channel) => channelValue(pose, channel)),
                joints: REFERENCE_JOINTS.map((name) => [solved.joints[name].x, solved.joints[name].y, solved.joints[name].z]),
                camera: { yaw: camera.yaw, tilt: camera.tilt, center: [camera.center.x, camera.center.z] },
                ops: ops.map((op) => (op.kind === 'fill'
                    ? { fill: op.color, alpha: op.alpha, ...fillSummary(op.points) }
                    : {
                        line: op.color,
                        alpha: op.alpha,
                        width: op.width,
                        count: op.points.length,
                        ends: [op.points[0].x, op.points[0].y, op.points[op.points.length - 1].x, op.points[op.points.length - 1].y],
                    })),
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
