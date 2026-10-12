"""Tests for GameState lifecycle, scoring, collisions, and wave timers."""

import pytest
from game.settings import (
    SCORE_PELLET, SCORE_POWER_PELLET, SCORE_GHOST_BASE,
    GhostState, GhostAlgorithm
)
from game.game_state import GameState


@pytest.fixture
def state():
    # Disable audio to run cleanly in test harness
    return GameState(sound_enabled=False)


def test_initial_state(state):
    assert state.score == 0
    assert state.lives == 3
    assert state.level == 1
    assert state.is_game_over is False
    assert state.is_paused is False
    assert state.power_pellet_active is False
    assert len(state.ghosts) == 4


def test_pellet_eating_and_score(state):
    # Place Pac-Man directly on a pellet
    pellet_coord = next(iter(state.maze.pellets))
    state.pacman.tile_x, state.pacman.tile_y = pellet_coord

    state.check_collisions()

    assert state.score == SCORE_PELLET
    assert pellet_coord not in state.maze.pellets


def test_power_pellet_and_frightened_transition(state):
    power_coord = next(iter(state.maze.power_pellets))
    state.pacman.tile_x, state.pacman.tile_y = power_coord

    state.check_collisions()

    assert state.score == SCORE_POWER_PELLET
    assert state.power_pellet_active is True
    assert state.power_timer_left > 0.0

    # Released ghosts should now be frightened
    for ghost in state.ghosts:
        if ghost.state != GhostState.IN_HOUSE:
            assert ghost.state == GhostState.FRIGHTENED


def test_ghost_eaten_combo_multiplier(state):
    # Activate power pellet
    state.power_pellet_active = True
    state.power_timer_left = 7.0
    state.ghost_eaten_combo = 0

    blinky = state.ghosts[0]
    blinky.state = GhostState.FRIGHTENED
    blinky.x = state.pacman.x
    blinky.y = state.pacman.y

    # First ghost: 200 pts
    state.check_collisions()
    assert state.score == 200
    assert blinky.state == GhostState.EATEN
    assert state.ghost_eaten_combo == 1

    # Second ghost: 400 pts
    pinky = state.ghosts[1]
    pinky.state = GhostState.FRIGHTENED
    pinky.x = state.pacman.x
    pinky.y = state.pacman.y

    state.check_collisions()
    assert state.score == 200 + 400
    assert pinky.state == GhostState.EATEN
    assert state.ghost_eaten_combo == 2


def test_pacman_death_and_game_over(state):
    blinky = state.ghosts[0]
    blinky.state = GhostState.CHASE
    blinky.x = state.pacman.x
    blinky.y = state.pacman.y

    state.check_collisions()
    assert state.pacman.is_dying is True

    # Fast forward death animation
    state.pacman.death_timer = 1.3
    state.update(dt=0.01)

    assert state.lives == 2
    assert state.pacman.is_dying is False


def test_advance_level(state):
    state.score = 500
    state.advance_level()

    assert state.level == 2
    assert state.score == 500
    assert state.maze.is_cleared() is False
    assert state.maze.remaining_pellets() == state.maze.total_pellets()
