"""
Random agent baseline for Mini Metro.

This agent randomly selects actions and serves as a baseline for comparison.
"""
import numpy as np
from typing import Any


class RandomAgent:
    """
    Random agent that selects actions uniformly at random.

    Useful for:
    - Baseline performance comparison
    - Testing the environment
    - Generating random exploration data
    """

    def __init__(self, action_space):
        """
        Initialize the random agent.

        Args:
            action_space: Gym action space
        """
        self.action_space = action_space

    def predict(self, observation: Any, deterministic: bool = False) -> tuple[int, None]:
        """
        Select a random action.

        Args:
            observation: Current observation (ignored)
            deterministic: Whether to act deterministically (ignored for random agent)

        Returns:
            action: Random action
            state: Agent state (None for stateless agents)
        """
        action = self.action_space.sample()
        return action, None

    def learn(self, *args, **kwargs):
        """Random agent doesn't learn."""
        pass

    def save(self, path: str):
        """Random agent has no parameters to save."""
        pass

    def load(self, path: str):
        """Random agent has no parameters to load."""
        pass
