"""
Watch trained agent play.

Usage:
  python play.py                              # Use default model
  python play.py --model models/ppo_fast_final.zip  # Use specific model
"""
import sys
import pygame
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from rl_env.metro_env import MetroEnv
from game.game_state import GameConfig
from rl_env.rewards import InfrastructureReward


def mask_fn(env):
    """Extract action mask from environment."""
    return env.action_masks()


print("=" * 60)
print("Watching Trained Agent")
print("=" * 60)

# Parse command line arguments
model_path = "models/ppo_final.zip"
if "--model" in sys.argv:
    idx = sys.argv.index("--model")
    if idx + 1 < len(sys.argv):
        model_path = sys.argv[idx + 1]

# Load model
try:
    model = MaskablePPO.load(model_path)
    print(f"Loaded model: {model_path}\n")
except FileNotFoundError:
    print(f"❌ Model not found: {model_path}")
    print("\nAvailable models:")
    import os
    if os.path.exists("models"):
        for f in os.listdir("models"):
            if f.endswith(".zip"):
                print(f"  - models/{f}")
    sys.exit(1)

env = MetroEnv(
    config=GameConfig(seed=42),
    reward_function=InfrastructureReward(),
    flatten_obs=True,
    max_stations=10,
    max_steps=5000,
    steps_per_action=5,
    render_mode='human'
)
env = ActionMasker(env, mask_fn)

clock = pygame.time.Clock()
speed_fps = 120
render_enabled = True

try:
    for episode in range(10):
        obs, info = env.reset()
        done = False
        episode_reward = 0
        valid_actions = 0
        total_actions = 0

        print(f"\nEpisode {episode + 1}")

        while not done:
            # Use action masking during prediction
            action, _ = model.predict(obs, deterministic=True, action_masks=info.get('action_mask'))
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            done = terminated or truncated

            if info.get('action_valid', False):
                valid_actions += 1
            total_actions += 1

            if render_enabled:
                env.render()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        raise KeyboardInterrupt
                    elif event.key == pygame.K_SPACE:
                        render_enabled = not render_enabled
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        speed = event.key - pygame.K_0
                        speed_fps = speed * 30

            if render_enabled:
                clock.tick(speed_fps)

        valid_pct = 100.0 * valid_actions / total_actions if total_actions > 0 else 0
        print(f"  Reward: {episode_reward:.1f}, Valid: {valid_pct:.1f}%, Lines: {info['num_lines']}, Trains: {info['num_trains']}, Score: {info['score']}")

except KeyboardInterrupt:
    print("\nStopped")

env.close()
