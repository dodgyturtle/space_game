import asyncio
import curses
from os import execlp
import random
import time
from itertools import cycle
from types import coroutine

from curses_tools import draw_frame, get_frame_size, read_controls
from physics import update_speed
from obstacles import Obstacle, show_obstacles, has_collision

STAR_SYMBOLS = "+*.:"
SKY_FILLING = 30
SYMBOL_AREA = 25
GARBAGE_COUNT = 6
GARBAGE_COROTINES = []
FIRE_COROTINES = []
OBSTACLES = []
OBSTACLES_IN_LAST_COLLISIONS = []


def read_file(filename):
    with open(filename, "r") as my_file:
        file_content = my_file.read()
    return file_content


def get_frame_max_size(frames):
    frames_sizes = [get_frame_size(frame) for frame in frames]
    frame_max_size = max(frames_sizes, key=max)
    return frame_max_size


def apply_ship_acceleration(rows_direction, columns_direction):
    if rows_direction == -1:
        row_speed, column_speed = update_speed(rows_direction, columns_direction, -1, 0)
        rows_direction = rows_direction + row_speed
    if rows_direction == 0:
        row_speed, column_speed = update_speed(rows_direction, columns_direction, 0, 0)
        rows_direction = rows_direction + row_speed
    if rows_direction == 1:
        row_speed, column_speed = update_speed(rows_direction, columns_direction, 1, 0)
        rows_direction = rows_direction + row_speed
    if columns_direction == -1:
        row_speed, column_speed = update_speed(rows_direction, columns_direction, 0, -1)
        columns_direction = columns_direction + column_speed
    if columns_direction == 0:
        row_speed, column_speed = update_speed(rows_direction, columns_direction, 0, 0)
        columns_direction = columns_direction + column_speed
    if columns_direction == 1:
        row_speed, column_speed = update_speed(rows_direction, columns_direction, 0, 1)
        columns_direction = columns_direction + column_speed
    return rows_direction, columns_direction


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        frame_height, frame_width = get_frame_size(garbage_frame)
        obstacle = Obstacle(row, column, frame_height, frame_width)
        OBSTACLES.append(obstacle)
        await asyncio.sleep(0)
        if obstacle in OBSTACLES_IN_LAST_COLLISIONS:
            OBSTACLES_IN_LAST_COLLISIONS.remove(obstacle)
            OBSTACLES.remove(obstacle)
            draw_frame(canvas, row, column, garbage_frame, negative=True)
            return
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        try:
            OBSTACLES.remove(obstacle)
        except:
            pass
        row += speed


async def fill_orbit_with_garbage(canvas):
    window_height, window_width = canvas.getmaxyx()
    garbage_frame_files = ["frames/trash_large.txt", "frames/trash_small.txt", "frames/trash_xl.txt"]
    garbage_frames = [read_file(garbage_frame) for garbage_frame in garbage_frame_files]
    frame_height, frame_width = get_frame_max_size(garbage_frames)
    garbage_column = random.randint(2, window_width - frame_width - 2)
    garbage_frame = random.choice(garbage_frames)
    GARBAGE_COROTINES.append(fly_garbage(canvas, garbage_column, garbage_frame))
    await asyncio.sleep(0)


def distribute_stars_in_sky(canvas, star_symbol, sky_filling):
    stars_on_sky = []
    window_height, window_width = canvas.getmaxyx()
    sky_filling_number = int((window_height * window_width * sky_filling / 100) // SYMBOL_AREA)
    for _ in range(sky_filling_number):
        star_symbol = random.choice(STAR_SYMBOLS)
        star_row = random.randint(2, window_height - 2)
        star_column = random.randint(2, window_width - 2)
        stars_on_sky.append(
            {
                "star_symbol": star_symbol,
                "star_row": star_row,
                "star_column": star_column,
            }
        )
    return stars_on_sky


def check_frame_crossing_border(canvas, frame_row, frame_column, columns_direction, rows_direction, frames):
    frame_height, frame_width = get_frame_max_size(frames)
    window_height, window_width = canvas.getmaxyx()
    if frame_column <= 1:
        frame_column = 2
        return frame_row, frame_column

    if frame_column >= window_width - frame_width - 1:
        frame_column = window_width - frame_width - 2
        return frame_row, frame_column

    if frame_row <= 1:
        frame_row = 2
        return frame_row, frame_column

    if frame_row >= window_height - frame_height - 1:
        frame_row = window_height - frame_height - 2
        return frame_row, frame_column

    return frame_row + rows_direction, frame_column + columns_direction


async def animate_spaceship(canvas, ship_row, ship_column, frames):
    for frame in frames:
        draw_frame(canvas, ship_row, ship_column, frame, negative=True)
    await asyncio.sleep(0)

    for frame in cycle(frames):
        draw_frame(canvas, ship_row, ship_column, frame)
        await asyncio.sleep(0)
        draw_frame(canvas, ship_row, ship_column, frame)
        await asyncio.sleep(0)
        draw_frame(canvas, ship_row, ship_column, frame, negative=True)


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), "*")
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), "O")
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), " ")

    row += rows_speed
    column += columns_speed

    symbol = "-" if columns_speed else "|"

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        for obstacle in OBSTACLES:
            if obstacle.has_collision(round(row), round(column)):
                OBSTACLES_IN_LAST_COLLISIONS.append(obstacle)
                canvas.addstr(round(row), round(column), " ")
                return
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), " ")
        row += rows_speed
        column += columns_speed


