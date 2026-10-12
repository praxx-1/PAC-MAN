"""Procedural retro arcade renderer, HUD displays, and AI telemetry visualization."""

import math
from typing import Dict, List, Optional, Tuple
import pygame
from .settings import (
    COLOR_BLACK, COLOR_WHITE, COLOR_MAZE_WALL, COLOR_MAZE_BORDER,
    COLOR_MAZE_GATE, COLOR_PELLET, COLOR_POWER_PELLET, COLOR_PACMAN,
    COLOR_BLINKY, COLOR_PINKY, COLOR_INKY, COLOR_CLYDE,
    COLOR_FRIGHTENED_BLUE, COLOR_FRIGHTENED_WHITE,
    COLOR_GHOST_EYE, COLOR_GHOST_PUPIL,
    COLOR_BG_SIDEBAR, COLOR_CARD_BG, COLOR_CARD_BORDER,
    COLOR_TEXT_TITLE, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_ACCENT_GREEN, COLOR_ACCENT_RED, COLOR_ACCENT_ORANGE, COLOR_ACCENT_PURPLE,
    Direction, GhostAlgorithm, GhostState,
    TILE_SIZE, MAZE_COLS, MAZE_ROWS, MAZE_OFFSET_Y, MAZE_WIDTH, MAZE_HEIGHT,
    SCREEN_WIDTH, SCREEN_HEIGHT, SIDEBAR_WIDTH, HUD_TOP_HEIGHT,
)
from .maze import Maze
from .pacman import Pacman
from .ghost import Ghost
from .metrics import MetricsTracker
from .fuzzy_logic import FuzzyInferenceResult


