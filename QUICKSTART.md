# Quick Start Guide

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-rl.txt  # For RL training
```

## Common Tasks

### Play the Game as Human

```bash
python main.py
```

### Test the RL Environment

```bash
python test_env.py
```

### Train Random Agent (Baseline)

```bash
# 100 episodes, headless (fast)
python train.py --mode random --episodes 100

# With visualization every 10 episodes
python train.py --mode random --episodes 100 --render-every 10
```

### Train PPO Agent (Requires stable-baselines3)

```bash
# Basic training (100k timesteps)
python train.py --mode ppo --timesteps 100000

# Longer training (1M timesteps)
python train.py --mode ppo --timesteps 1000000
```

### Train Other Algorithms

```bash
# DQN
python train.py --mode dqn --timesteps 100000

# A2C
python train.py --mode a2c --timesteps 100000
```

### Watch Agents Play

```bash
# Watch random agent
python play.py --mode watch --agent random

# Watch trained agent (PPO)
python play.py --mode watch --agent trained --model-path models/PPO_final.zip

# Watch at different speeds (FPS)
python play.py --mode watch --agent trained --model-path models/PPO_final.zip --fps 30
```

### Compare Multiple Agents

```bash
# Compare all available agents
python play.py --mode compare --episodes 10
```

### Monitor Training with TensorBoard

```bash
# Start tensorboard (in another terminal)
tensorboard --logdir logs/

# Then open http://localhost:6006 in your browser
```

## File Structure Quick Reference

```
mini-metro-RL/
├── train.py          # Training script
├── play.py           # Play/watch script
├── test_env.py       # Test environment
├── main.py           # Original game (backward compatibility)
│
├── game/             # Game logic
│   ├── game_state.py    # Headless game (for RL)
│   ├── game_logic.py    # Pure functions
│   └── game.py          # Original pygame game
│
├── env/              # RL environment
│   ├── metro_env.py     # Gym environment
│   ├── action_space.py  # Actions
│   ├── observation_space.py  # Observations
│   └── rewards.py       # Reward functions
│
└── agents/           # RL agents
    ├── random_agent.py  # Random baseline
    └── rl_agent.py      # Your agent (placeholder)
```

## Typical Workflow

### 1. Establish Baseline

```bash
# Run random agent to get baseline performance
python train.py --mode random --episodes 100
```

Expected output:
```
Random Baseline Results
Total Episodes: 100
Mean Reward: -50.23 ± 45.12
Mean Score: 2.34 ± 1.89
```

### 2. Train PPO Agent

```bash
# Train for 100k steps (takes ~10-30 minutes)
python train.py --mode ppo --timesteps 100000
```

Models will be saved to:
- `models/PPO/` - Checkpoints every 10k steps
- `models/PPO_final.zip` - Final model

### 3. Evaluate Your Agent

```bash
# Compare with random baseline
python play.py --mode compare --episodes 20
```

### 4. Watch Your Agent Play

```bash
python play.py --mode watch --agent trained --model-path models/PPO_final.zip
```

### 5. Iterate and Improve

Experiment with:
- Different reward functions (edit `env/rewards.py`)
- Different observation spaces (edit `env/observation_space.py`)
- Different hyperparameters
- Different algorithms (PPO, DQN, A2C)

## Custom Training Example

```python
from env.metro_env import MetroEnv
from env.rewards import ShapedReward
from game.game_state import GameConfig
from stable_baselines3 import PPO

# Create custom config
config = GameConfig(
    initial_stations=10,
    max_passengers_per_station=15,
    seed=42
)

# Create custom reward
reward = ShapedReward(
    score_weight=15.0,
    survival_weight=0.5,
    overcrowding_penalty_weight=3.0
)

# Create environment
env = MetroEnv(
    config=config,
    reward_function=reward,
    flatten_obs=True,
    steps_per_action=5,  # More frequent decisions
    render_mode=None  # Headless for speed
)

# Train PPO
model = PPO('MlpPolicy', env, verbose=1)
model.learn(total_timesteps=200000)
model.save('my_custom_agent')
```

## Performance Tips

### Maximum Training Speed

```python
env = MetroEnv(
    flatten_obs=True,      # Faster than dict
    render_mode=None,      # No rendering
    steps_per_action=10,   # Fewer agent decisions
    max_steps=5000         # Shorter episodes
)
```

### Render Every N Episodes

```python
for episode in range(1000):
    if episode % 100 == 0:
        env.render_mode = 'human'
    else:
        env.render_mode = None
    # ... run episode
```

### Parallel Training (Advanced)

```python
from stable_baselines3.common.vec_env import SubprocVecEnv

# Create 4 parallel environments
def make_env():
    return MetroEnv(flatten_obs=True, render_mode=None)

env = SubprocVecEnv([make_env for _ in range(4)])
model = PPO('MlpPolicy', env, verbose=1)
model.learn(total_timesteps=400000)
```

## Troubleshooting

**Training is too slow:**
- Set `render_mode=None`
- Increase `steps_per_action` (fewer agent decisions)
- Use `flatten_obs=True`

**Agent not learning:**
- Try different reward function (DenseReward for more feedback)
- Increase training timesteps
- Adjust hyperparameters
- Check if actions are valid (add logging)

**Out of memory:**
- Reduce `max_stations`, `max_lines`, `max_trains`
- Use `flatten_obs=True`
- Reduce batch size in RL algorithm

## Next Steps

- Read [README_RL.md](README_RL.md) for detailed documentation
- Check [INSTALL.md](INSTALL.md) for installation help
- Explore `env/rewards.py` to customize rewards
- Experiment with different RL algorithms
- Implement action masking for better performance

## Useful Links

- Stable-Baselines3 Docs: https://stable-baselines3.readthedocs.io/
- Gymnasium Docs: https://gymnasium.farama.org/
- Mini Metro (original game): https://dinopoloclub.com/games/mini-metro/