async def blink(canvas, row, column, symbol="*"):
    for _ in range(random.randint(1, 10)):
        await sleep(random.randint(1, 10))

    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await asyncio.sleep(0)

        await sleep(20)

        canvas.addstr(row, column, symbol, curses.A_NORMAL)
        await asyncio.sleep(0)

        await sleep(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await asyncio.sleep(0)

        await sleep(5)

        canvas.addstr(row, column, symbol, curses.A_NORMAL)
        await asyncio.sleep(0)

        await sleep(3)


async def animate_garbage(canvas):
    start_number = 0
    while True:
        for coroutine_index in range(start_number + 1):
            try:
                GARBAGE_COROTINES[coroutine_index].send(None)
            except StopIteration:
                GARBAGE_COROTINES.remove(GARBAGE_COROTINES[coroutine_index])
                garbage_fill_corotine = fill_orbit_with_garbage(canvas)
                garbage_fill_corotine.send(None)

        start_number += 1
        if start_number == GARBAGE_COUNT:
            start_number = 0
        await asyncio.sleep(0)


async def do_fireshot(canvas, ship_row, ship_column, fireshot):
    if fireshot:
        FIRE_COROTINES.append(fire(canvas, ship_row, ship_column))
    while True:
        for fire_coroutine in FIRE_COROTINES:
            try:
                fire_coroutine.send(None)
            except StopIteration:
                FIRE_COROTINES.remove(fire_coroutine)
        await asyncio.sleep(0)


def draw(canvas):
    rocket_frame_files = ["frames/rocket_frame_1.txt", "frames/rocket_frame_2.txt"]
    rocket_frames = [read_file(rocket_frame) for rocket_frame in rocket_frame_files]

    curses.curs_set(False)
    canvas.nodelay(True)
    canvas.border()

    stars_in_sky = distribute_stars_in_sky(canvas, STAR_SYMBOLS, SKY_FILLING)
    star_coroutines = [
        blink(canvas, star["star_row"], star["star_column"], star["star_symbol"]) for star in stars_in_sky
    ]

    window_height, window_width = canvas.getmaxyx()
    start_row = int(window_height // 2)
    start_column = int(window_width // 2)

    ship_column = start_column
    ship_row = start_row
    ship_coroutine = animate_spaceship(canvas, ship_row, ship_column, rocket_frames)

    for _ in range(GARBAGE_COUNT):
        garbage_fill_corotine = fill_orbit_with_garbage(canvas)
        garbage_fill_corotine.send(None)

    garbage_fly_corotine = animate_garbage(canvas)
    while True:
        for star_coroutine in star_coroutines:
            star_coroutine.send(None)

        garbage_fly_corotine.send(None)

        rows_direction, columns_direction, space_pressed = read_controls(canvas)

        if rows_direction or columns_direction:
            rows_direction, columns_direction = apply_ship_acceleration(rows_direction, columns_direction)
            ship_coroutine = animate_spaceship(canvas, ship_row, ship_column, rocket_frames)
            ship_coroutine.send(None)
            ship_row, ship_column = check_frame_crossing_border(
                canvas, ship_row, ship_column, columns_direction, rows_direction, rocket_frames
            )
            ship_coroutine = animate_spaceship(canvas, ship_row, ship_column, rocket_frames)
            ship_coroutine.send(None)

        ship_coroutine.send(None)
        canvas.border()

        fireshot_coroutine = do_fireshot(canvas, ship_row, ship_column + 2, space_pressed)
        fireshot_coroutine.send(None)

        canvas.border()

        canvas.refresh()
        time.sleep(0.1)


if __name__ == "__main__":
    curses.update_lines_cols()
    curses.wrapper(draw)
