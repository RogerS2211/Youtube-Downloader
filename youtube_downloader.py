#!/usr/bin/env python3
"""
YouTube Downloader with Interactive GUI and Video Background
Requires: pygame, yt-dlp, opencv-python, moviepy
"""

import os
import sys
import threading
import time
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import queue

# Try importing all required packages
try:
    import pygame
    import yt_dlp
    import cv2
    from moviepy.editor import VideoFileClip
except ImportError as e:
    missing_module = str(e).split("'")[1] if "'" in str(e) else str(e)
    
    package_map = {
        'pygame': 'pygame',
        'yt_dlp': 'yt-dlp', 
        'cv2': 'opencv-python',
        'moviepy': 'moviepy',
        'imageio_ffmpeg': 'imageio-ffmpeg'  # Sometimes needed for moviepy
    }
    
    print(f"Import error: {e}")
    print("\nMissing required packages. Install them with:")
    
    if 'moviepy' in str(e).lower() or 'imageio' in str(e).lower():
        print("pip install moviepy imageio-ffmpeg")
    elif missing_module in package_map:
        print(f"pip install {package_map[missing_module]}")
    else:
        print("pip install pygame yt-dlp opencv-python moviepy imageio-ffmpeg")
    
    print("\nIf moviepy issues persist, try:")
    print("pip uninstall moviepy")
    print("pip install moviepy==1.0.3")
    sys.exit(1)

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Constants
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (64, 64, 64)
BLUE = (0, 100, 200)
LIGHT_BLUE = (100, 150, 255)
GREEN = (0, 200, 100)
RED = (200, 50, 50)
ORANGE = (255, 165, 0)

# Fonts
FONT_LARGE = pygame.font.Font(None, 24)
FONT_MEDIUM = pygame.font.Font(None, 20)
FONT_SMALL = pygame.font.Font(None, 16)

@dataclass
class VideoInfo:
    """Data class for video information"""
    id: str
    title: str
    duration: str
    uploader: str
    url: str
    thumbnail: str = ""
    selected: bool = False

class VideoBackground:
    """Handles video background playback with audio"""
    
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.cap = None
        self.clip = None
        self.is_playing = False
        self.current_frame = 0
        self.fps = 30
        self.volume = 0.3
        self.audio_started = False
        
        if os.path.exists(video_path):
            self.load_video()
    
    def load_video(self):
        """Load video file"""
        try:
            self.cap = cv2.VideoCapture(self.video_path)
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            
            # Load audio with moviepy
            self.clip = VideoFileClip(self.video_path)
            self.clip = self.clip.volumex(self.volume)
            
        except Exception as e:
            print(f"Error loading video: {e}")
    
    def start_playback(self):
        """Start video and audio playback"""
        if self.cap and self.clip:
            self.is_playing = True
            if not self.audio_started:
                # Start audio in a separate thread
                threading.Thread(target=self._play_audio, daemon=True).start()
                self.audio_started = True
    
    def stop_playback(self):
        """Stop video playback"""
        self.is_playing = False
    
    def _play_audio(self):
        """Play audio in separate thread"""
        try:
            # Convert moviepy audio to pygame-compatible format
            temp_audio = "temp_audio.wav"
            self.clip.audio.write_audiofile(temp_audio, verbose=False, logger=None)
            pygame.mixer.music.load(temp_audio)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(-1)  # Loop indefinitely
            
            # Clean up temp file after a delay
            def cleanup():
                time.sleep(2)
                try:
                    os.remove(temp_audio)
                except:
                    pass
            threading.Thread(target=cleanup, daemon=True).start()
            
        except Exception as e:
            print(f"Audio playback error: {e}")
    
    def get_frame(self) -> Optional[pygame.Surface]:
        """Get current video frame as pygame surface"""
        if not self.cap or not self.is_playing:
            return None
        
        ret, frame = self.cap.read()
        if not ret:
            # Loop video
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
        
        if ret:
            # Convert BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Rotate 90 degrees to correct orientation
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            # Convert to pygame surface
            frame = pygame.surfarray.make_surface(frame)
            return pygame.transform.scale(frame, (WINDOW_WIDTH, WINDOW_HEIGHT))
        
        return None
    
    def set_volume(self, volume: float):
        """Set audio volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.volume)

class Button:
    """Interactive button widget"""
    
    def __init__(self, x: int, y: int, width: int, height: int, text: str, 
                 font: pygame.font.Font = FONT_MEDIUM, color: Tuple = BLUE):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = tuple(min(255, c + 50) for c in color)
        self.pressed = False
        self.enabled = True
        self.hovered = False
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle mouse events, return True if clicked"""
        if not self.enabled:
            return False
        
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.pressed and self.rect.collidepoint(event.pos):
                self.pressed = False
                return True
            self.pressed = False
        
        return False
    
    def draw(self, surface: pygame.Surface):
        """Draw button"""
        color = self.hover_color if self.hovered else self.color
        if not self.enabled:
            color = GRAY
        
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, WHITE, self.rect, 2)
        
        text_surface = self.font.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

