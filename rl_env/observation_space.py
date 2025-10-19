"""
Observation space definition for the Mini Metro RL environment.

Defines how the game state is represented as input to the RL agent.
"""
import numpy as np
from typing import Dict, List, Tuple
from game.game_state import GameState
from game.game_logic import SHAPES


def get_observation_shape(max_stations: int = 20, max_lines: int = 6, max_trains: int = 10) -> Dict[str, Tuple]:
    """
    Returns the shapes of each component of the observation space.

    The observation is a dictionary with multiple components for better learning:
    - global_features: Scalar game-level information
    - station_features: Per-station information (matrix)
    - line_features: Per-line information (matrix)
    - train_features: Per-train information (matrix)
    - connectivity_matrix: Station-to-station connectivity
    """
    num_shapes = len(SHAPES)

    return {
        'global_features': (8,),  # [score, time, num_stations, num_lines, num_trains, total_waiting, total_on_trains, game_over]
        'station_features': (max_stations, 6 + num_shapes),  # [x, y, upgraded, waiting_count, shape_one_hot(4), on_lines_count, is_exchange]
        'line_features': (max_lines, 5),  # [num_trails, num_stations, r, g, b]
        'train_features': (max_trains, 6),  # [line_id, num_passengers, capacity, current_station, target_station, progress]
        'connectivity_matrix': (max_stations, max_stations),  # 1 if connected, 0 otherwise
    }


def extract_observation(game_state: GameState, max_stations: int = 20, max_lines: int = 6, max_trains: int = 10) -> Dict[str, np.ndarray]:
    """
    Extract observation from the game state.

    Returns a dictionary of numpy arrays representing the current state.
    """
    # Global features
    global_features = np.array([
        game_state.score,
        game_state.time_elapsed,
        len(game_state.stations),
        len(game_state.lines),
        len(game_state.trains),
        sum(len(s.waiting) for s in game_state.stations.values()),
        sum(len(t.passengers) for t in game_state.trains.values()),
        float(game_state.game_over)
    ], dtype=np.float32)

    # Station features
    station_features = np.zeros((max_stations, 6 + len(SHAPES)), dtype=np.float32)
    station_id_to_idx = {}  # Map station ID to array index

    for idx, (station_id, station) in enumerate(game_state.stations.items()):
        if idx >= max_stations:
            break

        station_id_to_idx[station_id] = idx

        # Normalize position to [0, 1]
        x_norm = station.pos[0] / game_state.config.map_width
        y_norm = station.pos[1] / game_state.config.map_height

        # Shape one-hot encoding
        shape_idx = SHAPES.index(station.shape)
        shape_one_hot = np.zeros(len(SHAPES))
        shape_one_hot[shape_idx] = 1.0

        # Number of lines this station is on
        on_lines_count = len(game_state.station_lines.get(station_id, []))

        # Is it an exchange station?
        is_exchange = float(station_id in game_state.exchange_stations)

        station_features[idx] = np.concatenate([
            [x_norm, y_norm, float(station.upgraded), len(station.waiting)],
            shape_one_hot,
            [on_lines_count, is_exchange]
        ])

    # Line features
    line_features = np.zeros((max_lines, 5), dtype=np.float32)
    for idx, (line_id, line) in enumerate(game_state.lines.items()):
        if idx >= max_lines:
            break

        # Normalize color to [0, 1]
        r, g, b = line.color
        line_features[idx] = [
            len(line.trails),
            len(line.get_stations()),
            r / 255.0,
            g / 255.0,
            b / 255.0
        ]

    # Train features
    train_features = np.zeros((max_trains, 6), dtype=np.float32)
    for idx, (train_id, train) in enumerate(game_state.trains.items()):
        if idx >= max_trains:
            break

        # Map station IDs to indices (0 if not found)
        current_idx = station_id_to_idx.get(train.current_station_id, 0)
        target_idx = station_id_to_idx.get(train.target_station_id, 0)

        train_features[idx] = [
            train.line_id,
            len(train.passengers),
            train.effective_capacity(),
            current_idx,
            target_idx,
            train.progress
        ]

    # Connectivity matrix (adjacency matrix of the station graph)
    connectivity_matrix = np.zeros((max_stations, max_stations), dtype=np.float32)
    for line in game_state.lines.values():
        for trail in line.trails:
            if trail.station_a in station_id_to_idx and trail.station_b in station_id_to_idx:
                idx_a = station_id_to_idx[trail.station_a]
                idx_b = station_id_to_idx[trail.station_b]
                connectivity_matrix[idx_a, idx_b] = 1.0
                connectivity_matrix[idx_b, idx_a] = 1.0

    return {
        'global_features': global_features,
        'station_features': station_features,
        'line_features': line_features,
        'train_features': train_features,
        'connectivity_matrix': connectivity_matrix
    }


def flatten_observation(obs_dict: Dict[str, np.ndarray]) -> np.ndarray:
    """
    Flatten the observation dictionary into a single 1D array.

    Useful for algorithms that expect flat input (e.g., DQN with MLP).
    """
    return np.concatenate([
        obs_dict['global_features'],
        obs_dict['station_features'].flatten(),
        obs_dict['line_features'].flatten(),
        obs_dict['train_features'].flatten(),
        obs_dict['connectivity_matrix'].flatten()
    ])


def get_flat_observation_size(max_stations: int = 20, max_lines: int = 6, max_trains: int = 10) -> int:
    """Calculate the size of the flattened observation vector."""
    shapes = get_observation_shape(max_stations, max_lines, max_trains)
    total_size = 0
    for shape in shapes.values():
        size = 1
        for dim in shape:
            size *= dim
        total_size += size
    return total_size
