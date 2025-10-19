# Mini Metro Mechanics Analysis & Implementation Plan

## Research Summary: Actual Mini Metro Mechanics

### 1. Station System

#### Station Types & Spawning
**Actual Mini Metro:**
- **Circle**: Most common station type, appears frequently throughout the game
- **Triangle**: Second most common
- **Square**: Third most common
- **Special shapes** (Star, Pentagon, Cross, Diamond, Wedge, Egg, Gem): Each appears only ONCE per map
- When a special station spawns, there's a 50% chance it replaces an existing regular station
- Circle stations can spontaneously transform into any other station type

**Current Implementation:**
- Only 4 shapes: circle, square, triangle, pentagon
- All shapes spawn with equal probability
- No special station mechanics
- No station transformation
- Initial 8 stations, no progressive spawning

#### Station Capacity
**Actual Mini Metro:**
- Regular stations: **6 passengers** max
- Interchange stations: **18 passengers** max
- Overcrowding triggers a countdown timer
- If still overcrowded when timer expires → Game Over (Normal/Extreme modes)
- Endless mode: No overcrowding game over

**Current Implementation:**
- Max 12 passengers per station (configurable)
- Instant game over when exceeded (no timer)
- No interchange stations
- No station upgrade capacity system

### 2. Passenger System

#### Passenger Spawning Rules
**Actual Mini Metro:**
- Passengers spawn at every station on the map
- Spawn rate tied to **in-game clock** (happens at regular intervals)
- Each station type generates different amounts of passengers for other station types
- **Spawn rate scaling**: Increases as game progresses (passengerSpawnScale parameter)
- Some maps (Hong Kong, Osaka, São Paulo) have faster spawn rates
- **Critical rule**: Passengers never spawn at a station matching their destination shape
- **Triangle special rule**: Triangles never want to go to squares (only circles, stars, pentagons)

**Current Implementation:**
- Random station selection for spawning
- Fixed spawn interval (1.0 seconds, configurable)
- No spawn rate scaling over time
- No station-type-specific spawn rules
- No special routing rules for triangles
- Correctly implements: passengers don't spawn for their own shape

#### Passenger Routing
**Actual Mini Metro:**
- Passengers automatically board trains going toward their destination
- Multi-line journeys possible via interchanges
- Smart pathfinding through the network

**Current Implementation:**
- Has pathfinding system (A* based)
- Supports multi-line journeys
- Has exchange station detection
- **Good implementation** - matches actual game

### 3. Train System

#### Train Capacity
**Actual Mini Metro:**
- Base locomotive: **6 passengers** (4 on Cairo/Mumbai maps)
- Each carriage: **+6 passengers**
- Multiple carriages allowed per train
- Max **4 trains per line**

**Current Implementation:**
- Train capacity: 3 passengers (hardcoded)
- Carriages: 0-3 per train (but capacity calculation unclear)
- No map-specific capacity variations
- No trains-per-line limit

#### Train Speed
**Actual Mini Metro:**
- Standard speed for most trains
- Special Shinkansen in Osaka: **2x speed**
- No speed variations otherwise

**Current Implementation:**
- Fixed speed: 100 pixels/second
- No special trains
- No speed variations

#### Train Behavior
**Actual Mini Metro:**
- Trains automatically traverse lines
- Stop at every station UNLESS:
  - Station is empty AND
  - No passengers on train want that station
- Cannot control trains directly (only move between lines)

**Current Implementation:**
- Trains traverse lines automatically
- Stop at all stations (no skip logic)
- Move through waypoint-based paths
- **Needs improvement**: Skip empty stations

### 4. Line System

#### Line Creation
**Actual Mini Metro:**
- Lines use orthogonal/diagonal paths only (0°, 45°, 90°)
- Lines can be loops or linear paths
- Max 4 trains per line
- In Extreme mode: Lines cannot be edited once set

