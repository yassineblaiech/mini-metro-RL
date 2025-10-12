import pygame
import random
import time
import math
from typing import Dict, List, Tuple
from .entities import Station, Passenger, Line, Train
from .entities import Obstacle, Trail

SHAPES = ['circle', 'square', 'triangle', 'pentagon']
LINE_COLORS = [(220,20,60),(30,144,255),(34,139,34),(255,165,0),(148,0,211),(0,191,255)]

class Game:
    def __init__(self, window_size=(960,640)):
        pygame.init()
        self.screen = pygame.display.set_mode(window_size)
        pygame.display.set_caption('Mini Metro — Python prototype')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 16)
        self.running = True
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


        self.init_map()

    def init_map(self):
        # create some initial stations placed randomly but not overlapping too much
        w,h = self.screen.get_size()
        margin = 60
        for i in range(8):
            x = random.randint(margin, w - self.sidebar_width - margin)
            y = random.randint(margin, h-margin)
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
        s = random.choice(list(self.stations.values()))
        dest_shape = random.choice(SHAPES)
        # avoid same shape destination
        if dest_shape == s.shape:
            dest_shape = random.choice([sh for sh in SHAPES if sh != s.shape])
        p = Passenger(origin_id=s.id, dest_shape=dest_shape)
        s.add_passenger(p)

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
                                    # Find the line that contains both stations
                                    line_a = self.find_line_with_station(station_a_id)
                                    line_b = self.find_line_with_station(station_b_id)
                                    if line_a is not None and line_a == line_b:
                                        self.lines[line_a].remove_trail(station_a_id, station_b_id)

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
                        self.temp_mouse_pos = None
                elif ev.button == 3:  # right click finish/cancel
                    # cancel any current drawing or editing
                    self.current_line_drawing = None
                    self.current_edit_line_id = None
                    self.current_edit_anchor = None
                    self.temp_mouse_pos = None
                    self.first_station_for_trail = None
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
        tr.load_passengers(start_station)
    
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
                    tr.load_passengers(s_to)

                # AI: Choose next station
                tr.target_station_id = self.choose_next_station(tr, line, last_station_id)

        # overcrowding check
        for s in self.stations.values():
            if len(s.waiting) > 12:
                # game over
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
            passenger_dests = {p.dest_shape for p in train.passengers}
            
            best_path = None
            for path_station_id in potential_paths:
                # Simple check: does this immediate neighbor match a destination?
                if self.stations[path_station_id].shape in passenger_dests:
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

        target_line.add_trail(new_trail)

    def draw_station(self, s: Station):
        x,y = s.pos
        color = (200,200,200)
        pygame.draw.circle(self.screen, (40,40,40), (x,y), 16, 2)
        # draw shape symbol
        if s.shape == 'circle':
            pygame.draw.circle(self.screen, (200,40,40), (x,y), 6)
        elif s.shape == 'square':
            pygame.draw.rect(self.screen, (40,200,40), (x-6,y-6,12,12))
        elif s.shape == 'triangle':
            points = [(x,y-7),(x-6,y+6),(x+6,y+6)]
            pygame.draw.polygon(self.screen, (40,40,200), points)
        elif s.shape == 'pentagon':
            pts = []
            for i in range(5):
                a = -math.pi/2 + i*2*math.pi/5
                pts.append((x+6*math.cos(a), y+6*math.sin(a)))
            pygame.draw.polygon(self.screen, (200,140,40), pts)
        # draw waiting count
        txt = self.font.render(str(len(s.waiting)), True, (0,0,0))
        self.screen.blit(txt, (x-10,y+18))

    def draw_line(self, line: Line):
        if line.trails:
            # draw thicker line but make it discontinuous where it crosses obstacles
            seg_width = 6
            for trail in line.trails:
                s1 = self.stations.get(trail.station_a)
                s2 = self.stations.get(trail.station_b)
                x1, y1 = s1.pos
                x2, y2 = s2.pos
                seg_len = math.hypot(x2-x1, y2-y1)
                if seg_len == 0:
                    continue
                # split segment into small pieces
                piece = 12
                d = 0.0
                while d < seg_len:
                    t1 = d/seg_len
                    t2 = min((d+piece)/seg_len, 1.0)
                    sx = x1 + (x2-x1)*t1
                    sy = y1 + (y2-y1)*t1
                    ex = x1 + (x2-x1)*t2
                    ey = y1 + (y2-y1)*t2
                    # check midpoint against obstacles
                    mx = (sx+ex)/2
                    my = (sy+ey)/2
                    inside_any = False
                    for ob in self.obstacles.values():
                        if ob.contains_point((int(mx), int(my))):
                            inside_any = True
                            break
                    if not inside_any:
                        pygame.draw.line(self.screen, line.color, (int(sx),int(sy)), (int(ex),int(ey)), seg_width)
                    d += piece
            # draw bridge overlay if applicable (lighter dashed overlay)
            if line.has_bridge:
                for trail in line.trails:
                    s1 = self.stations.get(trail.station_a)
                    s2 = self.stations.get(trail.station_b)
                    x1, y1 = s1.pos
                    x2, y2 = s2.pos
                    seg_len = int(math.hypot(x2-x1, y2-y1))
                    d = 0
                    while d < seg_len:
                        t1 = d/seg_len
                        t2 = min((d+12)/seg_len,1.0)
                        sx = int(x1 + (x2-x1)*t1)
                        sy = int(y1 + (y2-y1)*t1)
                        ex = int(x1 + (x2-x1)*t2)
                        ey = int(y1 + (y2-y1)*t2)
                        pygame.draw.line(self.screen, (220,220,220), (sx,sy), (ex,ey), 3)
                        d += 24

    def draw_train(self, tr: Train):
        line = self.lines.get(tr.line_id)
        station_sequence = line.station_sequence() if line else []
        if not line or not tr.current_station_id or not tr.target_station_id:
            return
        s_from = self.stations[tr.current_station_id]
        s_to = self.stations[tr.target_station_id]
        fx,fy = s_from.pos
        tx,ty = s_to.pos
        x = fx + (tx-fx)*tr.progress
        y = fy + (ty-fy)*tr.progress
        # draw rectangle for train
        w,h = 18,10
        angle = math.atan2(ty-fy, tx-fx)
        surf = pygame.Surface((w,h), pygame.SRCALPHA)
        surf.fill((0,0,0))
        pygame.draw.rect(surf, (50,50,50), (0,0,w,h))
        rot = pygame.transform.rotate(surf, -math.degrees(angle))
        rx = x - rot.get_width()/2
        ry = y - rot.get_height()/2
        self.screen.blit(rot, (rx,ry))
        txt = self.font.render(str(len(tr.passengers)), True, (255,255,255))
        self.screen.blit(txt, (x-6,y-6))

    def draw_ui(self):
        txt = self.font.render(f'Score: {self.score}  Trains: {len(self.trains)}  Lines: {len(self.lines)}', True, (0,0,0))
        self.screen.blit(txt, (8,8))
        ox = self.screen.get_width() - 200
        oy = 40
        for ob in self.obstacles.values():
            txt_o = self.font.render('Obstacle (needs bridge/tunnel)', True, (0,0,0))
            self.screen.blit(txt_o, (ox, oy))
            break
        if self.paused:
            p = self.font.render('PAUSED', True, (200,0,0))
            self.screen.blit(p, (self.screen.get_width()-80, 8))
        # draw the sidebar visuals
        self.draw_sidebar()

        # Draw preview line if we are in the middle of creating a trail
        if self.first_station_for_trail is not None and self.temp_mouse_pos is not None:
            start_pos = self.stations[self.first_station_for_trail].pos
            end_pos = self.temp_mouse_pos
            preview_color = self.selected_color
            if self.selected_tool == 'remove':
                preview_color = (128, 128, 128)
            pygame.draw.line(self.screen, preview_color, start_pos, end_pos, 4)
        
        # Draw dragged locomotive icon
        if self.dragging_tool == 'locomotive' and self.temp_mouse_pos:
            icon_x, icon_y = self.temp_mouse_pos
            pygame.draw.rect(self.screen, (70,70,70), (icon_x-10, icon_y-6, 20, 12))
            pygame.draw.circle(self.screen, (30,30,30), (icon_x-4, icon_y+8), 3)
            pygame.draw.circle(self.screen, (30,30,30), (icon_x+6, icon_y+8), 3)

        # Draw direction selection prompt
        if self.pending_train_placement:
            trail = self.pending_train_placement['trail']
            s1 = self.stations[trail.station_a]
            s2 = self.stations[trail.station_b]
            pygame.draw.circle(self.screen, (255, 255, 0), s1.pos, 20, 4) # Yellow highlight
            pygame.draw.circle(self.screen, (255, 255, 0), s2.pos, 20, 4) # Yellow highlight

    def draw_sidebar(self):
        sx = self.screen.get_width() - self.sidebar_width
        pygame.draw.rect(self.screen, (245,245,245), (sx, 0, self.sidebar_width, self.screen.get_height()))
        t = self.font.render('Tools', True, (20,20,20))
        self.screen.blit(t, (sx+12, 6))
        y = 30
        for idx,c in enumerate(self.available_colors[:6]):
            cx = sx + 20 + (idx%2)*28
            cy = y + (idx//2)*28
            pygame.draw.circle(self.screen, c, (cx,cy), 12)
            if c == self.selected_color:
                pygame.draw.circle(self.screen, (0,0,0), (cx,cy), 14, 2)
        # tools
        tools_y = 140
        for i,tname in enumerate(self.tools):
            tx = sx + 12
            ty = tools_y + i*44
            rect = (tx, ty, self.sidebar_width-24, 36)
            # highlight selected tool
            if tname == self.selected_tool:
                pygame.draw.rect(self.screen, (220,230,255), rect)
                pygame.draw.rect(self.screen, (80,120,200), rect, 2)
            else:
                pygame.draw.rect(self.screen, (235,235,235), rect)
            # draw icon for tool
            icon_x = tx + 8
            icon_y = ty + 18
            if tname == 'line':
                pygame.draw.circle(self.screen, self.selected_color, (icon_x, icon_y), 8)
            elif tname == 'remove':
                # Red 'X' icon for remove tool
                pygame.draw.line(self.screen, (200, 0, 0), (icon_x - 6, icon_y - 6), (icon_x + 6, icon_y + 6), 3)
                pygame.draw.line(self.screen, (200, 0, 0), (icon_x - 6, icon_y + 6), (icon_x + 6, icon_y - 6), 3)
            elif tname == 'locomotive':
                # small train icon (rectangle + wheel)
                pygame.draw.rect(self.screen, (70,70,70), (icon_x-10, ty+8, 20, 12))
                pygame.draw.circle(self.screen, (30,30,30), (icon_x-4, ty+22), 3)
                pygame.draw.circle(self.screen, (30,30,30), (icon_x+6, ty+22), 3)
            elif tname == 'carriage':
                pygame.draw.rect(self.screen, (120,80,40), (icon_x-10, ty+8, 20, 12))
                pygame.draw.circle(self.screen, (30,30,30), (icon_x-4, ty+22), 3)
            elif tname == 'interchange':
                # star-like upgrade icon
                pygame.draw.polygon(self.screen, (200,160,0), [(icon_x, ty+6),(icon_x+4, ty+14),(icon_x-4, ty+10),(icon_x+4, ty+10),(icon_x-4, ty+14)])
            # label
            lbl = self.font.render(tname.capitalize(), True, (10,10,10))
            self.screen.blit(lbl, (tx+40, ty+8))

    def run(self):
        last = time.time()
        while self.running:
            now = time.time()
            dt = now - last
            last = now
            self.handle_events()
            self.update(dt)
            self.screen.fill((240,240,240))
            # draw lines
            for line in self.lines.values():
                self.draw_line(line)
            # draw obstacles (between lines and stations)
            for ob in self.obstacles.values():
                pygame.draw.polygon(self.screen, (180,200,255), ob.points)
                pygame.draw.polygon(self.screen, (90,120,160), ob.points, 2)
            # draw stations
            for s in self.stations.values():
                self.draw_station(s)
            # draw trains
            for tr in self.trains.values():
                self.draw_train(tr)
            
            # UI must be drawn last to be on top
            self.draw_ui()
            pygame.display.flip()
            self.clock.tick(60)
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
