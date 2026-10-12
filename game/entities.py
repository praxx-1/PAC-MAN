"""Base entity mechanics with subpixel movement, grid snapping, and tunnel wrapping."""

from typing import Optional, Tuple
from .settings import Direction, TILE_SIZE, MAZE_COLS, MAZE_ROWS
from .maze import Maze


class Entity:
    """Base class for movable actors (Pac-Man and Ghosts)."""

    def __init__(self, tile_x: int, tile_y: int, speed: float = 2.0) -> None:
        self.tile_x: int = tile_x
        self.tile_y: int = tile_y
        self.speed: float = speed

        # Continuous pixel coordinates (centered on tile)
        self.x: float = tile_x * TILE_SIZE + (TILE_SIZE / 2.0)
        self.y: float = tile_y * TILE_SIZE + (TILE_SIZE / 2.0)

        self.direction: Direction = Direction.NONE
        self.next_direction: Direction = Direction.NONE

        self.is_ghost: bool = False
        self.allow_door: bool = False

    def reset_position(self, tile_x: int, tile_y: int) -> None:
        """Resets the entity to the center of a specified tile."""
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.x = tile_x * TILE_SIZE + (TILE_SIZE / 2.0)
        self.y = tile_y * TILE_SIZE + (TILE_SIZE / 2.0)
        self.direction = Direction.NONE
        self.next_direction = Direction.NONE

    def update_tile_coords(self) -> None:
        """Derives discrete tile indices from pixel position."""
        self.tile_x = int(self.x // TILE_SIZE)
        self.tile_y = int(self.y // TILE_SIZE)

    def is_tile_centered(self, tolerance: float = 2.5) -> bool:
        """Checks if the entity is currently close to the geometric center of its tile."""
        target_center_x = self.tile_x * TILE_SIZE + (TILE_SIZE / 2.0)
        target_center_y = self.tile_y * TILE_SIZE + (TILE_SIZE / 2.0)
        return (abs(self.x - target_center_x) <= tolerance and
                abs(self.y - target_center_y) <= tolerance)

    def snap_to_tile_center(self) -> None:
        """Snaps coordinates to the exact geometric center of the current tile."""
        self.x = self.tile_x * TILE_SIZE + (TILE_SIZE / 2.0)
        self.y = self.tile_y * TILE_SIZE + (TILE_SIZE / 2.0)

    def can_move_in_direction(self, direction: Direction, maze: Maze) -> bool:
        """Checks if the next adjacent tile in the given direction is walkable."""
        if direction == Direction.NONE:
            return True

        target_tx = self.tile_x + direction.dx
        target_ty = self.tile_y + direction.dy

        # Allow horizontal tunnel wrap
        target_tx, target_ty = maze.wrap_coords(target_tx, target_ty)

        return maze.is_walkable(
            target_tx,
            target_ty,
            is_ghost=self.is_ghost,
            allow_door=self.allow_door,
        )

    def step_movement(self, move_speed: float, maze: Maze) -> None:
        """Executes one frame of collision-checked directional movement with tunnel wrap."""
        # 1. Immediate 180-degree reversal check (can reverse anytime without centering)
        if self.next_direction != Direction.NONE and self.next_direction == self.direction.opposite:
            self.direction = self.next_direction
            self.next_direction = Direction.NONE

        # 2. Orthogonal direction change check when aligned with tile center
        elif self.next_direction != Direction.NONE and self.next_direction != self.direction:
            if self.is_tile_centered(tolerance=max(move_speed, 2.0)):
                if self.can_move_in_direction(self.next_direction, maze):
                    self.snap_to_tile_center()
                    self.direction = self.next_direction
                    self.next_direction = Direction.NONE

        # 3. Check forward movement validity
        if self.direction != Direction.NONE:
            target_center_x = self.tile_x * TILE_SIZE + (TILE_SIZE / 2.0)
            target_center_y = self.tile_y * TILE_SIZE + (TILE_SIZE / 2.0)

            # If approaching or at tile center, check if the upcoming tile is blocked
            blocked = False
            if not self.can_move_in_direction(self.direction, maze):
                # If moving right/down and past center, or moving left/up and past center
                if (self.direction == Direction.RIGHT and self.x >= target_center_x) or \
                   (self.direction == Direction.LEFT and self.x <= target_center_x) or \
                   (self.direction == Direction.DOWN and self.y >= target_center_y) or \
                   (self.direction == Direction.UP and self.y <= target_center_y):
                    self.snap_to_tile_center()
                    blocked = True

            if not blocked:
                self.x += self.direction.dx * move_speed
                self.y += self.direction.dy * move_speed

        # 4. Handle Tunnel wrap-around at maze borders
        total_width = MAZE_COLS * TILE_SIZE
        if self.x < 0:
            self.x += total_width
        elif self.x >= total_width:
            self.x -= total_width

        # 5. Refresh tile coordinates
        self.update_tile_coords()
        # Keep horizontal tile coordinate bounded
        self.tile_x %= MAZE_COLS