**Current Implementation:**
- ✅ Orthogonal/diagonal paths implemented
- ✅ Loops supported
- ❌ No trains-per-line limit
- ❌ No mode restrictions

#### Parallel Lines
**Actual Mini Metro:**
- When multiple lines share a segment, they render with perpendicular offset
- Visual clarity for complex networks

**Current Implementation:**
- ✅ **Excellent implementation** - already has parallel line offset rendering
- Uses PARALLEL_LINE_OFFSET = 8 pixels

### 5. Weekly Upgrade System

**Actual Mini Metro:**
- Game progresses in **weeks** (time-based)
- Every week: **Guaranteed 1 locomotive** + **choice between 2 other assets**
- Available assets:
  - **Locomotives**: New train
  - **Carriages**: +6 capacity to existing train
  - **Lines**: New line (different color)
  - **Interchanges**: Upgrade station to 18 capacity
  - **Tunnels/Bridges**: Cross water obstacles

**Current Implementation:**
- Time-based unlocking every 30 seconds
- Auto-unlocks: +1 line (max 6) + +1 train
- No player choice
- No carriages as pickups
- No interchange upgrades
- No tunnels (obstacles exist but no crossing mechanic)

### 6. Map & Obstacles

**Actual Mini Metro:**
- Maps based on real cities
- Water obstacles require tunnels/bridges to cross
- Progressive station spawning at map edges
- Unique map characteristics (spawn rates, capacities)

**Current Implementation:**
- Generic rectangular map
- Obstacles exist but cannot be crossed
- All stations spawn at start (no progressive spawning)
- No map-specific tuning

### 7. Game Modes

**Actual Mini Metro:**
- **Normal**: Overcrowding timer, standard difficulty
- **Extreme**: Lines cannot be edited, harder
- **Endless**: No game over, infinite mode

**Current Implementation:**
- Only one mode
- No difficulty variations

---

## Current Implementation vs Actual Mini Metro

### ✅ What's Already Good
1. **Orthogonal/diagonal line paths** - Perfect implementation
2. **Parallel line rendering** - Excellent visual system
3. **Passenger pathfinding** - Multi-line routing works
4. **Basic train movement** - Waypoint-based traversal
5. **Shape-based destinations** - Core mechanic working
6. **Line loop support** - Can create circular routes

### ⚠️ What Needs Improvement
1. **Station spawning** - Missing progressive spawning, special stations
2. **Passenger spawn rates** - No scaling, no station-type rules
3. **Train capacity** - Too low (3 vs 6), no carriage system
4. **Station capacity** - Wrong value (12 vs 6), no interchanges
5. **Weekly upgrades** - No player choice, wrong mechanics
6. **Game over** - No overcrowding timer
7. **Train optimization** - No station skipping

### ❌ What's Missing Entirely
1. **Special station types** (star, cross, diamond, etc.)
2. **Station transformation** (circles changing shape)
3. **Weekly choice system** (pick 1 of 2 upgrades)
4. **Interchange stations**
5. **Tunnel/bridge crossing mechanics**
6. **Triangle routing rules** (no squares)
7. **Station-type-specific passenger generation**
8. **Spawn rate scaling over time**
9. **Multiple game modes**
10. **Map-specific tuning**
11. **Max trains per line limit**
12. **Overcrowding countdown timer**

---

## Implementation Priority Plan

I'll organize the changes into 4 priority tiers based on:
- **Impact on gameplay accuracy**
- **Complexity of implementation**
- **Dependencies between features**

### 🔴 TIER 1: Critical Core Mechanics (High Impact, Medium Complexity)

These fundamentally change how the game plays and are essential for Mini Metro authenticity.

#### 1.1 Fix Station Capacity (6 passengers)
- **File**: `game/game_state.py`, `game/entities.py`
- **Change**: Default max_passengers_per_station: 12 → 6
- **Impact**: Makes overcrowding happen much faster (more challenging)
- **Complexity**: Low (config change)

