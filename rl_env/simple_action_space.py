"""
Simplified action space that uses relative indices for better validity.

Instead of referencing absolute station IDs (0-19), we use relative indices
based on currently existing stations. This dramatically increases the % of valid actions.
"""
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional


class SimpleActionType(IntEnum):
    """Simplified action types."""
    NO_OP = 0
    CONNECT_STATIONS = 1  # Connect two stations (auto-picks color)
    ADD_TRAIN_TO_LINE = 2  # Add train to a line
    ADD_CARRIAGE = 3  # Add carriage to a train
    UPGRADE_STATION = 4  # Upgrade a station


def get_simple_action_space_size(max_stations: int = 10, max_lines: int = 6, max_trains: int = 10) -> int:
    """
    Calculate size of simplified action space.

    Action breakdown:
    - NO_OP: 1
    - CONNECT_STATIONS: max_stations * max_stations * (max_lines + 1)
      - Each connection can specify which line to extend (0..max_lines-1) or create new (-1)
      - Example: 10 * 10 * 7 = 700
    - ADD_TRAIN_TO_LINE: max_lines (e.g., 6)
    - ADD_CARRIAGE: max_trains (e.g., 10)
    - UPGRADE_STATION: max_stations (e.g., 10)

    Total: 727 actions (was 127 before adding line choice)
    """
    line_choices = max_lines + 1  # Can extend any of max_lines or create new (-1)
    return (
        1 +  # NO_OP
        max_stations * max_stations * line_choices +  # CONNECT_STATIONS with line choice
        max_lines +  # ADD_TRAIN_TO_LINE
        max_trains +  # ADD_CARRIAGE
        max_stations  # UPGRADE_STATION
    )


@dataclass
class SimpleAction:
    """Simplified action representation."""
    action_type: SimpleActionType
    param1: Optional[int] = None  # Station index, line index, or train index
    param2: Optional[int] = None  # Second station index (for CONNECT_STATIONS)
    param3: Optional[int] = None  # Line choice for CONNECT_STATIONS (-1 = new line, 0..5 = extend line)


def encode_simple_action(action: SimpleAction, max_stations: int = 10, max_lines: int = 6, max_trains: int = 10) -> int:
    """Encode a simple action to an integer."""
    if action.action_type == SimpleActionType.NO_OP:
        return 0

    offset = 1

    if action.action_type == SimpleActionType.CONNECT_STATIONS:
        # 3D encoding: station_a × station_b × line_choice
        # line_choice: -1 maps to 0, 0..5 maps to 1..6
        line_choice_idx = (action.param3 if action.param3 is not None else -1) + 1
        idx = (action.param1 * max_stations + action.param2) * (max_lines + 1) + line_choice_idx
        return offset + idx

    offset += max_stations * max_stations * (max_lines + 1)

    if action.action_type == SimpleActionType.ADD_TRAIN_TO_LINE:
        return offset + action.param1

    offset += max_lines

    if action.action_type == SimpleActionType.ADD_CARRIAGE:
        return offset + action.param1

    offset += max_trains

    if action.action_type == SimpleActionType.UPGRADE_STATION:
        return offset + action.param1

    raise ValueError(f"Unknown action type: {action.action_type}")


def decode_simple_action(action_int: int, max_stations: int = 10, max_lines: int = 6, max_trains: int = 10) -> SimpleAction:
    """Decode an integer to a simple action."""
    if action_int == 0:
        return SimpleAction(action_type=SimpleActionType.NO_OP)

    offset = 1

    # CONNECT_STATIONS (now 3D: station_a × station_b × line_choice)
    line_choices = max_lines + 1
    connect_size = max_stations * max_stations * line_choices
    if action_int < offset + connect_size:
        idx = action_int - offset
        line_choice_idx = idx % line_choices
        remaining = idx // line_choices
        param2 = remaining % max_stations
        param1 = remaining // max_stations
        param3 = line_choice_idx - 1  # Convert back: 0 -> -1, 1..6 -> 0..5
        return SimpleAction(action_type=SimpleActionType.CONNECT_STATIONS, param1=param1, param2=param2, param3=param3)

    offset += connect_size

    # ADD_TRAIN_TO_LINE
    if action_int < offset + max_lines:
        return SimpleAction(action_type=SimpleActionType.ADD_TRAIN_TO_LINE, param1=action_int - offset)

    offset += max_lines

    # ADD_CARRIAGE
    if action_int < offset + max_trains:
        return SimpleAction(action_type=SimpleActionType.ADD_CARRIAGE, param1=action_int - offset)

    offset += max_trains

    # UPGRADE_STATION
    return SimpleAction(action_type=SimpleActionType.UPGRADE_STATION, param1=action_int - offset)


def execute_simple_action(action: SimpleAction, game_state) -> bool:
    """
    Execute a simple action on the game state.

    Returns:
        success: Whether the action was executed successfully
    """
    if action.action_type == SimpleActionType.NO_OP:
        return True

    station_ids = list(game_state.stations.keys())

    if action.action_type == SimpleActionType.CONNECT_STATIONS:
        # Map relative indices to actual station IDs
        if action.param1 < len(station_ids) and action.param2 < len(station_ids):
            if action.param1 != action.param2:  # Can't connect to self
                sid_a = station_ids[action.param1]
                sid_b = station_ids[action.param2]

                # Determine color based on line choice (param3)
                line_choice = action.param3 if action.param3 is not None else -1

                if line_choice == -1:
                    # Create new line - pick next available color
                    if game_state.available_colors and len(game_state.lines) < len(game_state.available_colors):
                        color = game_state.available_colors[len(game_state.lines) % len(game_state.available_colors)]
                    else:
                        return False  # No colors available or at max lines
                else:
                    # Extend existing line - use that line's color
                    line_ids = list(game_state.lines.keys())
                    if line_choice < len(line_ids):
                        line_id = line_ids[line_choice]
                        color = game_state.lines[line_id].color
                    else:
                        return False  # Invalid line index

                return game_state.add_trail(sid_a, sid_b, color)
        return False

    elif action.action_type == SimpleActionType.ADD_TRAIN_TO_LINE:
        # Map relative line index to actual line ID
        line_ids = list(game_state.lines.keys())
        if action.param1 < len(line_ids):
            line_id = line_ids[action.param1]
            line = game_state.lines[line_id]

            # Get line's station sequence
            seq = line.station_sequence()
            if len(seq) >= 2:
                # Add train going from start to second station
                return game_state.add_train(line_id, seq[0], seq[1])
        return False

    elif action.action_type == SimpleActionType.ADD_CARRIAGE:
        # Map relative train index to actual train ID
        train_ids = list(game_state.trains.keys())
        if action.param1 < len(train_ids):
            train_id = train_ids[action.param1]
            return game_state.add_carriage_to_train(train_id)
        return False

    elif action.action_type == SimpleActionType.UPGRADE_STATION:
        # Map relative station index to actual station ID
        if action.param1 < len(station_ids):
            sid = station_ids[action.param1]
            return game_state.upgrade_station(sid)
        return False

    return False
