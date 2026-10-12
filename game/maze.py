"""Maze representation, tile parsing, pellet tracking, and tunnel handling."""

from typing import Dict, List, Optional, Set, Tuple
from .settings import MAZE_COLS, MAZE_ROWS, Direction

# Classic 28 x 31 arcade Pac-Man maze map:
# '#' = Wall
# '.' = Standard Pellet (dot)
# 'o' = Power Pellet (energizer)
# ' ' = Empty path / tunnel
# '_' = Ghost House Door
# 'H' = Ghost House Interior
# 'P' = Pac-Man starting location
# 'B' = Blinky starting location
# 'K' = Pinky starting location
# 'I' = Inky starting location
# 'C' = Clyde starting location
DEFAULT_MAZE_LAYOUT = [
    "############################",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#o####.#####.##.#####.####o#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "#.####.##.########.##.####.#",
    "#.####.##.########.##.####.#",
    "#......##....##....##......#",
    "######.##### ## #####.######",
    "     #.##### ## #####.#     ",
    "     #.##    B     ##.#     ",
    "     #.## ###__### ##.#     ",
    "######.## #  K   # ##.######",
    "      .   # I  C #   .      ",
    "######.## #      # ##.######",
    "     #.## ######## ##.#     ",
    "     #.##          ##.#     ",
    "     #.## ######## ##.#     ",
    "######.## ######## ##.######",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#.####.#####.##.#####.####.#",
    "#o..##.......P........##..o#",
    "###.##.##.########.##.##.###",
    "###.##.##.########.##.##.###",
    "#......##....##....##......#",
    "#.##########.##.##########.#",
    "#.##########.##.##########.#",
    "#..........................#",
    "############################",
]

# Ensure exactly 31 rows and 28 cols
assert len(DEFAULT_MAZE_LAYOUT) == MAZE_ROWS
assert all(len(row) == MAZE_COLS for row in DEFAULT_MAZE_LAYOUT)


