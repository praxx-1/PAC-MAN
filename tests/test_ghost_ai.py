"""Tests for Ghost AI personalities, target selection, and dynamic algorithm switching."""

import pytest
from game.settings import (
    COLOR_BLINKY, COLOR_PINKY, COLOR_INKY, COLOR_CLYDE,
    Direction, GhostAlgorithm, GhostState, MAZE_COLS
)
from game.maze import Maze
from game.pacman import Pacman
from game.ghost import Ghost
from game.ai_controller import AIController


@pytest.fixture
def maze():
    return Maze()


@pytest.fixture
def pacman():
    p = Pacman(13, 23)
    p.direction = Direction.LEFT
    p.facing = Direction.LEFT
    return p


def test_blinky_direct_chase(maze, pacman):
    controller = AIController()
    blinky = Ghost("Blinky", COLOR_BLINKY, (13, 11), (25, 0), GhostAlgorithm.A_STAR)
    blinky.state = GhostState.CHASE

    target = controller.compute_target_tile(blinky, pacman, blinky, maze)
    assert target == (pacman.tile_x, pacman.tile_y)


def test_pinky_predictive_intercept(maze, pacman):
    controller = AIController()
    pinky = Ghost("Pinky", COLOR_PINKY, (13, 14), (2, 0), GhostAlgorithm.PREDICTIVE)
    pinky.state = GhostState.CHASE

    pacman.facing = Direction.LEFT
    target = controller.compute_target_tile(pinky, pacman, pinky, maze)

    # 4 tiles to the left
    expected_x = (pacman.tile_x - 4) % MAZE_COLS
    assert target == (expected_x, pacman.tile_y)


def test_inky_flanking_vector(maze, pacman):
    controller = AIController()
    blinky = Ghost("Blinky", COLOR_BLINKY, (13, 11), (25, 0), GhostAlgorithm.A_STAR)
    inky = Ghost("Inky", COLOR_INKY, (11, 14), (27, 31), GhostAlgorithm.BFS)
    inky.state = GhostState.CHASE

    target = controller.compute_target_tile(inky, pacman, blinky, maze)
    # Target should be distinct from Pac-Man's exact tile
    assert target != (pacman.tile_x, pacman.tile_y)


def test_frightened_and_eaten_targets(maze, pacman):
    controller = AIController()
    ghost = Ghost("Blinky", COLOR_BLINKY, (13, 11), (25, 0), GhostAlgorithm.A_STAR)
    blinky = ghost

    # Frightened target should be a corner
    ghost.state = GhostState.FRIGHTENED
    target_frightened = controller.compute_target_tile(ghost, pacman, blinky, maze, power_pellet_active=True)
    assert target_frightened in [(1, 1), (26, 1), (1, 29), (26, 29)]

    # Eaten target must be ghost house gate
    ghost.state = GhostState.EATEN
    target_eaten = controller.compute_target_tile(ghost, pacman, blinky, maze)
    assert target_eaten == maze.ghost_house_gate


def test_ghost_enter_frightened_reverses_direction():
    ghost = Ghost("Blinky", COLOR_BLINKY, (1, 1), (25, 0), GhostAlgorithm.A_STAR)
    ghost.state = GhostState.CHASE
    ghost.direction = Direction.RIGHT

    ghost.enter_frightened()
    assert ghost.state == GhostState.FRIGHTENED
    assert ghost.direction == Direction.LEFT


def test_dynamic_algorithm_switching(maze):
    ghost = Ghost("Blinky", COLOR_BLINKY, (1, 1), (25, 0), GhostAlgorithm.A_STAR)
    assert ghost.algorithm == GhostAlgorithm.A_STAR

    # Run A*
    res_a = ghost.calculate_path(maze, (26, 29))
    assert res_a.algorithm_name == "A*"

    # Switch to BFS
    ghost.set_algorithm(GhostAlgorithm.BFS)
    assert ghost.algorithm == GhostAlgorithm.BFS
    res_b = ghost.calculate_path(maze, (26, 29))
    assert res_b.algorithm_name == "BFS"

    # Both find same optimal path length
    assert res_a.path_length == res_b.path_length
