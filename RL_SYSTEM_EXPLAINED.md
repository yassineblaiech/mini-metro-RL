# Mini Metro RL System - Complete Explanation

This document explains exactly how the reinforcement learning system works: what actions the agent can take, what information it receives, and how it's rewarded.

---

## 1. Actions (What the agent can do)

The agent has **127 possible actions** using a simplified action space:

### Action Types:

1. **NO_OP** (1 action)
   - Do nothing this turn
   - Only allowed AFTER creating at least 1 line (forced to act at start)

2. **CONNECT_STATIONS** (100 actions)
   - Connect two stations with a metro line
   - Format: `CONNECT_STATIONS(station_i, station_j)`
   - Uses relative indices (0-9 for up to 10 stations)
   - Automatically picks next available color
   - **Limited**: Blocked when at max lines (6)

3. **ADD_TRAIN_TO_LINE** (6 actions)
   - Add a train to an existing line
   - Format: `ADD_TRAIN_TO_LINE(line_index)`
   - Uses relative line index (0-5 for up to 6 lines)
   - **Limited**: Blocked when at max trains (starts at 3, grows)

4. **ADD_CARRIAGE** (10 actions)
   - Add carriage to existing train (+3 capacity)
   - Format: `ADD_CARRIAGE(train_index)`
   - Max 3 carriages per train
   - Base capacity: 6, max: 15

5. **UPGRADE_STATION** (10 actions)
   - Upgrade station to hold more passengers
   - Format: `UPGRADE_STATION(station_index)`
   - Can only upgrade once per station

### Action Masking (Critical!)

**Action masking prevents invalid actions entirely:**
- ❌ Can't CONNECT_STATIONS when at max lines (6)
- ❌ Can't ADD_TRAIN when at max trains
- ❌ Can't ADD_CARRIAGE to non-existent train
- ❌ Can't UPGRADE_STATION twice
- ❌ Can't use NO_OP before creating first line

**Location**: `rl_env/metro_env.py` → `get_action_mask()`

---

## 2. Observations (What the agent sees)

The agent receives a **flattened observation vector** containing:

### Station Features (per station, max 10):
- X, Y position (normalized)
- Shape type (encoded)
- Number of waiting passengers
- Whether upgraded
- Shape-specific features

### Line Features (per line, max 6):
- Color (R, G, B normalized)
- Number of trails (connections)
- Number of stations on line

### Train Features (per train, max 10):
- Line ID
- Current position progress
- Number of passengers onboard
- Number of carriages
- Capacity

### Connectivity Matrix:
- Which stations are connected
- Binary adjacency matrix

### Global State:
- Total score
- Time elapsed
- Number of lines
- Number of trains
- Max lines available
- Max trains available

**Location**: `rl_env/observation_space.py` → `extract_observation()`

---

## 3. Rewards (How the agent learns)

The reward function is defined in `rl_env/rewards.py` → `InfrastructureReward`

### Default Reward Structure:

```python
InfrastructureReward(
    line_creation_reward=50.0,                    # BIG reward for creating lines
    train_creation_reward=30.0,                   # BIG reward for adding trains
    isolated_station_connection_reward=30.0,      # BIG reward for connecting isolated stations
    score_weight=10.0,                            # Multiplier for game score
    survival_weight=0.5,                          # Small reward per valid action
    infrastructure_bonus_per_step=1.0,            # Reward per line/train existing
    invalid_action_penalty=1.0,                   # Penalty for invalid actions
    game_over_penalty=100.0                       # Big penalty for losing
)
```

### Reward Calculation Each Step:

**Game Over:**
```
reward = -100.0
```

**Invalid Action:**
```
reward = -1.0
```