class Maze:
    """Manages the grid, walls, pellets, and coordinate conversions."""

    def __init__(self, layout: Optional[List[str]] = None) -> None:
        self.raw_layout = layout or list(DEFAULT_MAZE_LAYOUT)
        self.cols = MAZE_COLS
        self.rows = MAZE_ROWS

        # Entity spawn coordinates
        self.pacman_spawn: Tuple[int, int] = (13, 23)
        self.blinky_spawn: Tuple[int, int] = (13, 11)
        self.pinky_spawn: Tuple[int, int] = (13, 14)
        self.inky_spawn: Tuple[int, int] = (11, 14)
        self.clyde_spawn: Tuple[int, int] = (15, 14)
        self.ghost_house_gate: Tuple[int, int] = (13, 12)

        # Tunnel row (typically row 14)
        self.tunnel_row = 14

        # Static sets
        self.walls: Set[Tuple[int, int]] = set()
        self.ghost_doors: Set[Tuple[int, int]] = set()
        self.ghost_house_tiles: Set[Tuple[int, int]] = set()

        # Dynamic pellet sets
        self.pellets: Set[Tuple[int, int]] = set()
        self.power_pellets: Set[Tuple[int, int]] = set()
        self._initial_pellets: Set[Tuple[int, int]] = set()
        self._initial_power_pellets: Set[Tuple[int, int]] = set()

        self._parse_layout()

    def _parse_layout(self) -> None:
        """Parses the layout into spatial sets and initial spawn points."""
        for y, row in enumerate(self.raw_layout):
            for x, char in enumerate(row):
                coord = (x, y)
                if char == "#":
                    self.walls.add(coord)
                elif char == ".":
                    self.pellets.add(coord)
                elif char == "o":
                    self.power_pellets.add(coord)
                elif char == "_":
                    self.ghost_doors.add(coord)
                elif char == "H":
                    self.ghost_house_tiles.add(coord)
                elif char == "P":
                    self.pacman_spawn = coord
                elif char == "B":
                    self.blinky_spawn = coord
                elif char == "K":
                    self.pinky_spawn = coord
                    self.ghost_house_tiles.add(coord)
                elif char == "I":
                    self.inky_spawn = coord
                    self.ghost_house_tiles.add(coord)
                elif char == "C":
                    self.clyde_spawn = coord
                    self.ghost_house_tiles.add(coord)

        # Also designate the rest of the house interior
        for hx in range(10, 18):
            for hy in range(12, 16):
                if (hx, hy) not in self.walls and (hx, hy) not in self.ghost_doors:
                    self.ghost_house_tiles.add((hx, hy))

        self._initial_pellets = set(self.pellets)
        self._initial_power_pellets = set(self.power_pellets)

    def is_wall(self, x: int, y: int) -> bool:
        """Returns True if the tile at (x, y) is a solid wall."""
        nx, ny = self.wrap_coords(x, y)
        if ny < 0 or ny >= self.rows:
            return True
        return (nx, ny) in self.walls

    def is_ghost_door(self, x: int, y: int) -> bool:
        """Returns True if the tile is a ghost door threshold."""
        nx, ny = self.wrap_coords(x, y)
        return (nx, ny) in self.ghost_doors

    def is_ghost_house(self, x: int, y: int) -> bool:
        """Returns True if the tile is inside the ghost house interior."""
        nx, ny = self.wrap_coords(x, y)
        return (nx, ny) in self.ghost_house_tiles

    def is_tunnel(self, x: int, y: int) -> bool:
        """Returns True if the position is in the side wrap-around tunnels."""
        return y == self.tunnel_row and (x < 6 or x >= self.cols - 6)

    def is_walkable(
        self,
        x: int,
        y: int,
        is_ghost: bool = False,
        allow_door: bool = False,
    ) -> bool:
        """Determines if a tile can be traversed."""
        nx, ny = self.wrap_coords(x, y)

        if ny < 0 or ny >= self.rows:
            return False

        if (nx, ny) in self.walls:
            return False

        if (nx, ny) in self.ghost_doors:
            return is_ghost and allow_door

        if (nx, ny) in self.ghost_house_tiles and not is_ghost:
            return False

        return True

    def wrap_coords(self, x: int, y: int) -> Tuple[int, int]:
        """Wraps horizontal coordinates across side tunnels."""
        wrapped_x = x % self.cols
        return (wrapped_x, y)

    def get_valid_neighbors(
        self,
        x: int,
        y: int,
        is_ghost: bool = False,
        allow_door: bool = False,
    ) -> List[Tuple[int, int, Direction]]:
        """Returns all walkable neighboring coordinates with the movement direction."""
        neighbors: List[Tuple[int, int, Direction]] = []

        # Standard 4 directions: UP, LEFT, DOWN, RIGHT
        for direction in [Direction.UP, Direction.LEFT, Direction.DOWN, Direction.RIGHT]:
            nx = x + direction.dx
            ny = y + direction.dy
            wrapped_x, wrapped_y = self.wrap_coords(nx, ny)

            if self.is_walkable(wrapped_x, wrapped_y, is_ghost=is_ghost, allow_door=allow_door):
                neighbors.append((wrapped_x, wrapped_y, direction))

        return neighbors

    def eat_pellet(self, x: int, y: int) -> Optional[str]:
        """Consumes a pellet or energizer at (x, y) if present.

        Returns 'pellet', 'power_pellet', or None.
        """
        coord = self.wrap_coords(x, y)
        if coord in self.pellets:
            self.pellets.remove(coord)
            return "pellet"
        if coord in self.power_pellets:
            self.power_pellets.remove(coord)
            return "power_pellet"
        return None

    def total_pellets(self) -> int:
        """Returns the total number of pellets and power pellets originally present."""
        return len(self._initial_pellets) + len(self._initial_power_pellets)

    def remaining_pellets(self) -> int:
        """Returns the count of remaining unconsumed pellets."""
        return len(self.pellets) + len(self.power_pellets)

    def remaining_pellet_ratio(self) -> float:
        """Returns remaining pellets as a normalized ratio [0.0, 1.0]."""
        total = self.total_pellets()
        if total == 0:
            return 0.0
        return self.remaining_pellets() / total

    def is_cleared(self) -> bool:
        """Returns True if all dots and power pellets have been eaten."""
        return len(self.pellets) == 0 and len(self.power_pellets) == 0

    def reset_pellets(self) -> None:
        """Restores all pellets and power pellets for a new level/restart."""
        self.pellets = set(self._initial_pellets)
        self.power_pellets = set(self._initial_power_pellets)
