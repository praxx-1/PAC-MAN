"""Pathfinding implementations: Breadth-First Search (BFS) and A* Search."""

from collections import deque
from dataclasses import dataclass, field
import heapq
import time
from typing import Dict, List, Optional, Set, Tuple
from .settings import Direction, MAZE_COLS
from .maze import Maze


@dataclass
class PathResult:
    """Holds path planning output, performance metrics, and exploration history."""
    path: List[Tuple[int, int]] = field(default_factory=list)
    nodes_expanded: int = 0
    visited_nodes: Set[Tuple[int, int]] = field(default_factory=set)
    execution_time_us: float = 0.0
    algorithm_name: str = ""
    target_reached: bool = False

    @property
    def path_length(self) -> int:
        return max(0, len(self.path) - 1)

    @property
    def next_direction(self) -> Direction:
        """Determines the immediate direction from start to first step."""
        if len(self.path) < 2:
            return Direction.NONE
        x1, y1 = self.path[0]
        x2, y2 = self.path[1]

        # Handle wrap around tunnel
        if x1 == 0 and x2 == MAZE_COLS - 1:
            return Direction.LEFT
        if x1 == MAZE_COLS - 1 and x2 == 0:
            return Direction.RIGHT

        dx = x2 - x1
        dy = y2 - y1
        for d in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            if d.dx == dx and d.dy == dy:
                return d
        return Direction.NONE


def toroidal_manhattan_distance(p1: Tuple[int, int], p2: Tuple[int, int], cols: int = MAZE_COLS) -> int:
    """Calculates Manhattan distance accounting for toroidal horizontal tunnel wrap."""
    x1, y1 = p1
    x2, y2 = p2
    dx = abs(x1 - x2)
    wrap_dx = min(dx, cols - dx)
    dy = abs(y1 - y2)
    return wrap_dx + dy


def euclidean_distance(p1: Tuple[int, int], p2: Tuple[int, int], cols: int = MAZE_COLS) -> float:
    """Calculates Euclidean distance accounting for tunnel wrap."""
    x1, y1 = p1
    x2, y2 = p2
    dx = abs(x1 - x2)
    wrap_dx = min(dx, cols - dx)
    dy = y1 - y2
    return (wrap_dx * wrap_dx + dy * dy) ** 0.5


def reconstruct_path(
    came_from: Dict[Tuple[int, int], Tuple[int, int]],
    current: Tuple[int, int],
) -> List[Tuple[int, int]]:
    """Reconstructs the coordinate path from start to goal."""
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def breadth_first_search(
    maze: Maze,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    is_ghost: bool = True,
    allow_door: bool = False,
    forbid_reverse_direction: Optional[Direction] = None,
) -> PathResult:
    """Breadth-First Search (BFS) shortest-path implementation.

    Explores nodes layer by layer using collections.deque (FIFO queue).
    Guarantees shortest unweighted path in unit-cost grid.
    """
    start_time = time.perf_counter_ns()

    # Wrap coordinates
    start = maze.wrap_coords(*start)
    goal = maze.wrap_coords(*goal)

    if start == goal:
        elapsed_us = (time.perf_counter_ns() - start_time) / 1000.0
        return PathResult(
            path=[start],
            nodes_expanded=0,
            visited_nodes={start},
            execution_time_us=elapsed_us,
            algorithm_name="BFS",
            target_reached=True,
        )

    queue: deque[Tuple[int, int]] = deque([start])
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    visited: Set[Tuple[int, int]] = {start}
    nodes_expanded = 0

    target_reached = False
    closest_node = start
    closest_dist = toroidal_manhattan_distance(start, goal)

    while queue:
        current = queue.popleft()
        nodes_expanded += 1

        if current == goal:
            target_reached = True
            break

        # Check for closest fallback if target is unreachable (e.g. inside a wall)
        dist = toroidal_manhattan_distance(current, goal)
        if dist < closest_dist:
            closest_dist = dist
            closest_node = current

        cx, cy = current
        neighbors = maze.get_valid_neighbors(cx, cy, is_ghost=is_ghost, allow_door=allow_door)

        for nx, ny, direction in neighbors:
            # Check 180-degree reverse prohibition at initial tile
            if current == start and forbid_reverse_direction and direction == forbid_reverse_direction:
                continue

            neighbor_pos = (nx, ny)
            if neighbor_pos not in visited:
                visited.add(neighbor_pos)
                came_from[neighbor_pos] = current
                queue.append(neighbor_pos)

    end_time = time.perf_counter_ns()
    elapsed_us = (end_time - start_time) / 1000.0

    end_tile = goal if target_reached else closest_node
    path = reconstruct_path(came_from, end_tile)

    return PathResult(
        path=path,
        nodes_expanded=nodes_expanded,
        visited_nodes=visited,
        execution_time_us=elapsed_us,
        algorithm_name="BFS",
        target_reached=target_reached,
    )


