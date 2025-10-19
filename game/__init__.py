"""
Mini Metro Game Package.

Components:
- entities: Core game entities (Station, Line, Train, etc.)
- game_state: Headless game state for RL training
- game_logic: Pure game logic functions
- game: Original pygame-based game with UI
- rendering: Rendering functions for visualization
"""
from .entities import Station, Passenger, Line, Train, Obstacle, Trail, ShapeType
from .game_state import GameState, GameConfig
from .game import Game
from .rendering import Renderer

__all__ = [
    'Station', 'Passenger', 'Line', 'Train', 'Obstacle', 'Trail', 'ShapeType',
    'GameState', 'GameConfig',
    'Game',
    'Renderer'
]
