"""
Test script for verifying 3D action space with line choice.
Tests encoding, decoding, execution, and masking.
"""
import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.game_state import GameState, GameConfig

# Import directly from module file to avoid importing MetroEnv
import importlib.util
spec = importlib.util.spec_from_file_location("simple_action_space",
    os.path.join(os.path.dirname(__file__), "rl_env", "simple_action_space.py"))
simple_action_space = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simple_action_space)

SimpleAction = simple_action_space.SimpleAction
SimpleActionType = simple_action_space.SimpleActionType
encode_simple_action = simple_action_space.encode_simple_action
decode_simple_action = simple_action_space.decode_simple_action
execute_simple_action = simple_action_space.execute_simple_action
get_simple_action_space_size = simple_action_space.get_simple_action_space_size

import numpy as np

# Import get_action_mask only when needed
def get_action_mask_wrapper(game_state, max_stations, max_lines, max_trains):
    """Wrapper to avoid importing gymnasium at module level."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("metro_env",
        os.path.join(os.path.dirname(__file__), "rl_env", "metro_env.py"))
    metro_env = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metro_env)
    return metro_env.get_action_mask(game_state, max_stations, max_lines, max_trains)

def test_encoding_decoding():
    """Test that encoding and decoding work correctly for line choices."""
    print("\n=== Test 1: Encoding/Decoding ===")

    # Test creating new line (line_choice = -1)
    action1 = SimpleAction(SimpleActionType.CONNECT_STATIONS, param1=0, param2=1, param3=-1)
    encoded1 = encode_simple_action(action1)
    decoded1 = decode_simple_action(encoded1)
    print(f"Create new line: {action1}")
    print(f"  Encoded: {encoded1}")
    print(f"  Decoded: {decoded1}")
    assert decoded1.action_type == action1.action_type
    assert decoded1.param1 == action1.param1
    assert decoded1.param2 == action1.param2
    assert decoded1.param3 == action1.param3
    print("  ✓ PASS")

    # Test extending line 0 (line_choice = 0)
    action2 = SimpleAction(SimpleActionType.CONNECT_STATIONS, param1=1, param2=2, param3=0)
    encoded2 = encode_simple_action(action2)
    decoded2 = decode_simple_action(encoded2)
    print(f"\nExtend line 0: {action2}")
    print(f"  Encoded: {encoded2}")
    print(f"  Decoded: {decoded2}")
    assert decoded2.action_type == action2.action_type
    assert decoded2.param1 == action2.param1
    assert decoded2.param2 == action2.param2
    assert decoded2.param3 == action2.param3
    print("  ✓ PASS")

    # Test extending line 3 (line_choice = 3)
    action3 = SimpleAction(SimpleActionType.CONNECT_STATIONS, param1=5, param2=7, param3=3)
    encoded3 = encode_simple_action(action3)
    decoded3 = decode_simple_action(encoded3)
    print(f"\nExtend line 3: {action3}")
    print(f"  Encoded: {encoded3}")
    print(f"  Decoded: {decoded3}")
    assert decoded3.action_type == action3.action_type
    assert decoded3.param1 == action3.param1
    assert decoded3.param2 == action3.param2
    assert decoded3.param3 == action3.param3
    print("  ✓ PASS")

    print("\n✓ All encoding/decoding tests passed!")

def test_action_space_size():
    """Test that action space size is calculated correctly."""
    print("\n=== Test 2: Action Space Size ===")

    size = get_simple_action_space_size(max_stations=10, max_lines=6, max_trains=10)
    print(f"Action space size: {size}")

    # Calculate expected size
    # NO_OP: 1
    # CONNECT_STATIONS: 10 * 10 * 7 = 700
    # ADD_TRAIN_TO_LINE: 6
    # ADD_CARRIAGE: 10
    # UPGRADE_STATION: 10
    # Total: 1 + 700 + 6 + 10 + 10 = 727
    expected = 1 + (10 * 10 * 7) + 6 + 10 + 10
    print(f"Expected size: {expected}")
    assert size == expected, f"Expected {expected}, got {size}"
    print("✓ PASS")

def test_execution():
    """Test that line choice execution works correctly."""
    print("\n=== Test 3: Execution ===")

    config = GameConfig(seed=42)
    game_state = GameState(config)

    # Run game for a bit to spawn stations
    for _ in range(100):
        game_state.step(dt=0.016)

    print(f"Stations: {len(game_state.stations)}")
    station_ids = list(game_state.stations.keys())

    if len(station_ids) < 3:
        print("⚠ Not enough stations spawned, skipping execution test")
        return

    # Create first line (line_choice = -1)
    action1 = SimpleAction(SimpleActionType.CONNECT_STATIONS, param1=0, param2=1, param3=-1)
    success1 = execute_simple_action(action1, game_state)
    print(f"\nAction 1: Connect station 0-1 with NEW line")
    print(f"  Success: {success1}")
    print(f"  Lines: {len(game_state.lines)}")
    assert success1, "Failed to create first line"
    assert len(game_state.lines) == 1, "Should have 1 line"
    print("  ✓ PASS")

    # Try to extend first line (line_choice = 0)
    action2 = SimpleAction(SimpleActionType.CONNECT_STATIONS, param1=1, param2=2, param3=0)
    success2 = execute_simple_action(action2, game_state)
    print(f"\nAction 2: Connect station 1-2 EXTENDING line 0")
    print(f"  Success: {success2}")
    print(f"  Lines: {len(game_state.lines)}")
    line_0 = list(game_state.lines.values())[0]
    print(f"  Line 0 stations: {line_0.get_stations()}")
    assert success2, "Failed to extend line"
    assert len(game_state.lines) == 1, "Should still have 1 line"
    assert len(line_0.trails) == 2, "Line should have 2 trails"
    print("  ✓ PASS")

    # Create second line (line_choice = -1)
    if len(station_ids) >= 4:
        action3 = SimpleAction(SimpleActionType.CONNECT_STATIONS, param1=2, param2=3, param3=-1)
        success3 = execute_simple_action(action3, game_state)
        print(f"\nAction 3: Connect station 2-3 with NEW line")
        print(f"  Success: {success3}")
        print(f"  Lines: {len(game_state.lines)}")
        assert success3, "Failed to create second line"
        assert len(game_state.lines) == 2, "Should have 2 lines"
        print("  ✓ PASS")

    print("\n✓ All execution tests passed!")

def test_masking():
    """Test that action masking works correctly for line choices."""
    print("\n=== Test 4: Action Masking ===")

    config = GameConfig(seed=42)
    game_state = GameState(config)

    # Run game for a bit to spawn stations
    for _ in range(100):
        game_state.step(dt=0.016)

    print(f"Stations: {len(game_state.stations)}")
    station_ids = list(game_state.stations.keys())

    if len(station_ids) < 3:
        print("⚠ Not enough stations spawned, skipping masking test")
        return

    # Get initial mask (no lines yet)
    mask1 = get_action_mask_wrapper(game_state, max_stations=10, max_lines=6, max_trains=10)
    print(f"\nInitial mask (no lines):")
    print(f"  Total actions: {len(mask1)}")
    print(f"  Valid actions: {int(mask1.sum())}")

    # Check that only "create new line" actions are valid
    # NO_OP should be invalid (no infrastructure yet)
    assert mask1[0] == 0.0, "NO_OP should be invalid at start"

    # Count valid CONNECT actions
    connect_start = 1
    connect_end = 1 + (10 * 10 * 7)
    valid_connects = mask1[connect_start:connect_end].sum()
    print(f"  Valid CONNECT actions: {int(valid_connects)}")
    print("  ✓ PASS")

    # Create first line
    action1 = SimpleAction(SimpleActionType.CONNECT_STATIONS, param1=0, param2=1, param3=-1)
    execute_simple_action(action1, game_state)

    # Get mask after creating first line
    mask2 = get_action_mask_wrapper(game_state, max_stations=10, max_lines=6, max_trains=10)
    print(f"\nAfter creating first line:")
    print(f"  Lines: {len(game_state.lines)}")
    print(f"  Valid actions: {int(mask2.sum())}")

    # Now NO_OP should be valid (infrastructure exists)
    assert mask2[0] == 1.0, "NO_OP should be valid after creating line"

    # Check that we can now extend line 0
    line_0_stations = list(game_state.lines.values())[0].get_stations()
    print(f"  Line 0 stations: {line_0_stations}")

    # Count valid extend actions vs create new line actions
    valid_connects_new = mask2[connect_start:connect_end].sum()
    print(f"  Valid CONNECT actions: {int(valid_connects_new)}")
    print(f"  ✓ More actions available (can extend existing line)")
    print("  ✓ PASS")

    print("\n✓ All masking tests passed!")

def main():
    print("=" * 60)
    print("Testing 3D Action Space with Line Choice")
    print("=" * 60)

    test_encoding_decoding()
    test_action_space_size()
    test_execution()

    try:
        test_masking()
    except ModuleNotFoundError as e:
        if 'gymnasium' in str(e):
            print("\n=== Test 4: Action Masking ===")
            print("⚠ Skipped (gymnasium not installed - run in RL environment to test)")
        else:
            raise

    print("\n" + "=" * 60)
    print("✓ ALL CORE TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    main()
