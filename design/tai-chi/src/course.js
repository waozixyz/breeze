// The course: Foundations, eight lessons of the 24-form, and the full form.
//
// The form is built once as one continuous motion. Lessons play slices of
// it. Each movement has three versions: a demo at normal speed, a slow
// breakdown that pauses on every step with its cue, and a follow-along that
// does the movement on both sides.
//
// Items show words in one of two ways (`cues`). Drills and breakdowns teach
// step by step ('steps'): each step's words, with the step slowed until
// they can be read. Items played at the form's tempo ('moves') name the
// movement instead, since their steps pass too quickly to read.

import { Form } from './form.js'
import { clonePose, mirrorPose, rotatePose, stanceCenter, standingPose, translatePose } from './pose.js'
import { Timeline } from './timeline.js'
import { FORM_MOVES, LESSONS } from '../form/index.js'
import { FOUNDATIONS } from '../form/foundations.js'

const BREAKDOWN_SLOWDOWN = 1.7
const BREAKDOWN_HOLD = 1.6
const SLOW_FORM = 1.5

// A step this much short of its reading time is long enough.
const READING_SLACK = 0.001

// How long a step's words need on screen: a moment to notice them, then
// about 14 characters a second, and never less than 2 seconds.
export function readingTime(cue) {
    return Math.max(2, 0.8 + cue.length / 14)
}

// The key whose segment starts showing the words of cued key `index`: the
// key before it, or one earlier when that key is a lead-in (no words of its
// own and not a pause).
function cueStart(keys, index) {
    const lead = index - 1
    return lead >= 1 && !keys[lead].cue && !keys[lead].held ? lead - 1 : lead
}

// The words shown on the segment from key `index` to the next: the next
// key's, else past a lead-in key the one after's, else the last words
// shown, which stay until new words start. Key 0's own words belong to the
// motion before the item and never show.
export function cueAt(keys, index) {
    const next = keys[index + 1]
    if (next?.cue) {
        return next.cue
    }
    if (next && !next.held && keys[index + 2]?.cue) {
        return keys[index + 2].cue
    }
    for (let back = index; back >= 1; back -= 1) {
        if (keys[back].cue) {
            return keys[back].cue
        }
    }
    return null
}

// Slows every cued step whose words would not stay on screen for their
// reading time, until they do. Pauses after a step count as reading time.
function slowForReading(keys) {
    const cued = []
    for (let index = 1; index < keys.length; index += 1) {
        if (keys[index].cue) {
            cued.push(index)
        }
    }
    for (let n = 0; n < cued.length; n += 1) {
        const index = cued[n]
        const start = cueStart(keys, index)
        const end = n + 1 < cued.length ? cueStart(keys, cued[n + 1]) : keys.length - 1
        const shown = keys[end].t - keys[start].t
        const motion = keys[index].t - keys[start].t
        const need = readingTime(keys[index].cue)
        if (shown >= need - READING_SLACK || motion <= 0) {
            continue
        }
        const stretch = (need - shown) / motion
        const origin = keys[start].t
        for (let later = start + 1; later < keys.length; later += 1) {
            keys[later].t += later <= index ? (keys[later].t - origin) * stretch : need - shown
        }
    }
    return keys
}

// Keys from `start` to `end` (inclusive), moved to start at time 0 and
// stretched by `scale`; `holdAfterCue` pauses on every key that ends a cued
// step, and `readable` slows steps until their words can be read.
function retime(keys, { scale = 1, holdAfterCue = 0, readable = false } = {}) {
    const result = []
    const origin = keys[0].t
    let shift = 0
    for (let index = 0; index < keys.length; index += 1) {
        const key = keys[index]
        const t = (key.t - origin) * scale + shift
        result.push({ ...key, t })
        const isLast = index === keys.length - 1
        if (holdAfterCue > 0 && key.cue && !isLast) {
            shift += holdAfterCue
            result.push({ ...key, t: t + holdAfterCue, cue: null, held: true })
        }
    }
    return readable ? slowForReading(result) : result
}

