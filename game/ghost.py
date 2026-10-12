"""Ghost agent implementation with state machine, navigation, and telemetry."""

from typing import List, Optional, Set, Tuple
from .settings import (
    COLOR_BLINKY, COLOR_PINKY, COLOR_INKY, COLOR_CLYDE,
    Direction, GhostAlgorithm, GhostState,
    GHOST_SPEED_NORMAL, GHOST_SPEED_SCATTER, GHOST_SPEED_FRIGHTENED,
    GHOST_SPEED_EATEN, GHOST_SPEED_TUNNEL,
    TILE_SIZE,
)
from .entities import Entity
from .maze import Maze
from .pathfinding import PathResult, a_star_search, breadth_first_search, toroidal_manhattan_distance


class Ghost(Entity):
    """Ghost AI agent capable of dynamic pathfinding and state-driven behavior."""

    def __init__(
        self,
        name: str,
        color: Tuple[int, int, int],
        spawn_tile: Tuple[int, int],
        scatter_tile: Tuple[int, int],
        algorithm: GhostAlgorithm,
    ) -> None:
        super().__init__(spawn_tile[0], spawn_tile[1], speed=GHOST_SPEED_NORMAL)
        self.name = name
        self.base_color = color
        self.spawn_pos = spawn_tile
        self.scatter_tile = scatter_tile
        self.algorithm = algorithm

        self.is_ghost = True
        self.allow_door = False

        # State Machine
        self.state: GhostState = GhostState.IN_HOUSE
        self.previous_state: GhostState = GhostState.SCATTER

        # Target tile for pathfinding
        self.target_tile: Tuple[int, int] = scatter_tile

        # AI & Pathfinding Cache
        self.current_path: List[Tuple[int, int]] = []
        self.visited_frontier: Set[Tuple[int, int]] = set()
        self.nodes_expanded: int = 0
        self.last_execution_time_us: float = 0.0
        self.last_path_length: int = 0
        self.fuzzy_aggression: float = 0.5
        self.speed_multiplier: float = 1.0

        # House & release management
        self.house_bob_direction = 1
        self.house_bob_timer = 0.0
        self.release_pellet_threshold = 0
        self.release_time_threshold = 0.0
        self.is_released = False

        # Visuals
        self.animation_frame = 0
        self.animation_timer = 0.0

    def reset(self) -> None:
        """Resets the ghost to initial spawn position and state."""
        self.reset_position(*self.spawn_pos)
        self.state = GhostState.IN_HOUSE if self.name != "Blinky" else GhostState.SCATTER
        self.is_released = (self.name == "Blinky")
        self.allow_door = False
        self.current_path = []
        self.visited_frontier = set()
        self.target_tile = self.scatter_tile
        self.speed_multiplier = 1.0

    def set_algorithm(self, algo: GhostAlgorithm) -> None:
        """Dynamically switches pathfinding/AI algorithm in real-time."""
        self.algorithm = algo

    def enter_frightened(self) -> None:
        """Transitions into Frightened state and reverses direction immediately."""
        if self.state not in [GhostState.EATEN, GhostState.IN_HOUSE]:
            self.state = GhostState.FRIGHTENED
            # Classic Pac-Man rule: Ghosts reverse direction when entering frightened mode
            self.direction = self.direction.opposite

    def enter_eaten(self) -> None:
        """Transitions into Eaten eyes mode returning to ghost house."""
        self.state = GhostState.EATEN
        self.allow_door = True

    def calculate_path(self, maze: Maze, goal_tile: Tuple[int, int]) -> PathResult:
        """Computes a path to the goal using the currently assigned algorithm."""
        start_tile = (self.tile_x, self.tile_y)
        forbid_rev = self.direction.opposite if self.direction != Direction.NONE else None

        # Choose search implementation
        if self.algorithm == GhostAlgorithm.BFS:
            result = breadth_first_search(
                maze,
                start=start_tile,
                goal=goal_tile,
                is_ghost=True,
                allow_door=self.allow_door,
                forbid_reverse_direction=forbid_rev,
            )
        else:
            # Default to A* Search (used by A_STAR, PREDICTIVE, and FUZZY target selectors)
            result = a_star_search(
                maze,
                start=start_tile,
                goal=goal_tile,
                is_ghost=True,
                allow_door=self.allow_door,
                forbid_reverse_direction=forbid_rev,
            )

        self.current_path = result.path
        self.visited_frontier = result.visited_nodes
        self.nodes_expanded = result.nodes_expanded
        self.last_execution_time_us = result.execution_time_us
        self.last_path_length = result.path_length
        return result

    def get_current_speed(self, maze: Maze) -> float:
        """Calculates current speed considering state, tunnel, and fuzzy aggression."""
        if self.state == GhostState.EATEN:
            return GHOST_SPEED_EATEN

        if maze.is_tunnel(self.tile_x, self.tile_y):
            return GHOST_SPEED_TUNNEL

        if self.state == GhostState.FRIGHTENED:
            return GHOST_SPEED_FRIGHTENED

        base_speed = GHOST_SPEED_SCATTER if self.state == GhostState.SCATTER else GHOST_SPEED_NORMAL
        return base_speed * self.speed_multiplier

    def update_house_state(self, maze: Maze) -> None:
        """Handles bobbing inside ghost house and moving up through the door upon release."""
        gate_x, gate_y = maze.ghost_house_gate

        if not self.is_released:
            # Bob gently up and down inside the house
            self.house_bob_timer += 0.05
            target_center_y = self.spawn_pos[1] * TILE_SIZE + (TILE_SIZE / 2.0)
            bob_offset = 4.0 * (1 if int(self.house_bob_timer) % 2 == 0 else -1)
            self.y = target_center_y + bob_offset
            return

        # Leaving ghost house
        self.allow_door = True
        gate_pixel_x = gate_x * TILE_SIZE + (TILE_SIZE / 2.0)
        gate_pixel_y = (gate_y - 1) * TILE_SIZE + (TILE_SIZE / 2.0)

        # First align horizontally with the gate
        if abs(self.x - gate_pixel_x) > 1.5:
            self.x += 1.5 if self.x < gate_pixel_x else -1.5
            self.direction = Direction.RIGHT if self.x < gate_pixel_x else Direction.LEFT
        # Then move upward through the door
        elif self.y > gate_pixel_y:
            self.y -= 1.5
            self.direction = Direction.UP
        else:
            # Successfully exited the ghost house!
            self.snap_to_tile_center()
            self.allow_door = False
            self.state = GhostState.CHASE
            self.direction = Direction.LEFT

    def update(self, maze: Maze, pacman_pos: Tuple[int, int]) -> None:
        """Executes ghost movement, state transitions, and path navigation."""
        self.animation_timer += 0.15
        if self.animation_timer >= 1.0:
            self.animation_timer = 0.0
            self.animation_frame = 1 - self.animation_frame

        if self.state == GhostState.IN_HOUSE:
            self.update_house_state(maze)
            self.update_tile_coords()
            return

        # Check if returning eaten eyes reached ghost house gate
        if self.state == GhostState.EATEN:
            gate_x, gate_y = maze.ghost_house_gate
            if (self.tile_x, self.tile_y) == (gate_x, gate_y) or (self.tile_x, self.tile_y) == (gate_x, gate_y + 1):
                self.state = GhostState.IN_HOUSE
                self.is_released = True
                self.allow_door = True
                return

        current_speed = self.get_current_speed(maze)

        # Junction Decision: when centered on a tile, query AI for next direction
        if self.is_tile_centered(tolerance=max(current_speed, 2.0)):
            # Recalculate path to target tile
            result = self.calculate_path(maze, self.target_tile)
            next_dir = result.next_direction

            if next_dir != Direction.NONE:
                self.next_direction = next_dir
            else:
                # Fallback: pick best available neighbor minimizing distance to target
                neighbors = maze.get_valid_neighbors(
                    self.tile_x,
                    self.tile_y,
                    is_ghost=True,
                    allow_door=self.allow_door,
                )
                valid_moves = [
                    (nx, ny, d) for nx, ny, d in neighbors
                    if d != self.direction.opposite or len(neighbors) == 1
                ]
                if valid_moves:
                    best_move = min(
                        valid_moves,
                        key=lambda m: toroidal_manhattan_distance((m[0], m[1]), self.target_tile)
                    )
                    self.next_direction = best_move[2]

        # Execute physical movement
        self.step_movement(current_speed, maze)