class InputField:
    """Text input field widget"""
    
    def __init__(self, x: int, y: int, width: int, height: int, placeholder: str = ""):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = ""
        self.placeholder = placeholder
        self.active = False
        self.cursor_pos = 0
        self.cursor_visible = True
        self.cursor_timer = 0
    
    def handle_event(self, event: pygame.event.Event):
        """Handle keyboard and mouse events"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            # Handle Ctrl key combinations
            keys_pressed = pygame.key.get_pressed()
            ctrl_held = keys_pressed[pygame.K_LCTRL] or keys_pressed[pygame.K_RCTRL]
            
            if ctrl_held:
                if event.key == pygame.K_v:  # Ctrl+V - Paste
                    try:
                        import tkinter as tk
                        root = tk.Tk()
                        root.withdraw()  # Hide the tkinter window
                        clipboard_text = root.clipboard_get()
                        root.destroy()
                        
                        # Insert clipboard text at cursor position
                        self.text = self.text[:self.cursor_pos] + clipboard_text + self.text[self.cursor_pos:]
                        self.cursor_pos += len(clipboard_text)
                    except:
                        pass  # Ignore clipboard errors
                elif event.key == pygame.K_c:  # Ctrl+C - Copy
                    try:
                        import tkinter as tk
                        root = tk.Tk()
                        root.withdraw()
                        root.clipboard_clear()
                        root.clipboard_append(self.text)
                        root.update()
                        root.destroy()
                    except:
                        pass
                elif event.key == pygame.K_a:  # Ctrl+A - Select All
                    self.cursor_pos = len(self.text)
                elif event.key == pygame.K_x:  # Ctrl+X - Cut
                    try:
                        import tkinter as tk
                        root = tk.Tk()
                        root.withdraw()
                        root.clipboard_clear()
                        root.clipboard_append(self.text)
                        root.update()
                        root.destroy()
                        self.text = ""
                        self.cursor_pos = 0
                    except:
                        pass
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_pos > 0:
                    self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                    self.cursor_pos -= 1
            elif event.key == pygame.K_DELETE:
                if self.cursor_pos < len(self.text):
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
            elif event.key == pygame.K_LEFT:
                self.cursor_pos = max(0, self.cursor_pos - 1)
            elif event.key == pygame.K_RIGHT:
                self.cursor_pos = min(len(self.text), self.cursor_pos + 1)
            elif event.key == pygame.K_HOME:
                self.cursor_pos = 0
            elif event.key == pygame.K_END:
                self.cursor_pos = len(self.text)
            elif event.unicode.isprintable():
                self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                self.cursor_pos += 1
    
    def update(self, dt: float):
        """Update cursor blinking"""
        self.cursor_timer += dt
        if self.cursor_timer >= 500:  # Blink every 500ms
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0
    
    def draw(self, surface: pygame.Surface):
        """Draw input field"""
        color = WHITE if self.active else LIGHT_GRAY
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, BLACK, self.rect, 2)
        
        # Draw text or placeholder
        display_text = self.text if self.text else self.placeholder
        text_color = BLACK if self.text else GRAY
        
        text_surface = FONT_MEDIUM.render(display_text, True, text_color)
        text_rect = pygame.Rect(self.rect.x + 5, self.rect.y, self.rect.width - 10, self.rect.height)
        surface.blit(text_surface, (text_rect.x, text_rect.centery - text_surface.get_height() // 2))
        
        # Draw cursor
        if self.active and self.cursor_visible and self.text:
            cursor_x = self.rect.x + 5 + FONT_MEDIUM.size(self.text[:self.cursor_pos])[0]
            pygame.draw.line(surface, BLACK, 
                           (cursor_x, self.rect.y + 5), 
                           (cursor_x, self.rect.bottom - 5), 2)

class Slider:
    """Volume slider widget"""
    
    def __init__(self, x: int, y: int, width: int, height: int, min_val: float = 0.0, max_val: float = 1.0):
        self.rect = pygame.Rect(x, y, width, height)
        self.min_val = min_val
        self.max_val = max_val
        self.value = 0.5
        self.dragging = False
        self.knob_radius = height // 2
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle mouse events, return True if value changed"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._update_value(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_value(event.pos[0])
            return True
        return False
    
    def _update_value(self, mouse_x: int):
        """Update slider value based on mouse position"""
        relative_x = mouse_x - self.rect.x
        relative_x = max(0, min(self.rect.width, relative_x))
        self.value = self.min_val + (relative_x / self.rect.width) * (self.max_val - self.min_val)
    
    def draw(self, surface: pygame.Surface):
        """Draw slider"""
        # Draw track
        track_rect = pygame.Rect(self.rect.x, self.rect.centery - 2, self.rect.width, 4)
        pygame.draw.rect(surface, GRAY, track_rect)
        
        # Draw knob
        knob_x = self.rect.x + int((self.value - self.min_val) / (self.max_val - self.min_val) * self.rect.width)
        pygame.draw.circle(surface, BLUE, (knob_x, self.rect.centery), self.knob_radius)
        pygame.draw.circle(surface, WHITE, (knob_x, self.rect.centery), self.knob_radius, 2)

class ScrollableList:
    """Scrollable list widget for videos"""
    
    def __init__(self, x: int, y: int, width: int, height: int):
        self.rect = pygame.Rect(x, y, width, height)
        self.items: List[VideoInfo] = []
        self.scroll_y = 0
        self.item_height = 60
        self.max_scroll = 0
        self.scroll_speed = 30
    
    def set_items(self, items: List[VideoInfo]):
        """Set list items"""
        self.items = items
        self.max_scroll = max(0, len(items) * self.item_height - self.rect.height)
        self.scroll_y = min(self.scroll_y, self.max_scroll)
    
    def handle_event(self, event: pygame.event.Event) -> Optional[int]:
        """Handle events, return clicked item index or None"""
        if not self.rect.collidepoint(pygame.mouse.get_pos()):
            return None
        
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - event.y * self.scroll_speed))
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                relative_y = event.pos[1] - self.rect.y + self.scroll_y
                item_index = relative_y // self.item_height
                if 0 <= item_index < len(self.items):
                    return item_index
        
        return None
    
    def draw(self, surface: pygame.Surface):
        """Draw scrollable list"""
        # Create a subsurface for clipping
        list_surface = surface.subsurface(self.rect)
        list_surface.fill(WHITE)
        
        # Draw items
        start_item = max(0, self.scroll_y // self.item_height)
        end_item = min(len(self.items), start_item + (self.rect.height // self.item_height) + 2)
        
        for i in range(start_item, end_item):
            item = self.items[i]
            y = i * self.item_height - self.scroll_y
            
            if y < -self.item_height or y > self.rect.height:
                continue
            
            # Draw item background
            item_rect = pygame.Rect(0, y, self.rect.width - 20, self.item_height)
            color = LIGHT_BLUE if item.selected else WHITE
            pygame.draw.rect(list_surface, color, item_rect)
            pygame.draw.rect(list_surface, GRAY, item_rect, 1)
            
            # Draw checkbox
            checkbox_rect = pygame.Rect(10, y + 20, 20, 20)
            pygame.draw.rect(list_surface, WHITE, checkbox_rect)
            pygame.draw.rect(list_surface, BLACK, checkbox_rect, 2)
            if item.selected:
                pygame.draw.line(list_surface, GREEN, 
                               (checkbox_rect.x + 3, checkbox_rect.y + 10),
                               (checkbox_rect.x + 8, checkbox_rect.y + 15), 3)
                pygame.draw.line(list_surface, GREEN,
                               (checkbox_rect.x + 8, checkbox_rect.y + 15),
                               (checkbox_rect.x + 17, checkbox_rect.y + 5), 3)
            
            # Draw title
            title = item.title
            if len(title) > 60:
                title = title[:57] + "..."
            title_surface = FONT_MEDIUM.render(title, True, BLACK)
            list_surface.blit(title_surface, (40, y + 5))
            
            # Draw duration and uploader
            info_text = f"{item.duration} • {item.uploader}"
            info_surface = FONT_SMALL.render(info_text, True, DARK_GRAY)
            list_surface.blit(info_surface, (40, y + 35))
        
        # Draw scrollbar
        if self.max_scroll > 0:
            scrollbar_height = max(20, int(self.rect.height * self.rect.height / (len(self.items) * self.item_height)))
            scrollbar_y = int(self.scroll_y / self.max_scroll * (self.rect.height - scrollbar_height))
            scrollbar_rect = pygame.Rect(self.rect.width - 15, scrollbar_y, 10, scrollbar_height)
            pygame.draw.rect(surface, GRAY, scrollbar_rect.move(self.rect.x, self.rect.y))

class YouTubeDownloader:
    """Main application class"""
    
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("YouTube Downloader with Video Background")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Video background
        self.video_bg = VideoBackground("background.mp4")  # Place your video file here
        
        # UI Elements
        self.url_input = InputField(50, 50, 600, 40, "Enter YouTube URL or Playlist URL...")
        self.fetch_button = Button(670, 50, 100, 40, "Fetch")
        self.download_button = Button(780, 50, 100, 40, "Download")
        self.cancel_button = Button(890, 50, 100, 40, "Cancel")
        self.play_bg_button = Button(1000, 50, 80, 40, "Play BG")
        self.stop_bg_button = Button(1090, 50, 80, 40, "Stop BG")
        
        # Volume slider
        self.volume_slider = Slider(50, 110, 200, 20)
        
        # Video list
        self.video_list = ScrollableList(50, 150, WINDOW_WIDTH - 100, WINDOW_HEIGHT - 250)
        
        # Status and progress
        self.status_text = "Ready"
        self.progress_text = ""
        self.videos: List[VideoInfo] = []
        
        # Threading
        self.fetch_thread: Optional[threading.Thread] = None
        self.download_thread: Optional[threading.Thread] = None
        self.cancel_download = threading.Event()
        self.message_queue = queue.Queue()
        
        # Download settings
        self.download_path = "downloads"
        os.makedirs(self.download_path, exist_ok=True)
    
    def fetch_video_info(self, url: str):
        """Fetch video information in background thread"""
        try:
            self.message_queue.put(("status", "Fetching video information..."))
            
            # Start with basic extraction to determine type
            ydl_opts_basic = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'socket_timeout': 30,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts_basic) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                except Exception as e:
                    self.message_queue.put(("status", f"Error fetching basic info: {str(e)}"))
                    return
                
                videos = []
                
                if 'entries' in info and info['entries']:  # Playlist
                    entries = [e for e in info['entries'] if e is not None][:20]  # Limit to 20 videos
                    self.message_queue.put(("status", f"Found playlist with {len(entries)} videos. Getting details..."))
                    
                    # Process each video individually with timeout
                    for i, entry in enumerate(entries):
                        try:
                            self.message_queue.put(("status", f"Processing video {i+1}/{len(entries)}..."))
                            
                            video_id = entry.get('id', f'unknown_{i}')
                            video_url = entry.get('url') or entry.get('webpage_url') or f"https://www.youtube.com/watch?v={video_id}"
                            
                            # Try to get more detailed info for this specific video
                            ydl_opts_single = {
                                'quiet': True,
                                'no_warnings': True,
                                'socket_timeout': 15,
                                'extract_flat': False,
                            }
                            
                            try:
                                with yt_dlp.YoutubeDL(ydl_opts_single) as ydl_single:
                                    single_info = ydl_single.extract_info(video_url, download=False)
                                    
                                    title = (single_info.get('title') or 
                                            entry.get('title') or 
                                            f"Video {i+1}")
                                    duration = self._format_duration(single_info.get('duration') or entry.get('duration') or 0)
                                    uploader = (single_info.get('uploader') or 
                                              single_info.get('channel') or 
                                              entry.get('uploader') or 
                                              'Unknown Channel')
                            except:
                                # Fall back to basic info if detailed extraction fails
                                title = entry.get('title') or f"Video {i+1}"
                                duration = self._format_duration(entry.get('duration') or 0)
                                uploader = entry.get('uploader') or 'Unknown Channel'
                            
                            video_info = VideoInfo(
                                id=video_id,
                                title=title,
                                duration=duration,
                                uploader=uploader,
                                url=video_url,
                                thumbnail=entry.get('thumbnail', '')
                            )
                            videos.append(video_info)
                            
                        except Exception as e:
                            print(f"Error processing video {i+1}: {e}")
                            continue
                    
                else:  # Single video
                    self.message_queue.put(("status", "Getting video details..."))
                    
                    # Try to get detailed info for single video
                    ydl_opts_detailed = {
                        'quiet': True,
                        'no_warnings': True,
                        'socket_timeout': 30,
                        'extract_flat': False,
                    }
                    
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts_detailed) as ydl_detailed:
                            detailed_info = ydl_detailed.extract_info(url, download=False)
                            
                            title = (detailed_info.get('title') or 
                                    info.get('title') or 
                                    'Untitled Video')
                            duration = self._format_duration(detailed_info.get('duration') or info.get('duration') or 0)
                            uploader = (detailed_info.get('uploader') or 
                                      detailed_info.get('channel') or 
                                      info.get('uploader') or 
                                      'Unknown Channel')
                            
                            video_info = VideoInfo(
                                id=detailed_info.get('id', info.get('id', 'unknown')),
                                title=title,
                                duration=duration,
                                uploader=uploader,
                                url=url,
                                thumbnail=detailed_info.get('thumbnail', info.get('thumbnail', ''))
                            )
                            videos.append(video_info)
                    except:
                        # Fall back to basic info if detailed extraction fails
                        title = info.get('title', 'Untitled Video')
                        duration = self._format_duration(info.get('duration', 0))
                        uploader = info.get('uploader', 'Unknown Channel')
                        
                        video_info = VideoInfo(
                            id=info.get('id', 'unknown'),
                            title=title,
                            duration=duration,
                            uploader=uploader,
                            url=url,
                            thumbnail=info.get('thumbnail', '')
                        )
                        videos.append(video_info)
                
                self.message_queue.put(("videos", videos))
                self.message_queue.put(("status", f"Successfully loaded {len(videos)} video(s)"))
                
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                self.message_queue.put(("status", "Error: Request timed out. Check your internet connection."))
            elif "unavailable" in error_msg.lower():
                self.message_queue.put(("status", "Error: Video is unavailable or private"))
            elif "not found" in error_msg.lower():
                self.message_queue.put(("status", "Error: Video or playlist not found"))
            else:
                self.message_queue.put(("status", f"Error: {error_msg}"))
    
    def download_videos(self, videos: List[VideoInfo]):
        """Download selected videos in background thread"""
        try:
            selected_videos = [v for v in videos if v.selected]
            if not selected_videos:
                self.message_queue.put(("status", "No videos selected"))
                return
            
            total_videos = len(selected_videos)
            self.message_queue.put(("status", f"Downloading {total_videos} video(s)..."))
            
            for i, video in enumerate(selected_videos):
                if self.cancel_download.is_set():
                    self.message_queue.put(("status", "Download cancelled"))
                    return
                
                self.message_queue.put(("progress", f"Downloading {i+1}/{total_videos}: {video.title[:50]}..."))
                
                ydl_opts = {
                    'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
                    'format': 'best[height<=720]',
                    'quiet': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video.url])
            
            self.message_queue.put(("status", f"Successfully downloaded {total_videos} video(s)"))
            self.message_queue.put(("progress", ""))
            
        except Exception as e:
            self.message_queue.put(("status", f"Download error: {str(e)}"))
            self.message_queue.put(("progress", ""))
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to MM:SS or HH:MM:SS"""
        if not seconds:
            return "0:00"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # Handle UI events
            self.url_input.handle_event(event)
            
            if self.fetch_button.handle_event(event):
                if self.url_input.text.strip():
                    if self.fetch_thread and self.fetch_thread.is_alive():
                        continue
                    self.fetch_thread = threading.Thread(
                        target=self.fetch_video_info, 
                        args=(self.url_input.text.strip(),),
                        daemon=True
                    )
                    self.fetch_thread.start()
            
            if self.download_button.handle_event(event):
                if self.videos and not (self.download_thread and self.download_thread.is_alive()):
                    self.cancel_download.clear()
                    self.download_thread = threading.Thread(
                        target=self.download_videos,
                        args=(self.videos,),
                        daemon=True
                    )
                    self.download_thread.start()
            
            if self.cancel_button.handle_event(event):
                self.cancel_download.set()
            
            if self.play_bg_button.handle_event(event):
                self.video_bg.start_playback()
            
            if self.stop_bg_button.handle_event(event):
                self.video_bg.stop_playback()
            
            # Handle volume slider
            if self.volume_slider.handle_event(event):
                self.video_bg.set_volume(self.volume_slider.value)
            
            # Handle video list clicks
            clicked_item = self.video_list.handle_event(event)
            if clicked_item is not None:
                self.videos[clicked_item].selected = not self.videos[clicked_item].selected
                self.video_list.set_items(self.videos)
    
    def update(self, dt: float):
        """Update application state"""
        self.url_input.update(dt)
        
        # Process messages from background threads
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                if msg_type == "status":
                    self.status_text = data
                elif msg_type == "progress":
                    self.progress_text = data
                elif msg_type == "videos":
                    self.videos = data
                    self.video_list.set_items(self.videos)
        except queue.Empty:
            pass
        
        # Update button states
        self.fetch_button.enabled = bool(self.url_input.text.strip())
        self.download_button.enabled = bool(self.videos) and not (self.download_thread and self.download_thread.is_alive())
        self.cancel_button.enabled = self.download_thread and self.download_thread.is_alive()
    
    def draw(self):
        """Draw everything"""
        # Draw video background
        bg_frame = self.video_bg.get_frame()
        if bg_frame:
            # Darken background for better text visibility
            dark_overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            dark_overlay.set_alpha(100)
            dark_overlay.fill(BLACK)
            
            self.screen.blit(bg_frame, (0, 0))
            self.screen.blit(dark_overlay, (0, 0))
        else:
            self.screen.fill(DARK_GRAY)
        
        # Draw UI elements
        self.url_input.draw(self.screen)
        self.fetch_button.draw(self.screen)
        self.download_button.draw(self.screen)
        self.cancel_button.draw(self.screen)
        self.play_bg_button.draw(self.screen)
        self.stop_bg_button.draw(self.screen)
        
        # Draw volume control
        volume_label = FONT_SMALL.render("Volume:", True, WHITE)
        self.screen.blit(volume_label, (260, 115))
        self.volume_slider.draw(self.screen)
        volume_text = FONT_SMALL.render(f"{int(self.volume_slider.value * 100)}%", True, WHITE)
        self.screen.blit(volume_text, (320, 115))
        
        # Draw video list
        self.video_list.draw(self.screen)
        
        # Draw status and progress
        status_surface = FONT_MEDIUM.render(f"Status: {self.status_text}", True, WHITE)
        self.screen.blit(status_surface, (50, WINDOW_HEIGHT - 80))
        
        if self.progress_text:
            progress_surface = FONT_SMALL.render(self.progress_text, True, ORANGE)
            self.screen.blit(progress_surface, (50, WINDOW_HEIGHT - 50))
        
        # Draw instructions
        if not self.videos:
            instructions = [
                "Instructions:",
                "1. Enter a YouTube video or playlist URL",
                "2. Click 'Fetch' to get video information",
                "3. Select videos you want to download",
                "4. Click 'Download' to start downloading",
                "5. Use 'Play BG'/'Stop BG' to control background video"
            ]
            
            for i, instruction in enumerate(instructions):
                color = WHITE if i == 0 else LIGHT_GRAY
                font = FONT_MEDIUM if i == 0 else FONT_SMALL
                text_surface = font.render(instruction, True, color)
                self.screen.blit(text_surface, (50, 200 + i * 25))
        
        pygame.display.flip()
    
    def run(self):
        """Main application loop"""
        last_time = time.time()
        
        while self.running:
            current_time = time.time()
            dt = (current_time - last_time) * 1000  # Convert to milliseconds
            last_time = current_time
            
            self.handle_events()
            self.update(dt)
            self.draw()
            
            self.clock.tick(FPS)
        
        # Cleanup
        self.cancel_download.set()
        if self.video_bg.cap:
            self.video_bg.cap.release()
        pygame.quit()

def main():
    """Main function"""
    print("YouTube Downloader with Video Background")
    print("========================================")
    print("Required packages: pygame, yt-dlp, opencv-python, moviepy")
    print("Place a video file named 'background.mp4' in the same directory for background video")
    print("Downloads will be saved to 'downloads' folder")
    print()
    
    app = YouTubeDownloader()
    app.run()

if __name__ == "__main__":
    main()
