# Line Choice Update - Multi-Station Line Support

## Problem
The RL agent could not extend existing lines - it could only create new lines. This prevented the agent from building multi-station lines (lines connecting more than 2 stations).

**Root Cause**: The action space automatically selected colors based on `len(game_state.lines)`, preventing the agent from choosing which line to extend.

## Solution
Added explicit line choice parameter (`param3`) to the CONNECT_STATIONS action, allowing the agent to specify whether to create a new line or extend an existing one.

## Changes Made

### 1. Action Space Updates

#### [rl_env/simple_action_space.py](rl_env/simple_action_space.py)

**Added `param3` field** (line 48):
```python
@dataclass
class SimpleAction:
    action_type: SimpleActionType
    param1: Optional[int] = None  # Station index, line index, or train index
    param2: Optional[int] = None  # Second station index (for CONNECT_STATIONS)
    param3: Optional[int] = None  # Line choice for CONNECT_STATIONS (-1 = new line, 0..5 = extend line)
```

**Updated action space size** (lines 21-43):
- Old size: 127 actions
- New size: 727 actions
- CONNECT_STATIONS now uses 3D encoding: `station_a × station_b × line_choice`
- Example: 10 stations × 10 stations × 7 line choices = 700 actions

**Updated encoding** (lines 55-84):
- Now encodes 3D action (station_a, station_b, line_choice) to single integer
- Line choice mapping: -1 → 0, 0..5 → 1..6

**Updated decoding** (lines 87-121):
- Decodes integer back to 3D action
- Reverses line choice mapping: 0 → -1, 1..6 → 0..5

**Updated execution** (lines 136-162):
- `line_choice = -1`: Create new line with next available color
- `line_choice = 0..5`: Extend existing line using that line's color

### 2. Action Masking Updates

#### [rl_env/metro_env.py](rl_env/metro_env.py:20-87)

**Updated `get_action_mask()`** (lines 41-75):
- Now iterates over 3D space: `station_a × station_b × line_choice`
- For `line_choice = -1` (create new line):
  - Valid only if `num_lines < max_lines`
- For `line_choice = 0..5` (extend existing line):
  - Valid only if line exists
  - AND at least one station is already on that line
  - AND the trail addition would be valid (checked via `Line.can_add_trail()`)

## Testing

Created [test_line_choice.py](test_line_choice.py) to verify:

### Test Results
✓ **Test 1: Encoding/Decoding** - All 3D actions encode and decode correctly
✓ **Test 2: Action Space Size** - Correctly calculates 727 actions
✓ **Test 3: Execution** - Successfully creates and extends lines:
  - Action 1: Connect stations 0-1 with NEW line → 1 line created
  - Action 2: Connect stations 1-2 EXTENDING line 0 → Still 1 line, now with 3 stations
  - Action 3: Connect stations 2-3 with NEW line → 2 lines total

## Usage

### Creating a New Line
```python
action = SimpleAction(
    action_type=SimpleActionType.CONNECT_STATIONS,
    param1=0,  # First station (relative index)
    param2=1,  # Second station (relative index)
    param3=-1  # Create NEW line
)
```

### Extending Existing Line
```python
action = SimpleAction(
    action_type=SimpleActionType.CONNECT_STATIONS,
    param1=1,  # First station (relative index)
    param2=2,  # Second station (relative index)
    param3=0   # Extend line 0 (relative index)
)
```

## Next Steps

1. **Retrain Models**: Old models won't work with new action space (127 → 727 actions)
2. **Test in RL Environment**: Verify action masking works correctly during training
3. **Monitor Agent Behavior**: Check if agent learns to build multi-station lines

## Breaking Changes

⚠️ **Action space size changed from 127 to 727**
- All existing trained models are incompatible
- Must retrain from scratch
- Training scripts should work without modification (automatically use new action space size)

## Files Modified

- [rl_env/simple_action_space.py](rl_env/simple_action_space.py) - Added param3, updated encoding/decoding/execution
- [rl_env/metro_env.py](rl_env/metro_env.py) - Updated action masking for 3D action space
- [test_line_choice.py](test_line_choice.py) - New test file to verify functionality

## Verification

Run the test suite to verify the implementation:
```bash
python test_line_choice.py
```

Expected output:
```
✓ Test 1: Encoding/Decoding - PASS
✓ Test 2: Action Space Size - PASS
✓ Test 3: Execution - PASS
✓ ALL CORE TESTS PASSED!
```
