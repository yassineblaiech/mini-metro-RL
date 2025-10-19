"""
Placeholder for your RL agent implementation.

You can use popular RL libraries like:
- Stable-Baselines3 (PPO, DQN, A2C, etc.)
- RLlib (Ray)
- Custom implementations

Example with Stable-Baselines3:
```python
from stable_baselines3 import PPO, DQN
from env.metro_env import MetroEnv

# Create environment
env = MetroEnv(flatten_obs=True)

# Create agent
model = PPO('MlpPolicy', env, verbose=1)

# Train
model.learn(total_timesteps=100000)

# Save
model.save('metro_ppo_model')

# Load and use
model = PPO.load('metro_ppo_model')
obs, info = env.reset()
for _ in range(1000):
    action, _states = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()
```

For now, this file is a placeholder. Implement your agent here!
"""


class RLAgent:
    """
    Placeholder for your custom RL agent.

    You can either:
    1. Use this as a wrapper around Stable-Baselines3 models
    2. Implement your own RL algorithm here
    3. Use RLlib or other frameworks
    """

    def __init__(self, observation_space, action_space):
        """
        Initialize your RL agent.

        Args:
            observation_space: Gym observation space
            action_space: Gym action space
        """
        self.observation_space = observation_space
        self.action_space = action_space

        # TODO: Initialize your model/network here
        # Example:
        # self.model = PPO('MlpPolicy', env, verbose=1)

    def predict(self, observation, deterministic=False):
        """
        Predict an action given an observation.

        Args:
            observation: Current state observation
            deterministic: Whether to act deterministically

        Returns:
            action: Predicted action
            state: Internal agent state (if any)
        """
        # TODO: Implement your prediction logic
        # For now, return a random action
        return self.action_space.sample(), None

    def learn(self, total_timesteps: int):
        """
        Train the agent.

        Args:
            total_timesteps: Number of timesteps to train
        """
        # TODO: Implement your training loop
        pass

    def save(self, path: str):
        """Save the agent's parameters."""
        # TODO: Implement saving
        pass

    def load(self, path: str):
        """Load the agent's parameters."""
        # TODO: Implement loading
        pass
