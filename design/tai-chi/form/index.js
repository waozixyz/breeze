// The 24-form in order, and the lessons that teach it.
//
// Facing (degrees, positive turns left) runs continuously through the
// form: the opening travels to the left (90), Grasp the Bird's Tail turns
// right to -90, Single Whip back to 90, the kicks turn round to 270, and
// Cross Hands returns to the starting direction (0, a full turn later).

import * as lesson1 from './lesson1.js'
import * as lesson2 from './lesson2.js'
import * as lesson3 from './lesson3.js'
import * as lesson4 from './lesson4.js'
import * as lesson5 from './lesson5.js'
import * as lesson6 from './lesson6.js'
import * as lesson7 from './lesson7.js'
import * as lesson8 from './lesson8.js'

const MODULES = [lesson1, lesson2, lesson3, lesson4, lesson5, lesson6, lesson7, lesson8]

const TITLES = [
    'Opening',
    'Brushing and repulsing',
    'Grasp the Bird\'s Tail',
    'Single Whip and Cloud Hands',
    'Kicks and strikes',
    'Snake Creeps Down',
    'Shuttles, Needle and Fan',
    'Closing',
]

export const LESSONS = MODULES.map((module, index) => ({
    number: index + 1,
    title: TITLES[index],
    startPose: module.startPose ?? null,
    moves: module.MOVES,
}))

export const FORM_MOVES = MODULES.flatMap((module) => module.MOVES)
