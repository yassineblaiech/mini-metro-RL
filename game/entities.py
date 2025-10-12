import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple

ShapeType = str

@dataclass
class Passenger:
    origin_id: int
    dest_shape: ShapeType
    picked: bool = False

@dataclass
class Station:
    id: int
    pos: Tuple[int, int]
    shape: ShapeType
    waiting: List[Passenger] = field(default_factory=list)
    upgraded: bool = False

    def add_passenger(self, p: Passenger):
        self.waiting.append(p)

    def remove_passengers_for_shape(self, shape: ShapeType, count: int):
        taken = []
        remaining = []
        for p in self.waiting:
            if p.dest_shape == shape and len(taken) < count and not p.picked:
                p.picked = True
                taken.append(p)
            else:
                remaining.append(p)
        self.waiting = remaining
        return taken

@dataclass
class Trail:
    """A connection (segment) between two stations."""
    station_a: int
    station_b: int

@dataclass
class Line:
    id: int
    color: Tuple[int, int, int]
    trails: List[Trail] = field(default_factory=list)
    has_bridge: bool = False
    # The main traversable path for trains. Can be recalculated.
    _station_sequence: List[int] = field(default_factory=list, init=False)

    def get_stations(self) -> set[int]:
        """Returns a set of all unique station IDs on this line."""
        stations = set()
        if not self.trails and self._station_sequence: # single station line
            return set(self._station_sequence)
        for trail in self.trails:
            stations.add(trail.station_a)
            stations.add(trail.station_b)
        return stations

    def station_sequence(self) -> List[int]:
        """Returns the cached station sequence for train traversal."""
        return self._station_sequence

    def can_add_trail(self, new_trail: Trail) -> bool:
        """Checks if a new trail can be added to the line."""
        if not self.trails and not self._station_sequence:
            return True # First trail on a new line
        
        existing_stations = self.get_stations()
        is_connected = new_trail.station_a in existing_stations or new_trail.station_b in existing_stations
        is_duplicate = any(
            (t.station_a == new_trail.station_a and t.station_b == new_trail.station_b) or
            (t.station_a == new_trail.station_b and t.station_b == new_trail.station_a)
            for t in self.trails
        )

        if not (is_connected and not is_duplicate):
            return False

        # Check if the line is already a closed loop. If so, no more trails can be added.
        adj = {s: [] for s in self.get_stations()}
        for t in self.trails:
            adj[t.station_a].append(t.station_b)
            adj[t.station_b].append(t.station_a)
        
        # A line is a loop if it has stations and none of them are endpoints (degree 1).
        is_loop = self.trails and all(len(neighbors) != 1 for neighbors in adj.values())
        if is_loop:
            return False

        # Prevent creating a trail from an endpoint to a station in the middle of the sequence.
        # This avoids creating small, inefficient loops.
        sequence = self.station_sequence()
        if len(sequence) > 1:
            start_node, end_node = sequence[0], sequence[-1]
            s_a, s_b = new_trail.station_a, new_trail.station_b

            # Check if connecting from an endpoint (start_node) to a station already in the line
            if (s_a == start_node and s_b in sequence and s_b != end_node) or \
               (s_b == start_node and s_a in sequence and s_a != end_node) or \
               (s_a == end_node and s_b in sequence and s_b != start_node) or \
               (s_b == end_node and s_a in sequence and s_a != start_node):
                return False

        return True

    def add_trail(self, trail: Trail):
        """Adds a trail and recalculates the main station sequence."""
        if not self.can_add_trail(trail):
            return

        self.trails.append(trail)
        self.recalculate_sequence()

    def remove_trail(self, station_a_id: int, station_b_id: int):
        """Removes a trail between two stations and recalculates the sequence."""
        trail_to_remove = None
        for t in self.trails:
            if (t.station_a == station_a_id and t.station_b == station_b_id) or \
               (t.station_a == station_b_id and t.station_b == station_a_id):
                trail_to_remove = t
                break

        if trail_to_remove:
            self.trails.remove(trail_to_remove)
            # After removing a trail, the line might be split. We recalculate the main path.
            self.recalculate_sequence()

    def recalculate_sequence(self):
        """
        Builds an ordered sequence of stations from the trails.
        This finds the longest path between two endpoints in the trail graph.
        """
        if not self.trails:
            return

        adj = {s: [] for s in self.get_stations()}
        for t in self.trails:
            adj[t.station_a].append(t.station_b)
            adj[t.station_b].append(t.station_a)

        endpoints = [node for node, neighbors in adj.items() if len(neighbors) == 1]
        if not endpoints: # It's a cycle or single station
            self._station_sequence = list(adj.keys())
            return

        # Basic longest path: traverse from an endpoint. A more complex algorithm (like BFS from all endpoints)
        # could find the true longest path, but this is sufficient for typical gameplay.
        start_node = endpoints[0]
        path = [start_node]
        visited = {start_node}
        
        # Simple DFS to find a path to another endpoint
        q = [(start_node, [start_node])]
        longest_path = [start_node]

        while q:
            curr, p = q.pop(0)
            is_dead_end = True
            for neighbor in adj[curr]:
                if neighbor not in p:
                    is_dead_end = False
                    new_path = p + [neighbor]
                    q.append((neighbor, new_path))
            if is_dead_end and len(p) > len(longest_path):
                longest_path = p
        
        self._station_sequence = longest_path

    def get_neighbors(self, station_id: int) -> List[int]:
        """Gets all stations directly connected to the given station_id on this line."""
        neighbors = []
        for trail in self.trails:
            if trail.station_a == station_id: neighbors.append(trail.station_b)
            elif trail.station_b == station_id: neighbors.append(trail.station_a)
        return neighbors

