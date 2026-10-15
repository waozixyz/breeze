// Titles drawn over the finished picture: a transparent canvas the size of
// the frame, redrawn from film time and laid over the grade (sRGB), so words
// stay crisp and unbloomed. Every cue eases in and out on its own clock.
import { CanvasTexture, LinearFilter, NoColorSpace } from 'three'

const SANS = '"Quicksand", "Quicksand Medium", sans-serif'
const MEDIUM = '"Quicksand Medium", "Quicksand", sans-serif'

function smooth(x) {
    const t = Math.min(1, Math.max(0, x))
    return t * t * (3 - 2 * t)
}

// 0 → 1 → 0 over [from, to], `rise` seconds in and `fall` out.
export function presence(t, from, to, rise = 0.9, fall = 0.8) {
    return Math.min(smooth((t - from) / rise), smooth((to - t) / fall))
}

export function createOverlay(WIDTH = 1920, HEIGHT = 1080) {
    const canvas = document.createElement('canvas')
    canvas.width = WIDTH
    canvas.height = HEIGHT
    const context = canvas.getContext('2d')
    const map = new CanvasTexture(canvas)
    // Raw display values: the titles pass lays them over the encoded picture.
    map.colorSpace = NoColorSpace
    map.minFilter = LinearFilter
    map.generateMipmaps = false
    map.premultiplyAlpha = true

    const c = context
    function spaced(text, x, y, spacing, align = 'center') {
        // Letter-spaced text; the canvas property keeps kerning intact.
        c.letterSpacing = `${spacing}px`
        c.textAlign = align
        // Chromium adds the spacing after the last letter too.
        const shift = align === 'center' ? spacing / 2 : 0
        c.fillText(text, x + shift, y)
        c.letterSpacing = '0px'
    }

    function shadowed(draw, strength = 1) {
        c.save()
        c.shadowColor = `rgba(4, 8, 20, ${0.55 * strength})`
        c.shadowBlur = 28
        c.shadowOffsetY = 2
        draw()
        c.restore()
    }

    return {
        map,
        begin() {
            c.clearRect(0, 0, WIDTH, HEIGHT)
        },
        end() {
            map.needsUpdate = true
        },
        // A calm line of lowercase words. It rises a little and sharpens as
        // it appears. `y` is the first baseline; "\n" starts another line.
        line(text, t, from, to, { y = 860, size = 62, color = '#fff8ec', font = MEDIUM, x = WIDTH / 2, align = 'center', leading = 1.25 } = {}) {
            const k = presence(t, from, to)
            if (k <= 0) {
                return
            }
            c.save()
            c.globalAlpha = k
            c.font = `${size}px ${font}`
            c.fillStyle = color
            c.filter = k < 1 ? `blur(${((1 - k) * 6).toFixed(2)}px)` : 'none'
            text.split('\n').forEach((row, index) => shadowed(() => spaced(row, x, y + index * size * leading + (1 - k) * 14, 0.5, align)))
            c.restore()
        },
        // The product title: name, a thin gold rule and a quiet subline.
        title(name, subline, t, from, to, { y = 520, x = WIDTH / 2, size = 94, sublineSize = 40 } = {}) {
            const align = x === WIDTH / 2 ? 'center' : 'left'
            const k = presence(t, from, to, 1.1, 0.9)
            if (k <= 0) {
                return
            }
            c.save()
            c.globalAlpha = k
            c.filter = k < 1 ? `blur(${((1 - k) * 7).toFixed(2)}px)` : 'none'
            c.font = `bold ${size}px ${SANS}`
            c.fillStyle = '#fffaf0'
            shadowed(() => spaced(name, x, y + (1 - k) * 16, 1.5, align), 1.2)
            const rule = 260 * smooth((t - from - 0.3) / 1.0)
            c.filter = 'none'
            c.fillStyle = 'rgba(247, 214, 150, 0.9)'
            c.fillRect(align === 'center' ? x - rule / 2 : x + 4, y + 44, rule, 2)
            c.font = `${sublineSize}px ${MEDIUM}`
            c.fillStyle = '#f7dca0'
            c.globalAlpha = k * smooth((t - from - 0.5) / 0.9)
            shadowed(() => spaced(subline, x + (align === 'center' ? 0 : 4), y + 44 + sublineSize * 1.7, 3, align))
            c.restore()
        },
        // A feature fact in the lower left, behind a slim gold bar.
        fact(text, t, from, to, { y = 900, x = 150, size = 50 } = {}) {
            const k = presence(t, from, to, 0.7, 0.6)
            if (k <= 0) {
                return
            }
            c.save()
            c.globalAlpha = k
            c.fillStyle = 'rgba(247, 214, 150, 0.95)'
            const bar = 58 * smooth((t - from) / 0.6)
            c.fillRect(x, y - 44 - bar / 2 + 29, 3, bar)
            c.font = `${size}px ${MEDIUM}`
            c.fillStyle = '#fff8ec'
            c.filter = k < 1 ? `blur(${((1 - k) * 5).toFixed(2)}px)` : 'none'
            shadowed(() => spaced(text, x + 30 + (1 - k) * -18, y, 0.4, 'left'))
            c.restore()
        },
        // The movement being practised, as the app names it, lower right.
        movement(name, count, t, from, to, { x = 150, y = 128 } = {}) {
            const k = presence(t, from, to, 1.0, 0.8)
            if (k <= 0) {
                return
            }
            c.save()
            c.globalAlpha = k
            // A soft oval of shade behind the words, fading out in all directions.
            c.save()
            c.translate(x + 180, y + 24)
            c.scale(2.2, 1)
            const shade = c.createRadialGradient(0, 0, 10, 0, 0, 140)
            shade.addColorStop(0, 'rgba(10, 14, 30, 0.42)')
            shade.addColorStop(1, 'rgba(10, 14, 30, 0)')
            c.fillStyle = shade
            c.fillRect(-150, -150, 300, 300)
            c.restore()
            c.font = `26px ${MEDIUM}`
            c.fillStyle = '#f7dca0'
            shadowed(() => spaced(count.toUpperCase(), x, y, 5, 'left'))
            c.font = `44px ${MEDIUM}`
            c.fillStyle = '#fff8ec'
            shadowed(() => spaced(name, x, y + 54, 0.6, 'left'))
            c.restore()
        },
        // The end card's words under the app icon.
        card(t, from, to, { y = 590 } = {}) {
            const k = presence(t, from, to, 1.2, 0.6)
            if (k <= 0) {
                return
            }
            c.save()
            c.globalAlpha = k
            c.font = `bold 112px ${SANS}`
            c.fillStyle = '#fffaf0'
            shadowed(() => spaced('Inner Breeze', WIDTH / 2, y, 1.5), 1.2)
            c.globalAlpha = k * smooth((t - from - 0.4) / 0.9)
            c.font = `46px ${MEDIUM}`
            c.fillStyle = '#f7dca0'
            shadowed(() => spaced('Tai Chi, whenever you need a pause', WIDTH / 2, y + 90, 1))
            c.globalAlpha = k * smooth((t - from - 0.9) / 0.9)
            c.font = `38px ${MEDIUM}`
            c.fillStyle = '#eef1fa'
            shadowed(() => spaced('inbe.waozi.xyz   ·   open source', WIDTH / 2, y + 200, 2), 1.4)
            c.restore()
        },
    }
}