#### 1.2 Fix Train Base Capacity (6 passengers)
- **File**: `game/entities.py` (Train class)
- **Change**: Base capacity 3 → 6
- **Impact**: Allows proper passenger transport
- **Complexity**: Low (constant change)

#### 1.3 Implement Overcrowding Timer
- **File**: `game/game_state.py`, `game/entities.py`
- **New**: Station.overcrowding_timer field
- **Logic**:
  - When station hits 6 passengers, start timer (e.g., 10 seconds)
  - If still overcrowded when timer expires → game over
  - If cleared before timer → reset timer
- **Impact**: Gives player time to react (more fair)
- **Complexity**: Medium (new state tracking)

#### 1.4 Progressive Station Spawning
- **File**: `game/game_state.py`
- **Change**:
  - Start with fewer stations (e.g., 3-4)
  - Spawn new stations at map edges over time (e.g., every week)
  - Implement spawn_new_station() method
- **Impact**: Makes game progression feel like actual Mini Metro
- **Complexity**: Medium (spawn logic + positioning)

#### 1.5 Passenger Spawn Rate Scaling
- **File**: `game/game_state.py`
- **New**: passenger_spawn_scale multiplier
- **Logic**: Gradually increase spawn rate as game progresses
  - Start: 1.0 (normal interval)
  - Week 2: 0.9 (10% faster)
  - Week 3: 0.8 (20% faster)
  - etc.
- **Impact**: Creates late-game pressure
- **Complexity**: Low (simple multiplier)

### 🟡 TIER 2: Weekly Upgrade System (High Impact, High Complexity)

This is the signature Mini Metro feature - essential for authenticity.

#### 2.1 Week-Based Time System
- **File**: `game/game_state.py`
- **New**:
  - current_week: int
  - week_duration: float (e.g., 60 seconds)
  - on_week_complete() callback
- **Logic**: Track weeks instead of continuous time
- **Impact**: Foundation for upgrade system
- **Complexity**: Medium (time tracking refactor)

#### 2.2 Weekly Upgrade Choice System
- **File**: `game/game_state.py`, new `game/upgrades.py`
- **New**:
  - UpgradeType enum (LOCOMOTIVE, CARRIAGE, LINE, INTERCHANGE, TUNNEL)
  - available_upgrades: List[UpgradeType]
  - offer_upgrade_choice(option1, option2) method
- **Logic**:
  - Every week: give 1 locomotive + choice of 2 random upgrades
  - Player/agent selects one
  - Apply upgrade immediately
- **Impact**: Core progression system
- **Complexity**: High (UI/action space changes for RL)

#### 2.3 Interchange Station Upgrades
- **File**: `game/entities.py` (Station), `game/game_state.py`
- **New**:
  - Station.is_interchange: bool
  - Interchange capacity: 18 passengers
  - upgrade_to_interchange(station_id) method
- **Impact**: Strategic station upgrades
- **Complexity**: Medium (station upgrade system)

#### 2.4 Carriage System
- **File**: `game/entities.py` (Train)
- **Change**: Make carriages functional
  - Train.carriages: int (0-3)
  - Each carriage: +6 capacity
  - Total capacity = 6 + (carriages * 6)
- **Impact**: Train capacity management
- **Complexity**: Low (formula change)

### 🟢 TIER 3: Special Stations & Rules (Medium Impact, Medium Complexity)

Adds variety and depth to gameplay.

#### 3.1 Special Station Types
- **File**: `game/game_logic.py`, `game/entities.py`
- **New**: Expand SHAPES list:
  - Common: circle, triangle, square
  - Special (1 per map): star, pentagon, cross, diamond, wedge
- **Logic**:
  - Track which special stations have spawned
  - Special stations spawn once, may replace existing stations
- **Impact**: More variety in networks
- **Complexity**: Medium (spawn logic)

