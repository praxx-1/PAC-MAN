"""Pac-Man player entity with mouth chomp animation, life tracking, and input buffering."""

from typing import Optional
from .settings import Direction, PACMAN_SPEED_NORMAL, PACMAN_SPEED_FRIGHTENED
from .entities import Entity
from .maze import Maze


class Pacman(Entity):
    """The player character."""

    def __init__(self, spawn_tile_x: int, spawn_tile_y: int) -> None:
        super().__init__(spawn_tile_x, spawn_tile_y, speed=PACMAN_SPEED_NORMAL)
        self.spawn_pos = (spawn_tile_x, spawn_tile_y)
        self.is_ghost = False
        self.allow_door = False

        # Animation states
        self.mouth_angle: float = 0.0
        self.mouth_opening: bool = True
        self.mouth_speed: float = 8.0  # degrees per frame
        self.max_mouth_angle: float = 48.0

        # Death animation
        self.is_dying: bool = False
        self.death_timer: float = 0.0

        # Orientation for drawing
        self.facing: Direction = Direction.RIGHT

    def reset(self) -> None:
        """Resets Pac-Man to initial spawn state."""
        self.reset_position(*self.spawn_pos)
        self.direction = Direction.NONE
        self.next_direction = Direction.NONE
        self.facing = Direction.RIGHT
        self.mouth_angle = 0.0
        self.mouth_opening = True
        self.is_dying = False
        self.death_timer = 0.0

    def request_direction(self, new_dir: Direction) -> None:
        """Buffers a requested direction for pre-turning at upcoming junctions."""
        self.next_direction = new_dir

    def update(self, maze: Maze, is_power_active: bool = False) -> None:
        """Updates position, orientation, and chomp animation."""
        if self.is_dying:
            self.death_timer += 1.0 / 60.0
            return

        current_speed = PACMAN_SPEED_FRIGHTENED if is_power_active else PACMAN_SPEED_NORMAL
        self.step_movement(current_speed, maze)

        if self.direction != Direction.NONE:
            self.facing = self.direction

            # Animate mouth chomping
            if self.mouth_opening:
                self.mouth_angle += self.mouth_speed
                if self.mouth_angle >= self.max_mouth_angle:
                    self.mouth_angle = self.max_mouth_angle
                    self.mouth_opening = False
            else:
                self.mouth_angle -= self.mouth_speed
                if self.mouth_angle <= 0.0:
                    self.mouth_angle = 0.0
                    self.mouth_opening = True
        else:
            # Idle mouth half-open
            self.mouth_angle = 15.0
