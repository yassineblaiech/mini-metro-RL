"""
Test trained agent with visual rendering and detailed statistics.
"""
import pygame
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from rl_env.metro_env import MetroEnv
from rl_env.simple_action_space import decode_simple_action
from game.game_state import GameConfig
from rl_env.rewards import InfrastructureReward


def mask_fn(env):
    """Extract action mask from environment."""
    return env.action_masks()


print("=" * 60)
print("Trained Agent - Visual Test")
print("=" * 60)
print("\nControls:")
print("  1-9: Change speed")
print("  SPACE: Toggle rendering")
print("  ESC: Quit")
print("=" * 60)

# Load model
try:
    model = MaskablePPO.load("models/ppo_final.zip")
    print("\nLoaded trained model")
except:
    print("\nERROR: No trained model found!")
    print("Run: python train.py")
    exit(1)

# Speed settings
speed_fps = 120  # Start faster
render_enabled = True

# Create environment
env = MetroEnv(
    config=GameConfig(seed=42, initial_stations=6),
    reward_function=InfrastructureReward(),
    flatten_obs=True,
    max_stations=10,
    max_steps=2000,  # Shorter episodes
    steps_per_action=5,
    render_mode='human'
)
env = ActionMasker(env, mask_fn)

print(f"\nAction space size: {env.action_space.n}")
print("Agent will use action masking (invalid actions blocked)\n")

clock = pygame.time.Clock()

try:
    episode = 0
    while True:
        obs, info = env.reset()
        episode += 1
        episode_reward = 0
        done = False

        print(f"\n{'='*60}")
        print(f"Episode {episode} started")
        print(f"  Initial: {info['num_stations']} stations, {info['num_lines']} lines, {info['num_trains']} trains")

        valid_actions = 0
        invalid_actions = 0
        noop_actions = 0
        connect_actions = 0
        train_actions = 0
        lines_created = 0
        trains_created = 0

        step = 0
        while not done:
            # Use action masking during prediction
            action, _ = model.predict(obs, deterministic=True, action_masks=info.get('action_mask'))
            action_obj = decode_simple_action(int(action), env.env.max_stations, env.env.max_lines, env.env.max_trains)

            obs, reward, terminated, truncated, info = env.step(action)

            # Track action types
            action_type = action_obj.action_type.name
            if action_type == "NO_OP":
                noop_actions += 1
            elif action_type == "CONNECT_STATIONS":
                connect_actions += 1
            elif action_type == "ADD_TRAIN_TO_LINE":
                train_actions += 1

            if info.get('action_valid', False):
                valid_actions += 1

                # Track infrastructure creation
                if info['num_lines'] > lines_created:
                    lines_created = info['num_lines']
                    station_ids = list(env.env.game_state.stations.keys())
                    if action_obj.param1 < len(station_ids) and action_obj.param2 < len(station_ids):
                        sid_a = station_ids[action_obj.param1]
                        sid_b = station_ids[action_obj.param2]
                        print(f"  [Step {step}] LINE CREATED! Connected stations {sid_a}↔{sid_b} | Total lines: {lines_created}")

                if info['num_trains'] > trains_created:
                    trains_created = info['num_trains']
                    print(f"  [Step {step}] TRAIN ADDED! Total trains: {trains_created}")
            else:
                invalid_actions += 1

            episode_reward += reward
            done = terminated or truncated
            step += 1

            # Render only if enabled
            if render_enabled:
                env.render()

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        raise KeyboardInterrupt
                    elif event.key == pygame.K_SPACE:
                        render_enabled = not render_enabled
                        mode = "ON" if render_enabled else "OFF"
                        print(f"\n[Speed Boost] Rendering {mode}")
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        speed = event.key - pygame.K_0
                        speed_fps = speed * 30
                        print(f"\n[Speed] Set to {speed}x ({speed_fps} FPS)")

            if render_enabled:
                clock.tick(speed_fps)

        total_actions = valid_actions + invalid_actions
        valid_pct = (valid_actions / total_actions * 100) if total_actions > 0 else 0
        noop_pct = (noop_actions / total_actions * 100) if total_actions > 0 else 0

        print(f"\nEpisode {episode} finished:")
        print(f"  Steps: {step}")
        print(f"  Reward: {episode_reward:.2f}")
        print(f"  Score: {info['score']}")
        print(f"  Lines created: {info['num_lines']}")
        print(f"  Trains deployed: {info['num_trains']}")
        print(f"  Valid actions: {valid_actions}/{total_actions} ({valid_pct:.1f}%)")
        print(f"  Action breakdown:")
        print(f"    NO_OP: {noop_actions} ({noop_pct:.1f}%)")
        print(f"    CONNECT_STATIONS: {connect_actions}")
        print(f"    ADD_TRAIN_TO_LINE: {train_actions}")
        print(f"    Other: {total_actions - noop_actions - connect_actions - train_actions}")

        if info['num_lines'] > 0:
            print(f"\n  Line details:")
            for line_id, line in env.env.game_state.lines.items():
                print(f"    Line {line_id}: {len(line.trails)} trails, stations: {sorted(line.get_stations())}")

except KeyboardInterrupt:
    print("\n\nStopped by user")

finally:
    env.close()
