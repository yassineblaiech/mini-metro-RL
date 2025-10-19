# Installation Guide

## Quick Start

### 1. Basic Installation (Play the Game Only)

```bash
# Install core dependencies
pip install -r requirements.txt
```

This installs:
- `pygame` - For graphics and human play
- `numpy` - For numerical operations
- `gymnasium` - For the RL environment (even if not training)

**Test it works:**
```bash
python main.py
# or
python test_env.py
```

### 2. RL Training Installation (Recommended)

```bash
# Install core dependencies
pip install -r requirements.txt

# Install RL training dependencies
pip install -r requirements-rl.txt
```

This additionally installs:
- `stable-baselines3` - Pre-built RL algorithms (PPO, DQN, A2C, etc.)
- `tensorboard` - For training visualization

**Test it works:**
```bash
python test_env.py
python train.py --mode random --episodes 5
```

### 3. Full Installation (All Optional Dependencies)

```bash
# Install everything
pip install -r requirements.txt
pip install -r requirements-rl.txt
pip install matplotlib seaborn pandas
```

## Installation Options

### Option A: Virtual Environment (Recommended)

**Windows (PowerShell):**
```powershell
# Create virtual environment
python -m venv env

# Activate it
.\env\Scripts\Activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-rl.txt  # Optional
```

**Linux/Mac:**
```bash
# Create virtual environment
python -m venv env

# Activate it
source env/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-rl.txt  # Optional
```

### Option B: Conda Environment

```bash
# Create conda environment
conda create -n metro-rl python=3.10

# Activate it
conda activate metro-rl

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-rl.txt  # Optional
```

### Option C: System-wide Installation

```bash
# Not recommended, but if you prefer:
pip install -r requirements.txt
pip install -r requirements-rl.txt  # Optional
```

## Verify Installation

Run the test suite to verify everything works:

```bash
python test_env.py
```

Expected output:
```
===========================================================
MINI METRO RL - ENVIRONMENT TEST SUITE
===========================================================

✓ Environment created successfully
✓ Environment reset successfully
...
===========================================================
ALL TESTS PASSED! ✓
===========================================================
```

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'gymnasium'`

**Solution:**
```bash
pip install gymnasium
```

### Issue: `ModuleNotFoundError: No module named 'stable_baselines3'`

**Solution:**
```bash
pip install -r requirements-rl.txt
# or
pip install stable-baselines3
```

### Issue: Pygame window not appearing

**Solution (Windows):**
- Make sure you have DirectX/graphics drivers installed
- Try running as administrator

**Solution (Linux):**
```bash
# Install SDL dependencies
sudo apt-get install python3-pygame
```

### Issue: Import errors with numpy

**Solution:**
```bash
pip install --upgrade numpy
```

### Issue: PyTorch not found (for Stable-Baselines3)

Stable-Baselines3 requires PyTorch. It should install automatically, but if not:

```bash
# CPU version (faster installation)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# GPU version (if you have CUDA)
# Check https://pytorch.org/get-started/locally/ for your CUDA version
```

## What's Installed?

### Core Dependencies (`requirements.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| pygame | ≥2.0.0 | Graphics and game rendering |
| numpy | ≥1.21.0 | Numerical operations |
| gymnasium | ≥0.29.0 | RL environment interface |

### RL Dependencies (`requirements-rl.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| stable-baselines3 | ≥2.0.0 | Pre-built RL algorithms |
| tensorboard | ≥2.10.0 | Training visualization |

## Next Steps

After installation:

1. **Test the environment:**
   ```bash
   python test_env.py
   ```

2. **Play the game as human:**
   ```bash
   python main.py
   ```

3. **Run random agent baseline:**
   ```bash
   python train.py --mode random --episodes 10
   ```

4. **Train a PPO agent:**
   ```bash
   python train.py --mode ppo --timesteps 50000
   ```

5. **Watch your trained agent:**
   ```bash
   python play.py --mode watch --agent trained --model-path models/PPO_final.zip
   ```

## Minimal Installation (Just to Test)

If you just want to quickly test if the environment works without installing RL libraries:

```bash
pip install pygame numpy gymnasium
python test_env.py
```

This will run the tests with just the random agent (no Stable-Baselines3 needed).
