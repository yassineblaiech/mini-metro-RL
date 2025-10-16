import pygame
import random
import time
import math
import heapq
from typing import Dict, List, Tuple
from .entities import Station, Passenger, Line, Train
from .entities import Obstacle, Trail, ShapeType
from .rendering import Renderer

SHAPES = ['circle', 'square', 'triangle', 'pentagon']
LINE_COLORS = [(220,20,60),(30,144,255),(34,139,34),(255,165,0),(148,0,211),(0,191,255)]
# (Crimson), (Dodger Blue), (Forest Green), (Orange), (Dark Violet), (Deep Sky Blue)


class Game:
    def __init__(self, window_size=(960,640)):
        pygame.init()
        self.screen = pygame.display.set_mode(window_size)
        pygame.display.set_caption('Mini Metro — Python prototype')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 16)
        self.running = True
        self.game_over = False
        self.paused = False

        self.stations: Dict[int, Station] = {}
        self.lines: Dict[int, Line] = {}
        self.trains: Dict[int, Train] = {}
        self.obstacles: Dict[int, Obstacle] = {}

        self.next_station_id = 1
        self.next_line_id = 1
        self.next_train_id = 1

        self.score = 0
        self.time_elapsed = 0.0
        self.last_spawn = 0.0

        self.first_station_for_trail = None # stores ID of the first station clicked for creating a trail
        self.current_line_drawing = None  # line id being drawn
        self.selected_line = None
        # UI/tool state
        self.tools = ['line', 'remove', 'locomotive', 'carriage', 'interchange']
        self.selected_tool = 'line'
        self.available_colors = LINE_COLORS
        self.selected_color = self.available_colors[0]
        self.sidebar_width = 120
        self.temp_mouse_pos = None
        # editing existing line state
        self.current_edit_line_id = None
        self.current_edit_anchor = None  # 'start' or 'end'
        # drag and drop state
        self.dragging_tool = None
        self.pending_train_placement = None # stores {'line_id': int, 'trail': Trail}
        self.debug_selected_passenger: Passenger | None = None

        # Caches for performance
        self.line_station_shapes: Dict[int, set] = {}
        self.station_lines: Dict[int, List[int]] = {}
        self.exchange_stations: set[int] = set()

        self.init_map()
        self.renderer = Renderer(self.screen, self.font)

    def init_map(self):
        # create some initial stations placed randomly but not overlapping too much
        w,h = self.screen.get_size()
        margin = 60
        min_station_dist = 50 # Minimum distance between stations
        attempts = 0
        while len(self.stations) < 8 and attempts < 1000: # Limit attempts to avoid infinite loop
            attempts += 1
            x = random.randint(margin, w - self.sidebar_width - margin)
            y = random.randint(margin, h-margin)
            
            # Check distance to other stations
            too_close = False
            for s_existing in self.stations.values():
                dist = math.hypot(x - s_existing.pos[0], y - s_existing.pos[1])
                if dist < min_station_dist:
                    too_close = True
                    break
            
            if not too_close:
                s = Station(id=self.next_station_id, pos=(x,y), shape=random.choice(SHAPES))
                self.stations[self.next_station_id] = s
                self.next_station_id += 1
        # generate a few convex obstacles (rivers/lakes) smaller than 10% of map area and not containing stations
        w,h = self.screen.get_size()
        map_area = w * h
        obs_id = 1
        attempts = 0
        while len(self.obstacles) < 2 and attempts < 200:
            attempts += 1
            # random convex polygon: pick center and radius, create regular-ish polygon with jitter
            cx = random.randint(80, w - self.sidebar_width - 80)
            cy = random.randint(80, h-80)
            sides = random.randint(3,6)
            max_radius = int(min(w,h) * 0.12)
            radius = random.randint(30, max_radius)
            pts = []
            for i in range(sides):
                ang = 2*math.pi*i/sides + random.uniform(-0.3,0.3)
                r = radius * random.uniform(0.7,1.0)
                px = int(cx + r * math.cos(ang))
                py = int(cy + r * math.sin(ang))
                pts.append((px,py))
            ob = Obstacle(id=obs_id, points=pts)
            # size check
            if ob.area() > 0 and ob.area() < 0.10 * map_area and ob.is_convex():
                # ensure no station inside
                contains_station = any(ob.contains_point(s.pos) for s in self.stations.values())
                if not contains_station:
                    self.obstacles[obs_id] = ob
                    obs_id += 1
        # note: obstacles created; lines that cross obstacles will need a bridge to cross

    def spawn_passenger(self):
        # spawn at random station with random dest shape (not same as origin shape)
        origin_station = random.choice(list(self.stations.values()))
        
        # Find all possible destination shapes (not the origin's shape)
        possible_dest_shapes = [sh for sh in SHAPES if sh != origin_station.shape]
        if not possible_dest_shapes: return # Should not happen with >1 shape
        
        dest_shape = random.choice(possible_dest_shapes)

        # Find all stations on the map that match the destination shape
        valid_destinations = [
            s for s in self.stations.values() if s.shape == dest_shape
        ]

        if not valid_destinations:
            # This can happen if no station of the chosen shape exists on the map yet.
            return

        # Find the closest valid destination station by Euclidean distance.
        # The pathfinding logic will handle whether the passenger can actually be picked up.
        closest_dest_station = min(valid_destinations,
            key=lambda s: math.hypot(s.pos[0] - origin_station.pos[0], s.pos[1] - origin_station.pos[1]))
        p = Passenger(origin_id=origin_station.id, dest_shape=dest_shape, destination_id=closest_dest_station.id, next_hop_id=closest_dest_station.id)
        origin_station.add_passenger(p)

        # After spawning, we need to recalculate this passenger's route
        self.update_passenger_routes_at_station(origin_station)

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                # unified mouse down handling for sidebar and map
                if ev.button == 1:
                    mx,my = ev.pos
                    # sidebar click
                    if mx >= self.screen.get_width() - self.sidebar_width:
                        # first color palette area
                        y = 30
                        for idx,c in enumerate(self.available_colors[:6]):
                            cx = self.screen.get_width() - self.sidebar_width + 20 + (idx%2)*28
                            cy = y + (idx//2)*28
                            if (mx-cx)**2 + (my-cy)**2 <= 12*12:
                                self.selected_color = c
                                self.selected_tool = 'line'
                                break
                        else:
                            # tools area
                            tools_y = 140
                            for i,t in enumerate(self.tools):
                                tx = self.screen.get_width() - self.sidebar_width + 12
                                ty = tools_y + i*44
                                if tx <= mx <= tx + self.sidebar_width - 24 and ty <= my <= ty + 36:
                                    if t == 'locomotive':
                                        self.dragging_tool = 'locomotive'
                                    else:
                                        self.selected_tool = t
                                    break
                        continue
                    # map click
                    pos = (mx,my)

                    # Debugging: check for passenger click first
                    passenger = self.passenger_at_pos(pos)
                    if passenger:
                        self.debug_selected_passenger = passenger
                        continue # Prioritize passenger click over station click

                    clicked = self.station_at_pos(pos)
                    if clicked:
                        if self.pending_train_placement:
                            # We've dropped a loco and are now choosing a direction. This takes priority.
                            pending = self.pending_train_placement
                            trail = pending['trail']
                            if clicked.id == trail.station_a or clicked.id == trail.station_b:
                                self.place_new_train(
                                    line_id=pending['line_id'],
                                    start_station_id=trail.station_a if clicked.id == trail.station_b else trail.station_b,
                                    next_station_id=clicked.id
                                )
                                self.pending_train_placement = None
                            else:
                                # Clicked somewhere else, cancel placement
                                self.pending_train_placement = None

                        elif self.selected_tool == 'line':
                            if self.first_station_for_trail is None:
                                # This is the first station clicked for a new trail.
                                self.first_station_for_trail = clicked.id
                                self.temp_mouse_pos = pos # For drawing a preview line
                            else:
                                # This is the second station. Create the trail.
                                station_a_id = self.first_station_for_trail
                                station_b_id = clicked.id

                                if station_a_id != station_b_id:
                                    self.draw_trail_in_line(station_a_id, station_b_id)

                                # Reset for the next trail operation.
                                self.first_station_for_trail = None
                                self.temp_mouse_pos = None
                        
                        elif self.selected_tool == 'remove':
                            if self.first_station_for_trail is None:
                                # First station of the trail to remove.
                                self.first_station_for_trail = clicked.id
                                self.temp_mouse_pos = pos
                            else:
                                # Second station. Attempt to remove the trail.
                                station_a_id = self.first_station_for_trail
                                station_b_id = clicked.id

                                if station_a_id != station_b_id:
                                    # Find a line that has a trail directly connecting the two stations
                                    line_to_modify = None
                                    for line in self.lines.values():
                                        for trail in line.trails:
                                            if (trail.station_a == station_a_id and trail.station_b == station_b_id) or \
                                               (trail.station_a == station_b_id and trail.station_b == station_a_id):
                                                line_to_modify = line
                                                break
                                        if line_to_modify:
                                            break
                                    if line_to_modify:
                                        line_to_modify.remove_trail(station_a_id, station_b_id)
                                        self.update_exchange_caches(line_to_modify)

                                # Reset for the next operation.
                                self.first_station_for_trail = None
                                self.temp_mouse_pos = None
                        elif self.selected_tool == 'carriage':
                            lid = self.find_line_with_station(clicked.id)
                            if lid is not None:
                                trains = [t for t in self.trains.values() if t.line_id == lid]
                                if trains:
                                    trains[-1].carriages += 1
                                self.first_station_for_trail = None # Cancel line drawing
                        elif self.selected_tool == 'interchange':
                            clicked.upgraded = True
                            self.first_station_for_trail = None # Cancel line drawing
                    else:
                        # clicked empty map - cancel any drawing operation
                        self.first_station_for_trail = None
                        self.debug_selected_passenger = None
                        self.temp_mouse_pos = None
                elif ev.button == 3:  # right click finish/cancel
                    # cancel any current drawing or editing
                    self.current_line_drawing = None
                    self.current_edit_line_id = None
                    self.current_edit_anchor = None
                    self.temp_mouse_pos = None
                    self.first_station_for_trail = None
                    self.debug_selected_passenger = None
            elif ev.type == pygame.MOUSEMOTION:
                # update temporary mouse pos when drawing a line
                if (self.first_station_for_trail is not None and self.selected_tool in ['line', 'remove']) or self.dragging_tool:
                    self.temp_mouse_pos = ev.pos
            elif ev.type == pygame.MOUSEBUTTONUP:
                if ev.button == 1 and self.dragging_tool == 'locomotive':
                    # Dropped the locomotive
                    self.dragging_tool = None
                    found = self.find_trail_at_pos(ev.pos)
                    if found:
                        self.pending_train_placement = {
                            'line_id': found['line_id'],
                            'trail': found['trail']
                        }
                    self.temp_mouse_pos = None

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif ev.key == pygame.K_t:
                    # This key is now deprecated in favor of the drag/drop UI
                    # add locomotive to selected line (select by clicking any station earlier)
                    pos = pygame.mouse.get_pos()
                    st = self.station_at_pos(pos)
                    if st:
                        lid = self.find_line_with_station(st.id)
                        if lid is not None:
                            tr = Train(id=self.next_train_id, line_id=lid)
                            self.trains[tr.id] = tr
                            self.next_train_id += 1
                elif ev.key == pygame.K_c:
                    # This key is now deprecated in favor of the UI tool
                    # add carriage to last train
                    if self.trains:
                        last = max(self.trains.keys())
                        self.trains[last].carriages += 1

    def station_at_pos(self, pos, radius=14):
        x,y = pos
        for s in self.stations.values():
            sx,sy = s.pos
            if (sx-x)**2 + (sy-y)**2 <= radius*radius:
                return s
        return None

    def passenger_at_pos(self, pos):
        """Checks if a click position corresponds to a waiting passenger icon."""
        mx, my = pos
        passenger_icon_size = 4
        spacing = 10
        row_length = 5
        
        for station in self.stations.values():
            start_x = station.pos[0] + 20
            start_y = station.pos[1] - 10
            
            for i, p in enumerate(station.waiting):
                row = i // row_length
                col = i % row_length
                px = start_x + col * spacing
                py = start_y + row * spacing
                
                # Check if click is within the icon's bounding box (with a small buffer)
                if (mx - px)**2 + (my - py)**2 <= (passenger_icon_size + 2)**2:
                    return p
        return None

    def find_line_with_station(self, station_id):
        for lid,line in self.lines.items():
            if station_id in line.get_stations():
                return lid
        return None

    def find_trail_at_pos(self, pos, threshold=10):
        """Finds the closest trail to a given mouse position."""
        px, py = pos
        for line_id, line in self.lines.items():
            for trail in line.trails:
                s1 = self.stations.get(trail.station_a)
                s2 = self.stations.get(trail.station_b)
                if not s1 or not s2: continue

                x1, y1 = s1.pos
                x2, y2 = s2.pos

                # Basic point-to-line-segment distance calculation
                dx, dy = x2 - x1, y2 - y1
                if dx == 0 and dy == 0: continue # segment is a point
                
                t = ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)
                t = max(0, min(1, t)) # clamp to segment

                closest_x, closest_y = x1 + t * dx, y1 + t * dy
                dist = math.hypot(px - closest_x, py - closest_y)

                if dist < threshold:
                    return {'line_id': line_id, 'trail': trail}
        return None

    def place_new_train(self, line_id: int, start_station_id: int, next_station_id: int):
        """Creates and places a new train on a line, setting its initial direction."""
        line = self.lines.get(line_id)
        if not line: return

        station_sequence = line.station_sequence()
        try:
            start_idx = station_sequence.index(start_station_id)
            next_idx = station_sequence.index(next_station_id)
        except ValueError:
            return # Should not happen if logic is correct

        direction = 1 if next_idx > start_idx else -1

        # Set initial state for dynamic movement
        tr = Train(id=self.next_train_id, line_id=line_id, current_station_id=start_station_id, target_station_id=next_station_id)
        self.trains[tr.id] = tr
        self.next_train_id += 1

        # Perform initial passenger pickup
        start_station = self.stations[start_station_id]
        tr.load_passengers(start_station, line)
    
    def find_shortest_path_distance(self, start_id: int, end_id: int) -> float:
        """
        Calculates the shortest travel distance (in pixels) between two stations using Dijkstra's algorithm.
        Returns float('inf') if no path exists.
        """
        if start_id == end_id:
            return 0

        distances = {station_id: float('inf') for station_id in self.stations}
        distances[start_id] = 0
        
        pq = [(0, start_id)]  # (distance, station_id)

        while pq:
            current_dist, current_id = heapq.heappop(pq)

            if current_dist > distances[current_id]:
                continue

            if current_id == end_id:
                return current_dist

            # Find all neighbors of the current station across all lines it's on
            for line_id in self.station_lines.get(current_id, []):
                line = self.lines[line_id]
                for neighbor_id in line.get_neighbors(current_id):
                    # Calculate the pixel distance of this trail
                    edge_dist = math.hypot(self.stations[current_id].pos[0] - self.stations[neighbor_id].pos[0],
                                          self.stations[current_id].pos[1] - self.stations[neighbor_id].pos[1])
                    
                    if distances[current_id] + edge_dist < distances[neighbor_id]:
                        distances[neighbor_id] = distances[current_id] + edge_dist
                        heapq.heappush(pq, (distances[neighbor_id], neighbor_id))
        
        return float('inf') # No path found

    def update_exchange_caches(self, changed_line: Line | None = None):
        """Recalculates caches for line shapes and exchange stations. Can be optimized to update only changed lines."""
        self.station_lines.clear()
        for line_id, line in self.lines.items():
            line_stations = line.get_stations()
            # Cache shapes per line
            self.line_station_shapes[line_id] = {self.stations[sid].shape for sid in line_stations}
            # Cache lines per station
            for station_id in line_stations:
                self.station_lines.setdefault(station_id, []).append(line_id)
        
        # Identify exchange stations (stations on more than one line)
        self.exchange_stations = {sid for sid, lines in self.station_lines.items() if len(lines) > 1}

        # After updating caches, all passenger routes might need re-evaluation
        for station in self.stations.values():
            self.update_passenger_routes_at_station(station)

    def update_passenger_routes_at_station(self, station: Station):
        """For each passenger at a station, determine their best next hop."""
        for p in station.waiting:
            p.picked = False # Reset picked status when re-evaluating route

            # --- Recalculate the ULTIMATE destination, prioritizing same-line travel ---
            valid_destinations = [s for s in self.stations.values() if s.shape == p.dest_shape]
            if not valid_destinations:
                p.destination_id = None
                p.next_hop_id = None
                continue

            station_line_ids = self.station_lines.get(station.id, [])

            # Separate destinations into same-line and other-line
            same_line_dests = []
            other_dests = []
            for dest in valid_destinations:
                if any(dest.id in self.lines[lid].get_stations() for lid in station_line_ids):
                    same_line_dests.append(dest)
                else:
                    other_dests.append(dest)

            # Prioritize destinations on the same line
            target_list = same_line_dests if same_line_dests else other_dests

            best_destination = None
            min_travel_dist = float('inf')

            for dest_station in target_list:
                # Use Dijkstra to find the actual travel distance from the passenger's origin
                dist = self.find_shortest_path_distance(p.origin_id, dest_station.id)
                if dist < min_travel_dist:
                    min_travel_dist = dist
                    best_destination = dest_station

            p.destination_id = best_destination.id if best_destination else None

            # --- Now, calculate the NEXT HOP based on the new ultimate destination ---
            if p.destination_id is None:
                p.next_hop_id = None # No path to any valid destination
                continue

            station_line_ids = self.station_lines.get(station.id, [])
            # Check if destination is on any of the lines serving the current station
            can_reach_directly = any(p.dest_shape in self.line_station_shapes.get(lid, set()) for lid in station_line_ids)
            if can_reach_directly:
                p.next_hop_id = p.destination_id
                continue

            # Find a valid exchange station to get to the destination
            best_exchange_id = None
            for exchange_id in self.exchange_stations:
                if any(exchange_id in self.lines[lid].get_stations() for lid in station_line_ids) and \
                   any(p.dest_shape in self.line_station_shapes.get(other_lid, set()) for other_lid in self.station_lines.get(exchange_id, [])):
                    best_exchange_id = exchange_id
                    break # Simple approach: take the first valid one found.
            p.next_hop_id = best_exchange_id

    def update(self, dt):
        # If paused, we only process a delta time of 0 to freeze game state
        # but we still run the loop to check for game over conditions.
        effective_dt = 0 if self.paused else dt

        self.time_elapsed += effective_dt
        # spawn passengers periodically when not paused
        if not self.paused and self.time_elapsed - self.last_spawn > 1.0:  # every second
            self.spawn_passenger()
            self.last_spawn = self.time_elapsed
        # move trains
        for tr in list(self.trains.values()):
            line = self.lines.get(tr.line_id)
            if not line or not tr.current_station_id or not tr.target_station_id:
                continue

            s_from = self.stations[tr.current_station_id]
            s_to = self.stations[tr.target_station_id]

            # interpolate
            sx,sy = s_from.pos
            tx,ty = s_to.pos
            dist = math.hypot(tx-sx, ty-sy)
            if dist == 0:
                tr.progress = 1.0
            else:
                tr.progress += (tr.speed * effective_dt) / dist # speed is now pixels/sec

            if tr.progress >= 1.0:
                # arrive at s_to
                tr.progress = 0.0
                last_station_id = tr.current_station_id
                tr.current_station_id = tr.target_station_id

                # drop off
                dropped = tr.drop_off(s_to)
                self.score += dropped

                # pick up if capacity
                if tr.available_capacity() > 0:
                    tr.load_passengers(s_to, line)

                # AI: Choose next station
                tr.target_station_id = self.choose_next_station(tr, line, last_station_id)

        # overcrowding check
        for s in self.stations.values():
            if len(s.waiting) > 12:
                self.game_over = True
                self.running = False

    def choose_next_station(self, train: Train, line: Line, last_station_id: int) -> int | None:
        """AI logic for a train to decide where to go next."""
        current_station_id = train.current_station_id
        neighbors = line.get_neighbors(current_station_id)

        if not neighbors:
            return None # End of the line, nowhere to go

        # If it's a simple path (not a junction), just continue or turn around.
        if len(neighbors) == 1:
            return neighbors[0] # Only one way to go

        # At a junction.
        # Exclude the path we just came from, unless we have to turn around.
        potential_paths = [n for n in neighbors if n != last_station_id]
        if not potential_paths:
            return last_station_id # Must turn around

        # If there are passengers, try to find a path that serves them.
        if train.passengers:
            passenger_dests = {p.next_hop_id for p in train.passengers}
            
            best_path = None
            for path_station_id in potential_paths:
                # Simple check: does this immediate neighbor match a destination?
                if path_station_id in passenger_dests:
                    return path_station_id # Greedily go to the matching station

            # More advanced: Do a quick search down each path to see if it contains a destination shape.
            # For now, we'll just pick one of the potential paths.
            # A simple heuristic is to continue "straight" if possible, but that's complex.
            # We'll just pick the first available path.
            return random.choice(potential_paths)

        # No passengers, just explore. Avoid turning back if possible.
        return random.choice(potential_paths)

    def draw_trail_in_line(self, station_a_id: int, station_b_id: int):
        """
        Adds a trail between two stations to the line of the currently selected color.
        Creates a new line if one of that color doesn't exist.
        """
        new_trail = Trail(station_a_id, station_b_id)

        # Find if a line with the selected color already exists.
        target_line = None
        for line in self.lines.values():
            if line.color == self.selected_color:
                target_line = line
                break

        if target_line is None:
            # No line with this color, create a new one.
            target_line = Line(id=self.next_line_id, color=self.selected_color)
            self.lines[self.next_line_id] = target_line
            self.next_line_id += 1

        if target_line.can_add_trail(new_trail):
            target_line.add_trail(new_trail)
            self.update_exchange_caches(target_line)

    def run(self):
        last = time.time()
        while self.running:
            now = time.time()
            dt = now - last
            last = now
            self.handle_events()
            self.update(dt)
            self.renderer.draw(self)
            self.clock.tick(60)
        
        if self.game_over:
            self.show_game_over_screen()

    def show_game_over_screen(self):
        # game over screen
        self.screen.fill((30,30,30))
        go = self.font.render('GAME OVER - press ESC or close window', True, (255,255,255))
        sc = self.font.render(f'Final score: {self.score}', True, (255,255,255))
        self.screen.blit(go, (self.screen.get_width()/2-150, self.screen.get_height()/2-10))
        self.screen.blit(sc, (self.screen.get_width()/2-80, self.screen.get_height()/2+20))
        pygame.display.flip()
        # wait until quit
        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    return
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
            self.clock.tick(10)
