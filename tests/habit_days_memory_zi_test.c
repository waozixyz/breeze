#include "habit_types.h"
#include "habits/habit_days.h"

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

int
main(void)
{
    Habit habit = {0};

    assert(habit_days_habit_reserve_days(&habit, 1) == 1);
    assert(habit.day_capacity >= 1);
    for (int i = 0; i < habit.day_capacity; ++i) {
        habit.days[i].day_index = 20260901 + i;
        habit.days[i].completed = 1;
        habit.days[i].count = i + 1;
        habit.days[i].session_count = i + 2;
    }

    int old_capacity = habit.day_capacity;
    assert(habit_days_habit_reserve_days(&habit, old_capacity + 1) == 1);
    assert(habit.day_capacity > old_capacity);
    for (int i = 0; i < old_capacity; ++i) {
        assert(habit.days[i].day_index == 20260901 + i);
        assert(habit.days[i].session_count == i + 2);
    }
    for (int i = old_capacity; i < habit.day_capacity; ++i) {
        assert(habit.days[i].day_index == 0);
        assert(habit.days[i].completed == 0);
        assert(habit.days[i].count == 0);
        assert(habit.days[i].session_count == 0);
    }

    free(habit.days);
    puts("Ziran habit day allocation preserves and initializes all records");
    return 0;
}