function sliceMarks(moves, startIndex, endIndex, keys) {
    return moves
        .filter((move) => move.startIndex >= startIndex && move.endIndex <= endIndex)
        .map((move) => ({ id: move.id, title: move.title, number: move.number, start: move.start, end: move.end }))
        .map((mark) => ({ ...mark, start: mark.start - keys[startIndex].t, end: mark.end - keys[startIndex].t }))
}

function buildForm() {
    const form = new Form(standingPose())
    for (const move of FORM_MOVES) {
        form.move(move.id, move.title, (f) => move.build(f), { number: move.number, lesson: move.lesson, endFacing: move.endFacing })
    }
    return form
}

// `pose` turned to face `facing` and moved so its stance is centred where
// the figure stands now, so stepping into it takes the fewest steps.
function placeUnder(pose, current) {
    const center = stanceCenter(pose)
    const turned = rotatePose(pose, center, current.facing - pose.facing)
    const here = stanceCenter(current)
    return translatePose(turned, here.x - center.x, here.z - center.z)
}

// The movement on its side, then mirrored, then back to the start, so it
// can loop.
function followAlong(move, startPose) {
    const form = new Form(startPose)
    form.move(move.id, move.title, (f) => move.build(f), { number: move.number })
    const mirroredStart = mirrorPose(startPose, stanceCenter(startPose), startPose.facing)
    form.resetTo(placeUnder(mirroredStart, form.pose), 'Step into the mirrored starting position')
    form.mirrored = true
    form.move(`${move.id}-mirrored`, `${move.title} (other side)`, (f) => move.build(f), { number: move.number })
    form.mirrored = false
    form.resetTo(placeUnder(startPose, form.pose), 'Return to the starting position')
    return form
}

function marksOf(form, offset = 0) {
    return form.moves.map((move) => ({ id: move.id, title: move.title, number: move.number, start: move.start - offset, end: move.end - offset }))
}

