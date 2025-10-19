"""
Train with action masking to force valid actions only.

This uses MaskablePPO from sb3-contrib which respects action masks.
The agent CANNOT choose invalid actions, forcing it to learn productive behavior.
"""
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor
from pathlib import Path

from rl_env.metro_env import MetroEnv
from game.game_state import GameConfig
from rl_env.rewards import InfrastructureReward


def mask_fn(env):
    """Extract action mask from environment."""
    return env.action_masks()


print("=" * 60)
print("Training MaskablePPO with Action Masking")
print("=" * 60)

# Create directories
models_dir = Path("models")
logs_dir = Path("logs")
models_dir.mkdir(exist_ok=True)
logs_dir.mkdir(exist_ok=True)

# Create environment with action masking
env = MetroEnv(
    config=GameConfig(seed=42),
    reward_function=InfrastructureReward(
        line_creation_reward=50.0,
        train_creation_reward=30.0,
        infrastructure_bonus_per_step=1.0,
        invalid_action_penalty=1.0  # Shouldn't happen, but just in case
    ),
    flatten_obs=True,
    max_stations=10,
    max_steps=5000,
    steps_per_action=10,
    render_mode=None
)
env = ActionMasker(env, mask_fn)
env = Monitor(env, str(logs_dir / "train_monitor.log"))

# Create evaluation environment
eval_env = MetroEnv(
    config=GameConfig(seed=123),
    reward_function=InfrastructureReward(
        line_creation_reward=50.0,
        train_creation_reward=30.0,
        infrastructure_bonus_per_step=1.0,
        invalid_action_penalty=1.0
    ),
    flatten_obs=True,
    max_stations=10,
    max_steps=5000,
    steps_per_action=10,
    render_mode=None
)
eval_env = ActionMasker(eval_env, mask_fn)
eval_env = Monitor(eval_env, str(logs_dir / "eval_monitor.log"))

# Callbacks
checkpoint_callback = CheckpointCallback(
    save_freq=10000,
    save_path=str(models_dir),
    name_prefix="ppo"
)

eval_callback = EvalCallback(
    eval_env,
    best_model_save_path=str(models_dir),
    log_path=str(logs_dir),
    eval_freq=5000,
    deterministic=True,
    render=False
)

# Create MaskablePPO model
print("\nCreating MaskablePPO model...")
print("Action masking will prevent ALL invalid actions!")
print("Agent will be FORCED to create lines/trains\n")

model = MaskablePPO(
    'MlpPolicy',
    env,
    verbose=1,
    tensorboard_log=str(logs_dir),
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
    gamma=0.99,
    gae_lambda=0.95,
    clip_range=0.2,
    ent_coef=0.05  # Higher entropy = more exploration, less NO_OP spam
)

# Train
print("\n" + "=" * 60)
print("Training for 100,000 timesteps...")
print("Expected: 100% valid actions (invalid actions are blocked!)")
print("=" * 60 + "\n")

model.learn(
    total_timesteps=100000,
    callback=[checkpoint_callback, eval_callback],
    progress_bar=True
)

# Save final model
model.save(models_dir / "ppo_final")

print("\n" + "=" * 60)
print("Training Complete!")
print("=" * 60)
print(f"Model saved to: {models_dir / 'ppo_final.zip'}")
print("\nTo watch the agent play:")
print("  python play.py")
print("=" * 60)

env.close()
eval_env.close()
