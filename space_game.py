import asyncio
from asyncio.tasks import sleep
import time
import curses
import random

from itertools import cycle

from curses_tools import draw_frame, read_controls

STAR_SYMBOLS = "+*.:"
SKY_FILLING = 30


def read_file(filename):
    with open(filename, "r") as my_file:
        file_contents = my_file.read()
    return file_contents


def distribute_stars_on_sky(canvas, star_symbol, sky_filling):
    stars_on_sky = []
    window_height, window_width = canvas.getmaxyx()
    sky_filling_number = int((window_height * window_width * sky_filling / 100) // 25)
    for _ in range(sky_filling_number):
        star_symbol = random.choice(STAR_SYMBOLS)
        star_height = random.randint(2, window_height - 2)
        star_width = random.randint(2, window_width - 2)
        stars_on_sky.append(
            {
                "star_symbol": star_symbol,
                "star_height": star_height,
                "star_width": star_width,
            }
        )
    return stars_on_sky


async def animate_spaceship(canvas, start_row, start_column, frames):
    for frame in cycle(frames):
        draw_frame(canvas, start_row, start_column, frame)
        canvas.refresh()
        await asyncio.sleep(0)
        draw_frame(canvas, start_row, start_column, frame, negative=True)


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
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), " ")
        row += rows_speed
        column += columns_speed


async def blink(canvas, row, column, symbol="*"):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_NORMAL)
        await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_NORMAL)
        await asyncio.sleep(0)


async def draw_blink(canvas, star_coroutines):
    for multiplier in [20, 3, 5, 3]:
        for star_coroutine in star_coroutines:
            star_coroutine.send(None)
        canvas.refresh()
        await asyncio.sleep(0)
        time.sleep(0.1 * multiplier)


async def one_draw_blink(canvas, coroutine):
    for multiplier in [20, 3, 5, 3]:
        coroutine.send(None)
        time.sleep(0.1 * multiplier)
    await time.sleep(0)


def draw(canvas):
    frame_files = ["frames/rocket_frame_1.txt", "frames/rocket_frame_2.txt"]
    frames = [read_file(frame) for frame in frame_files]
    canvas.border()
    curses.curs_set(False)
    stars_on_sky = distribute_stars_on_sky(canvas, STAR_SYMBOLS, SKY_FILLING)
    star_coroutines = [
        blink(canvas, star["star_height"], star["star_width"], star["star_symbol"]) for star in stars_on_sky
    ]
    window_height, window_width = canvas.getmaxyx()
    start_column = int(window_height // 2)
    start_row = int(window_width // 2)
    get_fire = True
    fire_coroutine = fire(canvas, start_column, start_row)
    ship_coroutines = animate_spaceship(canvas, start_column, start_row, frames)
    while True:
        draw_blink_coroutins = draw_blink(canvas, star_coroutines)
        draw_blink_coroutins.send(None)

        ship_coroutines.send(None)

        if get_fire:
            try:
                fire_coroutine.send(None)
                canvas.refresh()
            except StopIteration:
                canvas.border()
                get_fire = False

        time.sleep(0.1)

        canvas.refresh()


if __name__ == "__main__":
    curses.update_lines_cols()
    curses.wrapper(draw)
