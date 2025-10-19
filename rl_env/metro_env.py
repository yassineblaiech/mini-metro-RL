"""
Action-masked Metro environment.

Uses action masking to prevent invalid actions entirely.
This forces the agent to learn productive behavior instead of spamming invalid actions.
"""
import gymnasium as gym
import numpy as np
from typing import Optional, Dict, Tuple, Any

from game.game_state import GameState, GameConfig
from .simple_action_space import (
    SimpleAction, SimpleActionType, decode_simple_action,
    execute_simple_action, get_simple_action_space_size
)
from .observation_space import extract_observation, get_flat_observation_size, flatten_observation
from .rewards import InfrastructureReward


def get_action_mask(game_state: GameState, max_stations: int, max_lines: int, max_trains: int) -> np.ndarray:
    """
    Returns binary mask indicating which actions are valid.

    Returns:
        np.ndarray: Binary mask of shape (action_space_size,) where 1 = valid, 0 = invalid
    """
    action_space_size = get_simple_action_space_size(max_stations, max_lines, max_trains)
    mask = np.zeros(action_space_size, dtype=np.float32)

    num_stations = len(game_state.stations)
    num_lines = len(game_state.lines)
    num_trains = len(game_state.trains)

    # NO_OP is valid ONLY if infrastructure already exists
    # This forces the agent to build lines/trains at the start!
    if num_lines > 0:
        mask[0] = 1.0

    action_idx = 1

    # CONNECT_STATIONS actions (3D: station_a × station_b × line_choice)
    station_ids = list(game_state.stations.keys())
    line_ids = list(game_state.lines.keys())

    for i in range(max_stations):
        for j in range(max_stations):
            for line_choice_idx in range(max_lines + 1):  # 0..max_lines (0 = new line, 1..max_lines = extend line 0..max_lines-1)
                # Convert line_choice_idx back to actual line_choice (-1 = new, 0..5 = extend)
                line_choice = line_choice_idx - 1

                # Check basic validity: both stations exist and are different
                if i < num_stations and j < num_stations and i != j:
                    sid_a = station_ids[i]
                    sid_b = station_ids[j]

                    if line_choice == -1:
                        # Create new line - only valid if not at max_lines
                        if num_lines < game_state.max_lines:
                            mask[action_idx] = 1.0
                    else:
                        # Extend existing line - check if line exists and connection is valid
                        if line_choice < num_lines:
                            line_id = line_ids[line_choice]
                            line = game_state.lines[line_id]
                            stations_on_line = line.get_stations()

                            # Can extend line only if at least one station is already on it
                            if sid_a in stations_on_line or sid_b in stations_on_line:
                                # Check if this would be a valid trail addition
                                from game.entities import Trail
                                test_trail = Trail(sid_a, sid_b)
                                if line.can_add_trail(test_trail):
                                    mask[action_idx] = 1.0

                action_idx += 1

    # ADD_TRAIN_TO_LINE actions
    for line_idx in range(max_lines):
        if line_idx < num_lines and num_trains < game_state.max_trains:
            # Valid only if line exists AND we have trains available
            mask[action_idx] = 1.0
        action_idx += 1

    # ADD_CARRIAGE actions
    for train_idx in range(max_trains):
        if train_idx < num_trains:
            train_id = list(game_state.trains.keys())[train_idx]
            train = game_state.trains[train_id]
            if train.carriages < 3:  # Max 3 carriages
                mask[action_idx] = 1.0
        action_idx += 1

    # UPGRADE_STATION actions
    for station_idx in range(max_stations):
        if station_idx < num_stations:
            station_id = list(game_state.stations.keys())[station_idx]
            station = game_state.stations[station_id]
            if not station.upgraded:  # Can upgrade if not already upgraded
                mask[action_idx] = 1.0
        action_idx += 1

    # If NO valid actions (shouldn't happen), at least allow NO_OP
    if mask.sum() == 0:
        mask[0] = 1.0

    return mask


