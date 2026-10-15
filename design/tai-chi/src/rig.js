// Body proportions for the Tai Chi figures.
//
// Lengths are fractions of standing height. Choreography is written in
// metres for a 1.70 m person; `scale` maps those positions to each figure.

export const REFERENCE_HEIGHT = 1.70

const BASE = {
    ankleHeight: 0.046,
    heelBack: 0.030,
    ball: 0.085,
    toeTip: 0.120,
    footHalfWidth: 0.026,
    shin: 0.243,
    thigh: 0.235,
    hipHalfWidth: 0.052,
    hipDrop: 0.025,
    spine: [0.070, 0.100, 0.110],
    neck: 0.035,
    headHeight: 0.136,
    shoulderHalfWidth: 0.106,
    shoulderDrop: 0.014,
    upperArm: 0.172,
    foreArm: 0.150,
    palmOffset: 0.035,
    handLength: 0.108,
}

// The figures the studio can show. Proportions are the same rig with a
// different height and a few widths.
export const FIGURES = {
    mannequin: { height: 1.70 },
    sageBun: { height: 1.66, shoulderHalfWidth: 0.102, hipHalfWidth: 0.054 },
    sageMale: { height: 1.78, shoulderHalfWidth: 0.114, hipHalfWidth: 0.050 },
    jadeWoman: { height: 1.65, shoulderHalfWidth: 0.102, hipHalfWidth: 0.054 },
    indigoMan: { height: 1.77, shoulderHalfWidth: 0.114, hipHalfWidth: 0.050 },
    monk: { height: 1.72, shoulderHalfWidth: 0.1, hipHalfWidth: 0.052 },
    tibetanWoman: { height: 1.62, shoulderHalfWidth: 0.098, hipHalfWidth: 0.056 },
}

export function makeRig(figure = 'mannequin') {
    const overrides = FIGURES[figure] ?? FIGURES.mannequin
    const height = overrides.height
    const fractions = { ...BASE, ...overrides }
    const metres = (fraction) => fraction * height
    const rig = {
        figure,
        height,
        scale: height / REFERENCE_HEIGHT,
        ankleHeight: metres(fractions.ankleHeight),
        heelBack: metres(fractions.heelBack),
        ball: metres(fractions.ball),
        toeTip: metres(fractions.toeTip),
        footHalfWidth: metres(fractions.footHalfWidth),
        shin: metres(fractions.shin),
        thigh: metres(fractions.thigh),
        hipHalfWidth: metres(fractions.hipHalfWidth),
        hipDrop: metres(fractions.hipDrop),
        spine: fractions.spine.map(metres),
        neck: metres(fractions.neck),
        headHeight: metres(fractions.headHeight),
        shoulderHalfWidth: metres(fractions.shoulderHalfWidth),
        shoulderDrop: metres(fractions.shoulderDrop),
        upperArm: metres(fractions.upperArm),
        foreArm: metres(fractions.foreArm),
        palmOffset: metres(fractions.palmOffset),
        handLength: metres(fractions.handLength),
    }
    rig.legLength = rig.thigh + rig.shin
    rig.armLength = rig.upperArm + rig.foreArm
    rig.hipHeight = rig.ankleHeight + rig.legLength
    rig.pelvisHeight = rig.hipHeight + rig.hipDrop
    return rig
}
