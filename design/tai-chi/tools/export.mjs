// Exports the course as data: the keyed poses, cues and timing that any
// renderer can play, plus a measured baked variant for size comparison.
//
//   node tools/export.mjs            writes docs/tai-chi-24.json
//   node tools/export.mjs --bake     also bakes joint rotations at 30 fps to
//                                    build/tai-chi/baked/ and reports sizes
//
// The keyed file is what Inbe would ship; it needs the solver (src/solve.js)
// to turn poses into a skeleton. The baked file needs no solver but is far
// larger.

import { mkdirSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { gzipSync } from 'node:zlib'
import { buildCourse, timelineFor } from '../src/course.js'
import { FIGURES, REFERENCE_HEIGHT, makeRig } from '../src/rig.js'
import { solvePose } from '../src/solve.js'
import { SEGMENTS } from '../src/view/figure.js'
import { STUDIO_ROOT } from './serve.mjs'

const INBE_ROOT = resolve(STUDIO_ROOT, '..', '..')
const OUTPUT = join(INBE_ROOT, 'docs', 'tai-chi-24.json')
const BAKED = join(INBE_ROOT, 'build', 'tai-chi', 'baked')

function round(value, digits = 4) {
    const scale = 10 ** digits
    return Math.round(value * scale) / scale
}

function roundDeep(value) {
    if (typeof value === 'number') {
        return round(value)
    }
    if (Array.isArray(value)) {
        return value.map(roundDeep)
    }
    if (value && typeof value === 'object') {
        return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, roundDeep(item)]))
    }
    return value
}

function exportKeys(keys) {
    return keys.map((key) => {
        const entry = { t: round(key.t, 3), pose: roundDeep(key.pose) }
        if (key.cue) {
            entry.cue = key.cue
        }
        if (key.move) {
            entry.move = key.move
        }
        return entry
    })
}

const course = buildCourse()
const form = course.form
const data = {
    format: 'inbe-tai-chi/1',
    description: 'Yang-style 24-form Tai Chi course: keyed poses for design/tai-chi/src/solve.js. Metres for a 1.70 m figure, radians, +Y up, the form starts facing +Z with +X on the figure\'s left.',
    referenceHeight: REFERENCE_HEIGHT,
    figures: FIGURES,
    tempo: { breakdownSlowdown: 1.7, breakdownHold: 1.6, slowForm: 1.5 },
    lessons: course.modules.map((module) => ({
        id: module.id,
        title: module.title,
        lessons: module.lessons.map((lesson) => ({
            id: lesson.id,
            title: lesson.title,
            subtitle: lesson.subtitle ?? null,
            items: lesson.items.map((item) => ({
                id: item.id,
                title: item.title,
                version: item.version ?? null,
                kind: item.kind,
                view: item.view,
                mirror: Boolean(item.mirror),
                duration: round(timelineFor(item).timeline.duration, 2),
            })),
        })),
    })),
    form: {
        duration: round(form.t, 2),
        moves: form.moves.map((move) => ({
            id: move.id,
            number: move.number,
            lesson: move.lesson,
            title: move.title,
            start: round(move.start, 3),
            end: round(move.end, 3),
            endFacing: move.endFacing,
        })),
        keys: exportKeys(form.keys),
    },
    drills: Object.fromEntries([...course.items.values()]
        .filter((item) => item.kind === 'drill')
        .map((item) => [item.id, exportKeys(timelineFor(item).keys)])),
}

// Readable and diffable: one key per line.
function format(value, indent = '') {
    if (Array.isArray(value) && value.length > 0 && value[0] && typeof value[0] === 'object' && 'pose' in value[0]) {
        return `[\n${value.map((entry) => `${indent} ${JSON.stringify(entry)}`).join(',\n')}\n${indent}]`
    }
    if (value && typeof value === 'object' && !Array.isArray(value)) {
        const entries = Object.entries(value).map(([key, item]) => `${indent} ${JSON.stringify(key)}: ${format(item, `${indent} `)}`)
        return `{\n${entries.join(',\n')}\n${indent}}`
    }
    if (Array.isArray(value) && value.some((item) => item && typeof item === 'object')) {
        return `[\n${value.map((item) => `${indent} ${format(item, `${indent} `)}`).join(',\n')}\n${indent}]`
    }
    return JSON.stringify(value)
}

const json = `${format(data)}\n`
JSON.parse(json)
writeFileSync(OUTPUT, json)
const compact = JSON.stringify(data)
console.log(`${OUTPUT}: ${(json.length / 1024).toFixed(0)} KB (${(gzipSync(compact).length / 1024).toFixed(0)} KB gzipped), ${form.keys.length} form keys, ${(form.t / 60).toFixed(2)} min`)

if (process.argv.includes('--bake')) {
    mkdirSync(BAKED, { recursive: true })
    const fps = 30
    for (const figure of Object.keys(FIGURES)) {
        const rig = makeRig(figure)
        const timeline = timelineFor(course.items.get('full/normal')).timeline
        const frames = Math.floor(timeline.duration * fps) + 1
        // Per frame: pelvis position (3 x int16 millimetres) and every
        // segment's rotation (4 x int16 quaternion components).
        const frameBytes = 6 + SEGMENTS.length * 8
        const buffer = Buffer.alloc(frames * frameBytes)
        for (let frame = 0; frame < frames; frame += 1) {
            const solved = solvePose(timeline.sample(frame / fps).pose, rig)
            let offset = frame * frameBytes
            const pelvis = solved.segments.pelvis.pos
            for (const value of [pelvis.x, pelvis.y, pelvis.z]) {
                buffer.writeInt16LE(Math.round(value * 1000), offset)
                offset += 2
            }
            for (const name of SEGMENTS) {
                const quat = solved.segments[name].quat
                for (const value of [quat.x, quat.y, quat.z, quat.w]) {
                    buffer.writeInt16LE(Math.round(value * 32767), offset)
                    offset += 2
                }
            }
        }
        const path = join(BAKED, `full-form-${figure}.bin`)
        writeFileSync(path, buffer)
        console.log(`${path}: ${(buffer.length / 1024 / 1024).toFixed(2)} MB (${(gzipSync(buffer).length / 1024 / 1024).toFixed(2)} MB gzipped), ${frames} frames`)
    }
}
