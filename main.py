"""
Main entry point for Mini Metro game (backward compatibility).

This file maintains backward compatibility with the original implementation.
For new features, see:
- train.py: RL training (headless, fast)
- play.py: Play as human or watch agents
"""
from game.game import Game

if __name__ == '__main__':
    print("=" * 60)
    print("Mini Metro - Python Prototype")
    print("=" * 60)
    print("Controls:")
    print("  - Click stations to draw/remove lines")
    print("  - Use sidebar tools")
    print("  - SPACE: Pause/Unpause")
    print("=" * 60)
    print("\nFor RL training, use: python train.py")
    print("For watching agents, use: python play.py --mode watch")
    print("=" * 60 + "\n")

    g = Game(window_size=(960, 640))
    g.run()
