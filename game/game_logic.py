"""
Pure game logic functions - no rendering, no pygame dependencies.
Contains helper functions for pathfinding, spawning, train AI, etc.
"""
import math
import random
import heapq
from typing import Dict, List, Tuple, Optional, Set
from .entities import Station, Passenger, Line, Train, Obstacle, Trail

SHAPES = ['circle', 'square', 'triangle', 'pentagon']

# Parallel line rendering constants
PARALLEL_LINE_OFFSET = 8  # Pixels to offset parallel lines from center


def calculate_orthogonal_path(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> List[Tuple[int, int]]:
    """
    Calculate an orthogonal/diagonal path between two points (Mini Metro style).
    Lines can only go:
    - Horizontally (dx, 0)
    - Vertically (0, dy)
    - Diagonally at 45° (dx, dx)

    Returns a list of waypoints including start and end positions.
    Uses a simple heuristic: prefer diagonal movement first, then orthogonal.
    """
    x1, y1 = pos1
    x2, y2 = pos2

    waypoints = [pos1]

    dx = x2 - x1
    dy = y2 - y1

    # If already aligned (horizontal, vertical, or diagonal), direct path
    if dx == 0 or dy == 0 or abs(dx) == abs(dy):
        waypoints.append(pos2)
        return waypoints

    # Strategy: Go diagonal as far as possible, then orthogonal
    # Move diagonally first (covers both x and y distance)
    diagonal_distance = min(abs(dx), abs(dy))
    sign_x = 1 if dx > 0 else -1
    sign_y = 1 if dy > 0 else -1

    # Move diagonally
    diag_x = x1 + sign_x * diagonal_distance
    diag_y = y1 + sign_y * diagonal_distance
    waypoints.append((diag_x, diag_y))

    # Then move orthogonally (either horizontal or vertical, whichever is needed)
    if diag_x != x2:
        # Need to move horizontally
        waypoints.append((x2, diag_y))
    elif diag_y != y2:
        # Need to move vertically
        waypoints.append((diag_x, y2))

    # Final position (should already be covered, but ensure it's there)
    if waypoints[-1] != pos2:
        waypoints.append(pos2)

    return waypoints


def calculate_orthogonal_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
    """
    Calculate the actual distance traveled along an orthogonal/diagonal path.
    This replaces Euclidean distance for gameplay purposes.
    """
    waypoints = calculate_orthogonal_path(pos1, pos2)
    total_distance = 0.0

    for i in range(len(waypoints) - 1):
        x1, y1 = waypoints[i]
        x2, y2 = waypoints[i + 1]
        total_distance += math.hypot(x2 - x1, y2 - y1)

    return total_distance


def calculate_perpendicular_offset(p1: Tuple[float, float], p2: Tuple[float, float],
                                   offset_distance: float) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """
    Calculate two points offset perpendicular to a line segment.
    Returns the offset points for p1 and p2.

    Args:
        p1: Start point (x, y)
        p2: End point (x, y)
        offset_distance: Distance to offset perpendicular to the line

    Returns:
        Tuple of (offset_p1, offset_p2)
    """
    x1, y1 = p1
    x2, y2 = p2

    # Calculate direction vector
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)

    if length == 0:
        return (p1, p2)

    # Normalize
    dx /= length
    dy /= length

    # Perpendicular vector (rotate 90 degrees)
    perp_x = -dy
    perp_y = dx

    # Offset points
    offset_p1 = (x1 + perp_x * offset_distance, y1 + perp_y * offset_distance)
    offset_p2 = (x2 + perp_x * offset_distance, y2 + perp_y * offset_distance)

    return (offset_p1, offset_p2)


def offset_waypoints(waypoints: List[Tuple[int, int]], offset_distance: float) -> List[Tuple[float, float]]:
    """
    Offset an entire path of waypoints perpendicular to its direction.
    This creates a parallel path for rendering multiple lines on the same segment.

    Args:
        waypoints: List of (x, y) positions
        offset_distance: Distance to offset (positive = right, negative = left)

    Returns:
        List of offset waypoints
    """
    if len(waypoints) < 2:
        return waypoints

    offset_points = []

    for i in range(len(waypoints) - 1):
        p1 = waypoints[i]
        p2 = waypoints[i + 1]

        offset_p1, offset_p2 = calculate_perpendicular_offset(p1, p2, offset_distance)

        if i == 0:
            offset_points.append(offset_p1)

        # For corners, we need to handle the intersection of offset segments
        if i < len(waypoints) - 2:
            # Get next segment's offset
            p3 = waypoints[i + 2]
            next_offset_p2, next_offset_p3 = calculate_perpendicular_offset(p2, p3, offset_distance)

            # Use the average of the two offset positions at corners for smoother rendering
            corner_x = (offset_p2[0] + next_offset_p2[0]) / 2
            corner_y = (offset_p2[1] + next_offset_p2[1]) / 2
            offset_points.append((corner_x, corner_y))
        else:
            # Last segment
            offset_points.append(offset_p2)

    return offset_points


