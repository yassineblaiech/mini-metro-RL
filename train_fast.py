"""
FAST TRAINING with parallel environments and optimized settings.

This script is 10-20x faster than train.py by:
1. Running 8 parallel environments
2. Reducing steps_per_action (10→2)
3. Shorter episodes (5000→2000)
4. GPU support (if available)
5. Optimized hyperparameters

Expected: 100k steps in 5-10 minutes (vs 1-2 hours)
"""
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from pathlib import Path

from rl_env.metro_env import MetroEnv
from game.game_state import GameConfig
from rl_env.rewards import InfrastructureReward


def mask_fn(env):
    """Extract action mask from environment."""
    return env.action_masks()


def make_env(rank, seed=0):
    """
    Utility function for creating a single environment.
    Used for parallel environment creation.
    """
    def _init():
        from sb3_contrib.common.wrappers import ActionMasker

        env = MetroEnv(
            config=GameConfig(seed=seed + rank),
            reward_function=InfrastructureReward(
                line_creation_reward=50.0,
                train_creation_reward=30.0,
                isolated_station_connection_reward=30.0,
                infrastructure_bonus_per_step=1.0,
                invalid_action_penalty=1.0
            ),
            flatten_obs=True,
            max_stations=10,
            max_steps=2000,  # Shorter episodes (was 5000)
            steps_per_action=2,  # Much faster (was 10)
            render_mode=None
        )
        env = ActionMasker(env, mask_fn)
        return env
    return _init


if __name__ == '__main__':
    print("=" * 60)
    print("FAST TRAINING - Parallel Environments")
    print("=" * 60)

    # Create directories
    models_dir = Path("models")
    logs_dir = Path("logs")
    models_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    # GPU detection
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\n🖥️  Device: {device.upper()}")
    if device == 'cuda':
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("   No GPU detected, using CPU")

    # Parallel environments
    n_envs = 8
    print(f"\n🚀 Creating {n_envs} parallel environments...")
    print(f"   Each environment:")
    print(f"     - max_steps: 2000 (shorter episodes)")
    print(f"     - steps_per_action: 2 (less simulation)")
    print(f"     - Estimated speedup: ~10-15x")

    env = SubprocVecEnv([make_env(i, seed=42) for i in range(n_envs)])
    env = VecMonitor(env, str(logs_dir / "train_monitor_fast"))

    # Single eval environment (no parallelization needed)
    print(f"\n📊 Creating evaluation environment...")
    from sb3_contrib.common.wrappers import ActionMasker
    eval_env = MetroEnv(
        config=GameConfig(seed=999),
        reward_function=InfrastructureReward(
            line_creation_reward=50.0,
            train_creation_reward=30.0,
            isolated_station_connection_reward=30.0,
            infrastructure_bonus_per_step=1.0,
            invalid_action_penalty=1.0
        ),
        flatten_obs=True,
        max_stations=10,
        max_steps=2000,
        steps_per_action=2,
        render_mode=None
    )
    eval_env = ActionMasker(eval_env, mask_fn)

    # Callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=20000,  # Less frequent (was 10000)
        save_path=str(models_dir),
        name_prefix="ppo_fast"
    )

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=str(models_dir),
        log_path=str(logs_dir),
        eval_freq=20000,  # Less frequent (was 5000)
        deterministic=True,
        render=False,
        n_eval_episodes=3  # Fewer eval episodes
    )

    # Create MaskablePPO model with optimized hyperparameters
    print("\n🧠 Creating MaskablePPO model...")
    print(f"   Hyperparameters optimized for speed:")
    print(f"     - n_steps: 512 (was 2048) - faster updates")
    print(f"     - batch_size: 64")
    print(f"     - n_epochs: 10")

    model = MaskablePPO(
        'MlpPolicy',
        env,
        device=device,
        verbose=1,
        tensorboard_log=str(logs_dir),
        learning_rate=3e-4,
        n_steps=512,  # Smaller buffer (was 2048)
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.05
    )

    # Train
    total_timesteps = 500000  # 5x longer for better learning
    print("\n" + "=" * 60)
    print(f"⚡ FAST TRAINING: {total_timesteps:,} timesteps")
    print("=" * 60)
    print(f"Expected time: ~25-50 minutes")
    print(f"Parallelization: {n_envs} environments")
    print(f"Action masking: ENABLED")
    print("=" * 60 + "\n")

    model.learn(
        total_timesteps=total_timesteps,
        callback=[checkpoint_callback, eval_callback],
        progress_bar=True
    )

    # Save final model
    model.save(models_dir / "ppo_fast_final")

    print("\n" + "=" * 60)
    print("✅ Training Complete!")
    print("=" * 60)
    print(f"Model saved to: {models_dir / 'ppo_fast_final.zip'}")
    print(f"\nTo watch the agent play:")
    print(f"  python play.py --model models/ppo_fast_final.zip")
    print("\nCompare with slow training:")
    print(f"  python train.py  (slow, 1-2 hours)")
    print(f"  python train_fast.py  (fast, 5-10 minutes)")
    print("=" * 60)

    env.close()
    eval_env.close()
