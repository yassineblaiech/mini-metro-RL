# Training Flow Visualization

## High-Level Training Loop

```
┌─────────────────────────────────────────────────────────────┐
│                     TRAINING EPISODE                         │
└─────────────────────────────────────────────────────────────┘

1. RESET
   ├─> Initialize game with 8 stations
   ├─> Set max_lines = 3, max_trains = 3
   └─> Return initial observation

2. AGENT DECISION LOOP (repeat until done)
   │
   ├─> Get observation (game state)
   │   ├─> Station features (positions, waiting passengers)
   │   ├─> Line features (connections, colors)
   │   ├─> Train features (positions, passengers)
   │   └─> Global state (score, time, resources)
   │
   ├─> Get action mask (valid actions only)
   │   ├─> NO_OP: blocked if no lines
   │   ├─> CONNECT_STATIONS: blocked if at max lines
   │   ├─> ADD_TRAIN: blocked if at max trains
   │   └─> Other actions based on existence
   │
   ├─> Agent picks action (using mask)
   │   └─> MaskablePPO ensures only valid actions
   │
   ├─> Execute action in game
   │   ├─> CONNECT_STATIONS(2,5) → Creates line
   │   ├─> ADD_TRAIN(0) → Adds train to line 0
   │   ├─> ADD_CARRIAGE(0) → Upgrades train 0
   │   └─> etc.
   │
   ├─> Simulate game (10 steps @ 60fps)
   │   ├─> Move trains
   │   ├─> Spawn passengers
   │   ├─> Unlock resources (every 30s)
   │   └─> Check game over
   │
   ├─> Calculate reward
   │   ├─> +50.0 if created line
   │   ├─> +30.0 if added train
   │   ├─> +0.5 survival
   │   ├─> +infrastructure_bonus
   │   ├─> -1.0 if invalid action
   │   └─> -100.0 if game over
   │
   ├─> Check if done
   │   ├─> Station overflow? (>12 waiting)
   │   ├─> Max steps reached? (5000)
   │   └─> No → continue loop
   │
   └─> Store experience (s, a, r, s', mask)

3. EPISODE END
   └─> Update policy using collected experience
```

---

## Detailed Step Breakdown

### STEP 1: Reset Environment

```python
obs, info = env.reset(seed=42)

# Game State After Reset:
{
    'stations': 8,          # Random positions
    'lines': 0,             # No lines yet
    'trains': 0,            # No trains yet
    'max_lines': 3,         # Limited resources!
    'max_trains': 3,
    'score': 0,
    'time_elapsed': 0.0
}

# Observation: [station_features, line_features, train_features, ...]
# Shape: (flat_vector of ~200 floats)

# Action Mask: [0, 1, 1, 1, ..., 1, 0, 0, ...]
# NO_OP blocked (0), CONNECT_STATIONS allowed (1), ADD_TRAIN blocked (0)
```

---

### STEP 2: Agent Selects Action

```python
action, _ = model.predict(obs, action_masks=info['action_mask'])

# Agent's Neural Network:
obs (200 floats)
  → Hidden Layer 1 (64 neurons)
  → Hidden Layer 2 (64 neurons)
  → Output Layer (127 actions)
  → Apply mask (set invalid to -inf)
  → Softmax → Pick action

# Example: action = 15
# Decodes to: CONNECT_STATIONS(station_0, station_3)
```

---

### STEP 3: Execute Action

```python
obs, reward, terminated, truncated, info = env.step(action)

# Behind the scenes:
1. Decode action 15 → CONNECT_STATIONS(0, 3)
2. Get actual station IDs: [1, 2, 3, 4, 5, 6, 7, 8]
3. Map indices: station_0 = ID 1, station_3 = ID 4
4. Execute: game_state.add_trail(1, 4, RED)
5. Simulate 10 game steps (trains move, passengers spawn)
6. Calculate reward
7. Update observation
```

---

### STEP 4: Reward Calculation

```python
# Example 1: Creating First Line
prev_state: num_lines = 0
new_state:  num_lines = 1

reward = 0.0
reward += 0.5                    # survival (valid action)
reward += 50.0 * 1               # line created!
reward += 1.0 * 1                # infrastructure bonus (1 line)
reward = 51.5                    # Total!

# Example 2: Adding Train to Line
prev_state: num_trains = 0
new_state:  num_trains = 1

reward = 0.0
reward += 0.5                    # survival
reward += 30.0 * 1               # train created!
reward += 1.0 * 2                # infrastructure bonus (1 line + 1 train)
reward = 32.5                    # Total!

# Example 3: Passenger Delivered
prev_state: score = 0
new_state:  score = 1

reward = 0.0
reward += 0.5                    # survival
reward += 1 * 10.0               # score increase (weight=10)
reward += 1.0 * 2                # infrastructure bonus
reward = 12.5                    # Total!

# Example 4: Game Over (station overflow)
reward = -100.0                  # Big penalty!
```

---

