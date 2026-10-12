"""AI Controller coordinating ghost target selection, predictive projection, and fuzzy logic."""

import random
from typing import Dict, List, Optional, Tuple
from .settings import Direction, GhostAlgorithm, GhostState, MAZE_COLS, MAZE_ROWS
from .maze import Maze
from .pacman import Pacman
from .ghost import Ghost
from .fuzzy_logic import GhostFuzzyEngine, FuzzyInferenceResult
from .pathfinding import toroidal_manhattan_distance


class AIController:
    """Manages target tile calculation and strategy execution for all ghosts."""

    def __init__(self) -> None:
        self.fuzzy_engine = GhostFuzzyEngine()
        self.last_fuzzy_result: Optional[FuzzyInferenceResult] = None

        # Fixed scatter corner tiles for each ghost
        self.scatter_targets = {
            "Blinky": (25, 0),    # Top-Right
            "Pinky": (2, 0),      # Top-Left
            "Inky": (27, 31),     # Bottom-Right
            "Clyde": (0, 31),     # Bottom-Left
        }

    def compute_predictive_tile(self, pacman: Pacman, lookahead_tiles: int = 4) -> Tuple[int, int]:
        """Calculates projected position ahead of Pac-Man's velocity vector."""
        dx = pacman.facing.dx
        dy = pacman.facing.dy

        # If Pac-Man is currently stationary, project along current facing
        target_x = pacman.tile_x + (dx * lookahead_tiles)
        target_y = pacman.tile_y + (dy * lookahead_tiles)

        # Wrap around horizontal boundaries
        target_x %= MAZE_COLS
        target_y = max(0, min(MAZE_ROWS - 1, target_y))

        return (target_x, target_y)

    def compute_inky_flank_tile(
        self,
        pacman: Pacman,
        blinky: Ghost,
        lead_tiles: int = 2,
    ) -> Tuple[int, int]:
        """Calculates Inky's tactical flanking target pinching Pac-Man against Blinky."""
        # 1. Pivot tile 2 spaces ahead of Pac-Man
        pivot_x = pacman.tile_x + (pacman.facing.dx * lead_tiles)
        pivot_y = pacman.tile_y + (pacman.facing.dy * lead_tiles)

        # 2. Vector from Blinky to pivot
        vec_x = pivot_x - blinky.tile_x
        vec_y = pivot_y - blinky.tile_y

        # 3. Double vector from Blinky
        target_x = (blinky.tile_x + 2 * vec_x) % MAZE_COLS
        target_y = max(0, min(MAZE_ROWS - 1, blinky.tile_y + 2 * vec_y))

        return (target_x, target_y)

    def compute_target_tile(
        self,
        ghost: Ghost,
        pacman: Pacman,
        blinky: Ghost,
        maze: Maze,
        power_pellet_active: bool = False,
        power_timer_left: float = 0.0,
    ) -> Tuple[int, int]:
        """Determines the target destination tile based on ghost personality, state, and AI mode."""
        # 1. Returning home after being eaten
        if ghost.state == GhostState.EATEN:
            return maze.ghost_house_gate

        # 2. In ghost house
        if ghost.state == GhostState.IN_HOUSE:
            return maze.ghost_house_gate

        # 3. Frightened / Power-Pellet state
        if ghost.state == GhostState.FRIGHTENED:
            # Flee to furthest corner away from Pac-Man
            pacman_pos = (pacman.tile_x, pacman.tile_y)
            corners = [(1, 1), (MAZE_COLS - 2, 1), (1, MAZE_ROWS - 2), (MAZE_COLS - 2, MAZE_ROWS - 2)]
            furthest_corner = max(corners, key=lambda c: toroidal_manhattan_distance(c, pacman_pos))
            return furthest_corner

        # 4. Scatter Mode
        if ghost.state == GhostState.SCATTER:
            return self.scatter_targets.get(ghost.name, (0, 0))

        # 5. Chase Mode (Personality and Algorithm Specific)
        algo = ghost.algorithm

        # Algorithm: Fuzzy Logic Adaptive
        if algo == GhostAlgorithm.FUZZY or ghost.name == "Clyde":
            dist = toroidal_manhattan_distance((ghost.tile_x, ghost.tile_y), (pacman.tile_x, pacman.tile_y))
            pellet_ratio = maze.remaining_pellet_ratio()
            threat = min(1.0, power_timer_left / 7.0) if power_pellet_active else 0.0

            fuzzy_res = self.fuzzy_engine.evaluate(dist, pellet_ratio, threat)
            self.last_fuzzy_result = fuzzy_res
            ghost.fuzzy_aggression = fuzzy_res.aggression_level
            ghost.speed_multiplier = fuzzy_res.speed_multiplier

            # If aggression is high (> 0.55), relentlessly hunt Pac-Man or cut him off
            if fuzzy_res.aggression_level > 0.55:
                # Modulate between direct chase and intercept
                if fuzzy_res.aggression_level > 0.8:
                    return self.compute_predictive_tile(pacman, lookahead_tiles=3)
                return (pacman.tile_x, pacman.tile_y)
            else:
                # Retreat to scatter corner when timid/passive
                return self.scatter_targets.get(ghost.name, (0, 31))

        # Algorithm: Predictive Intercept
        if algo == GhostAlgorithm.PREDICTIVE or ghost.name == "Pinky":
            return self.compute_predictive_tile(pacman, lookahead_tiles=4)

        # Inky tactical flanking
        if ghost.name == "Inky" and algo == GhostAlgorithm.BFS:
            return self.compute_inky_flank_tile(pacman, blinky, lead_tiles=2)

        # Default Direct Chase (Blinky / A* / BFS)
        return (pacman.tile_x, pacman.tile_y)

    def update_ghost_targets(
        self,
        ghosts: List[Ghost],
        pacman: Pacman,
        maze: Maze,
        power_pellet_active: bool = False,
        power_timer_left: float = 0.0,
    ) -> None:
        """Updates target tiles for all active ghosts in the scene."""
        blinky = next((g for g in ghosts if g.name == "Blinky"), ghosts[0])

        for ghost in ghosts:
            target = self.compute_target_tile(
                ghost=ghost,
                pacman=pacman,
                blinky=blinky,
                maze=maze,
                power_pellet_active=power_pellet_active,
                power_timer_left=power_timer_left,
            )
            ghost.target_tile = target
