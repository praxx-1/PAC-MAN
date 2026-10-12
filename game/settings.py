"""Game constants, display settings, color definitions, and control bindings."""

from enum import Enum
from typing import Tuple

# Screen & Grid Dimensions
TILE_SIZE = 24
MAZE_COLS = 28
MAZE_ROWS = 31

# Layout calculations
MAZE_WIDTH = MAZE_COLS * TILE_SIZE    # 672 px
MAZE_HEIGHT = MAZE_ROWS * TILE_SIZE   # 744 px
HUD_TOP_HEIGHT = 48                   # Top header for score / high score
MAZE_OFFSET_Y = HUD_TOP_HEIGHT

SIDEBAR_WIDTH = 380                   # Telemetry & AI comparison panel
SCREEN_WIDTH = MAZE_WIDTH + SIDEBAR_WIDTH  # 1052 px
SCREEN_HEIGHT = MAZE_HEIGHT + HUD_TOP_HEIGHT + 24  # 816 px

FPS = 60

# Speeds (in pixels per frame at 60 FPS)
# 1 tile = 24 pixels. A speed of 2.0 = 2 px/frame = 120 px/sec = 5 tiles/sec.
PACMAN_SPEED_NORMAL = 2.4
PACMAN_SPEED_FRIGHTENED = 2.8
GHOST_SPEED_NORMAL = 2.1
GHOST_SPEED_SCATTER = 2.1
GHOST_SPEED_FRIGHTENED = 1.3
GHOST_SPEED_EATEN = 4.8
GHOST_SPEED_TUNNEL = 1.2

# Timing & Durations (in seconds)
FRIGHTENED_DURATION = 7.0
FRIGHTENED_FLASH_START = 2.5  # Start flashing when 2.5s remaining
FRUIT_SPAWN_DURATION = 10.0

# Scatter-Chase Wave cycles (durations in seconds for Level 1)
# Waves: Scatter 7s, Chase 20s, Scatter 7s, Chase 20s, Scatter 5s, Chase 20s, Scatter 5s, Chase infinite
WAVE_DURATIONS = [
    (True, 7.0),    # Scatter
    (False, 20.0),  # Chase
    (True, 7.0),    # Scatter
    (False, 20.0),  # Chase
    (True, 5.0),    # Scatter
    (False, 20.0),  # Chase
    (True, 5.0),    # Scatter
    (False, 999999.0)  # Permanent Chase
]

# Scoring Constants
SCORE_PELLET = 10
SCORE_POWER_PELLET = 50
SCORE_GHOST_BASE = 200  # 200, 400, 800, 1600 per power pellet
SCORE_FRUIT = 100

# Classic Arcade Color Palette
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_MAZE_WALL = (25, 25, 200)         # Deep arcade neon blue
COLOR_MAZE_BORDER = (50, 75, 255)       # Outer glow
COLOR_MAZE_GATE = (255, 184, 222)       # Ghost house door pink

COLOR_PELLET = (255, 183, 174)          # Pale peach
COLOR_POWER_PELLET = (255, 255, 255)    # Bright energizer

COLOR_PACMAN = (255, 238, 0)            # Classic Pac-Man Yellow

# Ghost Signatures
COLOR_BLINKY = (255, 0, 0)              # Red (Shadow)
COLOR_PINKY = (255, 184, 255)           # Pink (Speedy)
COLOR_INKY = (0, 220, 255)              # Cyan (Bashful)
COLOR_CLYDE = (255, 184, 82)            # Orange (Pokey)

# Ghost States Colors
COLOR_FRIGHTENED_BLUE = (33, 33, 255)   # Dark blue
COLOR_FRIGHTENED_WHITE = (240, 240, 255) # Flash white
COLOR_GHOST_EYE = (255, 255, 255)
COLOR_GHOST_PUPIL = (33, 33, 222)

# UI & Telemetry Colors
COLOR_BG_SIDEBAR = (14, 18, 28)
COLOR_CARD_BG = (22, 28, 44)
COLOR_CARD_BORDER = (45, 55, 80)
COLOR_TEXT_TITLE = (255, 215, 0)
COLOR_TEXT_PRIMARY = (230, 235, 245)
COLOR_TEXT_MUTED = (140, 150, 175)
COLOR_ACCENT_GREEN = (46, 213, 115)
COLOR_ACCENT_RED = (255, 71, 87)
COLOR_ACCENT_ORANGE = (255, 165, 2)
COLOR_ACCENT_PURPLE = (165, 94, 234)

# Pathfinding Visualizer Colors
COLOR_PATH_A_STAR = (255, 60, 60)
COLOR_PATH_BFS = (0, 210, 255)
COLOR_PATH_PREDICTIVE = (255, 140, 255)
COLOR_PATH_FUZZY = (255, 175, 50)
COLOR_TARGET_MARKER = (255, 255, 0)
COLOR_FRONTIER = (70, 90, 130)

# Directions represented as (dx, dy)
class Direction(Enum):
    NONE = (0, 0)
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    @property
    def opposite(self) -> "Direction":
        if self == Direction.UP:
            return Direction.DOWN
        if self == Direction.DOWN:
            return Direction.UP
        if self == Direction.LEFT:
            return Direction.RIGHT
        if self == Direction.RIGHT:
            return Direction.LEFT
        return Direction.NONE


# Ghost AI Algorithms
class GhostAlgorithm(str, Enum):
    A_STAR = "A* Search"
    BFS = "BFS Search"
    PREDICTIVE = "Predictive Intercept"
    FUZZY = "Fuzzy Logic Adaptive"


# Ghost Operating State
class GhostState(str, Enum):
    IN_HOUSE = "IN_HOUSE"
    CHASE = "CHASE"
    SCATTER = "SCATTER"
    FRIGHTENED = "FRIGHTENED"
    EATEN = "EATEN"