class MetroEnv(gym.Env):
    """
    Action-masked Metro environment.

    Key features:
    - Provides action_mask() method for masked PPO
    - Prevents agent from choosing invalid actions
    - Forces learning of productive behavior
    """

    metadata = {'render_modes': ['human', 'rgb_array'], 'render_fps': 60}

    def __init__(
        self,
        config: Optional[GameConfig] = None,
        reward_function = None,
        max_stations: int = 10,
        max_lines: int = 6,
        max_trains: int = 10,
        max_steps: int = 10000,
        steps_per_action: int = 10,
        flatten_obs: bool = False,
        render_mode: Optional[str] = None
    ):
        super().__init__()

        self.config = config or GameConfig()
        self.reward_function = reward_function or InfrastructureReward()
        self.max_stations = max_stations
        self.max_lines = max_lines
        self.max_trains = max_trains
        self.max_steps = max_steps
        self.steps_per_action = steps_per_action
        self.flatten_obs = flatten_obs
        self.render_mode = render_mode

        self.game_state: Optional[GameState] = None
        self.prev_state_dict: Optional[Dict] = None
        self.current_step = 0

        # Action space
        action_space_size = get_simple_action_space_size(max_stations, max_lines, max_trains)
        self.action_space = gym.spaces.Discrete(action_space_size)

        print(f"[MetroEnv] Action space size: {action_space_size}")
        print(f"[MetroEnv] Action masking ENABLED - invalid actions will be blocked")

        # Observation space
        if self.flatten_obs:
            obs_size = get_flat_observation_size(max_stations, max_lines, max_trains)
            self.observation_space = gym.spaces.Box(
                low=-np.inf, high=np.inf, shape=(obs_size,), dtype=np.float32
            )
        else:
            from .observation_space import get_observation_shape
            obs_shapes = get_observation_shape(max_stations, max_lines, max_trains)
            self.observation_space = gym.spaces.Dict({
                name: gym.spaces.Box(low=-np.inf, high=np.inf, shape=shape, dtype=np.float32)
                for name, shape in obs_shapes.items()
            })

        self.renderer = None
        self.screen = None
        self.clock = None
        self.font = None

    def action_masks(self) -> np.ndarray:
        """
        Returns binary mask for valid actions.
        Required for SB3's MaskablePPO.
        """
        return get_action_mask(self.game_state, self.max_stations, self.max_lines, self.max_trains)

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[Any, Dict]:
        super().reset(seed=seed)

        if seed is not None:
            self.config.seed = seed

        self.game_state = GameState(self.config)
        self.prev_state_dict = self.game_state.get_state_dict()
        self.current_step = 0

        obs = self._get_observation()
        info = {
            'episode_step': self.current_step,
            'score': self.game_state.score,
            'time_elapsed': self.game_state.time_elapsed,
            'num_stations': len(self.game_state.stations),
            'num_lines': len(self.game_state.lines),
            'num_trains': len(self.game_state.trains),
            'action_mask': self.action_masks()
        }

        return obs, info

    def step(self, action: int) -> Tuple[Any, float, bool, bool, Dict]:
        # Decode action
        action_obj = decode_simple_action(action, self.max_stations, self.max_lines, self.max_trains)

        # Execute action
        action_valid = execute_simple_action(action_obj, self.game_state)

        # Simulate game
        for _ in range(self.steps_per_action):
            done = self.game_state.step(dt=0.016)
            if done:
                break

        self.current_step += 1

        # Calculate reward
        from .simple_action_space import SimpleActionType
        is_noop = (action_obj.action_type == SimpleActionType.NO_OP)
        reward = self.reward_function(self.game_state, self.prev_state_dict, action_valid, is_noop)

        self.prev_state_dict = self.game_state.get_state_dict()

        terminated = self.game_state.game_over
        truncated = self.current_step >= self.max_steps

        obs = self._get_observation()

        info = {
            'episode_step': self.current_step,
            'score': self.game_state.score,
            'time_elapsed': self.game_state.time_elapsed,
            'action_valid': action_valid,
            'action_type': action_obj.action_type.name,
            'num_stations': len(self.game_state.stations),
            'num_lines': len(self.game_state.lines),
            'num_trains': len(self.game_state.trains),
            'action_mask': self.action_masks()
        }

        return obs, reward, terminated, truncated, info

    def _get_observation(self) -> Any:
        obs_dict = extract_observation(self.game_state, self.max_stations, self.max_lines, self.max_trains)
        if self.flatten_obs:
            return flatten_observation(obs_dict)
        return obs_dict

    def render(self):
        if self.render_mode is None:
            return

        if self.render_mode == 'human':
            if self.renderer is None:
                import pygame
                from game.rendering import Renderer

                pygame.init()
                self.screen = pygame.display.set_mode((self.config.map_width, self.config.map_height))
                pygame.display.set_caption('Mini Metro RL - Action Masked')
                self.clock = pygame.time.Clock()
                self.font = pygame.font.SysFont('Arial', 16)
                self.renderer = Renderer(self.screen, self.font)

            class RenderableGameState:
                def __init__(self, game_state):
                    self.stations = game_state.stations
                    self.lines = game_state.lines
                    self.trains = game_state.trains
                    self.obstacles = game_state.obstacles
                    self.score = game_state.score
                    self.paused = False
                    self.sidebar_width = game_state.config.sidebar_width
                    self.available_colors = game_state.available_colors
                    self.selected_color = game_state.available_colors[0] if game_state.available_colors else (0, 0, 0)
                    self.tools = []
                    self.selected_tool = None
                    self.first_station_for_trail = None
                    self.temp_mouse_pos = None
                    self.dragging_tool = None
                    self.pending_train_placement = None
                    self.debug_selected_passenger = None

            renderable = RenderableGameState(self.game_state)
            self.renderer.draw(renderable)
            self.clock.tick(self.metadata['render_fps'])

    def close(self):
        if self.renderer is not None:
            import pygame
            pygame.quit()
            self.renderer = None
            self.screen = None
            self.clock = None
            self.font = None
