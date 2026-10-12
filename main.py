"""Main executable entry point for the Pac-Man Ghost AI Simulation game."""

import argparse
import os
import sys
import time
from typing import Optional
import pygame

from game.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, Direction, GhostAlgorithm,
    COLOR_BLACK, COLOR_WHITE, COLOR_TEXT_TITLE, COLOR_ACCENT_GREEN, COLOR_ACCENT_RED
)
from game.maze import Maze
from game.game_state import GameState
from game.renderer import GameRenderer, get_safe_font
from game.pathfinding import a_star_search, breadth_first_search, toroidal_manhattan_distance
from game.metrics import MetricsTracker


def run_benchmark(num_trials: int = 250) -> None:
    """Executes automated AI pathfinding benchmark comparing A* and BFS in the actual maze."""
    print("=" * 65)
    print(f"RUNNING AUTOMATED AI SEARCH BENCHMARK ({num_trials} TRIALS)...")
    print("=" * 65)

    maze = Maze()
    tracker = MetricsTracker(history_capacity=num_trials * 2)

    # Gather walkable tiles
    walkable_tiles = []
    for y in range(maze.rows):
        for x in range(maze.cols):
            if maze.is_walkable(x, y, is_ghost=True, allow_door=False):
                walkable_tiles.append((x, y))

    import random
    rng = random.Random(42)  # Deterministic seed for reproducible evaluation

    for trial in range(num_trials):
        start = rng.choice(walkable_tiles)
        goal = rng.choice(walkable_tiles)

        # Run A*
        a_star_res = a_star_search(maze, start, goal, is_ghost=True)
        tracker.record_query("A*", a_star_res.execution_time_us, a_star_res.nodes_expanded, a_star_res.path_length)

        # Run BFS
        bfs_res = breadth_first_search(maze, start, goal, is_ghost=True)
        tracker.record_query("BFS", bfs_res.execution_time_us, bfs_res.nodes_expanded, bfs_res.path_length)

    print(tracker.format_terminal_report())
    print("\nBenchmark completed successfully.")