**Valid Action:**
```python
reward = 0.0

# Score increase (passengers delivered)
reward += (new_score - old_score) * 10.0

# Survival bonus (NOT for NO_OP)
if not is_noop:
    reward += 0.5

# NO_OP penalty (if no infrastructure built yet)
if is_noop and num_lines == 0:
    reward -= 1.0

# NEW LINE CREATED - BIG REWARD!
if num_lines > previous_num_lines:
    reward += 50.0 * lines_created

# NEW TRAIN ADDED - BIG REWARD!
if num_trains > previous_num_trains:
    reward += 30.0 * trains_created

# ISOLATED STATION CONNECTED - BIG REWARD!
# Stations that were not on any line are now connected
if isolated_stations_connected > 0:
    reward += 30.0 * isolated_stations_connected

# Infrastructure exists bonus
reward += (num_lines + num_trains) * 1.0
```

### Example Reward Scenarios:

**Agent creates first line (connects stations 1 and 2, both isolated):**
```
reward = 0.5 (survival) + 50.0 (line) + 60.0 (2 isolated stations) + 1.0 (infrastructure) = 111.5
```

**Agent extends line to third isolated station:**
```
reward = 0.5 (survival) + 30.0 (1 isolated station) + 1.0 (infrastructure) = 31.5
```

**Agent connects two already-connected stations (no isolated stations):**
```
reward = 0.5 (survival) + 1.0 (infrastructure) = 1.5
```

**Agent adds train to line:**
```
reward = 0.5 (survival) + 30.0 (train) + 2.0 (bonus for 1 line + 1 train) = 32.5
```

**Agent does NO_OP (has lines):**
```
reward = 0.0 (no survival for noop) + 3.0 (bonus for 3 infrastructure) = 3.0
```

**Agent does NO_OP (no lines):**
```
reward = -1.0 (penalty) = -1.0
```

**Passengers delivered (score +3):**
```
reward = 0.5 + 30.0 (3 * 10.0) + infrastructure_bonus = ~33.5
```

---

## 4. Resource System (Mini Metro Rules)

### Starting Resources:
- **3 lines** (max 6)
- **3 trains** (unlimited growth)

### Resource Unlocking:
Every **30 seconds** of survival:
- +1 line (capped at 6)
- +1 train (no cap)

### Why This Matters:
- Agent must be **strategic** with limited resources
- Can't spam infinite trains on one line
- Must **survive longer** to unlock more options
- Forces learning **resource management**

**Location**: `game/game_state.py` → `_unlock_resources()`

---

## 5. Training Process

### Algorithm: MaskablePPO
```python
from sb3_contrib import MaskablePPO

model = MaskablePPO(
    'MlpPolicy',
    env,
    learning_rate=3e-4,
    n_steps=2048,           # Collect 2048 steps before update
    batch_size=64,          # Mini-batch size
    n_epochs=10,            # Optimization epochs per update
    gamma=0.99,             # Discount factor
    gae_lambda=0.95,        # GAE parameter
    clip_range=0.2,         # PPO clip parameter
    ent_coef=0.05           # Entropy for exploration
)
```

### Why MaskablePPO?
- **Action masking**: Prevents invalid actions entirely
- **On-policy**: Learns from recent experience
- **Stable**: Good for complex action spaces

### Training Configuration:
```python
env = MetroEnv(
    config=GameConfig(seed=42),
    reward_function=InfrastructureReward(...),
    flatten_obs=True,              # Flatten observations
    max_stations=10,               # Environment limits
    max_lines=6,
    max_trains=10,
    max_steps=5000,                # Episode length
    steps_per_action=10,           # Game steps per action
    render_mode=None               # No rendering during training
)
```

**Location**: `train.py`

---

## 6. Key Design Decisions

### Why Action Masking?
Without masking, agent learns to spam invalid actions (e.g., ADD_TRAIN when no lines exist). Action masking **forces** valid behavior.

### Why Block NO_OP at Start?
Agent would learn to do nothing forever (safest action). Blocking NO_OP forces line creation, breaking local minimum.

### Why Big Infrastructure Rewards?
Small rewards (e.g., +1 for line) aren't enough signal. Agent needs **clear incentive** to build infrastructure before passengers appear.