def find_shared_segments(lines: Dict[int, 'Line']) -> Dict[Tuple[int, int], List[int]]:
    """
    Find all trail segments that are shared between multiple lines.

    Args:
        lines: Dictionary of line_id -> Line objects

    Returns:
        Dictionary mapping (station_a, station_b) -> [list of line_ids using this segment]
        The station IDs are ordered (min, max) for consistent lookup.
    """
    segment_to_lines: Dict[Tuple[int, int], List[int]] = {}

    for line_id, line in lines.items():
        for trail in line.trails:
            # Create normalized key (smaller station id first)
            segment_key = tuple(sorted([trail.station_a, trail.station_b]))

            if segment_key not in segment_to_lines:
                segment_to_lines[segment_key] = []
            segment_to_lines[segment_key].append(line_id)

    # Only return segments shared by 2+ lines
    return {seg: line_ids for seg, line_ids in segment_to_lines.items() if len(line_ids) > 1}


def calculate_line_offset_for_segment(line_id: int, segment_key: Tuple[int, int],
                                      shared_segments: Dict[Tuple[int, int], List[int]]) -> float:
    """
    Calculate the perpendicular offset for a specific line on a shared segment.

    Args:
        line_id: The line we're calculating offset for
        segment_key: The (station_a, station_b) segment (normalized)
        shared_segments: Dictionary of shared segments

    Returns:
        Offset distance in pixels (0 if not shared, positive/negative for parallel lines)
    """
    if segment_key not in shared_segments:
        return 0.0  # Not a shared segment

    line_ids = shared_segments[segment_key]
    if len(line_ids) == 1:
        return 0.0  # Only one line, no offset needed

    # Find this line's index in the list
    try:
        line_index = line_ids.index(line_id)
    except ValueError:
        return 0.0

    # Calculate offset based on number of lines and this line's position
    num_lines = len(line_ids)

    if num_lines == 2:
        # Two lines: offset by ±PARALLEL_LINE_OFFSET
        return PARALLEL_LINE_OFFSET if line_index == 0 else -PARALLEL_LINE_OFFSET
    elif num_lines == 3:
        # Three lines: -offset, 0, +offset
        return (line_index - 1) * PARALLEL_LINE_OFFSET
    else:
        # More lines: spread them out
        # Calculate spacing so all lines fit
        spacing = PARALLEL_LINE_OFFSET
        center_offset = (num_lines - 1) * spacing / 2
        return line_index * spacing - center_offset


def generate_initial_stations(
    num_stations: int,
    map_width: int,
    map_height: int,
    margin: int = 60,
    min_distance: int = 50,
    sidebar_width: int = 120,
    seed: Optional[int] = None
) -> Dict[int, Station]:
    """Generate initial stations with random positions that don't overlap."""
    if seed is not None:
        random.seed(seed)

    stations = {}
    station_id = 1
    attempts = 0
    max_attempts = 1000

    while len(stations) < num_stations and attempts < max_attempts:
        attempts += 1
        x = random.randint(margin, map_width - sidebar_width - margin)
        y = random.randint(margin, map_height - margin)

        # Check distance to other stations
        too_close = False
        for existing_station in stations.values():
            dist = math.hypot(x - existing_station.pos[0], y - existing_station.pos[1])
            if dist < min_distance:
                too_close = True
                break

        if not too_close:
            station = Station(
                id=station_id,
                pos=(x, y),
                shape=random.choice(SHAPES)
            )
            stations[station_id] = station
            station_id += 1

    return stations


