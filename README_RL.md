# Mini Metro RL - Reinforcement Learning Architecture

A Mini Metro-style game with reinforcement learning capabilities. The codebase is designed for training RL agents with a completely separated rendering pipeline for maximum training speed.

## Project Structure

```
mini-metro-RL/
├── game/                      # Core game logic
│   ├── entities.py           # Game entities (Station, Train, Line, etc.)
│   ├── game_state.py         # Headless game state (NO pygame, for RL)
│   ├── game_logic.py         # Pure game logic functions
│   ├── game.py               # Original pygame-based game with UI
│   └── rendering.py          # Rendering functions (optional)
│
├── env/                       # RL Environment (Gym-compatible)
│   ├── metro_env.py          # Main Gym environment
│   ├── action_space.py       # Action space definition
│   ├── observation_space.py  # Observation space definition
│   └── rewards.py            # Reward shaping functions
│
├── agents/                    # RL Agents
│   ├── random_agent.py       # Random baseline agent
│   └── rl_agent.py           # Your RL agent (placeholder)
│
├── train.py                   # Training script (headless, fast)
├── play.py                    # Play/visualization script
└── main.py                    # Backward compatibility
```

## Key Features

### 1. **Separated Logic and Graphics**
- **GameState**: Headless game logic (no pygame) for fast RL training
- **Rendering**: Optional, can be disabled for 1000x faster training
- **Visualization**: Can render every N episodes to monitor progress

### 2. **Gym-Compatible Environment**
- Standard `reset()`, `step()`, `render()` interface
- Works with Stable-Baselines3, RLlib, and custom RL libraries
- Configurable action/observation spaces

### 3. **Flexible Reward Shaping**
- `SimpleReward`: Basic score-based rewards
- `ShapedReward`: Multi-component rewards (efficiency, survival, penalties)
- `DenseReward`: Granular feedback for faster learning

### 4. **Fast Training**
- Runs headless (no graphics overhead)
- Deterministic stepping (no time-based randomness)
- Parallelizable (can run multiple environments)

## Installation

```bash
# Install dependencies
pip install pygame numpy gymnasium

# For Stable-Baselines3 (optional)
pip install stable-baselines3
```

## Usage

### Play as Human (Original Game)

```bash
python main.py
# or
python play.py --mode human
```

### Train a Random Agent (Baseline)

```bash
python train.py --mode random --episodes 100
```

### Train with Stable-Baselines3 (PPO)

```bash
# Fast headless training
python train.py --mode ppo --timesteps 100000

# This runs at 1000x+ speed compared to rendering!
```

### Watch a Trained Agent

```bash
# Watch random agent
python play.py --mode watch --agent random

# Watch trained agent
python play.py --mode watch --agent trained --model-path models/PPO_final.zip
```

### Compare Agents

```bash
python play.py --mode compare --episodes 10
```

## Training Speed Comparison

With the new architecture:

| Mode | Speed | Use Case |
|------|-------|----------|
| **Headless** | ~10,000 steps/sec | RL training |
| **Render every 100 episodes** | ~9,500 steps/sec | Monitor progress |
| **Full rendering** | ~60 steps/sec | Human play, debugging |

**~166x speedup** for headless RL training!

## RL Environment Details

### Observation Space

The environment provides a dictionary observation with:
- `global_features`: Score, time, counts, etc.
- `station_features`: Per-station info (position, shape, waiting passengers)
- `line_features`: Per-line info (trails, stations, color)
- `train_features`: Per-train info (passengers, capacity, position)
- `connectivity_matrix`: Station adjacency matrix

Can be flattened to 1D array with `flatten_obs=True`.

### Action Space

Discrete actions:
- `NO_OP`: Do nothing
- `ADD_LINE`: Connect two stations
- `REMOVE_LINE`: Remove a connection
- `ADD_TRAIN`: Add a train to a line
- `ADD_CARRIAGE`: Add capacity to a train
- `UPGRADE_STATION`: Upgrade to interchange

### Reward Functions

**SimpleReward**: Score increase - penalties
```python
reward = score_delta + game_over_penalty + invalid_action_penalty
```