export function buildCourse() {
    const form = buildForm()
    const fullKeys = form.keys
    const items = new Map()
    const modules = []

    const addItem = (item) => {
        items.set(item.id, item)
        return item
    }

    // Foundations: drills that each start from standing.
    const foundationLessons = FOUNDATIONS.map((lesson) => {
        const drills = lesson.drills.map((drill) => addItem({
            id: `foundations/${drill.id}`,
            title: drill.title,
            kind: 'drill',
            cues: 'steps',
            view: drill.view ?? 'front',
            summary: drill.summary,
            build() {
                const drillForm = new Form(standingPose())
                drillForm.move(drill.id, drill.title, (f) => drill.build(f))
                const keys = retime(drillForm.keys, { readable: true })
                const end = keys[keys.length - 1].t
                return { keys, marks: marksOf(drillForm).map((mark) => ({ ...mark, start: 0, end })) }
            },
        }))
        return { id: lesson.id, title: lesson.title, summary: lesson.summary, items: drills }
    })
    modules.push({ id: 'foundations', title: 'Foundations', lessons: foundationLessons })

    // Lessons 1–8.
    const lessonEntries = LESSONS.map((lesson) => {
        const moves = form.moves.filter((move) => move.lesson === lesson.number)
        const entries = []
        if (moves.length > 0) {
            const first = moves[0]
            const last = moves[moves.length - 1]
            entries.push(addItem({
                id: `lesson-${lesson.number}/all`,
                title: `Whole lesson`,
                kind: 'lesson',
                cues: 'moves',
                view: 'behind',
                build() {
                    const keys = retime(fullKeys.slice(first.startIndex, last.endIndex + 1))
                    return { keys, marks: sliceMarks(form.moves, first.startIndex, last.endIndex, fullKeys) }
                },
            }))
        }
        for (const move of moves) {
            const definition = FORM_MOVES.find((candidate) => candidate.id === move.id)
            const slice = () => fullKeys.slice(move.startIndex, move.endIndex + 1)
            const marks = () => sliceMarks(form.moves, move.startIndex, move.endIndex, fullKeys)
            entries.push(addItem({
                id: `lesson-${lesson.number}/${move.id}/demo`,
                title: `${move.number}. ${move.title}`,
                version: 'Demo',
                kind: 'demo',
                cues: 'moves',
                view: 'behind',
                build() {
                    return { keys: retime(slice()), marks: marks() }
                },
            }))
            entries.push(addItem({
                id: `lesson-${lesson.number}/${move.id}/breakdown`,
                title: `${move.number}. ${move.title}`,
                version: 'Breakdown',
                kind: 'breakdown',
                cues: 'steps',
                view: 'behind',
                build() {
                    const keys = retime(slice(), { scale: BREAKDOWN_SLOWDOWN, holdAfterCue: BREAKDOWN_HOLD, readable: true })
                    const end = keys[keys.length - 1].t
                    return { keys, marks: marks().map((mark) => ({ ...mark, start: 0, end })) }
                },
            }))
            entries.push(addItem({
                id: `lesson-${lesson.number}/${move.id}/follow`,
                title: `${move.number}. ${move.title}`,
                version: 'Follow-along',
                kind: 'follow',
                cues: 'moves',
                view: 'behind',
                build() {
                    const drill = followAlong(definition, clonePose(move.startPose))
                    return { keys: retime(drill.keys), marks: marksOf(drill, drill.keys[0].t) }
                },
            }))
        }
        return { id: `lesson-${lesson.number}`, number: lesson.number, title: `Lesson ${lesson.number}`, subtitle: lesson.title, items: entries }
    })
    modules.push({ id: 'lessons', title: '24-form lessons', lessons: lessonEntries })

    // Each lesson on its own from its canonical starting pose, for checking
    // a lesson before the ones before it are finished. Not in the outline.
    for (const lesson of LESSONS) {
        const startPose = lesson.startPose?.()
        if (!startPose || lesson.moves.length === 0) {
            continue
        }
        items.set(`lesson-${lesson.number}/standalone`, {
            id: `lesson-${lesson.number}/standalone`,
            title: `Lesson ${lesson.number} on its own`,
            kind: 'lesson',
            cues: 'moves',
            view: 'behind',
            build() {
                const lessonForm = new Form(startPose)
                for (const move of lesson.moves) {
                    lessonForm.move(move.id, move.title, (f) => move.build(f), { number: move.number, lesson: move.lesson })
                }
                return { keys: lessonForm.keys, marks: marksOf(lessonForm) }
            },
        })
    }

    // The full form.
    const fullMarks = marksOf(form)
    const fullItems = [
        addItem({
            id: 'full/normal', title: 'Full form', version: 'Normal tempo', kind: 'full', cues: 'moves', view: 'front', mirror: true,
            build: () => ({ keys: retime(fullKeys), marks: fullMarks }),
        }),
        addItem({
            id: 'full/slow', title: 'Full form', version: 'Slow learning tempo', kind: 'full', cues: 'moves', view: 'behind',
            build: () => ({ keys: retime(fullKeys, { scale: SLOW_FORM }), marks: fullMarks.map((mark) => ({ ...mark, start: mark.start * SLOW_FORM, end: mark.end * SLOW_FORM })) }),
        }),
    ]
    modules.push({ id: 'full', title: 'Full form', lessons: [{ id: 'full', title: 'Full form', items: fullItems }] })

    return { form, modules, items, duration: form.t }
}

// A timeline for an item, built on first use.
const timelines = new Map()
export function timelineFor(item) {
    if (!timelines.has(item.id)) {
        const built = item.build()
        timelines.set(item.id, { timeline: new Timeline(built.keys), marks: built.marks, keys: built.keys })
    }
    return timelines.get(item.id)
}
