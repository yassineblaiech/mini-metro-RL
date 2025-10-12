Mini Metro — Python (Pygame) mini-clone

Overview

A simplified Mini Metro-like game implemented in Python using Pygame. It implements stations with shapes, passengers that spawn and wait, lines that connect stations, and trains that move along lines picking up/dropping off passengers. This is a small, extendable prototype — not a full commercial clone.

Requirements

- Python 3.8+
- Pygame

Install

# From PowerShell (Windows)
python -m pip install -r requirements.txt

Run

# From PowerShell
python main.py

Controls

- Left-click a station to start drawing a line, left-click another station to add it to the current line.
- Right-click to finish/cancel the current line.
- Press T to add a locomotive to the selected line (select by clicking any station on that line).
- Press C to add a carriage to the last-created train.
- Press Space to pause/unpause.

Notes

This is a compact prototype to explore the simulation and visuals. Feel free to extend: add upgrade UI, more station shapes, improved routing and pathfinding, better balancing and audio.
