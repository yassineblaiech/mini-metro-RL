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

        # Draw game world elements
        for line in game.lines.values():
            self.draw_line(line, game.stations, game.obstacles)
        
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

    def draw_station(self, s: Station):
        x, y = s.pos
        pygame.draw.circle(self.screen, (40, 40, 40), (x, y), 16, 2)
        # draw shape symbol
        if s.shape == 'circle':
            pygame.draw.circle(self.screen, (200, 40, 40), (x, y), 6)
        elif s.shape == 'square':
            pygame.draw.rect(self.screen, (40, 200, 40), (x - 6, y - 6, 12, 12))
        elif s.shape == 'triangle':
            points = [(x, y - 7), (x - 6, y + 6), (x + 6, y + 6)]
            pygame.draw.polygon(self.screen, (40, 40, 200), points)
        elif s.shape == 'pentagon':
            pts = []
            for i in range(5):
                a = -math.pi / 2 + i * 2 * math.pi / 5
                pts.append((x + 6 * math.cos(a), y + 6 * math.sin(a)))
            pygame.draw.polygon(self.screen, (200, 140, 40), pts)

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

            if p.dest_shape == 'circle':
                pygame.draw.circle(self.screen, (200, 40, 40), (px, py), passenger_icon_size) # Red color for circle shape
            elif p.dest_shape == 'square':
                pygame.draw.rect(self.screen, (40, 200, 40), (px - passenger_icon_size, py - passenger_icon_size, passenger_icon_size * 2, passenger_icon_size * 2)) # Green color for square shape
            elif p.dest_shape == 'triangle':
                points = [(px, py - passenger_icon_size), (px - passenger_icon_size, py + passenger_icon_size), (px + passenger_icon_size, py + passenger_icon_size)]
                pygame.draw.polygon(self.screen, (0, 0, 200), points) # Blue color for triangle shape
            elif p.dest_shape == 'pentagon':
                pts = []
                for j in range(5):
                    a = -math.pi / 2 + j * 2 * math.pi / 5
                    pts.append((px + passenger_icon_size * math.cos(a), py + passenger_icon_size * math.sin(a)))
                pygame.draw.polygon(self.screen, (200, 140, 40), pts) # Orange color for pentagon shape

    def draw_line(self, line: Line, stations, obstacles):
        if not line.trails:
            return
            
        seg_width = 6
        for trail in line.trails:
            s1 = stations.get(trail.station_a)
            s2 = stations.get(trail.station_b)
            x1, y1 = s1.pos
            x2, y2 = s2.pos
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
                s1 = stations.get(trail.station_a)
                s2 = stations.get(trail.station_b)
                x1, y1 = s1.pos
                x2, y2 = s2.pos
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
            
        s_from = game.stations[tr.current_station_id]
        s_to = game.stations[tr.target_station_id]
        fx, fy = s_from.pos
        tx, ty = s_to.pos
        x = fx + (tx - fx) * tr.progress
        y = fy + (ty - fy) * tr.progress
        
        w, h = 18, 10
        angle = math.atan2(ty - fy, tx - fx)
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
        if shape == 'circle':
            pygame.draw.circle(surface, (200, 40, 40), (x, y), size)
        elif shape == 'square':
            pygame.draw.rect(surface, (40, 200, 40), (x - size, y - size, size * 2, size * 2))
        elif shape == 'triangle':
            points = [(x, y - size), (x - size, y + size), (x + size, y + size)]
            pygame.draw.polygon(surface, (40, 40, 200), points)
        elif shape == 'pentagon':
            pts = []
            for j in range(5):
                a = -math.pi / 2 + j * 2 * math.pi / 5
                pts.append((x + size * math.cos(a), y + size * math.sin(a)))
            pygame.draw.polygon(surface, (200, 140, 40), pts)

    def draw_ui(self, game: 'Game'):
        txt = self.font.render(f'Score: {game.score}  Trains: {len(game.trains)}  Lines: {len(game.lines)}', True, (0, 0, 0))
        self.screen.blit(txt, (8, 8))
        
        if game.paused:
            p = self.font.render('PAUSED', True, (200, 0, 0))
            text_height = p.get_height()
            self.screen.blit(p, (8, self.screen.get_height() - text_height - 8))
            
        self.draw_sidebar(game)

        if game.first_station_for_trail is not None and game.temp_mouse_pos is not None:
            start_pos = game.stations[game.first_station_for_trail].pos
            end_pos = game.temp_mouse_pos
            preview_color = game.selected_color
            if game.selected_tool == 'remove':
                preview_color = (128, 128, 128)
            pygame.draw.line(self.screen, preview_color, start_pos, end_pos, 4)

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