def run_game(sound_enabled: bool = True, headless: bool = False, max_frames: Optional[int] = None) -> None:
    """Runs the main game loop with rendering and keyboard interaction."""
    if headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"

    pygame.init()
    pygame.display.set_caption("Pac-Man Ghost AI: Search & Fuzzy Logic Simulation")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    game_state = GameState(sound_enabled=sound_enabled and not headless)
    renderer = GameRenderer(screen)

    running = True
    frame_count = 0

    while running:
        dt = clock.tick(FPS) / 1000.0
        # Guard against large dt spikes during window movement
        dt = min(dt, 0.05)
        frame_count += 1

        if max_frames and frame_count >= max_frames:
            break

        # Event Processing
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                # Pac-Man Movement Directions (Arrow keys & WASD)
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    game_state.pacman.request_direction(Direction.UP)
                elif event.key in [pygame.K_DOWN, pygame.K_s]:
                    game_state.pacman.request_direction(Direction.DOWN)
                elif event.key in [pygame.K_LEFT, pygame.K_a]:
                    game_state.pacman.request_direction(Direction.LEFT)
                elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                    game_state.pacman.request_direction(Direction.RIGHT)

                # Overlays & Diagnostics Toggles
                elif event.key == pygame.K_p:
                    renderer.show_paths = not renderer.show_paths
                elif event.key == pygame.K_t:
                    renderer.show_targets = not renderer.show_targets
                elif event.key == pygame.K_f:
                    renderer.show_frontier = not renderer.show_frontier
                elif event.key == pygame.K_TAB:
                    renderer.show_sidebar = not renderer.show_sidebar

                # Algorithm Switchers (1: Blinky, 2: Pinky, 3: Inky, 4: Clyde)
                elif event.key == pygame.K_1:
                    game_state.cycle_ghost_algorithm(0)
                elif event.key == pygame.K_2:
                    game_state.cycle_ghost_algorithm(1)
                elif event.key == pygame.K_3:
                    game_state.cycle_ghost_algorithm(2)
                elif event.key == pygame.K_4:
                    game_state.cycle_ghost_algorithm(3)

                # Game Controls
                elif event.key == pygame.K_SPACE:
                    game_state.is_paused = not game_state.is_paused
                elif event.key == pygame.K_r:
                    if game_state.is_game_over:
                        game_state.reset_full_game()
                    elif game_state.is_level_cleared:
                        game_state.advance_level()
                    else:
                        game_state.reset_positions()

        # Update Logic
        game_state.update(dt)

        # Rendering
        if not headless:
            screen.fill(COLOR_BLACK)

            # Draw Maze, Pellets, and Energizers
            renderer.draw_maze(game_state.maze, game_state.pulse_timer)

            # Draw AI Overlays (Paths, Targets, Search Frontier, Cones)
            renderer.draw_ai_overlays(game_state.ghosts, game_state.pacman)

            # Draw Actors
            renderer.draw_pacman(game_state.pacman)
            for ghost in game_state.ghosts:
                renderer.draw_ghost(ghost, game_state.power_timer_left)

            # Top Header
            renderer.draw_top_hud(
                score=game_state.score,
                high_score=game_state.high_score,
                lives=game_state.lives,
                level=game_state.level,
            )

            # Telemetry & AI Inspector Side Panel
            renderer.draw_sidebar(
                ghosts=game_state.ghosts,
                metrics_tracker=game_state.metrics_tracker,
                fuzzy_result=game_state.ai_controller.last_fuzzy_result,
                maze=game_state.maze,
                wave_scatter=game_state.wave_scatter,
                wave_time_left=game_state.wave_timer,
                power_pellet_active=game_state.power_pellet_active,
                power_timer_left=game_state.power_timer_left,
            )

            # Game Over / Level Clear Dialog Overlays
            if game_state.is_game_over:
                _draw_centered_banner(screen, "GAME OVER", "Press 'R' to Restart", COLOR_ACCENT_RED)
            elif game_state.is_level_cleared:
                _draw_centered_banner(screen, "LEVEL CLEARED!", "Press 'R' for Next Level", COLOR_ACCENT_GREEN)
            elif game_state.is_paused:
                _draw_centered_banner(screen, "PAUSED", "Press SPACE to Resume", COLOR_WHITE)

            pygame.display.flip()

    pygame.quit()


def _draw_centered_banner(screen: pygame.Surface, title: str, subtitle: str, color: tuple) -> None:
    """Renders a translucent overlay message box."""
    overlay = pygame.Surface((400, 120), pygame.SRCALPHA)
    overlay.fill((10, 14, 24, 220))
    pygame.draw.rect(overlay, color, (0, 0, 400, 120), width=2, border_radius=8)

    font_large = get_safe_font(28, bold=True)
    font_small = get_safe_font(14)

    t_surf = font_large.render(title, True, color)
    s_surf = font_small.render(subtitle, True, COLOR_WHITE)

    overlay.blit(t_surf, ((400 - t_surf.get_width()) // 2, 24))
    overlay.blit(s_surf, ((400 - s_surf.get_width()) // 2, 70))

    screen.blit(overlay, (136, 320))


def main() -> None:
    parser = argparse.ArgumentParser(description="Pac-Man Ghost AI Simulation & Benchmark")
    parser.add_argument("--no-sound", action="store_true", help="Disable audio synthesis")
    parser.add_argument("--benchmark", action="store_true", help="Run automated A* vs BFS search benchmark")
    parser.add_argument("--headless", action="store_true", help="Run without graphical display")
    parser.add_argument("--trials", type=int, default=250, help="Number of benchmark trials")
    args = parser.parse_args()

    if args.benchmark:
        run_benchmark(num_trials=args.trials)
    else:
        run_game(sound_enabled=not args.no_sound, headless=args.headless)


if __name__ == "__main__":
    main()
