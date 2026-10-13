// Geometry helpers shared by the figure styles.

import { LatheGeometry, SphereGeometry, Vector2 } from 'three'

// A capsule hanging from the origin along -Y: radius `top` at y = 0 and
// `bottom` at y = -length, with round ends.
export function taperedCapsule(top, bottom, length, radialSegments = 20) {
    const points = []
    const steps = 8
    for (let index = 0; index <= steps; index += 1) {
        const angle = -Math.PI / 2 + (Math.PI / 2) * (index / steps)
        points.push(new Vector2(Math.cos(angle) * bottom, -length + Math.sin(angle) * bottom))
    }
    for (let index = 0; index <= steps; index += 1) {
        const angle = (Math.PI / 2) * (index / steps)
        points.push(new Vector2(Math.cos(angle) * top, Math.sin(angle) * top))
    }
    return new LatheGeometry(points, radialSegments)
}

// A capsule whose radius follows `profile`: [[y, radius], ...] from bottom
// to top, closed at both ends.
export function profileSolid(profile, radialSegments = 24) {
    const points = [new Vector2(0, profile[0][0])]
    for (const [y, radius] of profile) {
        points.push(new Vector2(radius, y))
    }
    points.push(new Vector2(0, profile[profile.length - 1][0]))
    return new LatheGeometry(points, radialSegments)
}

export function ellipsoid(rx, ry, rz, widthSegments = 24, heightSegments = 16) {
    const geometry = new SphereGeometry(1, widthSegments, heightSegments)
    geometry.scale(rx, ry, rz)
    return geometry
}