### STEP 5: Resource Unlocking

```python
# Time-based unlocking (every 30 seconds)

t = 0s:   max_lines = 3, max_trains = 3  # START
t = 30s:  max_lines = 4, max_trains = 4  # +1 +1
t = 60s:  max_lines = 5, max_trains = 5  # +1 +1
t = 90s:  max_lines = 6, max_trains = 6  # +1 +1 (lines capped)
t = 120s: max_lines = 6, max_trains = 7  # trains keep growing

# Console output:
[Resources] Unlocked line! Now have 4/6 lines available
[Resources] Unlocked train! Now have 4 trains available
```

---

## Action Masking Example

### Scenario: Agent has 2 lines, 2 trains, at max (3/3)

```python
Action Space (127 actions):
┌────────────────────────────────────────────┐
│ Action ID | Action Type        | Valid?   │
├────────────────────────────────────────────┤
│ 0         | NO_OP              | ✓ (has lines)
│ 1-100     | CONNECT_STATIONS   | ✗ (at max lines)
│ 101-106   | ADD_TRAIN_TO_LINE  | ✗ (at max trains)
│ 107-116   | ADD_CARRIAGE       | ✓ (if train exists)
│ 117-126   | UPGRADE_STATION    | ✓ (if not upgraded)
└────────────────────────────────────────────┘

Action Mask:
[1, 0, 0, 0, ..., 0, 1, 1, 0, 1, 1, 1, 0, ...]
 ↑  └─ CONNECT blocked   ↑ ADD_CARRIAGE ok
 NO_OP ok                  └─ ADD_TRAIN blocked

Agent can ONLY choose from valid actions!
Invalid actions have probability = 0
```

---

## Observation Structure

```python
# Station Features (10 stations max, 10 features each)
[
  # Station 0
  [x, y, shape_encoded, waiting, upgraded, shape_feature_1, ...],
  # Station 1
  [x, y, shape_encoded, waiting, upgraded, shape_feature_1, ...],
  ...
]

# Line Features (6 lines max, 5 features each)
[
  # Line 0
  [r, g, b, num_trails, num_stations],
  # Line 1
  [r, g, b, num_trails, num_stations],
  ...
]

# Train Features (10 trains max, 5 features each)
[
  # Train 0
  [line_id, progress, passengers, carriages, capacity],
  # Train 1
  [line_id, progress, passengers, carriages, capacity],
  ...
]

# Connectivity Matrix (10x10)
[
  [0, 1, 0, 1, 0, ...],  # Station 0 connected to 1 and 3
  [1, 0, 1, 0, 0, ...],  # Station 1 connected to 0 and 2
  ...
]

# Global Features
[score, time_elapsed, num_lines, num_trains, max_lines, max_trains]

# All flattened into single vector (~200 floats)
```

---

## Training Progress

```
Episode 1 (0 steps trained):
├─> Random actions (high entropy)
├─> Creates 1-2 lines randomly
├─> Adds 1-2 trains randomly
├─> Game over quickly (no strategy)
└─> Reward: ~100-200

Episode 10 (10k steps trained):
├─> Learns to create lines consistently
├─> Learns to add trains to lines
├─> Still poor passenger routing
├─> Survives 30-60 seconds
└─> Reward: ~500-1000

Episode 100 (100k steps trained):
├─> Strategic line placement
├─> Distributes trains across lines
├─> Routes passengers effectively
├─> Survives 2-3 minutes
└─> Reward: ~2000-3000

Expected learning curve:
  Reward
    ↑
3000|              ╱──────
    |            ╱
2000|          ╱
    |        ╱
1000|      ╱
    |    ╱
 500|  ╱
    |╱
    └────────────────────> Episodes
     0   50  100  150  200
```

---

## Common Training Issues

### Issue 1: Agent Spams NO_OP
**Symptom**: Does nothing, gets small positive reward
**Fix**: Block NO_OP until first line created ✓

### Issue 2: Agent Spams Invalid Actions
**Symptom**: Tries ADD_TRAIN when no lines exist
**Fix**: Use action masking to block invalid actions ✓

### Issue 3: Agent Builds One Line, Spam Trains
**Symptom**: Puts all trains on one line
**Fix**: Resource limits (max 3 trains at start) ✓

### Issue 4: Poor Exploration
**Symptom**: Gets stuck in local minimum
**Fix**: Higher entropy coefficient (ent_coef=0.05) ✓

### Issue 5: Ignores Passengers
**Symptom**: Builds infrastructure but doesn't route passengers
**Fix**: High score weight (score_weight=10.0) ✓

---

## Summary

**The agent learns through trial and error:**
1. Take action (masked for validity)
2. Get big rewards for infrastructure
3. Get score rewards for passengers
4. Get penalties for game over
5. Repeat 100,000+ times
6. Learn optimal policy

**Key to success:**
- Action masking forces valid behavior
- Big infrastructure rewards teach building
- Resource limits force strategy
- Time-based unlocking adds progression