def a_star_search(
    maze: Maze,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    is_ghost: bool = True,
    allow_door: bool = False,
    forbid_reverse_direction: Optional[Direction] = None,
    heuristic_weight: float = 1.0,
) -> PathResult:
    """A* Search implementation using priority queue (heapq).

    Uses toroidal Manhattan distance as admissible heuristic h(n).
    f(n) = g(n) + w * h(n).
    """
    start_time = time.perf_counter_ns()

    start = maze.wrap_coords(*start)
    goal = maze.wrap_coords(*goal)

    if start == goal:
        elapsed_us = (time.perf_counter_ns() - start_time) / 1000.0
        return PathResult(
            path=[start],
            nodes_expanded=0,
            visited_nodes={start},
            execution_time_us=elapsed_us,
            algorithm_name="A*",
            target_reached=True,
        )

    # Priority queue entries: (f_score, h_score, tie_breaker, (x, y))
    tie_breaker = 0
    start_h = toroidal_manhattan_distance(start, goal)
    open_heap: List[Tuple[float, float, int, Tuple[int, int]]] = [
        (start_h * heuristic_weight, start_h, tie_breaker, start)
    ]

    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g_score: Dict[Tuple[int, int], int] = {start: 0}
    visited: Set[Tuple[int, int]] = set()
    nodes_expanded = 0

    target_reached = False
    closest_node = start
    closest_dist = start_h

    while open_heap:
        current_f, current_h, _, current = heapq.heappop(open_heap)

        if current in visited:
            continue

        visited.add(current)
        nodes_expanded += 1

        if current == goal:
            target_reached = True
            break

        # Check closest candidate
        if current_h < closest_dist:
            closest_dist = current_h
            closest_node = current

        cx, cy = current
        current_g = g_score[current]
        neighbors = maze.get_valid_neighbors(cx, cy, is_ghost=is_ghost, allow_door=allow_door)

        for nx, ny, direction in neighbors:
            if current == start and forbid_reverse_direction and direction == forbid_reverse_direction:
                continue

            neighbor_pos = (nx, ny)
            tentative_g = current_g + 1

            if tentative_g < g_score.get(neighbor_pos, float("inf")):
                came_from[neighbor_pos] = current
                g_score[neighbor_pos] = tentative_g
                h = toroidal_manhattan_distance(neighbor_pos, goal)
                f = tentative_g + (h * heuristic_weight)
                tie_breaker += 1
                heapq.heappush(open_heap, (f, h, tie_breaker, neighbor_pos))

    end_time = time.perf_counter_ns()
    elapsed_us = (end_time - start_time) / 1000.0

    end_tile = goal if target_reached else closest_node
    path = reconstruct_path(came_from, end_tile)

    return PathResult(
        path=path,
        nodes_expanded=nodes_expanded,
        visited_nodes=visited,
        execution_time_us=elapsed_us,
        algorithm_name="A*",
        target_reached=target_reached,
    )
