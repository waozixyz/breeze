export const phases = {
    bruce_foundation_touch: ['Settle', 'Touch right thumb joint', 'Clockwise stirring', 'Continue stirring', 'Brush thumb and wrist', 'Left leg upward strokes', 'Right leg upward strokes', 'Both legs · sponge upward', 'Gentle strokes', 'Return and recall'],
    bruce_full_body_current: ['Settle', 'Right leg bounce', 'Left then both legs', 'Arm bounce', 'Feet to lower belly', 'Hands to lower belly', 'Inhale · feet to crown', 'Exhale · crown to belly', 'Full circuit', 'Simplify circuit', 'Last rounds', 'Return', 'Recall'],
    bruce_elevator_trance: ['Settle', 'Face release', 'Arms release', 'Legs release', 'Quiet thoughts', 'Breath anchor', 'Elevator descends', 'Felt descent', 'Passing floors', 'Pause · heaviness', 'Rest at breath', 'One more easy floor', 'Stay comfortable', 'Stop descent · return', 'Movement and recall'],
    bruce_spin_loosening: ['Settle', 'Room map', 'Release body', 'Breath anchor', 'Point forward and back', 'Touch the surface', 'Clockwise circuit', 'Steady circuit', 'Changing perspective', 'Body remains still', 'Steady rhythm', 'Felt position', 'Slow the circle', 'Point returns', 'Movement and recall'],
    bruce_rope_exit: ['Settle', 'Safe setup', 'Face release', 'Arms release', 'Legs release', 'Breath anchor', 'Optional descent', 'Brush limbs', 'Full circuit', 'Exterior point', 'Brief intention', 'Grasp rope', 'Hand over hand', 'Natural climbing rhythm', 'Continue gently', 'Reach · hold · pull', 'Release physical tension', 'Complete lift', 'Brief separation · return', 'Ground and recall'],
    bruce_roll_out_exit: ['Settle', 'Safe setup', 'Release body', 'Breath anchor', 'Energy circuit', 'Rest', 'Whole body turning', 'Roll left', 'Roll right', 'Choose clearer side', 'Roll farther', 'Continue gently', 'Complete roll', 'Brief separation · return', 'Ground and recall'],
}

export function sample(item, seconds) {
    const time = Math.max(0, Math.min(item.duration, seconds))
    const index = item.cues.findLastIndex(cue => cue.second <= time)
    const cue = item.cues[index]
    const end = item.cues[index + 1]?.second ?? item.duration
    return { time, index, cue, progress: (time - cue.second) / (end - cue.second), phase: phases[item.id][index] }
}