#### 3.2 Triangle Routing Rules
- **File**: `game/game_logic.py` (spawn_passenger)
- **Logic**: Triangles never generate passengers destined for squares
  - Filter destination shapes based on origin shape
  - Triangle → only circle, star, pentagon
- **Impact**: Subtle routing optimization
- **Complexity**: Low (spawn filter)

#### 3.3 Station-Type-Specific Spawn Rates
- **File**: `game/game_logic.py`
- **New**: SPAWN_RATE_MATRIX: Dict[str, Dict[str, float]]
  - Different probabilities for each origin→destination pair
  - Example: Circles generate more passengers than squares
- **Impact**: More realistic passenger patterns
- **Complexity**: Medium (spawn probability system)

#### 3.4 Circle Station Transformation
- **File**: `game/game_state.py`
- **Logic**: Circles can randomly transform into other station types
  - Low probability per week (e.g., 10%)
  - Update shape, trigger passenger rerouting
- **Impact**: Dynamic network challenges
- **Complexity**: Medium (transformation + rerouting)

### 🔵 TIER 4: Polish & Advanced Features (Low-Medium Impact, Variable Complexity)

Nice-to-haves that complete the experience.

#### 4.1 Train Station Skipping
- **File**: `game/game_state.py` (_update_trains)
- **Logic**: Trains skip stations if:
  - Station has no waiting passengers AND
  - No train passengers want that station
- **Impact**: Better train efficiency
- **Complexity**: Medium (routing logic)

#### 4.2 Max Trains Per Line (4)
- **File**: `game/entities.py` (Line), `rl_env/metro_env.py`
- **Logic**: Enforce max 4 trains on any single line
- **Impact**: Strategic train allocation
- **Complexity**: Low (validation check)

#### 4.3 Tunnel/Bridge Crossing
- **File**: `game/game_logic.py`, `game/game_state.py`
- **New**:
  - Line.tunnels_used: int
  - Available tunnels from upgrades
  - Allow lines to cross obstacles if tunnel available
- **Impact**: Obstacle crossing mechanic
- **Complexity**: High (pathfinding changes)

#### 4.4 Game Modes
- **File**: `game/game_state.py`, new `game/game_modes.py`
- **New**: GameMode enum (NORMAL, EXTREME, ENDLESS)
  - Normal: Standard rules
  - Extreme: Lines cannot be edited
  - Endless: No overcrowding game over
- **Impact**: Replayability
- **Complexity**: Medium (mode-specific logic)

#### 4.5 Map-Specific Tuning
- **File**: new `game/maps.py`
- **New**: Map presets with different parameters:
  - Spawn rates
  - Train capacities
  - Station spawn patterns
- **Impact**: Variety between games
- **Complexity**: Medium (config system)

---

## RL Environment Impact Analysis

### Action Space Changes Required

#### Current Actions (727 total):
1. NO_OP
2. CONNECT_STATIONS (with line choice)
3. ADD_TRAIN_TO_LINE
4. ADD_CARRIAGE
5. UPGRADE_STATION

#### New Actions Needed:

**For Weekly Upgrades (TIER 2.2):**
- **SELECT_WEEKLY_UPGRADE(choice: 0 or 1)** - Choose between 2 offered upgrades
  - Simple discrete action: 2 choices
  - Triggered at week boundary
  - **Impact**: +2 actions (or special handling in step())

**For Interchange Upgrades (TIER 2.3):**
- **UPGRADE_STATION** already exists - can repurpose for interchange upgrades
  - No action space change needed
  - Just change semantics: upgrade → make interchange

**For Train Movement Between Lines:**
- **MOVE_TRAIN(train_id, new_line_id)** - Move train to different line
  - Size: max_trains × max_lines = 10 × 6 = 60 actions
  - **Impact**: +60 actions
  - **Alternative**: Keep auto-placement, skip this action

### Observation Space Changes

**Current Observations:**
- Station features (position, shape, passenger count, etc.)
- Line features (stations on line, color, etc.)
- Train features (position, passengers, etc.)

