"""
Debug the trained agent - see exactly what it's doing.
"""
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from rl_env.metro_env import MetroEnv
from rl_env.simple_action_space import decode_simple_action
from game.game_state import GameConfig
from rl_env.rewards import InfrastructureReward


def mask_fn(env):
    """Extract action mask from environment."""
    return env.action_masks()


# Load model
try:
    model = MaskablePPO.load("models/ppo_final.zip")
    print("Loaded trained model\n")
except:
    print("ERROR: No trained model found!")
    print("Run: python train.py")
    exit(1)

# Create environment
env = MetroEnv(
    config=GameConfig(seed=42, initial_stations=5),
    reward_function=InfrastructureReward(),
    flatten_obs=True,
    max_stations=10,
    max_steps=200,
    steps_per_action=5,
    render_mode=None
)
env = ActionMasker(env, mask_fn)

obs, info = env.reset(seed=42)

print("=" * 60)
print("INITIAL STATE")
print("=" * 60)
print(f"Stations: {len(env.env.game_state.stations)}")
print(f"Station IDs: {list(env.env.game_state.stations.keys())}")
print(f"Lines: {len(env.env.game_state.lines)}")
print(f"Trains: {len(env.env.game_state.trains)}")
print(f"Action mask sum: {info['action_mask'].sum()}/{len(info['action_mask'])} valid actions")
print()

print("=" * 60)
print("FIRST 50 ACTIONS FROM MASKED TRAINED AGENT")
print("=" * 60)

action_counts = {}
valid_count = 0
invalid_count = 0

for step in range(50):
    # Use action masking during prediction
    action, _ = model.predict(obs, deterministic=True, action_masks=info.get('action_mask'))
    action_obj = decode_simple_action(int(action), env.env.max_stations, env.env.max_lines, env.env.max_trains)

    obs, reward, terminated, truncated, info = env.step(action)

    action_type = action_obj.action_type.name
    action_counts[action_type] = action_counts.get(action_type, 0) + 1

    if info['action_valid']:
        valid_count += 1
        status = "✓ VALID"
    else:
        invalid_count += 1
        status = "✗ INVALID"

    # Print first 20 actions in detail
    if step < 20:
        print(f"Step {step+1:2d}: {action_type:20} | {status:10} | "
              f"Reward: {reward:7.2f} | Lines: {info['num_lines']} | Trains: {info['num_trains']}")

        # If it's a CONNECT_STATIONS action, show which stations
        if action_type == "CONNECT_STATIONS":
            station_ids = list(env.env.game_state.stations.keys())
            if action_obj.param1 < len(station_ids) and action_obj.param2 < len(station_ids):
                sid_a = station_ids[action_obj.param1]
                sid_b = station_ids[action_obj.param2]
                print(f"       → Connecting station index {action_obj.param1}→{action_obj.param2} "
                      f"(IDs: {sid_a}→{sid_b})")

        # Show how many valid actions are available
        num_valid = int(info['action_mask'].sum())
        print(f"       → {num_valid} valid actions available after this step")

    if terminated or truncated:
        print(f"\nEpisode ended at step {step+1}")
        break

print("\n" + "=" * 60)
print("STATISTICS")
print("=" * 60)
print(f"Valid actions:   {valid_count} ({valid_count/(valid_count+invalid_count)*100:.1f}%)")
print(f"Invalid actions: {invalid_count} ({invalid_count/(valid_count+invalid_count)*100:.1f}%)")
print()
print("Action Type Breakdown:")
for action_type, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {action_type:20}: {count:3d} times")

print()
print("=" * 60)
print("FINAL STATE")
print("=" * 60)
print(f"Lines created: {info['num_lines']}")
print(f"Trains added: {info['num_trains']}")
print(f"Score: {info['score']}")

if info['num_lines'] > 0:
    print("\nLine details:")
    for line_id, line in env.env.game_state.lines.items():
        print(f"  Line {line_id}: {len(line.trails)} trails, stations: {line.get_stations()}")
else:
    print("\n⚠ WARNING: No lines created!")
    print("This should NOT happen with action masking!")
    print("The agent should be FORCED to create lines since invalid actions are blocked.")

if info['num_trains'] > 0:
    print("\nTrain details:")
    for train_id, train in env.env.game_state.trains.items():
        print(f"  Train {train_id}: Line {train.line_id}, Carriages: {train.carriages}, "
              f"Capacity: {train.effective_capacity()}, Passengers: {len(train.passengers)}")

env.close()
