import pygame
from config import (
    GRID_ROWS, GRID_COLS, CIRCLE_RADIUS, GRID_PADDING,
    WINDOW_WIDTH, WINDOW_HEIGHT,
    CIRCLE_INACTIVE, CIRCLE_ACTIVE, CIRCLE_HIT, CIRCLE_MISS
)


def build_grid():
    """
    Returns a list of (row, col, x, y) tuples for all 16 grid positions,
    evenly spaced within the window.
    """
    positions = []
    usable_w = WINDOW_WIDTH - 2 * GRID_PADDING
    usable_h = WINDOW_HEIGHT - 2 * GRID_PADDING - 80  # leave room for status bar

    col_spacing = usable_w // (GRID_COLS - 1)
    row_spacing = usable_h // (GRID_ROWS - 1)

    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            x = GRID_PADDING + col * col_spacing
            y = GRID_PADDING + 40 + row * row_spacing
            positions.append((row, col, x, y))

    return positions


def draw_grid(surface, positions, active_index=None, flash_index=None, flash_hit=True):
    """
    Draws all circles on the surface.
    - active_index: index of the currently lit target
    - flash_index: index of a briefly flashing circle (hit or miss feedback)
    - flash_hit: True = green flash, False = red flash
    """
    for i, (row, col, x, y) in enumerate(positions):
        if i == flash_index:
            color = CIRCLE_HIT if flash_hit else CIRCLE_MISS
        elif i == active_index:
            color = CIRCLE_ACTIVE
        else:
            color = CIRCLE_INACTIVE

        pygame.draw.circle(surface, color, (x, y), CIRCLE_RADIUS)
        pygame.draw.circle(surface, (200, 200, 200), (x, y), CIRCLE_RADIUS, 2)


def get_clicked_index(positions, mouse_x, mouse_y):
    """
    Returns the index of the circle clicked, or None if no circle was hit.
    """
    for i, (row, col, x, y) in enumerate(positions):
        dist = ((mouse_x - x) ** 2 + (mouse_y - y) ** 2) ** 0.5
        if dist <= CIRCLE_RADIUS:
            return i
    return None


def get_click_offset(positions, index, mouse_x, mouse_y):
    """
    Returns the Euclidean distance from the click to the center of the target.
    Used for spatial accuracy measurement.
    """
    _, _, x, y = positions[index]
    return ((mouse_x - x) ** 2 + (mouse_y - y) ** 2) ** 0.5