def get_safe_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Returns a font safely, falling back to pygame default font if sysfonts are blocked."""
    try:
        font = pygame.font.SysFont("monospace", size, bold=bold)
        return font
    except Exception:
        pass
    font = pygame.font.Font(None, size + 4)
    font.set_bold(bold)
    return font


class GameRenderer:
    """Renders game elements, procedural retro graphics, and AI debug overlays."""

    def __init__(self, surface: pygame.Surface) -> None:
        self.surface = surface
        pygame.font.init()
        self.font_title = get_safe_font(17, bold=True)
        self.font_bold = get_safe_font(13, bold=True)
        self.font_regular = get_safe_font(12)
        self.font_small = get_safe_font(10)

        # Visual overlay toggle flags
        self.show_paths: bool = True
        self.show_targets: bool = True
        self.show_frontier: bool = False
        self.show_predictive: bool = True
        self.show_sidebar: bool = True

        # Pre-create translucent surfaces for efficiency
        self.frontier_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        self.frontier_surf.fill((65, 105, 225, 65))

        self.reticle_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)

    def draw_maze(self, maze: Maze, pulse_timer: float) -> None:
        """Renders maze walls, pellets, power energizers, and ghost gate."""
        # Fill maze area with deep arcade black
        maze_rect = pygame.Rect(0, MAZE_OFFSET_Y, MAZE_WIDTH, MAZE_HEIGHT)
        pygame.draw.rect(self.surface, COLOR_BLACK, maze_rect)

        # 1. Draw Walls
        half_tile = TILE_SIZE // 2
        for x, y in maze.walls:
            px = x * TILE_SIZE
            py = y * TILE_SIZE + MAZE_OFFSET_Y
            wall_rect = pygame.Rect(px, py, TILE_SIZE, TILE_SIZE)

            # Draw outer wall block
            pygame.draw.rect(self.surface, COLOR_MAZE_WALL, wall_rect)

            # Draw subtle inner border to give double-line arcade neon look
            inner_rect = pygame.Rect(px + 3, py + 3, TILE_SIZE - 6, TILE_SIZE - 6)
            pygame.draw.rect(self.surface, (12, 12, 100), inner_rect, border_radius=2)
            pygame.draw.rect(self.surface, COLOR_MAZE_BORDER, wall_rect, width=1)

        # 2. Draw Ghost House Gate
        for x, y in maze.ghost_doors:
            px = x * TILE_SIZE
            py = y * TILE_SIZE + MAZE_OFFSET_Y + (half_tile - 2)
            pygame.draw.rect(self.surface, COLOR_MAZE_GATE, (px, py, TILE_SIZE, 4))

        # 3. Draw Pellets
        for x, y in maze.pellets:
            cx = x * TILE_SIZE + half_tile
            cy = y * TILE_SIZE + MAZE_OFFSET_Y + half_tile
            pygame.draw.circle(self.surface, COLOR_PELLET, (cx, cy), 3)

        # 4. Draw Power Pellets with glowing pulse
        pulse = (math.sin(pulse_timer * 6.0) + 1.0) / 2.0  # [0.0, 1.0]
        radius = int(6 + pulse * 2.5)
        for x, y in maze.power_pellets:
            cx = x * TILE_SIZE + half_tile
            cy = y * TILE_SIZE + MAZE_OFFSET_Y + half_tile
            # Ambient glow halo
            halo_color = (255, 255, 200, int(80 + pulse * 100))
            halo_surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(halo_surf, halo_color, (radius * 2, radius * 2), radius + 3)
            self.surface.blit(halo_surf, (cx - radius * 2, cy - radius * 2))
            # Core
            pygame.draw.circle(self.surface, COLOR_POWER_PELLET, (cx, cy), radius)

    def draw_pacman(self, pacman: Pacman) -> None:
        """Renders Pac-Man with smooth directional mouth chomping animation."""
        px = int(pacman.x)
        py = int(pacman.y) + MAZE_OFFSET_Y
        radius = TILE_SIZE // 2 - 1

        if pacman.is_dying:
            # Dying animation: mouth opens all the way
            death_progress = min(1.0, pacman.death_timer / 1.2)
            mouth_angle = death_progress * 180.0
            if death_progress >= 1.0:
                return  # Disappeared
        else:
            mouth_angle = pacman.mouth_angle

        # Determine rotation based on facing direction
        facing = pacman.facing
        if facing == Direction.RIGHT:
            start_angle = mouth_angle
            end_angle = 360.0 - mouth_angle
        elif facing == Direction.DOWN:
            start_angle = 270.0 + mouth_angle
            end_angle = 270.0 - mouth_angle + 360.0
        elif facing == Direction.LEFT:
            start_angle = 180.0 + mouth_angle
            end_angle = 180.0 - mouth_angle + 360.0
        elif facing == Direction.UP:
            start_angle = 90.0 + mouth_angle
            end_angle = 90.0 - mouth_angle + 360.0
        else:
            start_angle = mouth_angle
            end_angle = 360.0 - mouth_angle

        # Draw filled pie slice using polygon approximation
        points = [(px, py)]
        num_segments = 36
        span = (end_angle - start_angle) % 360.0
        if span == 0.0 and mouth_angle == 0.0:
            span = 360.0

        for i in range(num_segments + 1):
            theta = math.radians(start_angle + (i / num_segments) * span)
            sx = px + radius * math.cos(theta)
            sy = py - radius * math.sin(theta)  # Pygame y is inverted
            points.append((int(sx), int(sy)))

        if len(points) >= 3:
            pygame.draw.polygon(self.surface, COLOR_PACMAN, points)
            pygame.draw.polygon(self.surface, (200, 180, 0), points, width=1)

    def draw_ghost(self, ghost: Ghost, power_timer_left: float) -> None:
        """Procedurally draws classic arcade ghost with directional pupils and wavy skirt."""
        gx = int(ghost.x)
        gy = int(ghost.y) + MAZE_OFFSET_Y
        radius = TILE_SIZE // 2 - 1

        # Determine Body Color based on state
        if ghost.state == GhostState.EATEN:
            # Only draw eyes
            self._draw_ghost_eyes(gx, gy, ghost.direction)
            return

        if ghost.state == GhostState.FRIGHTENED:
            # Flash white when power pellet is expiring (< 2.5s remaining)
            if power_timer_left <= 2.5 and int(power_timer_left * 5.0) % 2 == 0:
                body_color = COLOR_FRIGHTENED_WHITE
                eye_color = (255, 0, 0)
            else:
                body_color = COLOR_FRIGHTENED_BLUE
                eye_color = (240, 240, 255)
        else:
            body_color = ghost.base_color
            eye_color = COLOR_GHOST_EYE

        # 1. Ghost Dome (Upper Semicircle)
        dome_rect = pygame.Rect(gx - radius, gy - radius, radius * 2, radius * 2)
        pygame.draw.arc(self.surface, body_color, dome_rect, 0, math.pi, width=radius)
        # Fill semicircle
        dome_pts = [(gx, gy)]
        for i in range(19):
            ang = math.pi * (i / 18.0)
            dome_pts.append((int(gx + radius * math.cos(ang)), int(gy - radius * math.sin(ang))))
        pygame.draw.polygon(self.surface, body_color, dome_pts)

        # 2. Ghost Main Body (Lower Rectangle)
        body_rect = pygame.Rect(gx - radius, gy, radius * 2, radius - 3)
        pygame.draw.rect(self.surface, body_color, body_rect)

        # 3. Animated Wavy Skirt (3 tentacles)
        tentacle_pts = [(gx - radius, gy + radius - 3)]
        frame = ghost.animation_frame
        num_tentacles = 3
        step = (radius * 2) / num_tentacles

        for t in range(num_tentacles):
            t_left = (gx - radius) + t * step
            t_mid = t_left + step / 2.0
            t_right = t_left + step
            wave_y = gy + radius if (t % 2 == frame) else gy + radius - 4
            tentacle_pts.append((int(t_mid), int(wave_y)))
            tentacle_pts.append((int(t_right), int(gy + radius - 3)))

        pygame.draw.polygon(self.surface, body_color, tentacle_pts)

        # 4. Ghost Eyes & Directional Pupils
        if ghost.state == GhostState.FRIGHTENED:
            # Small frightened dots & wavy mouth
            pygame.draw.circle(self.surface, eye_color, (gx - 4, gy - 2), 2)
            pygame.draw.circle(self.surface, eye_color, (gx + 4, gy - 2), 2)
            # Wavy mouth
            mouth_pts = [
                (gx - 6, gy + 4),
                (gx - 3, gy + 2),
                (gx, gy + 4),
                (gx + 3, gy + 2),
                (gx + 6, gy + 4)
            ]
            pygame.draw.lines(self.surface, eye_color, False, mouth_pts, width=1)
        else:
            self._draw_ghost_eyes(gx, gy, ghost.direction)

    def _draw_ghost_eyes(self, gx: int, gy: int, direction: Direction) -> None:
        """Renders white sclera with directional blue pupils."""
        dx, dy = direction.dx, direction.dy
        eye_offset_x = 4
        eye_y = gy - 3

        # Eye whites
        pygame.draw.circle(self.surface, COLOR_GHOST_EYE, (gx - eye_offset_x, eye_y), 4)
        pygame.draw.circle(self.surface, COLOR_GHOST_EYE, (gx + eye_offset_x, eye_y), 4)

        # Pupils looking in travel direction
        pupil_x_shift = dx * 2
        pupil_y_shift = dy * 2
        pygame.draw.circle(
            self.surface,
            COLOR_GHOST_PUPIL,
            (gx - eye_offset_x + pupil_x_shift, eye_y + pupil_y_shift),
            2,
        )
        pygame.draw.circle(
            self.surface,
            COLOR_GHOST_PUPIL,
            (gx + eye_offset_x + pupil_x_shift, eye_y + pupil_y_shift),
            2,
        )

    def draw_ai_overlays(self, ghosts: List[Ghost], pacman: Pacman) -> None:
        """Draws search frontiers, computed paths, target reticles, and predictive cones."""
        half_tile = TILE_SIZE // 2

        # 1. Search Frontier / Explored Nodes
        if self.show_frontier:
            for ghost in ghosts:
                if ghost.state in [GhostState.CHASE, GhostState.SCATTER]:
                    for fx, fy in ghost.visited_frontier:
                        px = fx * TILE_SIZE
                        py = fy * TILE_SIZE + MAZE_OFFSET_Y
                        self.surface.blit(self.frontier_surf, (px, py))

        # 2. Path Lines (A* vs BFS trajectories)
        if self.show_paths:
            for ghost in ghosts:
                if ghost.state in [GhostState.CHASE, GhostState.SCATTER, GhostState.EATEN]:
                    if len(ghost.current_path) >= 2:
                        points = []
                        for tx, ty in ghost.current_path:
                            px = tx * TILE_SIZE + half_tile
                            py = ty * TILE_SIZE + MAZE_OFFSET_Y + half_tile
                            points.append((px, py))

                        # Draw polyline in ghost's color
                        color = ghost.base_color if ghost.state != GhostState.EATEN else COLOR_WHITE
                        # Filter out wrap-around tunnel jumps so long lines don't streak across screen
                        segment = []
                        for i in range(len(points)):
                            if not segment:
                                segment.append(points[i])
                            else:
                                prev_x = segment[-1][0]
                                curr_x = points[i][0]
                                if abs(curr_x - prev_x) > TILE_SIZE * 2:
                                    if len(segment) >= 2:
                                        pygame.draw.lines(self.surface, color, False, segment, width=2)
                                    segment = [points[i]]
                                else:
                                    segment.append(points[i])
                        if len(segment) >= 2:
                            pygame.draw.lines(self.surface, color, False, segment, width=2)

        # 3. Target Reticles
        if self.show_targets:
            for ghost in ghosts:
                tx, ty = ghost.target_tile
                px = tx * TILE_SIZE
                py = ty * TILE_SIZE + MAZE_OFFSET_Y

                # Target box in ghost color
                target_rect = pygame.Rect(px + 2, py + 2, TILE_SIZE - 4, TILE_SIZE - 4)
                pygame.draw.rect(self.surface, ghost.base_color, target_rect, width=2)
                # Inner crosshair
                cx = px + half_tile
                cy = py + half_tile
                pygame.draw.line(self.surface, ghost.base_color, (cx - 4, cy), (cx + 4, cy), 1)
                pygame.draw.line(self.surface, ghost.base_color, (cx, cy - 4), (cx, cy + 4), 1)

        # 4. Pac-Man Predictive Vector (Pinky intercept line)
        if self.show_predictive and pacman.direction != Direction.NONE:
            start_px = int(pacman.x)
            start_py = int(pacman.y) + MAZE_OFFSET_Y
            proj_x = start_px + pacman.facing.dx * (TILE_SIZE * 4)
            proj_y = start_py + pacman.facing.dy * (TILE_SIZE * 4)
            pygame.draw.line(
                self.surface,
                COLOR_PINKY,
                (start_px, start_py),
                (proj_x, proj_y),
                width=2,
            )
            pygame.draw.circle(self.surface, COLOR_PINKY, (proj_x, proj_y), 4)

    def draw_top_hud(self, score: int, high_score: int, lives: int, level: int) -> None:
        """Renders top header with score, high score, and remaining lives."""
        top_rect = pygame.Rect(0, 0, MAZE_WIDTH, HUD_TOP_HEIGHT)
        pygame.draw.rect(self.surface, (10, 12, 18), top_rect)
        pygame.draw.line(self.surface, (30, 40, 60), (0, HUD_TOP_HEIGHT - 1), (MAZE_WIDTH, HUD_TOP_HEIGHT - 1))

        # Score & High Score
        txt_score_lbl = self.font_small.render("1UP SCORE", True, COLOR_TEXT_MUTED)
        txt_score_val = self.font_bold.render(f"{score:06d}", True, COLOR_WHITE)
        self.surface.blit(txt_score_lbl, (24, 8))
        self.surface.blit(txt_score_val, (24, 24))

        txt_hi_lbl = self.font_small.render("HIGH SCORE", True, COLOR_TEXT_MUTED)
        txt_hi_val = self.font_bold.render(f"{high_score:06d}", True, COLOR_TEXT_TITLE)
        self.surface.blit(txt_hi_lbl, (220, 8))
        self.surface.blit(txt_hi_val, (220, 24))

        txt_lvl_lbl = self.font_small.render("LEVEL", True, COLOR_TEXT_MUTED)
        txt_lvl_val = self.font_bold.render(f"{level}", True, COLOR_ACCENT_GREEN)
        self.surface.blit(txt_lvl_lbl, (420, 8))
        self.surface.blit(txt_lvl_val, (420, 24))

        # Lives icons
        txt_lives_lbl = self.font_small.render("LIVES", True, COLOR_TEXT_MUTED)
        self.surface.blit(txt_lives_lbl, (540, 8))
        for i in range(max(0, lives - 1)):
            lx = 540 + (i * 22)
            ly = 32
            pygame.draw.circle(self.surface, COLOR_PACMAN, (lx, ly), 7)
            # Pacman mouth wedge
            wedge_pts = [(lx, ly), (lx + 8, ly - 5), (lx + 8, ly + 5)]
            pygame.draw.polygon(self.surface, (10, 12, 18), wedge_pts)

    def draw_sidebar(
        self,
        ghosts: List[Ghost],
        metrics_tracker: MetricsTracker,
        fuzzy_result: Optional[FuzzyInferenceResult],
        maze: Maze,
        wave_scatter: bool,
        wave_time_left: float,
        power_pellet_active: bool,
        power_timer_left: float,
    ) -> None:
        """Renders comprehensive real-time AI telemetry, algorithm benchmarks, and controls."""
        if not self.show_sidebar:
            return

        sb_x = MAZE_WIDTH
        sb_width = SIDEBAR_WIDTH
        sb_height = SCREEN_HEIGHT

        # Background panel
        pygame.draw.rect(self.surface, COLOR_BG_SIDEBAR, (sb_x, 0, sb_width, sb_height))
        pygame.draw.line(self.surface, COLOR_CARD_BORDER, (sb_x, 0), (sb_x, sb_height), 2)

        cur_y = 16

        # Title Header
        title_surf = self.font_title.render("PAC-MAN AI TELEMETRY", True, COLOR_TEXT_TITLE)
        self.surface.blit(title_surf, (sb_x + 16, cur_y))
        cur_y += 30

        # CARD 1: Mode & Wave State
        cur_y = self._draw_wave_card(sb_x + 16, cur_y, sb_width - 32, wave_scatter, wave_time_left, power_pellet_active, power_timer_left)

        # CARD 2: Benchmark Comparison Card (A* vs BFS)
        cur_y = self._draw_benchmark_card(sb_x + 16, cur_y, sb_width - 32, metrics_tracker)

        # CARD 3: Ghost Status & Algorithm Table
        cur_y = self._draw_ghosts_table(sb_x + 16, cur_y, sb_width - 32, ghosts)

        # CARD 4: Fuzzy Logic Inspector (Clyde / Adaptive)
        cur_y = self._draw_fuzzy_card(sb_x + 16, cur_y, sb_width - 32, fuzzy_result, maze)

        # CARD 5: Interactive Controls Legend
        self._draw_controls_card(sb_x + 16, cur_y, sb_width - 32)

    def _draw_wave_card(
        self,
        x: int,
        y: int,
        w: int,
        wave_scatter: bool,
        wave_time: float,
        power_active: bool,
        power_time: float,
    ) -> int:
        card_h = 58
        pygame.draw.rect(self.surface, COLOR_CARD_BG, (x, y, w, card_h), border_radius=6)
        pygame.draw.rect(self.surface, COLOR_CARD_BORDER, (x, y, w, card_h), width=1, border_radius=6)

        if power_active:
            status_text = f"POWER-PELLET ACTIVE ({power_time:.1f}s)"
            badge_color = COLOR_ACCENT_PURPLE
        elif wave_scatter:
            status_text = f"SCATTER WAVE ({wave_time:.1f}s left)"
            badge_color = COLOR_ACCENT_ORANGE
        else:
            status_text = f"CHASE WAVE ({wave_time:.1f}s left)"
            badge_color = COLOR_ACCENT_RED

        lbl = self.font_small.render("GLOBAL GHOST PHASE", True, COLOR_TEXT_MUTED)
        val = self.font_bold.render(status_text, True, badge_color)
        self.surface.blit(lbl, (x + 12, y + 10))
        self.surface.blit(val, (x + 12, y + 28))

        return y + card_h + 12

    def _draw_benchmark_card(self, x: int, y: int, w: int, tracker: MetricsTracker) -> int:
        card_h = 135
        pygame.draw.rect(self.surface, COLOR_CARD_BG, (x, y, w, card_h), border_radius=6)
        pygame.draw.rect(self.surface, COLOR_CARD_BORDER, (x, y, w, card_h), width=1, border_radius=6)

        header = self.font_bold.render("ALGORITHM BENCHMARK (A* vs BFS)", True, COLOR_TEXT_TITLE)
        self.surface.blit(header, (x + 12, y + 10))

        summary = tracker.get_comparison_summary()
        a_star = summary["A*"]
        bfs = summary["BFS"]
        comp = summary["comparison"]

        row_y = y + 34
        # Columns
        col1 = x + 12
        col2 = x + 140
        col3 = x + 240

        h_stat = self.font_small.render("METRIC", True, COLOR_TEXT_MUTED)
        h_a = self.font_small.render("A* (HEAP)", True, COLOR_ACCENT_RED)
        h_b = self.font_small.render("BFS (QUEUE)", True, COLOR_INKY)
        self.surface.blit(h_stat, (col1, row_y))
        self.surface.blit(h_a, (col2, row_y))
        self.surface.blit(h_b, (col3, row_y))
        row_y += 18

        # Exec time
        t_lbl = self.font_regular.render("Exec Time (µs):", True, COLOR_TEXT_PRIMARY)
        t_a = self.font_regular.render(f"{a_star['avg_time_us']:.1f} µs", True, COLOR_WHITE)
        t_b = self.font_regular.render(f"{bfs['avg_time_us']:.1f} µs", True, COLOR_WHITE)
        self.surface.blit(t_lbl, (col1, row_y))
        self.surface.blit(t_a, (col2, row_y))
        self.surface.blit(t_b, (col3, row_y))
        row_y += 18

        # Nodes
        n_lbl = self.font_regular.render("Nodes Visited:", True, COLOR_TEXT_PRIMARY)
        n_a = self.font_regular.render(f"{a_star['avg_nodes']:.1f}", True, COLOR_WHITE)
        n_b = self.font_regular.render(f"{bfs['avg_nodes']:.1f}", True, COLOR_WHITE)
        self.surface.blit(n_lbl, (col1, row_y))
        self.surface.blit(n_a, (col2, row_y))
        self.surface.blit(n_b, (col3, row_y))
        row_y += 18

        # Node reduction badge
        reduction = comp["node_reduction_pct"]
        summary_str = f"A* Search expands {reduction:.1f}% fewer nodes than BFS"
        sub_text = self.font_small.render(summary_str, True, COLOR_ACCENT_GREEN)
        self.surface.blit(sub_text, (col1, row_y + 4))

        return y + card_h + 12

    def _draw_ghosts_table(self, x: int, y: int, w: int, ghosts: List[Ghost]) -> int:
        card_h = 160
        pygame.draw.rect(self.surface, COLOR_CARD_BG, (x, y, w, card_h), border_radius=6)
        pygame.draw.rect(self.surface, COLOR_CARD_BORDER, (x, y, w, card_h), width=1, border_radius=6)

        hdr = self.font_bold.render("GHOST AI AGENTS & ALGORITHMS", True, COLOR_TEXT_TITLE)
        self.surface.blit(hdr, (x + 12, y + 10))

        row_y = y + 32
        for ghost in ghosts:
            # Color pip
            pygame.draw.circle(self.surface, ghost.base_color, (x + 16, row_y + 8), 5)

            name_txt = self.font_bold.render(f"{ghost.name:<7}", True, ghost.base_color)
            algo_txt = self.font_small.render(f"[{ghost.algorithm.value}]", True, COLOR_TEXT_PRIMARY)
            mode_txt = self.font_small.render(f"{ghost.state.value}", True, COLOR_TEXT_MUTED)
            stats_txt = self.font_small.render(f"Nodes:{ghost.nodes_expanded:02d} | {ghost.last_execution_time_us:.0f}µs", True, COLOR_ACCENT_GREEN)

            self.surface.blit(name_txt, (x + 28, row_y))
            self.surface.blit(algo_txt, (x + 95, row_y + 1))
            self.surface.blit(mode_txt, (x + 270, row_y + 1))
            self.surface.blit(stats_txt, (x + 95, row_y + 14))

            row_y += 30

        return y + card_h + 12

    def _draw_fuzzy_card(
        self,
        x: int,
        y: int,
        w: int,
        fuzzy_result: Optional[FuzzyInferenceResult],
        maze: Maze,
    ) -> int:
        card_h = 120
        pygame.draw.rect(self.surface, COLOR_CARD_BG, (x, y, w, card_h), border_radius=6)
        pygame.draw.rect(self.surface, COLOR_CARD_BORDER, (x, y, w, card_h), width=1, border_radius=6)

        hdr = self.font_bold.render("FUZZY LOGIC ADAPTIVE ENGINE (CLYDE)", True, COLOR_TEXT_TITLE)
        self.surface.blit(hdr, (x + 12, y + 10))

        aggression = fuzzy_result.aggression_level if fuzzy_result else 0.5
        speed_mult = fuzzy_result.speed_multiplier if fuzzy_result else 1.0
        pellet_ratio = maze.remaining_pellet_ratio()

        row_y = y + 34
        bar_w = 140
        bar_h = 10

        # Bar 1: Pellet Progress
        p_lbl = self.font_small.render("Pellets Left:", True, COLOR_TEXT_MUTED)
        self.surface.blit(p_lbl, (x + 12, row_y))
        self._draw_progress_bar(x + 130, row_y + 2, bar_w, bar_h, pellet_ratio, COLOR_INKY)
        p_pct = self.font_small.render(f"{pellet_ratio * 100:.0f}%", True, COLOR_WHITE)
        self.surface.blit(p_pct, (x + 280, row_y))
        row_y += 22

        # Bar 2: Aggression Level
        a_lbl = self.font_small.render("Aggression:", True, COLOR_TEXT_MUTED)
        self.surface.blit(a_lbl, (x + 12, row_y))
        agg_color = COLOR_ACCENT_RED if aggression > 0.6 else COLOR_ACCENT_ORANGE if aggression > 0.3 else COLOR_ACCENT_GREEN
        self._draw_progress_bar(x + 130, row_y + 2, bar_w, bar_h, aggression, agg_color)
        a_val = self.font_small.render(f"{aggression:.2f}", True, agg_color)
        self.surface.blit(a_val, (x + 280, row_y))
        row_y += 22

        # Dynamic Speed multiplier
        s_lbl = self.font_small.render(f"Adaptive Speed Multiplier: {speed_mult:.2f}x", True, COLOR_TEXT_PRIMARY)
        self.surface.blit(s_lbl, (x + 12, row_y))

        return y + card_h + 12

    def _draw_progress_bar(self, x: int, y: int, w: int, h: int, ratio: float, color: Tuple[int, int, int]) -> None:
        """Renders filled horizontal meter with border."""
        pygame.draw.rect(self.surface, (35, 45, 65), (x, y, w, h), border_radius=3)
        fill_w = max(0, min(w, int(w * ratio)))
        if fill_w > 0:
            pygame.draw.rect(self.surface, color, (x, y, fill_w, h), border_radius=3)
        pygame.draw.rect(self.surface, COLOR_CARD_BORDER, (x, y, w, h), width=1, border_radius=3)

    def _draw_controls_card(self, x: int, y: int, w: int) -> int:
        card_h = 105
        pygame.draw.rect(self.surface, COLOR_CARD_BG, (x, y, w, card_h), border_radius=6)
        pygame.draw.rect(self.surface, COLOR_CARD_BORDER, (x, y, w, card_h), width=1, border_radius=6)

        hdr = self.font_bold.render("INTERACTIVE CONTROLS", True, COLOR_TEXT_TITLE)
        self.surface.blit(hdr, (x + 12, y + 8))

        c1 = "ARROWS/WASD: Move Pac-Man     | 1: Blinky Algo"
        c2 = "P: Toggle Paths              | 2: Pinky Algo"
        c3 = "T: Toggle Target Reticles    | 3: Inky Algo"
        c4 = "F: Toggle Search Frontier    | 4: Clyde Algo"
        c5 = "SPACE: Pause/Play            | R: Reset Level"

        lines = [c1, c2, c3, c4, c5]
        row_y = y + 26
        for line in lines:
            t = self.font_small.render(line, True, COLOR_TEXT_PRIMARY)
            self.surface.blit(t, (x + 12, row_y))
            row_y += 15

        return y + card_h
