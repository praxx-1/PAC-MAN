"""Game state machine, collision processing, sound synthesis, and wave management."""

import array
import math
from typing import List, Optional, Tuple
import pygame
from .settings import (
    COLOR_BLINKY, COLOR_PINKY, COLOR_INKY, COLOR_CLYDE,
    Direction, GhostAlgorithm, GhostState,
    SCORE_PELLET, SCORE_POWER_PELLET, SCORE_GHOST_BASE,
    FRIGHTENED_DURATION, WAVE_DURATIONS, TILE_SIZE,
)
from .maze import Maze
from .pacman import Pacman
from .ghost import Ghost
from .ai_controller import AIController
from .metrics import MetricsTracker


class SoundSynthesizer:
    """Pure-Python procedural retro sound generator with silent fallback."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.sounds: dict = {}
        if not self.enabled:
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._create_synthesized_tones()
        except Exception:
            # Silently disable audio if device is absent or unsupported
            self.enabled = False

    def _create_tone(self, freq: float, duration: float, volume: float = 0.25) -> Optional[pygame.mixer.Sound]:
        """Synthesizes a sinusoidal wave into a pygame Sound buffer."""
        try:
            sample_rate = 22050
            num_samples = int(sample_rate * duration)
            buf = array.array("h")
            for i in range(num_samples):
                t = i / sample_rate
                # Attenuate envelope
                env = 1.0 - (i / num_samples)
                sample = int(32767 * volume * env * math.sin(2.0 * math.pi * freq * t))
                buf.append(sample)
            return pygame.mixer.Sound(buffer=buf)
        except Exception:
            return None

    def _create_synthesized_tones(self) -> None:
        """Builds procedural sounds for eating, power pellet, and ghost capture."""
        self.sounds["chomp"] = self._create_tone(440.0, 0.08, volume=0.15)
        self.sounds["power"] = self._create_tone(220.0, 0.25, volume=0.25)
        self.sounds["eat_ghost"] = self._create_tone(880.0, 0.35, volume=0.30)
        self.sounds["death"] = self._create_tone(180.0, 0.60, volume=0.35)

    def play(self, sound_name: str) -> None:
        """Plays tone if audio is active."""
        if not self.enabled:
            return
        sound = self.sounds.get(sound_name)
        if sound:
            try:
                sound.play()
            except Exception:
                pass


class GameState:
    """Encapsulates the complete game state, entities, and lifecycle rules."""

    def __init__(self, sound_enabled: bool = True) -> None:
        self.maze = Maze()
        self.pacman = Pacman(*self.maze.pacman_spawn)

        # Initialize the 4 classic Ghosts with their distinctive algorithms
        self.ghosts: List[Ghost] = [
            Ghost("Blinky", COLOR_BLINKY, self.maze.blinky_spawn, (25, 0), GhostAlgorithm.A_STAR),
            Ghost("Pinky", COLOR_PINKY, self.maze.pinky_spawn, (2, 0), GhostAlgorithm.PREDICTIVE),
            Ghost("Inky", COLOR_INKY, self.maze.inky_spawn, (27, 31), GhostAlgorithm.BFS),
            Ghost("Clyde", COLOR_CLYDE, self.maze.clyde_spawn, (0, 31), GhostAlgorithm.FUZZY),
        ]

        self.ai_controller = AIController()
        self.metrics_tracker = MetricsTracker()
        self.sound = SoundSynthesizer(enabled=sound_enabled)

        # Game statistics
        self.score: int = 0
        self.high_score: int = 10000
        self.lives: int = 3
        self.level: int = 1

        # Power Pellet / Frightened State
        self.power_pellet_active: bool = False
        self.power_timer_left: float = 0.0
        self.ghost_eaten_combo: int = 0

        # Global Scatter-Chase Wave management
        self.wave_index: int = 0
        self.wave_timer: float = 0.0
        self.wave_scatter: bool = True

        # Flow flags
        self.is_paused: bool = False
        self.is_game_over: bool = False
        self.is_level_cleared: bool = False
        self.pulse_timer: float = 0.0
        self.level_timer: float = 0.0

        # Reset entity states
        self.reset_positions()

    def reset_positions(self) -> None:
        """Resets Pac-Man and Ghosts to their starting tiles after life loss."""
        self.pacman.reset()
        for ghost in self.ghosts:
            ghost.reset()

        self.power_pellet_active = False
        self.power_timer_left = 0.0
        self.ghost_eaten_combo = 0

        self.wave_index = 0
        self.wave_scatter, self.wave_timer = WAVE_DURATIONS[0]
        self.level_timer = 0.0

    def reset_full_game(self) -> None:
        """Full reset when starting a new game."""
        self.score = 0
        self.lives = 3
        self.level = 1
        self.is_game_over = False
        self.is_level_cleared = False
        self.is_paused = False
        self.maze.reset_pellets()
        self.reset_positions()

    def advance_level(self) -> None:
        """Proceeds to the next level with refreshed pellets and increased speed."""
        self.level += 1
        self.maze.reset_pellets()
        self.reset_positions()
        self.is_level_cleared = False

    def cycle_ghost_algorithm(self, ghost_index: int) -> None:
        """Cycles the selected ghost through all 4 AI algorithms."""
        if 0 <= ghost_index < len(self.ghosts):
            ghost = self.ghosts[ghost_index]
            algorithms = list(GhostAlgorithm)
            curr_idx = algorithms.index(ghost.algorithm)
            next_algo = algorithms[(curr_idx + 1) % len(algorithms)]
            ghost.set_algorithm(next_algo)

    def update_ghost_release(self, dt: float) -> None:
        """Controls progressive ghost departure from the central ghost house."""
        eaten_pellets = self.maze.total_pellets() - self.maze.remaining_pellets()

        # Pinky exits right away
        pinky = next((g for g in self.ghosts if g.name == "Pinky"), None)
        if pinky and not pinky.is_released:
            pinky.is_released = True

        # Inky exits after 30 pellets or 4 seconds
        inky = next((g for g in self.ghosts if g.name == "Inky"), None)
        if inky and not inky.is_released:
            if eaten_pellets >= 30 or self.level_timer >= 4.0:
                inky.is_released = True

        # Clyde exits after 60 pellets or 8 seconds
        clyde = next((g for g in self.ghosts if g.name == "Clyde"), None)
        if clyde and not clyde.is_released:
            if eaten_pellets >= 60 or self.level_timer >= 8.0:
                clyde.is_released = True

    def update_wave_timers(self, dt: float) -> None:
        """Manages the global scatter and chase wave schedule."""
        if self.power_pellet_active:
            # Wave timers pause during frightened mode
            return

        self.wave_timer -= dt
        if self.wave_timer <= 0:
            if self.wave_index < len(WAVE_DURATIONS) - 1:
                self.wave_index += 1
                self.wave_scatter, self.wave_timer = WAVE_DURATIONS[self.wave_index]

                # Update ghost states
                new_state = GhostState.SCATTER if self.wave_scatter else GhostState.CHASE
                for ghost in self.ghosts:
                    if ghost.state in [GhostState.CHASE, GhostState.SCATTER]:
                        ghost.state = new_state
                        # Reversal on wave transition
                        ghost.direction = ghost.direction.opposite

    def update_power_pellet(self, dt: float) -> None:
        """Counts down power pellet duration and handles reversion to normal mode."""
        if not self.power_pellet_active:
            return

        self.power_timer_left -= dt
        if self.power_timer_left <= 0:
            self.power_pellet_active = False
            self.power_timer_left = 0.0
            self.ghost_eaten_combo = 0

            # Restore normal state to ghosts
            normal_state = GhostState.SCATTER if self.wave_scatter else GhostState.CHASE
            for ghost in self.ghosts:
                if ghost.state == GhostState.FRIGHTENED:
                    ghost.state = normal_state

    def check_collisions(self) -> None:
        """Handles pellet eating, ghost captures, and player deaths."""
        # 1. Pellet consumption
        pellet_type = self.maze.eat_pellet(self.pacman.tile_x, self.pacman.tile_y)
        if pellet_type == "pellet":
            self.score += SCORE_PELLET
            self.sound.play("chomp")
        elif pellet_type == "power_pellet":
            self.score += SCORE_POWER_PELLET
            self.power_pellet_active = True
            self.power_timer_left = FRIGHTENED_DURATION
            self.ghost_eaten_combo = 0
            self.sound.play("power")

            for ghost in self.ghosts:
                ghost.enter_frightened()

        # Update high score
        if self.score > self.high_score:
            self.high_score = self.score

        # Check level clear
        if self.maze.is_cleared():
            self.is_level_cleared = True
            return

        # 2. Ghost Collisions (distance threshold < 14 px)
        pac_center = (self.pacman.x, self.pacman.y)
        collision_dist_sq = 14.0 * 14.0

        for ghost in self.ghosts:
            if ghost.state == GhostState.IN_HOUSE:
                continue

            dx = ghost.x - self.pacman.x
            dy = ghost.y - self.pacman.y
            dist_sq = dx * dx + dy * dy

            if dist_sq <= collision_dist_sq:
                if ghost.state == GhostState.FRIGHTENED:
                    # Eat Ghost!
                    self.sound.play("eat_ghost")
                    points = SCORE_GHOST_BASE * (2 ** self.ghost_eaten_combo)
                    self.score += points
                    self.ghost_eaten_combo = min(3, self.ghost_eaten_combo + 1)
                    ghost.enter_eaten()

                elif ghost.state in [GhostState.CHASE, GhostState.SCATTER]:
                    # Pac-Man dies!
                    self.sound.play("death")
                    self.pacman.is_dying = True
                    break

    def update(self, dt: float = 1.0 / 60.0) -> None:
        """Main game update tick."""
        if self.is_paused or self.is_game_over or self.is_level_cleared:
            return

        self.pulse_timer += dt
        self.level_timer += dt

        # Handle Pac-Man dying animation
        if self.pacman.is_dying:
            self.pacman.update(self.maze)
            if self.pacman.death_timer >= 1.2:
                self.lives -= 1
                if self.lives <= 0:
                    self.is_game_over = True
                else:
                    self.reset_positions()
            return

        # Wave schedule and power timers
        self.update_wave_timers(dt)
        self.update_power_pellet(dt)
        self.update_ghost_release(dt)

        # Update Pac-Man
        self.pacman.update(self.maze, is_power_active=self.power_pellet_active)

        # Update AI Ghost Targets
        self.ai_controller.update_ghost_targets(
            ghosts=self.ghosts,
            pacman=self.pacman,
            maze=self.maze,
            power_pellet_active=self.power_pellet_active,
            power_timer_left=self.power_timer_left,
        )

        # Update Ghosts & Record Pathfinding Telemetry
        pacman_pos = (self.pacman.tile_x, self.pacman.tile_y)
        for ghost in self.ghosts:
            ghost.update(self.maze, pacman_pos)

            # Record metrics when ghost performed search
            if ghost.nodes_expanded > 0:
                self.metrics_tracker.record_query(
                    algorithm=ghost.algorithm.value,
                    execution_time_us=ghost.last_execution_time_us,
                    nodes_expanded=ghost.nodes_expanded,
                    path_length=ghost.last_path_length,
                )

        # Collision detection
        self.check_collisions()
