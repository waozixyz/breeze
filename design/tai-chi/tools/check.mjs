// Runs the motion checks over the course and prints what fails.
//
//   node tools/check.mjs                      every item, all figures
//   node tools/check.mjs --item lesson-2/standalone --figure sageBun
//   node tools/check.mjs --warnings           also list warnings
//
// Exits 1 when any check reports an error.

import { buildCourse, timelineFor } from '../src/course.js'
import { checkTimeline } from '../src/checks.js'
import { FIGURES, makeRig } from '../src/rig.js'

const args = process.argv.slice(2)
const option = (name) => {
    const index = args.indexOf(`--${name}`)
    return index >= 0 ? args[index + 1] : undefined
}
const showWarnings = args.includes('--warnings')
const fps = Number(option('fps') ?? 20)

const course = buildCourse()
const figures = option('figure') ? [option('figure')] : Object.keys(FIGURES)
const itemIds = option('item')
    ? [option('item')]
    : [...course.items.keys()].filter((id) => !id.endsWith('/breakdown') && id !== 'full/slow')

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60)
    return `${minutes}:${(seconds - minutes * 60).toFixed(1).padStart(4, '0')}`
}

let errors = 0
let warnings = 0
for (const id of itemIds) {
    const item = course.items.get(id)
    if (!item) {
        console.error(`No item ${id}`)
        process.exit(2)
    }
    const { timeline, marks } = timelineFor(item)
    for (const figure of figures) {
        const rig = makeRig(figure)
        const moves = item.kind === 'full'
            ? marks.map((mark) => ({ ...mark, endFacing: course.form.moves.find((move) => move.id === mark.id)?.endFacing }))
            : []
        const expectDuration = id === 'full/normal' && course.form.moves.length >= 24 ? [270, 390] : null
        const result = checkTimeline(timeline, rig, { fps, moves, expectDuration })
        errors += result.errors
        warnings += result.warnings
        const listed = result.issues.filter((issue) => showWarnings || issue.severity === 'error')
        const status = result.errors === 0 ? (result.warnings === 0 ? 'ok' : `ok, ${result.warnings} warnings`) : `${result.errors} errors, ${result.warnings} warnings`
        console.log(`${id} [${figure}] ${formatTime(timeline.duration)}: ${status}`)
        for (const issue of listed) {
            const mark = marks.find((candidate) => issue.at >= candidate.start && issue.at <= candidate.end)
            const span = issue.end > issue.start ? `${formatTime(issue.start)}–${formatTime(issue.end)}` : formatTime(issue.start)
            console.log(`  ${issue.severity === 'error' ? 'ERROR' : 'warn '} ${span} ${mark ? `(${mark.title}) ` : ''}${issue.message}`)
        }
    }
}
console.log(`\n${errors} errors, ${warnings} warnings`)
process.exit(errors > 0 ? 1 : 0)
