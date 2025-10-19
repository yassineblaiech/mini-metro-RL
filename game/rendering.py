import pygame
import math
from typing import TYPE_CHECKING

from .entities import Station, Line, Train

if TYPE_CHECKING:
    from .game import Game


class Renderer:
    """Handles all drawing operations for the game."""

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font):
        self.screen = screen
        self.font = font

    def draw(self, game: 'Game'):
        """The main drawing method, called every frame."""
        self.screen.fill((240, 240, 240))

        # Calculate shared segments for parallel line rendering
        from .game_logic import find_shared_segments
        shared_segments = find_shared_segments(game.lines)

        # Draw game world elements
        for line_id, line in game.lines.items():
            self.draw_line(line, line_id, game.stations, game.obstacles, shared_segments)
        
        for ob in game.obstacles.values():
            pygame.draw.polygon(self.screen, (180, 200, 255), ob.points)
            pygame.draw.polygon(self.screen, (90, 120, 160), ob.points, 2)

        for s in game.stations.values():
            self.draw_station(s)

        for tr in game.trains.values():
            self.draw_train(tr, game)

        # Draw UI elements on top
        self.draw_ui(game)

        pygame.display.flip()

    def _get_shape_draw_info(self, shape: str) -> dict:
        """Returns drawing info (color, drawing function) for a shape."""
        shape_map = {
            'circle': {'color': (200, 40, 40), 'draw_func': pygame.draw.circle},
            'square': {'color': (40, 200, 40), 'draw_func': lambda s, c, p, sz: pygame.draw.rect(s, c, (p[0] - sz, p[1] - sz, sz * 2, sz * 2))},
            'triangle': {'color': (40, 40, 200), 'draw_func': lambda s, c, p, sz: pygame.draw.polygon(s, c, [(p[0], p[1] - sz), (p[0] - sz, p[1] + sz), (p[0] + sz, p[1] + sz)])},
            'pentagon': {'color': (200, 140, 40), 'draw_func': self._draw_polygon_shape}
        }
        return shape_map.get(shape)

    def _draw_polygon_shape(self, surface, color, center, size, sides=5):
        """Helper to draw a regular polygon."""
        pts = []
        for i in range(sides):
            angle = -math.pi / 2 + i * 2 * math.pi / sides
            pts.append((center[0] + size * math.cos(angle), center[1] + size * math.sin(angle)))
        pygame.draw.polygon(surface, color, pts)

    def draw_station(self, s: Station):
        x, y = s.pos
        pygame.draw.circle(self.screen, (40, 40, 40), (x, y), 16, 2)
        # draw shape symbol
        draw_info = self._get_shape_draw_info(s.shape)
        if draw_info:
            draw_info['draw_func'](self.screen, draw_info['color'], (x, y), 6 if s.shape != 'triangle' else 7)

        # Draw waiting passengers as small shapes
        passenger_icon_size = 4
        spacing = 10
        row_length = 5
        start_x = x + 20
        start_y = y - 10

        for i, p in enumerate(s.waiting):
            row = i // row_length
            col = i % row_length
            px = start_x + col * spacing
            py = start_y + row * spacing
            draw_info = self._get_shape_draw_info(p.dest_shape)
            if draw_info:
                draw_info['draw_func'](self.screen, draw_info['color'], (px, py), passenger_icon_size)

    def draw_line(self, line: Line, line_id: int, stations, obstacles, shared_segments):
        if not line.trails:
            return

        from .game_logic import calculate_line_offset_for_segment, offset_waypoints

        seg_width = 6
        for trail in line.trails:
            # Use waypoints for orthogonal/diagonal rendering
            waypoints = trail.waypoints if trail.waypoints else [stations[trail.station_a].pos, stations[trail.station_b].pos]

            # Calculate offset for this segment if it's shared
            segment_key = tuple(sorted([trail.station_a, trail.station_b]))
            offset_distance = calculate_line_offset_for_segment(line_id, segment_key, shared_segments)

            # Apply offset to waypoints if needed
            if abs(offset_distance) > 0.1:
                render_waypoints = offset_waypoints(waypoints, offset_distance)
            else:
                render_waypoints = waypoints

            # Draw each segment between consecutive waypoints
            for i in range(len(render_waypoints) - 1):
                x1, y1 = render_waypoints[i]
                x2, y2 = render_waypoints[i + 1]
                seg_len = math.hypot(x2 - x1, y2 - y1)
                if seg_len == 0:
                    continue

                piece = 12
                d = 0.0
                while d < seg_len:
                    t1 = d / seg_len
                    t2 = min((d + piece) / seg_len, 1.0)
                    sx, sy = x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1
                    ex, ey = x1 + (x2 - x1) * t2, y1 + (y2 - y1) * t2
                    mx, my = (sx + ex) / 2, (sy + ey) / 2

                    inside_any = any(ob.contains_point((int(mx), int(my))) for ob in obstacles.values())
                    if not inside_any:
                        pygame.draw.line(self.screen, line.color, (int(sx), int(sy)), (int(ex), int(ey)), seg_width)
                    d += piece

        if line.has_bridge:
            for trail in line.trails:
                waypoints = trail.waypoints if trail.waypoints else [stations[trail.station_a].pos, stations[trail.station_b].pos]

                # Calculate offset for bridge marks too
                segment_key = tuple(sorted([trail.station_a, trail.station_b]))
                offset_distance = calculate_line_offset_for_segment(line_id, segment_key, shared_segments)

                if abs(offset_distance) > 0.1:
                    render_waypoints = offset_waypoints(waypoints, offset_distance)
                else:
                    render_waypoints = waypoints

                # Draw bridge marks on each segment
                for i in range(len(render_waypoints) - 1):
                    x1, y1 = render_waypoints[i]
                    x2, y2 = render_waypoints[i + 1]
                    seg_len = int(math.hypot(x2 - x1, y2 - y1))
                    d = 0
                    while d < seg_len:
                        t1, t2 = d / seg_len, min((d + 12) / seg_len, 1.0)
                        sx, sy = int(x1 + (x2 - x1) * t1), int(y1 + (y2 - y1) * t1)
                        ex, ey = int(x1 + (x2 - x1) * t2), int(y1 + (y2 - y1) * t2)
                        pygame.draw.line(self.screen, (220, 220, 220), (sx, sy), (ex, ey), 3)
                        d += 24

    def draw_train(self, tr: Train, game: 'Game'):
        if not tr.line_id or not tr.current_station_id or not tr.target_station_id:
            return

        # Get the trail and waypoints
        line = game.lines.get(tr.line_id)
        if not line:
            return

        trail = line.get_trail_between(tr.current_station_id, tr.target_station_id)
        if not trail:
            return

        s_from = game.stations[tr.current_station_id]
        s_to = game.stations[tr.target_station_id]

        # Get waypoints for this trail
        waypoints = trail.waypoints if trail.waypoints else [s_from.pos, s_to.pos]

        # Ensure waypoints are in correct direction (from current_station to target_station)
        # The trail stores waypoints from station_a to station_b, but train might go b to a
        if trail.station_a == tr.current_station_id:
            # Train going station_a → station_b, waypoints are correct
            pass
        elif trail.station_b == tr.current_station_id:
            # Train going station_b → station_a, reverse waypoints
            waypoints = list(reversed(waypoints))
        else:
            # Fallback: check endpoints
            if waypoints[0] != s_from.pos and waypoints[-1] == s_from.pos:
                waypoints = list(reversed(waypoints))

        # Calculate offset for parallel lines
        from .game_logic import find_shared_segments, calculate_line_offset_for_segment, offset_waypoints
        shared_segments = find_shared_segments(game.lines)
        segment_key = tuple(sorted([trail.station_a, trail.station_b]))
        offset_distance = calculate_line_offset_for_segment(tr.line_id, segment_key, shared_segments)

        # Apply offset to waypoints if on a shared segment
        if abs(offset_distance) > 0.1:
            render_waypoints = offset_waypoints(waypoints, offset_distance)
        else:
            render_waypoints = waypoints

        # Calculate total distance along the offset path
        total_distance = 0.0
        segment_lengths = []
        for i in range(len(render_waypoints) - 1):
            x1, y1 = render_waypoints[i]
            x2, y2 = render_waypoints[i + 1]
            seg_len = math.hypot(x2 - x1, y2 - y1)
            segment_lengths.append(seg_len)
            total_distance += seg_len

        if total_distance == 0:
            x, y = s_from.pos
            angle = 0
        else:
            # Find which segment the train is on based on progress
            target_distance = tr.progress * total_distance
            accumulated_dist = 0.0
            current_segment = 0
            segment_progress = 0.0

            for i, seg_len in enumerate(segment_lengths):
                if accumulated_dist + seg_len >= target_distance:
                    current_segment = i
                    if seg_len > 0:
                        segment_progress = (target_distance - accumulated_dist) / seg_len
                    break
                accumulated_dist += seg_len

            # Interpolate position within the current segment (using offset waypoints)
            x1, y1 = render_waypoints[current_segment]
            x2, y2 = render_waypoints[current_segment + 1]
            x = x1 + (x2 - x1) * segment_progress
            y = y1 + (y2 - y1) * segment_progress
            angle = math.atan2(y2 - y1, x2 - x1)

        w, h = 18, 10
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (50, 50, 50), (0, 0, w, h)) # Draw the train body

        # Draw passengers inside the train on the un-rotated surface
        passenger_icon_size = 2 # Half-width/radius for passengers on train
        p_spacing = 1 # Spacing between passenger icons
        
        x_start_on_surf = (w - (3 * (passenger_icon_size*2 + p_spacing) - p_spacing)) / 2
        y_start_on_surf = (h - (2 * (passenger_icon_size*2 + p_spacing) - p_spacing)) / 2

        for i, p in enumerate(tr.passengers):
            if i >= tr.effective_capacity():
                break
            
            row = i // 3
            col = i % 3
            
            px_local = x_start_on_surf + col * (passenger_icon_size*2 + p_spacing) + passenger_icon_size
            py_local = y_start_on_surf + row * (passenger_icon_size*2 + p_spacing) + passenger_icon_size

            self._draw_passenger_shape_on_surface(surf, p.dest_shape, px_local, py_local, passenger_icon_size)

        # Now, rotate the surface with the passengers on it and blit it
        rot = pygame.transform.rotate(surf, -math.degrees(angle))
        rx = x - rot.get_width() / 2
        ry = y - rot.get_height() / 2
        self.screen.blit(rot, (rx, ry))

    def _draw_passenger_shape_on_surface(self, surface: pygame.Surface, shape: str, x: int, y: int, size: int):
        """Helper to draw a passenger shape on a specific surface."""
        draw_info = self._get_shape_draw_info(shape)
        if draw_info:
            draw_info['draw_func'](surface, draw_info['color'], (x, y), size)

    def draw_ui(self, game: 'Game'):
        txt = self.font.render(f'Score: {game.score}  Trains: {len(game.trains)}  Lines: {len(game.lines)}', True, (0, 0, 0))
        self.screen.blit(txt, (8, 8))
        
        if game.paused:
            p = self.font.render('PAUSED', True, (200, 0, 0))
            text_height = p.get_height()
            self.screen.blit(p, (8, self.screen.get_height() - text_height - 8))
            
        self.draw_sidebar(game)

        if game.first_station_for_trail is not None and game.temp_mouse_pos is not None:
            from .game_logic import calculate_orthogonal_path
            preview_color = game.selected_color
            if game.selected_tool == 'remove':
                preview_color = (128, 128, 128)

            # Draw preview path
            if game.is_dragging_line and len(game.intermediate_stations) > 1:
                # Show preview of all segments being created
                for i in range(len(game.intermediate_stations) - 1):
                    start_pos = game.stations[game.intermediate_stations[i]].pos
                    end_pos = game.stations[game.intermediate_stations[i + 1]].pos
                    waypoints = calculate_orthogonal_path(start_pos, end_pos)
                    for j in range(len(waypoints) - 1):
                        pygame.draw.line(self.screen, preview_color, waypoints[j], waypoints[j + 1], 4)

                # Draw preview from last intermediate station to mouse cursor
                last_station = game.stations[game.intermediate_stations[-1]]
                waypoints = calculate_orthogonal_path(last_station.pos, game.temp_mouse_pos)
                for i in range(len(waypoints) - 1):
                    pygame.draw.line(self.screen, preview_color, waypoints[i], waypoints[i + 1], 4)

                # Highlight intermediate stations
                for station_id in game.intermediate_stations:
                    station = game.stations[station_id]
                    pygame.draw.circle(self.screen, preview_color, station.pos, 20, 3)
            else:
                # Original preview (non-drag or first click)
                start_pos = game.stations[game.first_station_for_trail].pos
                end_pos = game.temp_mouse_pos
                waypoints = calculate_orthogonal_path(start_pos, end_pos)
                for i in range(len(waypoints) - 1):
                    pygame.draw.line(self.screen, preview_color, waypoints[i], waypoints[i + 1], 4)

        if game.dragging_tool == 'locomotive' and game.temp_mouse_pos:
            icon_x, icon_y = game.temp_mouse_pos
            pygame.draw.rect(self.screen, (70, 70, 70), (icon_x - 10, icon_y - 6, 20, 12))
            pygame.draw.circle(self.screen, (30, 30, 30), (icon_x - 4, icon_y + 8), 3)
            pygame.draw.circle(self.screen, (30, 30, 30), (icon_x + 6, icon_y + 8), 3)

        if game.pending_train_placement:
            trail = game.pending_train_placement['trail']
            s1 = game.stations[trail.station_a]
            s2 = game.stations[trail.station_b]
            pygame.draw.circle(self.screen, (255, 255, 0), s1.pos, 20, 4)
            pygame.draw.circle(self.screen, (255, 255, 0), s2.pos, 20, 4)

        # Draw debug highlight for selected passenger
        if game.debug_selected_passenger:
            # Draw final destination in red
            if game.debug_selected_passenger.destination_id:
                dest_station = game.stations.get(game.debug_selected_passenger.destination_id)
                if dest_station:
                    pygame.draw.circle(self.screen, (255, 0, 0), dest_station.pos, 22, 3) # Red for final destination

            # Draw next hop in green, if it's an intermediate stop
            if game.debug_selected_passenger.next_hop_id:
                hop_station = game.stations.get(game.debug_selected_passenger.next_hop_id)
                if hop_station:
                    pygame.draw.circle(self.screen, (0, 200, 0), hop_station.pos, 25, 3) # Green for next hop


    def draw_sidebar(self, game: 'Game'):
        sx = self.screen.get_width() - game.sidebar_width
        pygame.draw.rect(self.screen, (245, 245, 245), (sx, 0, game.sidebar_width, self.screen.get_height()))
        t = self.font.render('Tools', True, (20, 20, 20))
        self.screen.blit(t, (sx + 12, 6))
        
        y = 30
        for idx, c in enumerate(game.available_colors[:6]):
            cx = sx + 20 + (idx % 2) * 28
            cy = y + (idx // 2) * 28
            pygame.draw.circle(self.screen, c, (cx, cy), 12)
            if c == game.selected_color:
                pygame.draw.circle(self.screen, (0, 0, 0), (cx, cy), 14, 2)

        tools_y = 140
        for i, tname in enumerate(game.tools):
            tx = sx + 12
            ty = tools_y + i * 44
            rect = (tx, ty, game.sidebar_width - 24, 36)
            
            if tname == game.selected_tool:
                pygame.draw.rect(self.screen, (220, 230, 255), rect)
                pygame.draw.rect(self.screen, (80, 120, 200), rect, 2)
            else:
                pygame.draw.rect(self.screen, (235, 235, 235), rect)

            self.draw_tool_icon(tname, tx, ty, game.selected_color)
            
            lbl = self.font.render(tname.capitalize(), True, (10, 10, 10))
            self.screen.blit(lbl, (tx + 40, ty + 8))

    def draw_tool_icon(self, tname, tx, ty, selected_color):
        icon_x = tx + 18 # Centered better
        icon_y = ty + 18

        if tname == 'line':
            pygame.draw.circle(self.screen, selected_color, (icon_x, icon_y), 8)
        elif tname == 'remove':
            pygame.draw.line(self.screen, (200, 0, 0), (icon_x - 6, icon_y - 6), (icon_x + 6, icon_y + 6), 3)
            pygame.draw.line(self.screen, (200, 0, 0), (icon_x - 6, icon_y + 6), (icon_x + 6, icon_y - 6), 3)
        elif tname == 'locomotive':
            pygame.draw.rect(self.screen, (70, 70, 70), (icon_x - 10, icon_y - 6, 20, 12))
            pygame.draw.circle(self.screen, (30, 30, 30), (icon_x - 4, icon_y + 8), 3)
            pygame.draw.circle(self.screen, (30, 30, 30), (icon_x + 6, icon_y + 8), 3)
        elif tname == 'carriage':
            pygame.draw.rect(self.screen, (120, 80, 40), (icon_x - 10, icon_y - 6, 20, 12))
            pygame.draw.circle(self.screen, (30, 30, 30), (icon_x - 4, icon_y + 8), 3)
        elif tname == 'interchange':
            pygame.draw.polygon(self.screen, (200, 160, 0), [(icon_x, icon_y-6), (icon_x+4, icon_y+2), (icon_x-4, icon_y-2), (icon_x+4, icon_y-2), (icon_x-4, icon_y+2)])