def generate_obstacles(
    num_obstacles: int,
    map_width: int,
    map_height: int,
    stations: Dict[int, Station],
    sidebar_width: int = 120,
    seed: Optional[int] = None
) -> Dict[int, Obstacle]:
    """Generate convex polygon obstacles (rivers/lakes) that don't contain stations."""
    if seed is not None:
        random.seed(seed)

    obstacles = {}
    obstacle_id = 1
    map_area = map_width * map_height
    attempts = 0
    max_attempts = 200

    while len(obstacles) < num_obstacles and attempts < max_attempts:
        attempts += 1

        # Random convex polygon: pick center and radius, create regular-ish polygon with jitter
        cx = random.randint(80, map_width - sidebar_width - 80)
        cy = random.randint(80, map_height - 80)
        sides = random.randint(3, 6)
        max_radius = int(min(map_width, map_height) * 0.12)
        radius = random.randint(30, max_radius)

        pts = []
        for i in range(sides):
            ang = 2 * math.pi * i / sides + random.uniform(-0.3, 0.3)
            r = radius * random.uniform(0.7, 1.0)
            px = int(cx + r * math.cos(ang))
            py = int(cy + r * math.sin(ang))
            pts.append((px, py))

        obstacle = Obstacle(id=obstacle_id, points=pts)

        # Size check and convexity check
        if obstacle.area() > 0 and obstacle.area() < 0.10 * map_area and obstacle.is_convex():
            # Ensure no station inside
            contains_station = any(obstacle.contains_point(s.pos) for s in stations.values())
            if not contains_station:
                obstacles[obstacle_id] = obstacle
                obstacle_id += 1

    return obstacles


def spawn_passenger(
    stations: Dict[int, Station],
    seed: Optional[int] = None
) -> Optional[Station]:
    """
    Spawn a passenger at a random station with a random destination shape.
    Returns the origin station if successful, None otherwise.
    """
    if not stations:
        return None

    if seed is not None:
        random.seed(seed)

    origin_station = random.choice(list(stations.values()))

    # Find all possible destination shapes (not the origin's shape)
    possible_dest_shapes = [sh for sh in SHAPES if sh != origin_station.shape]
    if not possible_dest_shapes:
        return None

    dest_shape = random.choice(possible_dest_shapes)

    # Find all stations on the map that match the destination shape
    valid_destinations = [s for s in stations.values() if s.shape == dest_shape]

    if not valid_destinations:
        return None

    # Find the closest valid destination station by Euclidean distance
    closest_dest_station = min(
        valid_destinations,
        key=lambda s: math.hypot(
            s.pos[0] - origin_station.pos[0],
            s.pos[1] - origin_station.pos[1]
        )
    )

    passenger = Passenger(
        origin_id=origin_station.id,
        dest_shape=dest_shape,
        destination_id=closest_dest_station.id,
        next_hop_id=closest_dest_station.id
    )
    origin_station.add_passenger(passenger)

    return origin_station


def find_shortest_path_distance(
    start_id: int,
    end_id: int,
    stations: Dict[int, Station],
    station_lines: Dict[int, List[int]],
    lines: Dict[int, Line]
) -> float:
    """
    Calculate the shortest travel distance (in pixels) between two stations using Dijkstra's algorithm.
    Uses orthogonal/diagonal distance (Mini Metro style) instead of Euclidean distance.
    Returns float('inf') if no path exists.
    """
    if start_id == end_id:
        return 0.0

    distances = {station_id: float('inf') for station_id in stations}
    distances[start_id] = 0.0

    pq = [(0.0, start_id)]  # (distance, station_id)

    while pq:
        current_dist, current_id = heapq.heappop(pq)

        if current_dist > distances[current_id]:
            continue

        if current_id == end_id:
            return current_dist

        # Find all neighbors of the current station across all lines it's on
        for line_id in station_lines.get(current_id, []):
            line = lines[line_id]
            for neighbor_id in line.get_neighbors(current_id):
                # Calculate the orthogonal/diagonal distance of this trail
                edge_dist = calculate_orthogonal_distance(
                    stations[current_id].pos,
                    stations[neighbor_id].pos
                )

                if distances[current_id] + edge_dist < distances[neighbor_id]:
                    distances[neighbor_id] = distances[current_id] + edge_dist
                    heapq.heappush(pq, (distances[neighbor_id], neighbor_id))

    return float('inf')  # No path found