### Why Relative Indices?
Using absolute station IDs (0-19) means 95% invalid actions. Relative indices (0 to current_num_stations) give ~60% valid rate.

### Why Resource Limits?
- Matches real Mini Metro gameplay
- Prevents degenerate strategies (spam trains on one line)
- Forces strategic thinking
- Makes problem harder → better agent

---

## 7. Training Progression

### Phase 1: Random Exploration (0-10k steps)
- Agent tries random valid actions
- Learns action masking respects constraints
- Gets big rewards for creating infrastructure

### Phase 2: Infrastructure Building (10k-50k steps)
- Agent learns: create lines → get reward
- Agent learns: add trains → get reward
- Starts connecting stations strategically

### Phase 3: Optimization (50k+ steps)
- Learns passenger routing
- Learns resource management
- Learns survival strategies

### Expected Issues:
- **Local minima**: Agent may spam one action type
- **Resource hogging**: May use all trains on one line
- **Ignoring passengers**: May build infrastructure but not route passengers

---

## 8. File Structure

```
rl_env/
├── metro_env.py              # Main environment (MetroEnv class)
│   ├── action_masks()        # Returns valid actions
│   ├── reset()               # Start new episode
│   ├── step()                # Execute action, get reward
│   └── render()              # Visualize (optional)
│
├── simple_action_space.py    # Action encoding/decoding
│   ├── SimpleActionType      # Enum of action types
│   ├── encode_simple_action()
│   ├── decode_simple_action()
│   └── execute_simple_action()  # Actually perform action
│
├── observation_space.py      # Observation encoding
│   ├── extract_observation() # Get game state features
│   ├── flatten_observation() # Convert to vector
│   └── get_flat_observation_size()
│
└── rewards.py                # Reward calculation
    └── InfrastructureReward  # Main reward function

game/
├── game_state.py             # Core game logic (headless)
│   ├── step()                # Update game
│   ├── add_trail()           # Create line connection
│   ├── add_train()           # Deploy train
│   └── _unlock_resources()   # Resource system
│
├── game_logic.py             # Pure functions (pathfinding, etc)
└── entities.py               # Data classes (Station, Line, Train)
```

---

## 9. Debugging & Monitoring

### Debug Script: `debug_agent.py`
Shows first 50 actions with details:
- Action type taken
- Valid/invalid status
- Reward received
- Lines/trains created

### Test Script: `test_agent.py`
Visual gameplay with statistics:
- Real-time line/train creation
- Action breakdown (NO_OP %, CONNECT %, etc.)
- Episode summary

### Play Script: `play.py`
Watch agent play multiple episodes:
- Speed controls (1-9)
- Toggle rendering (SPACE)
- Episode statistics

---

## 10. Next Steps & Improvements

### Current Limitations:
1. **Simple action space**: Doesn't allow complex line editing
2. **No passenger awareness**: Agent doesn't explicitly see passenger destinations
3. **Fixed unlocking**: Resources unlock on time, not performance
4. **Limited strategy**: Can't remove lines or reroute trains

### Potential Improvements:
1. **Better observation**: Add passenger destination heatmap
2. **Curriculum learning**: Train on easy maps first
3. **Reward shaping**: Reward connecting high-traffic stations
4. **Action space**: Add REMOVE_TRAIN, CLOSE_LINE actions
5. **Dynamic resources**: Unlock based on score, not time

---

## Quick Reference

### Start Training:
```bash
python train.py
```

### Watch Agent:
```bash
python play.py
```

### Debug Agent:
```bash
python debug_agent.py
```

### Test with Stats:
```bash
python test_agent.py
```

---

**Key Files**:
- Actions: `rl_env/simple_action_space.py`
- Observations: `rl_env/observation_space.py`
- Rewards: `rl_env/rewards.py`
- Environment: `rl_env/metro_env.py`
- Game Logic: `game/game_state.py`
- Training: `train.py`
