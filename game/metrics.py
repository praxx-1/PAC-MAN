"""Performance measurement, telemetry history, and algorithm comparison metrics."""

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SearchSample:
    """A single pathfinding query sample."""
    algorithm: str
    execution_time_us: float
    nodes_expanded: int
    path_length: int


class MetricsTracker:
    """Aggregates and compares AI search performance in real-time."""

    def __init__(self, history_capacity: int = 150) -> None:
        self.history_capacity = history_capacity
        self.samples: Dict[str, deque[SearchSample]] = {
            "A*": deque(maxlen=history_capacity),
            "BFS": deque(maxlen=history_capacity),
        }
        self.cumulative_counts: Dict[str, int] = {"A*": 0, "BFS": 0}
        self.cumulative_time_us: Dict[str, float] = {"A*": 0.0, "BFS": 0.0}
        self.cumulative_nodes: Dict[str, int] = {"A*": 0, "BFS": 0}

    def record_query(
        self,
        algorithm: str,
        execution_time_us: float,
        nodes_expanded: int,
        path_length: int,
    ) -> None:
        """Records a pathfinding sample into moving window and cumulative stats."""
        # Normalize key
        key = "A*" if "A*" in algorithm else "BFS"
        sample = SearchSample(
            algorithm=key,
            execution_time_us=execution_time_us,
            nodes_expanded=nodes_expanded,
            path_length=path_length,
        )

        if key not in self.samples:
            self.samples[key] = deque(maxlen=self.history_capacity)
            self.cumulative_counts[key] = 0
            self.cumulative_time_us[key] = 0.0
            self.cumulative_nodes[key] = 0

        self.samples[key].append(sample)
        self.cumulative_counts[key] += 1
        self.cumulative_time_us[key] += execution_time_us
        self.cumulative_nodes[key] += nodes_expanded

    def get_average_time_us(self, algorithm: str) -> float:
        """Returns average execution time in microseconds over the recent sample window."""
        key = "A*" if "A*" in algorithm else "BFS"
        history = self.samples.get(key, deque())
        if not history:
            return 0.0
        return sum(s.execution_time_us for s in history) / len(history)

    def get_average_nodes(self, algorithm: str) -> float:
        """Returns average nodes expanded over the recent sample window."""
        key = "A*" if "A*" in algorithm else "BFS"
        history = self.samples.get(key, deque())
        if not history:
            return 0.0
        return sum(s.nodes_expanded for s in history) / len(history)

    def get_average_path_length(self, algorithm: str) -> float:
        """Returns average path length over the recent sample window."""
        key = "A*" if "A*" in algorithm else "BFS"
        history = self.samples.get(key, deque())
        if not history:
            return 0.0
        return sum(s.path_length for s in history) / len(history)

    def get_comparison_summary(self) -> Dict[str, Dict[str, float]]:
        """Returns side-by-side performance comparison metrics."""
        summary = {}
        for algo in ["A*", "BFS"]:
            history = self.samples.get(algo, deque())
            count = len(history)
            avg_time = self.get_average_time_us(algo)
            avg_nodes = self.get_average_nodes(algo)
            avg_len = self.get_average_path_length(algo)

            summary[algo] = {
                "sample_count": count,
                "avg_time_us": avg_time,
                "avg_nodes": avg_nodes,
                "avg_path_length": avg_len,
                "total_queries": self.cumulative_counts.get(algo, 0),
            }

        # Comparative ratios
        a_star_nodes = summary["A*"]["avg_nodes"]
        bfs_nodes = summary["BFS"]["avg_nodes"]
        node_reduction = ((bfs_nodes - a_star_nodes) / bfs_nodes * 100.0) if bfs_nodes > 0 else 0.0

        a_star_time = summary["A*"]["avg_time_us"]
        bfs_time = summary["BFS"]["avg_time_us"]
        speedup = (bfs_time / a_star_time) if a_star_time > 0 else 1.0

        summary["comparison"] = {
            "node_reduction_pct": max(0.0, node_reduction),
            "speedup_factor": speedup,
        }

        return summary

    def format_terminal_report(self) -> str:
        """Generates a formatted ASCII comparison table for CLI outputs."""
        summary = self.get_comparison_summary()
        a_star = summary["A*"]
        bfs = summary["BFS"]
        comp = summary["comparison"]

        lines = [
            "=" * 60,
            "               ALGORITHM PERFORMANCE BENCHMARK               ",
            "=" * 60,
            f"{'Metric':<25} | {'A* Search':<14} | {'BFS Search':<14}",
            "-" * 60,
            f"{'Sample Count':<25} | {a_star['sample_count']:<14} | {bfs['sample_count']:<14}",
            f"{'Avg Exec Time (µs)':<25} | {a_star['avg_time_us']:<14.2f} | {bfs['avg_time_us']:<14.2f}",
            f"{'Avg Nodes Expanded':<25} | {a_star['avg_nodes']:<14.1f} | {bfs['avg_nodes']:<14.1f}",
            f"{'Avg Path Length':<25} | {a_star['avg_path_length']:<14.1f} | {bfs['avg_path_length']:<14.1f}",
            "-" * 60,
            f"Node Expansion Reduction by A*: {comp['node_reduction_pct']:.1f}%",
            f"Heuristic Search Efficiency:   {comp['speedup_factor']:.2f}x relative time ratio",
            "=" * 60,
        ]
        return "\n".join(lines)