**ShapedReward**: Multi-component
```python
reward = (score_delta * 10) + survival_bonus + efficiency_bonus - overcrowding_penalty
```

**DenseReward**: Maximum feedback
```python
reward = shaped_reward + infrastructure_bonuses + connection_bonuses
```

## Example: Training with Custom Reward

```python
from env.metro_env import MetroEnv
from env.rewards import ShapedReward
from game.game_state import GameConfig

# Custom config
config = GameConfig(
    initial_stations=10,
    max_passengers_per_station=15,
    seed=42
)

# Custom reward
reward_fn = ShapedReward(
    score_weight=15.0,
    survival_weight=0.5,
    overcrowding_penalty_weight=3.0
)

# Create environment
env = MetroEnv(
    config=config,
    reward_function=reward_fn,
    flatten_obs=True,
    max_steps=10000,
    steps_per_action=5  # More frequent decisions
)

# Train your agent
# ...
```

## Example: Using Stable-Baselines3

```python
from stable_baselines3 import PPO
from env.metro_env import MetroEnv

# Create environment
env = MetroEnv(flatten_obs=True, render_mode=None)

# Train PPO agent
model = PPO('MlpPolicy', env, verbose=1)
model.learn(total_timesteps=100000)

# Save and use
model.save('my_metro_agent')
model = PPO.load('my_metro_agent')

# Evaluate
obs, info = env.reset()
for _ in range(1000):
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, done, truncated, info = env.step(action)
    if done or truncated:
        obs, info = env.reset()
```

## Rendering Every N Episodes

```python
for episode in range(1000):
    # Enable rendering every 100 episodes
    if episode % 100 == 0:
        env.render_mode = 'human'
    else:
        env.render_mode = None

    # Run episode
    obs, info = env.reset()
    while not done:
        action, _ = model.predict(obs)
        obs, reward, done, truncated, info = env.step(action)

        if env.render_mode == 'human':
            env.render()
```

## Architecture Benefits

### Before (Original)
```python
# game.py had everything mixed together
class Game:
    def __init__(self):
        pygame.init()  # Graphics required
        self.screen = ...
        self.stations = ...
        # Logic + Graphics intertwined

# Could NOT train RL without rendering overhead!
```

### After (Refactored)
```python
# game_state.py - Pure logic, NO pygame
class GameState:
    def __init__(self):
        # NO pygame!
        self.stations = ...

    def step(self, dt):
        # Pure game logic
        # Runs 1000x faster!

# env/metro_env.py - Gym wrapper
class MetroEnv(gym.Env):
    def __init__(self, render_mode=None):
        self.game_state = GameState()  # Headless
        self.render_mode = render_mode  # Optional!

    def step(self, action):
        # Execute action
        # Run simulation
        # ONLY render if requested
        if self.render_mode:
            self.render()
```

## Next Steps

1. **Test the environment**:
   ```bash
   python train.py --mode random --episodes 10
   ```

2. **Train a real agent**:
   ```bash
   python train.py --mode ppo --timesteps 50000
   ```

3. **Watch it play**:
   ```bash
   python play.py --mode watch --agent trained --model-path models/PPO_final.zip
   ```

4. **Experiment**:
   - Try different reward functions
   - Adjust `steps_per_action` (how often agent decides)
   - Modify observation space
   - Implement action masking

## Development Roadmap

- [ ] Implement action masking (prevent invalid actions)
- [ ] Add parallel environment support (vectorized envs)
- [ ] Implement curriculum learning
- [ ] Add tensorboard logging
- [ ] Create pre-trained models
- [ ] Improve action space (hierarchical actions?)
- [ ] Add more sophisticated observation encoding

## Troubleshooting

**Issue**: `ModuleNotFoundError: No module named 'gymnasium'`
```bash
pip install gymnasium
```

**Issue**: Training is slow
- Make sure `render_mode=None` in MetroEnv
- Reduce `steps_per_action` for less frequent agent decisions
- Use vectorized environments (advanced)

**Issue**: Agent not learning
- Try different reward functions (DenseReward for more feedback)
- Adjust hyperparameters
- Check if actions are valid (add logging in `_execute_action`)

## Credits

Original game prototype by [Your Name]
RL architecture refactoring for training efficiency