@dataclass
class Train:
    id: int
    line_id: int
    position_index: int = 0  # index into line stations list
    progress: float = 0.0  # 0..1 between stations
    speed: float = 50.0  # pixels per second
    capacity: int = 4
    passengers: List[Passenger] = field(default_factory=list)
    direction: int = 1  # 1 forward, -1 backward
    carriages: int = 0
    current_station_id: int | None = None
    target_station_id: int | None = None
    def effective_capacity(self):
        return self.capacity + self.carriages * 3

    def available_capacity(self):
        return max(0, self.effective_capacity() - len(self.passengers))

    def load_passengers(self, station: Station):
        # load passengers whose destination shape exists on the line (handled by caller)
        cap = self.available_capacity()
        if cap <= 0:
            return 0
        # take any passengers up to cap
        to_take = []
        remaining = []
        for p in station.waiting:
            if len(to_take) < cap and not p.picked:
                p.picked = True
                to_take.append(p)
            else:
                remaining.append(p)
        station.waiting = remaining
        self.passengers.extend(to_take)
        return len(to_take)

    def initial_load(self, station: Station, line: Line):
        """
        Special loading logic for when a train is first placed.
        It only picks up passengers whose destination is on the line.
        """
        cap = self.available_capacity()
        if cap <= 0:
            return 0
        
        line_stations = line.get_stations()
        to_take = []
        # In a more complex system, we'd check if a path exists. Here, we just check if the shape is on the line.
        line_shapes = {s.shape for sid, s in station.parent_stations.items() if sid in line_stations}

        station.remove_passengers_if(lambda p: p.dest_shape in line_shapes and len(to_take) < cap, to_take)
        self.passengers.extend(to_take)
        return len(to_take)

    def drop_off(self, station: Station):
        dropped = [p for p in self.passengers if p.dest_shape == station.shape]
        self.passengers = [p for p in self.passengers if p.dest_shape != station.shape]
        return len(dropped)


@dataclass
class Obstacle:
    """A convex polygon obstacle (e.g. a river or lake) that stations/lines cannot be placed inside.

    Stores a list of points (x,y) in order. Provides area and point-in-polygon utilities.
    """
    id: int
    points: List[Tuple[int, int]]

    def area(self) -> float:
        # polygon area via shoelace formula
        a = 0.0
        pts = self.points
        n = len(pts)
        for i in range(n):
            x1,y1 = pts[i]
            x2,y2 = pts[(i+1)%n]
            a += x1*y2 - x2*y1
        return abs(a) / 2.0

    def contains_point(self, pt: Tuple[int,int]) -> bool:
        # ray-casting algorithm for point in polygon
        x,y = pt
        inside = False
        pts = self.points
        n = len(pts)
        j = n - 1
        for i in range(n):
            xi, yi = pts[i]
            xj, yj = pts[j]
            intersect = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi)
            if intersect:
                inside = not inside
            j = i
        return inside

    def is_convex(self) -> bool:
        # simple convexity check (all cross products have same sign)
        pts = self.points
        n = len(pts)
        if n < 3:
            return False
        sign = 0
        for i in range(n):
            x1,y1 = pts[i]
            x2,y2 = pts[(i+1)%n]
            x3,y3 = pts[(i+2)%n]
            dx1 = x2-x1; dy1 = y2-y1
            dx2 = x3-x2; dy2 = y3-y2
            z = dx1*dy2 - dy1*dx2
            if z != 0:
                if sign == 0:
                    sign = 1 if z > 0 else -1
                else:
                    if (z > 0 and sign < 0) or (z < 0 and sign > 0):
                        return False
        return True
