"""
Better reward shaping specifically for the simplified action space.
Gives STRONG positive signals for infrastructure building.
"""
from typing import Dict
from game.game_state import GameState


class InfrastructureReward:
    """
    Reward function that heavily encourages building infrastructure.

    Designed to help the agent learn basic actions:
    - Big reward for creating lines
    - Big reward for adding trains
    - Continuous reward for having working infrastructure
    """

    def __init__(
        self,
        line_creation_reward: float = 50.0,  # BIG reward for creating lines
        train_creation_reward: float = 30.0,  # BIG reward for adding trains
        isolated_station_connection_reward: float = 30.0,  # BIG reward for connecting isolated stations
        score_weight: float = 10.0,
        survival_weight: float = 0.5,
        infrastructure_bonus_per_step: float = 1.0,  # Reward for having infrastructure
        invalid_action_penalty: float = 0.1,  # Small penalty
        game_over_penalty: float = 100.0
    ):
        self.line_creation_reward = line_creation_reward
        self.train_creation_reward = train_creation_reward
        self.isolated_station_connection_reward = isolated_station_connection_reward
        self.score_weight = score_weight
        self.survival_weight = survival_weight
        self.infrastructure_bonus_per_step = infrastructure_bonus_per_step
        self.invalid_action_penalty = invalid_action_penalty
        self.game_over_penalty = game_over_penalty

    def __call__(self, game_state: GameState, prev_state_dict: Dict, action_valid: bool, is_noop: bool = False) -> float:
        """Calculate reward."""
        reward = 0.0

        # Game over - big penalty
        if game_state.game_over:
            return -self.game_over_penalty

        # Invalid action - small penalty (not too harsh!)
        if not action_valid:
            return -self.invalid_action_penalty

        # Score increase (passengers delivered)
        score_increase = game_state.score - prev_state_dict.get('score', 0)
        reward += score_increase * self.score_weight

        # Survival bonus - but NOT for NO_OP!
        if not is_noop:
            reward += self.survival_weight

        # NO_OP penalty if no infrastructure exists yet
        if is_noop and len(game_state.lines) == 0:
            reward -= 1.0  # Penalty for doing nothing when you should be building

        # NEW LINE CREATED - BIG REWARD!
        num_lines_prev = prev_state_dict.get('num_lines', 0)
        num_lines_now = len(game_state.lines)
        if num_lines_now > num_lines_prev:
            lines_created = num_lines_now - num_lines_prev
            reward += lines_created * self.line_creation_reward
            # print(f"  [REWARD] Created {lines_created} line(s)! +{lines_created * self.line_creation_reward}")

        # NEW TRAIN ADDED - BIG REWARD!
        num_trains_prev = prev_state_dict.get('num_trains', 0)
        num_trains_now = len(game_state.trains)
        if num_trains_now > num_trains_prev:
            trains_created = num_trains_now - num_trains_prev
            reward += trains_created * self.train_creation_reward
            # print(f"  [REWARD] Added {trains_created} train(s)! +{trains_created * self.train_creation_reward}")

        # ISOLATED STATION CONNECTION - BIG REWARD!
        # Reward for connecting stations that were not on any line
        isolated_connected = self._count_newly_connected_isolated_stations(
            game_state, prev_state_dict
        )
        if isolated_connected > 0:
            reward += isolated_connected * self.isolated_station_connection_reward
            # print(f"  [REWARD] Connected {isolated_connected} isolated station(s)! "
            #       f"+{isolated_connected * self.isolated_station_connection_reward}")

        # Infrastructure exists bonus (encourages maintaining infrastructure)
        infrastructure_count = len(game_state.lines) + len(game_state.trains)
        reward += infrastructure_count * self.infrastructure_bonus_per_step

        return reward

    def _count_newly_connected_isolated_stations(
        self, game_state: GameState, prev_state_dict: Dict
    ) -> int:
        """
        Count how many stations that were isolated (not on any line)
        are now connected.

        Returns:
            Number of newly connected isolated stations
        """
        # Get previous station connectivity
        prev_stations = prev_state_dict.get('stations', {})

        # Find which stations are currently on lines
        current_connected_stations = set()
        for line in game_state.lines.values():
            current_connected_stations.update(line.get_stations())

        # Find which stations were previously on lines
        prev_connected_stations = set()
        prev_lines = prev_state_dict.get('lines', {})
        if isinstance(prev_lines, dict):
            for line_data in prev_lines.values():
                if isinstance(line_data, dict) and 'stations' in line_data:
                    prev_connected_stations.update(line_data['stations'])

        # Count stations that were isolated but are now connected
        newly_connected = 0
        for station_id in current_connected_stations:
            if station_id not in prev_connected_stations:
                # This station was isolated before, now it's connected!
                newly_connected += 1

        return newly_connected