def update_exchange_caches(
    lines: Dict[int, Line],
    stations: Dict[int, Station]
) -> Tuple[Dict[int, Set[str]], Dict[int, List[int]], Set[int]]:
    """
    Recalculate caches for line shapes and exchange stations.

    Returns:
        - line_station_shapes: Dict[line_id, Set[shape_types]]
        - station_lines: Dict[station_id, List[line_ids]]
        - exchange_stations: Set[station_ids] (stations on more than one line)
    """
    line_station_shapes: Dict[int, Set[str]] = {}
    station_lines: Dict[int, List[int]] = {}

    for line_id, line in lines.items():
        line_stations = line.get_stations()
        # Cache shapes per line
        line_station_shapes[line_id] = {stations[sid].shape for sid in line_stations}
        # Cache lines per station
        for station_id in line_stations:
            if station_id not in station_lines:
                station_lines[station_id] = []
            station_lines[station_id].append(line_id)

    # Identify exchange stations (stations on more than one line)
    exchange_stations = {sid for sid, lines_list in station_lines.items() if len(lines_list) > 1}

    return line_station_shapes, station_lines, exchange_stations


def update_passenger_routes_at_station(
    station: Station,
    stations: Dict[int, Station],
    lines: Dict[int, Line],
    station_lines: Dict[int, List[int]],
    line_station_shapes: Dict[int, Set[str]],
    exchange_stations: Set[int]
):
    """
    For each passenger at a station, determine their best next hop.
    This updates the passenger objects in-place.
    """
    for passenger in station.waiting:
        passenger.picked = False  # Reset picked status when re-evaluating route

        # Recalculate the ULTIMATE destination, prioritizing same-line travel
        valid_destinations = [s for s in stations.values() if s.shape == passenger.dest_shape]
        if not valid_destinations:
            passenger.destination_id = None
            passenger.next_hop_id = None
            continue

        station_line_ids = station_lines.get(station.id, [])

        # Separate destinations into same-line and other-line
        same_line_dests = []
        other_dests = []
        for dest in valid_destinations:
            if any(dest.id in lines[lid].get_stations() for lid in station_line_ids):
                same_line_dests.append(dest)
            else:
                other_dests.append(dest)

        # Prioritize destinations on the same line
        target_list = same_line_dests if same_line_dests else other_dests

        best_destination = None
        min_travel_dist = float('inf')

        for dest_station in target_list:
            # Use Dijkstra to find the actual travel distance from the passenger's origin
            dist = find_shortest_path_distance(
                passenger.origin_id,
                dest_station.id,
                stations,
                station_lines,
                lines
            )
            if dist < min_travel_dist:
                min_travel_dist = dist
                best_destination = dest_station

        passenger.destination_id = best_destination.id if best_destination else None

        # Now, calculate the NEXT HOP based on the new ultimate destination
        if passenger.destination_id is None:
            passenger.next_hop_id = None  # No path to any valid destination
            continue

        station_line_ids = station_lines.get(station.id, [])
        # Check if destination is on any of the lines serving the current station
        can_reach_directly = any(
            passenger.dest_shape in line_station_shapes.get(lid, set())
            for lid in station_line_ids
        )
        if can_reach_directly:
            passenger.next_hop_id = passenger.destination_id
            continue

        # Find a valid exchange station to get to the destination
        best_exchange_id = None
        for exchange_id in exchange_stations:
            if any(exchange_id in lines[lid].get_stations() for lid in station_line_ids) and \
               any(passenger.dest_shape in line_station_shapes.get(other_lid, set())
                   for other_lid in station_lines.get(exchange_id, [])):
                best_exchange_id = exchange_id
                break  # Simple approach: take the first valid one found
        passenger.next_hop_id = best_exchange_id


def choose_next_station(
    train: Train,
    line: Line,
    last_station_id: int,
    seed: Optional[int] = None
) -> Optional[int]:
    """
    AI logic for a train to decide where to go next.
    Returns the next station ID or None if nowhere to go.
    """
    if seed is not None:
        random.seed(seed)

    current_station_id = train.current_station_id
    neighbors = line.get_neighbors(current_station_id)

    if not neighbors:
        return None  # End of the line, nowhere to go

    # If it's a simple path (not a junction), just continue or turn around
    if len(neighbors) == 1:
        return neighbors[0]  # Only one way to go

    # At a junction - exclude the path we just came from, unless we have to turn around
    potential_paths = [n for n in neighbors if n != last_station_id]
    if not potential_paths:
        return last_station_id  # Must turn around

    # If there are passengers, try to find a path that serves them
    if train.passengers:
        passenger_dests = {p.next_hop_id for p in train.passengers}

        for path_station_id in potential_paths:
            # Simple check: does this immediate neighbor match a destination?
            if path_station_id in passenger_dests:
                return path_station_id  # Greedily go to the matching station

        # No immediate match, pick randomly
        return random.choice(potential_paths)

    # No passengers, just explore. Avoid turning back if possible.
    return random.choice(potential_paths)
