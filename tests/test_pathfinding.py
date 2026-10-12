"""Tests comparing Breadth-First Search (BFS) and A* Search pathfinding."""

import pytest
from game.settings import Direction
from game.maze import Maze
from game.pathfinding import (
    a_star_search, breadth_first_search,
    toroidal_manhattan_distance, euclidean_distance,
)


@pytest.fixture
def maze():
    return Maze()


def test_toroidal_manhattan_distance():
    # Regular distance
    assert toroidal_manhattan_distance((1, 1), (4, 5), cols=28) == (3 + 4)  # 7

    # Wrap-around across tunnel (col 0 and col 27 are 1 step apart!)
    assert toroidal_manhattan_distance((0, 14), (27, 14), cols=28) == 1
    assert toroidal_manhattan_distance((1, 14), (26, 14), cols=28) == 3


def test_bfs_and_astar_same_path_length(maze):
    """Both BFS and A* must guarantee shortest path length on unit grids."""
    test_cases = [
        ((1, 1), (1, 5)),
        ((1, 1), (26, 1)),
        ((13, 23), (1, 1)),
        ((1, 29), (26, 29)),
        ((0, 14), (27, 14)),  # Across tunnel
    ]

    for start, goal in test_cases:
        bfs_res = breadth_first_search(maze, start, goal, is_ghost=True)
        astar_res = a_star_search(maze, start, goal, is_ghost=True)

        assert bfs_res.target_reached is True, f"BFS failed to reach {goal} from {start}"
        assert astar_res.target_reached is True, f"A* failed to reach {goal} from {start}"
        assert bfs_res.path_length == astar_res.path_length, (
            f"Path lengths differ for {start}->{goal}: BFS={bfs_res.path_length}, A*={astar_res.path_length}"
        )


def test_astar_expands_fewer_or_equal_nodes(maze):
    """A* with admissible heuristic should explore fewer or equal nodes than uninformed BFS."""
    start = (1, 1)
    goal = (26, 29)  # Opposite corner

    bfs_res = breadth_first_search(maze, start, goal, is_ghost=True)
    astar_res = a_star_search(maze, start, goal, is_ghost=True)

    assert astar_res.nodes_expanded <= bfs_res.nodes_expanded
    assert astar_res.nodes_expanded < bfs_res.nodes_expanded  # Significant pruning on diagonal cross


def test_start_equals_goal(maze):
    pos = (13, 23)
    bfs_res = breadth_first_search(maze, pos, pos, is_ghost=True)
    astar_res = a_star_search(maze, pos, pos, is_ghost=True)

    assert bfs_res.path == [pos]
    assert bfs_res.path_length == 0
    assert bfs_res.nodes_expanded == 0

    assert astar_res.path == [pos]
    assert astar_res.path_length == 0
    assert astar_res.nodes_expanded == 0


def test_unreachable_target_fallback(maze):
    """When goal is inside a solid wall, search returns path to closest accessible neighbor."""
    start = (1, 1)
    wall_goal = (0, 0)  # Solid wall

    bfs_res = breadth_first_search(maze, start, wall_goal, is_ghost=True)
    astar_res = a_star_search(maze, start, wall_goal, is_ghost=True)

    assert bfs_res.target_reached is False
    assert astar_res.target_reached is False
    assert len(bfs_res.path) > 0
    assert len(astar_res.path) > 0
    # Destination in path is walkable
    assert maze.is_walkable(*bfs_res.path[-1], is_ghost=True)


def test_forbid_reverse_direction(maze):
    """Initial direction reverse restriction is respected."""
    start = (1, 2)
    goal = (1, 5)

    # If moving UP, forbid DOWN reversal
    astar_res = a_star_search(
        maze,
        start,
        goal,
        is_ghost=True,
        forbid_reverse_direction=Direction.DOWN,
    )

    if len(astar_res.path) >= 2:
        step_dir = astar_res.next_direction
        assert step_dir != Direction.DOWN