**New Observations Needed:**

**TIER 1 Changes:**
- Station.overcrowding_timer (float, 0-10 seconds)
- game_state.passenger_spawn_scale (float multiplier)
- **Impact**: +2 floats per observation

**TIER 2 Changes:**
- game_state.current_week (int)
- game_state.available_upgrades (list of 2 upgrade types)
- Station.is_interchange (bool per station)
- Train.total_capacity (int, includes carriages)
- **Impact**: +1 int, +2 upgrade types, +1 bool per station, +1 int per train

### Reward Function Changes

**Current Reward (InfrastructureReward):**
- Line creation: +50
- Train creation: +30
- Isolated station connection: +30
- Infrastructure bonus per step: +1
- Invalid action: -1

**Suggested Changes:**

**TIER 1:**
- **Passenger delivered**: +10 per passenger (encourage actually moving people!)
- **Station overcrowding penalty**: -5 per overcrowded station per step
- **Station cleared from overcrowding**: +20 (encourage fixing problems)

**TIER 2:**
- **Interchange created**: +40 (valuable upgrade)
- **Carriage added**: +10 (increases capacity)
- **Weekly survival bonus**: +100 per week completed

**TIER 3:**
- **Special station connected**: +50 (more valuable)

### Training Impact

**Complexity Increase:**
- Action space: 727 → ~789 (if we add MOVE_TRAIN)
- Observation space: ~10-15% larger
- Episode length: Longer (weeks instead of arbitrary time)
- Strategy depth: Much higher (upgrade choices, timing, capacity management)

**Training Time:**
- Expect 2-3x longer training time
- More complex strategies to learn
- May need curriculum learning (start simple, add features gradually)

---

## Recommended Implementation Phases

### Phase 1: Core Fixes (Week 1)
**Goal**: Make base game match Mini Metro fundamentals
- ✅ Station capacity: 6
- ✅ Train capacity: 6
- ✅ Overcrowding timer
- ✅ Spawn rate scaling
- ✅ Progressive station spawning

**Outcome**: Game feels like Mini Metro, proper difficulty curve

### Phase 2: Upgrade System (Week 2)
**Goal**: Add signature weekly choice mechanic
- ✅ Week-based time
- ✅ Weekly upgrade offerings
- ✅ Interchange stations
- ✅ Functional carriage system

**Outcome**: Strategic depth, player agency

### Phase 3: Station Variety (Week 3)
**Goal**: Add special stations and rules
- ✅ Special station types
- ✅ Triangle routing rules
- ✅ Station-specific spawn rates
- ✅ Circle transformation (optional)

**Outcome**: More variety, closer to original

### Phase 4: Polish (Week 4)
**Goal**: Final touches for completeness
- ✅ Train station skipping
- ✅ Trains-per-line limit
- ✅ Game modes (optional)
- ✅ Tunnels (optional)

**Outcome**: Feature-complete Mini Metro clone

---

## Questions for Clarification

Before I present the final plan, I need to know:

1. **Scope**: Do you want ALL tiers, or focus on specific ones?
   - Just TIER 1 (core fixes)?
   - TIER 1 + TIER 2 (upgrades)?
   - All tiers?

2. **RL Priority**: Is this primarily for:
   - RL training (need to carefully design action/observation spaces)?
   - Manual play (can add complex UI interactions)?
   - Both equally?

3. **Weekly Upgrade Handling for RL**:
   - Should the agent choose upgrades (adds complexity)?
   - Or auto-select upgrades (simpler training)?

4. **Breaking Changes**: Are you OK with:
   - Retraining all RL models from scratch (action space changes)?
   - Changing game difficulty significantly (capacity changes)?

5. **Timeline**: How fast do you want this?
   - All at once (big refactor)?
   - Incremental phases (test between phases)?

Please let me know your preferences and I'll create a detailed, prioritized implementation plan!
