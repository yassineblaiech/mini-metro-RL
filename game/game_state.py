"""
Headless game state - pure game logic without any rendering dependencies.
This can run fast simulations for RL training without pygame overhead.
"""
import math
import random
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field

from .entities import Station, Passenger, Line, Train, Obstacle, Trail
from . import game_logic

LINE_COLORS = [
    (220, 20, 60),   # Crimson
    (30, 144, 255),  # Dodger Blue
    (34, 139, 34),   # Forest Green
    (255, 165, 0),   # Orange
    (148, 0, 211),   # Dark Violet
    (0, 191, 255)    # Deep Sky Blue
]


@dataclass
class GameConfig:
    """Configuration for game initialization and behavior."""
    map_width: int = 960
    map_height: int = 640
    sidebar_width: int = 120
    initial_stations: int = 8
    initial_obstacles: int = 2
    passenger_spawn_interval: float = 1.0  # seconds
    max_passengers_per_station: int = 12
    seed: Optional[int] = None


class GameState:
    """
    Headless game state for fast simulation.
    No pygame, no rendering - pure game logic.
    """

    def __init__(self, config: Optional[GameConfig] = None):
        self.config = config or GameConfig()

        # Set random seed if provided
        if self.config.seed is not None:
            random.seed(self.config.seed)

        # Game entities
        self.stations: Dict[int, Station] = {}
        self.lines: Dict[int, Line] = {}
        self.trains: Dict[int, Train] = {}
        self.obstacles: Dict[int, Obstacle] = {}

        # ID counters
        self.next_station_id = 1
        self.next_line_id = 1
        self.next_train_id = 1

        # Game state
        self.score = 0
        self.time_elapsed = 0.0
        self.last_spawn = 0.0
        self.game_over = False
        self.step_count = 0

        # Available resources (limited!)
        self.available_colors = LINE_COLORS.copy()
        self.max_lines = 3  # Start with 3 lines
        self.max_trains = 3  # Start with 3 trains
        self.last_unlock_time = 0.0  # Track when we last unlocked resources

        # Caches for performance
        self.line_station_shapes: Dict[int, Set[str]] = {}
        self.station_lines: Dict[int, List[int]] = {}
        self.exchange_stations: Set[int] = set()

        # Initialize the map
        self._init_map()

    def _init_map(self):
        """Initialize the game map with stations and obstacles."""
        # Generate stations
        self.stations = game_logic.generate_initial_stations(
            num_stations=self.config.initial_stations,
            map_width=self.config.map_width,
            map_height=self.config.map_height,
            sidebar_width=self.config.sidebar_width,
            seed=self.config.seed
        )
        self.next_station_id = len(self.stations) + 1

        # Generate obstacles
        self.obstacles = game_logic.generate_obstacles(
            num_obstacles=self.config.initial_obstacles,
            map_width=self.config.map_width,
            map_height=self.config.map_height,
            stations=self.stations,
            sidebar_width=self.config.sidebar_width,
            seed=self.config.seed
        )

    def step(self, dt: float = 0.016):
        """
        Advance the game state by one timestep.

        Args:
            dt: Delta time in seconds (default ~60 FPS)

        Returns:
            done: Whether the game is over
        """
        if self.game_over:
            return True

        self.time_elapsed += dt
        self.step_count += 1

        # Unlock resources based on survival time
        self._unlock_resources()

        # Spawn passengers periodically
        if self.time_elapsed - self.last_spawn > self.config.passenger_spawn_interval:
            origin_station = game_logic.spawn_passenger(self.stations)
            if origin_station:
                self.update_passenger_routes_at_station(origin_station)
            self.last_spawn = self.time_elapsed

        # Move trains
        self._update_trains(dt)

        # Check game over condition
        for station in self.stations.values():
            if len(station.waiting) > self.config.max_passengers_per_station:
                self.game_over = True
                return True

        return False

    def _unlock_resources(self):
        """
        Unlock resources (lines and trains) as the agent survives longer.

        Unlocking schedule:
        - Start: 3 lines, 3 trains
        - Every 30 seconds: +1 line (max 6), +1 train (no limit)
        """
        UNLOCK_INTERVAL = 30.0  # Unlock every 30 seconds

        # Check if enough time has passed since last unlock
        if self.time_elapsed - self.last_unlock_time >= UNLOCK_INTERVAL:
            # Unlock one line (max 6)
            if self.max_lines < 6:
                self.max_lines += 1
                print(f"[Resources] Unlocked line! Now have {self.max_lines}/6 lines available")

            # Unlock one train (no limit)
            self.max_trains += 1
            print(f"[Resources] Unlocked train! Now have {self.max_trains} trains available")

            self.last_unlock_time = self.time_elapsed

    def _update_trains(self, dt: float):
        """Update all train positions and handle passenger pickup/dropoff."""
        for train in list(self.trains.values()):
            line = self.lines.get(train.line_id)
            if not line or not train.current_station_id or not train.target_station_id:
                continue

            # Get the trail between current and target stations
            trail = line.get_trail_between(train.current_station_id, train.target_station_id)
            if not trail:
                continue

            # Get waypoints (include station positions at start/end)
            s_from = self.stations[train.current_station_id]
            s_to = self.stations[train.target_station_id]

            waypoints = trail.waypoints if trail.waypoints else [s_from.pos, s_to.pos]

            # Ensure waypoints are in correct direction (from current to target)
            if waypoints[0] != s_from.pos and waypoints[-1] == s_from.pos:
                waypoints = list(reversed(waypoints))

            # Calculate total distance along waypoints
            total_distance = 0.0
            for i in range(len(waypoints) - 1):
                x1, y1 = waypoints[i]
                x2, y2 = waypoints[i + 1]
                total_distance += math.hypot(x2 - x1, y2 - y1)

            if total_distance == 0:
                train.progress = 1.0
            else:
                # Move train along the path
                distance_to_travel = train.speed * dt
                train.progress += distance_to_travel / total_distance

            # Arrived at station
            if train.progress >= 1.0:
                train.progress = 0.0
                train.waypoint_index = 0
                train.waypoint_progress = 0.0
                last_station_id = train.current_station_id
                train.current_station_id = train.target_station_id

                # Drop off passengers
                dropped = train.drop_off(s_to)
                self.score += dropped

                # Pick up passengers if capacity available
                if train.available_capacity() > 0:
                    train.load_passengers(s_to, line)

                # Choose next station (AI)
                train.target_station_id = game_logic.choose_next_station(
                    train, line, last_station_id
                )

    def add_trail(self, station_a_id: int, station_b_id: int, color: Tuple[int, int, int]):
        """
        Add a trail between two stations with the specified color.
        Creates a new line if one with that color doesn't exist.
        Calculates orthogonal/diagonal waypoints for Mini Metro-style rendering.
        Automatically adds a train to new lines (if trains available).

        Returns:
            success: Whether the trail was successfully added
        """
        if station_a_id not in self.stations or station_b_id not in self.stations:
            return False

        if station_a_id == station_b_id:
            return False

        # Calculate orthogonal path waypoints
        pos_a = self.stations[station_a_id].pos
        pos_b = self.stations[station_b_id].pos
        waypoints = game_logic.calculate_orthogonal_path(pos_a, pos_b)

        new_trail = Trail(station_a_id, station_b_id, waypoints=waypoints)

        # Find or create line with this color
        target_line = None
        is_new_line = False
        for line in self.lines.values():
            if line.color == color:
                target_line = line
                break

        if target_line is None:
            # Check if we have lines available
            if len(self.lines) >= self.max_lines:
                return False  # Can't create more lines

            target_line = Line(id=self.next_line_id, color=color)
            self.lines[self.next_line_id] = target_line
            self.next_line_id += 1
            is_new_line = True

        if target_line.can_add_trail(new_trail):
            target_line.add_trail(new_trail)
            self.update_exchange_caches()

            # Auto-add train to new line (first segment only) if trains available
            if is_new_line and len(target_line.trails) == 1 and len(self.trains) < self.max_trains:
                self.add_train(
                    line_id=target_line.id,
                    start_station_id=station_a_id,
                    direction_station_id=station_b_id
                )

            return True

        return False

    def remove_trail(self, station_a_id: int, station_b_id: int) -> bool:
        """
        Remove a trail between two stations.

        Returns:
            success: Whether a trail was found and removed
        """
        line_to_modify = None
        for line in self.lines.values():
            for trail in line.trails:
                if (trail.station_a == station_a_id and trail.station_b == station_b_id) or \
                   (trail.station_a == station_b_id and trail.station_b == station_a_id):
                    line_to_modify = line
                    break
            if line_to_modify:
                break

        if line_to_modify:
            line_to_modify.remove_trail(station_a_id, station_b_id)
            self.update_exchange_caches()
            return True

        return False

    def add_train(self, line_id: int, start_station_id: int, direction_station_id: int) -> bool:
        """
        Add a train to a line at a specific station with a specific direction.

        Returns:
            success: Whether the train was successfully added
        """
        line = self.lines.get(line_id)
        if not line:
            return False

        # Check if we have trains available
        if len(self.trains) >= self.max_trains:
            return False  # Can't create more trains

        station_sequence = line.station_sequence()
        try:
            start_idx = station_sequence.index(start_station_id)
            direction_idx = station_sequence.index(direction_station_id)
        except ValueError:
            return False

        # Create train
        train = Train(
            id=self.next_train_id,
            line_id=line_id,
            current_station_id=start_station_id,
            target_station_id=direction_station_id
        )
        self.trains[train.id] = train
        self.next_train_id += 1

        # Perform initial passenger pickup
        start_station = self.stations[start_station_id]
        train.load_passengers(start_station, line)

        return True

    def add_carriage_to_train(self, train_id: int) -> bool:
        """Add a carriage to a specific train."""
        train = self.trains.get(train_id)
        if train:
            train.carriages += 1
            return True
        return False

    def upgrade_station(self, station_id: int) -> bool:
        """Upgrade a station to an interchange."""
        station = self.stations.get(station_id)
        if station:
            station.upgraded = True
            return True
        return False

    def update_exchange_caches(self):
        """Recalculate caches for line shapes and exchange stations."""
        self.line_station_shapes, self.station_lines, self.exchange_stations = \
            game_logic.update_exchange_caches(self.lines, self.stations)

        # After updating caches, all passenger routes might need re-evaluation
        for station in self.stations.values():
            self.update_passenger_routes_at_station(station)

    def update_passenger_routes_at_station(self, station: Station):
        """Update routing information for all passengers at a station."""
        game_logic.update_passenger_routes_at_station(
            station,
            self.stations,
            self.lines,
            self.station_lines,
            self.line_station_shapes,
            self.exchange_stations
        )

    def get_state_dict(self) -> dict:
        """
        Get a serializable representation of the game state.
        Useful for RL observation space and debugging.
        """
        return {
            'score': self.score,
            'time_elapsed': self.time_elapsed,
            'step_count': self.step_count,
            'game_over': self.game_over,
            'num_stations': len(self.stations),
            'num_lines': len(self.lines),
            'num_trains': len(self.trains),
            'max_lines': self.max_lines,
            'max_trains': self.max_trains,
            'total_waiting_passengers': sum(len(s.waiting) for s in self.stations.values()),
            'total_passengers_on_trains': sum(len(t.passengers) for t in self.trains.values()),
            'stations': {
                sid: {
                    'pos': s.pos,
                    'shape': s.shape,
                    'waiting': len(s.waiting),
                    'upgraded': s.upgraded
                }
                for sid, s in self.stations.items()
            },
            'lines': {
                lid: {
                    'color': l.color,
                    'num_trails': len(l.trails),
                    'num_stations': len(l.get_stations()),
                    'stations': list(l.get_stations())  # For reward tracking
                }
                for lid, l in self.lines.items()
            },
            'trains': {
                tid: {
                    'line_id': t.line_id,
                    'passengers': len(t.passengers),
                    'capacity': t.effective_capacity(),
                    'current_station': t.current_station_id,
                    'target_station': t.target_station_id
                }
                for tid, t in self.trains.items()
            }
        }

    def reset(self, seed: Optional[int] = None) -> dict:
        """
        Reset the game state to initial conditions.

        Returns:
            Initial state dict
        """
        if seed is not None:
            self.config.seed = seed
            random.seed(seed)

        # Clear all game entities
        self.stations.clear()
        self.lines.clear()
        self.trains.clear()
        self.obstacles.clear()

        # Reset counters
        self.next_station_id = 1
        self.next_line_id = 1
        self.next_train_id = 1

        # Reset game state
        self.score = 0
        self.time_elapsed = 0.0
        self.last_spawn = 0.0
        self.game_over = False
        self.step_count = 0

        # Reset caches
        self.line_station_shapes.clear()
        self.station_lines.clear()
        self.exchange_stations.clear()

        # Reinitialize map
        self._init_map()

        return self.get_state_dict()
