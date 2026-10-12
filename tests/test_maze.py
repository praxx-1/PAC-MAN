"""Tests for maze layout, collision geometry, wraparound, and pellet tracking."""

import pytest
from game.settings import MAZE_COLS, MAZE_ROWS, Direction
from game.maze import Maze, DEFAULT_MAZE_LAYOUT


def test_maze_dimensions():
    maze = Maze()
    assert maze.cols == MAZE_COLS == 28
    assert maze.rows == MAZE_ROWS == 31
    assert len(DEFAULT_MAZE_LAYOUT) == 31
    assert all(len(row) == 28 for row in DEFAULT_MAZE_LAYOUT)


def test_wall_detection():
    maze = Maze()
    # Corners are solid walls
    assert maze.is_wall(0, 0) is True
    assert maze.is_wall(27, 0) is True
    assert maze.is_wall(0, 30) is True
    assert maze.is_wall(27, 30) is True

    # Inside corridor is not a wall
    assert maze.is_wall(1, 1) is False
    assert maze.is_wall(13, 23) is False  # Pac-Man spawn


def test_wraparound_tunnel():
    maze = Maze()
    tunnel_row = 14

    # Wrapping left edge past 0 gives 27
    wrapped_left = maze.wrap_coords(-1, tunnel_row)
    assert wrapped_left == (27, tunnel_row)

    # Wrapping right edge past 27 gives 0
    wrapped_right = maze.wrap_coords(28, tunnel_row)
    assert wrapped_right == (0, tunnel_row)

    # Tunnel tiles are recognized as walkable
    assert maze.is_walkable(0, tunnel_row, is_ghost=False) is True
    assert maze.is_walkable(27, tunnel_row, is_ghost=False) is True
    assert maze.is_tunnel(0, tunnel_row) is True


def test_ghost_door_and_house_rules():
    maze = Maze()
    gate_x, gate_y = maze.ghost_house_gate

    # Pac-Man can never walk through ghost house door
    assert maze.is_walkable(gate_x, gate_y, is_ghost=False, allow_door=False) is False
    assert maze.is_walkable(gate_x, gate_y, is_ghost=False, allow_door=True) is False

    # Ghost cannot walk through door unless allow_door=True
    assert maze.is_walkable(gate_x, gate_y, is_ghost=True, allow_door=False) is False
    assert maze.is_walkable(gate_x, gate_y, is_ghost=True, allow_door=True) is True


def test_pellets_consumption_and_reset():
    maze = Maze()
    total = maze.total_pellets()
    assert total > 200  # Classic arcade layout has ~244 pellets
    assert maze.remaining_pellets() == total
    assert maze.is_cleared() is False

    # Find a tile with a regular pellet
    pellet_coord = next(iter(maze.pellets))
    result = maze.eat_pellet(*pellet_coord)
    assert result == "pellet"
    assert maze.remaining_pellets() == total - 1
    assert pellet_coord not in maze.pellets

    # Eating the same tile again returns None
    assert maze.eat_pellet(*pellet_coord) is None

    # Power pellet test
    power_coord = next(iter(maze.power_pellets))
    p_result = maze.eat_pellet(*power_coord)
    assert p_result == "power_pellet"

    # Reset
    maze.reset_pellets()
    assert maze.remaining_pellets() == total
    assert pellet_coord in maze.pellets
    assert power_coord in maze.power_pellets


def test_get_valid_neighbors():
    maze = Maze()
    # At (1, 1), standard corridor has 2 valid neighbors (Right and Down)
    neighbors = maze.get_valid_neighbors(1, 1, is_ghost=False)
    neighbor_coords = [(n[0], n[1]) for n in neighbors]

    assert (2, 1) in neighbor_coords  # Right
    assert (1, 2) in neighbor_coords  # Down
    assert (0, 1) not in neighbor_coords  # Left is wall
    assert (1, 0) not in neighbor_coords  # Up is wall
