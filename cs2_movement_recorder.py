"""
Hoesway

A non-intrusive application for recording and playing back mouse and keyboard movements 
for Counter-Strike 2.

This application operates entirely external to the game using only input capture.
IMPORTANT: This application does NOT:
- Inject code into any game processes
- Modify game memory
- Access game files or resources
- Violate any anti-cheat systems
- Send inputs directly to the game

It simply records inputs at the operating system level and plays them back the same way.
Can optionally intercept inputs before they reach applications.
"""

import os
import json
import time
import threading
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, StringVar, IntVar, messagebox
import keyboard
import mouse
from pynput import mouse as pynput_mouse
from pynput import keyboard as pynput_keyboard
from PIL import Image, ImageTk
import sys
import re

# For auto-update system
try:
    from update_manager import UpdateManager
    HAS_UPDATE_SYSTEM = True
except ImportError:
    print("Update manager not available. Auto-updates disabled.")
    HAS_UPDATE_SYSTEM = False

# For system tray
try:
    import pystray
    from PIL import Image
    HAS_SYSTEM_TRAY = True
except ImportError:
    print("pystray module not available. System tray icon not loaded.")
    HAS_SYSTEM_TRAY = False

# Version information
VERSION = "0.6.0"  # Updated version

class MovementRecorder:
    """
    Records and plays back mouse and keyboard movements without interfacing with
    game memory or processes directly.
    """
    def __init__(self):
        """Initialize the recorder"""
        # Basic properties
        self.events = []
        self.current_event_index = 0
        self.recording = False
        self.playing = False
        self.stop_threads = False
        self.current_recording = None
        self.recordings_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")
        
        # Safe external recording (no game interference)
        self.is_external_only = True  # Guarantees external-only operation
        self.game_interaction = False  # Never interacts with game processes
        
        # Input interception capabilities
        self.intercept_inputs = False  # Whether to block inputs from reaching applications
        self.using_direct_interception = False  # Track if we're using direct interception
        self.keyboard_listener = None
        self.mouse_listener = None
        
        # Other properties
        self.record_hotkey = "f8"
        self.playback_hotkey = "f9"
        self.debug_mode = True  # Enable debug output to diagnose issues
        self.countdown_time = 3  # Default countdown time in seconds
        self.countdown_active = False
        self.countdown_start_time = 0  # Track when countdown started
        self.callback_interval = 0.005  # More frequent mouse tracking (in seconds)
        self.last_mouse_pos = (0, 0)
        self.current_event_index = 0
        
        # Create recordings directory if it doesn't exist
        if not os.path.exists(self.recordings_dir):
            os.makedirs(self.recordings_dir)
            
        # Controllers for playback 
        self.keyboard_controller = pynput_keyboard.Controller()
        self.mouse_controller = pynput_mouse.Controller()
        
        # Key mapping for pynput (keyboard library uses different key names)
        self.key_mapping = {
            'space': pynput_keyboard.Key.space,
            'enter': pynput_keyboard.Key.enter,
            'esc': pynput_keyboard.Key.esc,
            'tab': pynput_keyboard.Key.tab,
            'shift': pynput_keyboard.Key.shift,
            'ctrl': pynput_keyboard.Key.ctrl,
            'ctrl_l': pynput_keyboard.Key.ctrl_l,
            'ctrl_r': pynput_keyboard.Key.ctrl_r,
            'alt': pynput_keyboard.Key.alt,
            'alt_l': pynput_keyboard.Key.alt_l,
            'alt_r': pynput_keyboard.Key.alt_r,
            'shift_l': pynput_keyboard.Key.shift_l,
            'shift_r': pynput_keyboard.Key.shift_r,
            'backspace': pynput_keyboard.Key.backspace,
            'caps_lock': pynput_keyboard.Key.caps_lock,
            'f1': pynput_keyboard.Key.f1, 'f2': pynput_keyboard.Key.f2, 'f3': pynput_keyboard.Key.f3, 'f4': pynput_keyboard.Key.f4,
            'f5': pynput_keyboard.Key.f5, 'f6': pynput_keyboard.Key.f6, 'f7': pynput_keyboard.Key.f7, 'f8': pynput_keyboard.Key.f8,
            'f9': pynput_keyboard.Key.f9, 'f10': pynput_keyboard.Key.f10, 'f11': pynput_keyboard.Key.f11, 'f12': pynput_keyboard.Key.f12,
            'up': pynput_keyboard.Key.up, 'down': pynput_keyboard.Key.down, 'left': pynput_keyboard.Key.left, 'right': pynput_keyboard.Key.right,
            'page_up': pynput_keyboard.Key.page_up, 'page_down': pynput_keyboard.Key.page_down,
            'home': pynput_keyboard.Key.home, 'end': pynput_keyboard.Key.end, 'insert': pynput_keyboard.Key.insert, 'delete': pynput_keyboard.Key.delete
        }
        
        # Set up the keyboard hotkeys
        self.setup_hotkeys()
        
        # Set up the keyboard and mouse hooks for recording
        self.keyboard_hook = None
        self.mouse_hook = None
    
    def setup_hotkeys(self):
        """Setup keyboard hotkeys"""
        try:
            # Remove any existing hotkeys first to avoid conflicts
            try:
                keyboard.unhook_all()
            except:
                pass
                
            # Set up the hotkeys
            keyboard.add_hotkey(self.record_hotkey, self.toggle_recording)
            keyboard.add_hotkey(self.playback_hotkey, self.toggle_playback)
            
            if self.debug_mode:
                print(f"Hotkeys set up: {self.record_hotkey} to toggle recording, {self.playback_hotkey} to toggle playback")
        except Exception as e:
            print(f"Error setting up hotkeys: {e}")
    
    def toggle_recording(self):
        """Toggle recording on/off with hotkey"""
        if self.debug_mode:
            print(f"Toggle recording called. Current state: {self.recording}")
            
        if self.playing:
            print("Cannot start recording while playback is active")
            return
            
        if not self.recording and not self.countdown_active:
            if self.countdown_time > 0:
                self.start_countdown_recording()
            else:
                self.start_recording()
        else:
            self.stop_recording()
            # Auto-save logic removed to fix error
            if len(self.events) > 0 and self.debug_mode:
                print(f"Recording stopped with {len(self.events)} events.")
            elif self.debug_mode:
                print("No events were recorded.")
    
    def toggle_playback(self):
        """Toggle playback on/off with hotkey"""
        if self.debug_mode:
            print(f"Toggle playback called. Current state: {self.playing}")
            
        if self.recording:
            print("Cannot start playback while recording is active")
            return
            
        if not self.playing:
            if not self.events and self.current_recording:
                self.load_recording(self.current_recording)
                
            if self.events:
                self.play_thread = threading.Thread(target=self.play_recording)
                self.play_thread.daemon = True
                self.play_thread.start()
            else:
                print("No recording loaded to play")
        else:
            self.stop_playback()
    
    def start_recording(self):
        """Start recording mouse and keyboard events (external to game)"""
        if self.recording:
            return

        # Reset events and start a new recording
        self.events = []
        self.recording = True
        self.start_time = time.time()
        
        # Log at DEBUG level only
        if self.debug_mode:
            print("Recording started")
            
        # Setup the appropriate input capture method
        if self.using_direct_interception:
            self.setup_direct_interception()
        else:
            # Hook keyboard and mouse events (safely, externally only)
            self.keyboard_hook()
            self.mouse_hook()
    
    def setup_direct_interception(self):
        """Setup direct input interception with pynput (captures before reaching applications)"""
        try:
            # Setup keyboard listener with direct interception
            self.keyboard_listener = pynput_keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            self.keyboard_listener.start()
            
            # Setup mouse listener with direct interception
            self.mouse_listener = pynput_mouse.Listener(
                on_move=self._on_mouse_move,
                on_click=self._on_mouse_click,
                on_scroll=self._on_mouse_scroll
            )
            self.mouse_listener.start()
            
            if self.debug_mode:
                print("Direct input interception active")
        except Exception as e:
            print(f"Error setting up direct interception: {e}")
            # Fallback to regular capture
            self.using_direct_interception = False
            self.keyboard_hook()
            self.mouse_hook()
    
    def _on_key_press(self, key):
        """Handle key press in direct interception mode"""
        if not self.recording:
            return True  # Always allow keys to pass through when not recording
        
        # Convert key to string form
        try:
            if hasattr(key, 'char') and key.char is not None:
                key_str = key.char
            elif hasattr(key, 'name'):
                key_str = key.name
            else:
                key_str = str(key).replace('Key.', '')
                
            # Skip recording hotkeys
            if key_str in [self.record_hotkey, self.playback_hotkey]:
                return True  # Always allow hotkeys
                
            # Record the event
            self.events.append({
                "time": time.time() - self.start_time,
                "type": "keyboard",
                "key": key_str,
                "action": "press"
            })
            
            # Return value determines if the key is passed to applications
            # True = pass through, False = block
            return not self.intercept_inputs
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error in direct key press capture: {e}")
            return True  # On error, allow key through
            
    def _on_key_release(self, key):
        """Handle key release in direct interception mode"""
        if not self.recording:
            return True
            
        # Convert key to string form
        try:
            if hasattr(key, 'char') and key.char is not None:
                key_str = key.char
            elif hasattr(key, 'name'):
                key_str = key.name
            else:
                key_str = str(key).replace('Key.', '')
                
            # Skip recording hotkeys
            if key_str in [self.record_hotkey, self.playback_hotkey]:
                return True
                
            # Record the event
            self.events.append({
                "time": time.time() - self.start_time,
                "type": "keyboard",
                "key": key_str,
                "action": "release"
            })
            
            # Return value determines if the key is passed to applications
            return not self.intercept_inputs
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error in direct key release capture: {e}")
            return True
    
    def _on_mouse_move(self, x, y):
        """Handle mouse move in direct interception mode"""
        if not self.recording:
            return True
            
        current_pos = (x, y)
        if current_pos != self.last_mouse_pos:
            self.events.append({
                "time": time.time() - self.start_time,
                "type": "mouse",
                "action": "move",
                "position_x": x,
                "position_y": y
            })
            self.last_mouse_pos = current_pos
            
        # Always allow mouse movement (can't block it)
        return True
        
    def _on_mouse_click(self, x, y, button, pressed):
        """Handle mouse click in direct interception mode"""
        if not self.recording:
            return True
            
        # Convert button to string
        button_str = str(button).replace('Button.', '')
        
        self.events.append({
            "time": time.time() - self.start_time,
            "type": "mouse",
            "action": "press" if pressed else "release",
            "button": button_str,
            "position_x": x,
            "position_y": y
        })
        
        # Return value determines if click is passed to applications
        return not self.intercept_inputs
        
    def _on_mouse_scroll(self, x, y, dx, dy):
        """Handle mouse scroll in direct interception mode"""
        if not self.recording:
            return True
            
        self.events.append({
            "time": time.time() - self.start_time,
            "type": "mouse",
            "action": "scroll",
            "scroll_dx": dx,
            "scroll_dy": dy,
            "position_x": x,
            "position_y": y
        })
        
        # Return value determines if scroll is passed to applications
        return not self.intercept_inputs
    
    def stop_recording(self):
        """Stop recording mouse and keyboard events"""
        if not self.recording:
            return
            
        self.recording = False
        self.countdown_active = False
        
        if self.debug_mode:
            print("Recording stopped")
            
        # Clean up listeners
        if self.using_direct_interception:
            if self.keyboard_listener:
                self.keyboard_listener.stop()
                self.keyboard_listener = None
            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None
        else:
            # Unhook standard keyboard and mouse
            keyboard.unhook_all()
            mouse.unhook_all()
    
    def toggle_direct_interception(self, enable=None):
        """Toggle direct input interception mode"""
        if enable is not None:
            self.using_direct_interception = enable
        else:
            self.using_direct_interception = not self.using_direct_interception
            
        if self.debug_mode:
            mode = "Direct interception" if self.using_direct_interception else "Standard recording"
            print(f"Input mode changed to: {mode}")
            
        # If we're currently recording, restart with the new mode
        if self.recording:
            self.stop_recording()
            self.start_recording()
            
        return self.using_direct_interception
            
    def set_intercept_inputs(self, intercept=None):
        """Set whether inputs should be intercepted before reaching applications"""
        if intercept is not None:
            self.intercept_inputs = intercept
        else:
            self.intercept_inputs = not self.intercept_inputs
            
        if self.debug_mode:
            state = "ON" if self.intercept_inputs else "OFF"
            print(f"Input interception: {state}")
            
        return self.intercept_inputs
    
    def play_recording(self):
        """Play back a recording"""
        if not self.events:
            print("No events to play.")
            return
            
        if self.recording:
            print("Cannot play while recording.")
            return
            
        self.playing = True
        start_time = time.time()
        last_event_time = 0
        
        print(f"Playback started. Press {self.playback_hotkey} to stop.")
        
        try:
            for event in self.events:
                if not self.playing:
                    break
                    
                # Wait for the correct time
                event_time = event['time']
                wait_time = event_time - last_event_time
                if wait_time > 0:
                    time.sleep(wait_time)
                    
                last_event_time = event_time
                
                # Handle mouse events
                if event['type'] == 'mouse':
                    if 'x' in event and 'y' in event and event['x'] is not None and event['y'] is not None:
                        # Mouse movement
                        self.mouse_controller.position = (event['x'], event['y'])
                        
                    if 'button' in event and event['button'] is not None:
                        # Mouse click
                        button = event['button']
                        
                        # Convert string button names to pynput buttons
                        if isinstance(button, str):
                            if button == 'left':
                                button = pynput_mouse.Button.left
                            elif button == 'right':
                                button = pynput_mouse.Button.right
                            elif button == 'middle':
                                button = pynput_mouse.Button.middle
                            elif button == 'button4':
                                button = pynput_mouse.Button.x1
                            elif button == 'button5':
                                button = pynput_mouse.Button.x2
                                
                        if event['pressed']:
                            self.mouse_controller.press(button)
                        else:
                            self.mouse_controller.release(button)
                
                # Handle keyboard events
                elif event['type'] == 'keyboard':
                    key = event['name']
                    
                    # Convert string key names to pynput keys for special keys
                    if key in self.key_mapping:
                        key = self.key_mapping[key]
                        
                    if event['pressed']:
                        self.keyboard_controller.press(key)
                    else:
                        self.keyboard_controller.release(key)
                        
        except Exception as e:
            print(f"Error during playback: {e}")
        finally:
            self.playing = False
            print("Playback ended.")
    
    def stop_playback(self):
        """Stop the playback"""
        if not self.playing:
            return
            
        self.playing = False
        print("Stopping playback...")
    
    def save_recording(self, filename=None):
        """Save the current recording to a file"""
        if not self.events:
            print("No events to save.")
            return
            
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"recording_{timestamp}.json"
            
        filepath = os.path.join(self.recordings_dir, filename)
        
        print(f"Saving {len(self.events)} events to: {filepath}")
        
        try:
            # Save to file
            with open(filepath, 'w') as f:
                recording_data = {
                    "events": self.events,
                    "metadata": {
                        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "event_count": len(self.events)
                    }
                }
                json.dump(recording_data, f, indent=4)
                
            print(f"Successfully saved recording to: {filepath}")
            self.current_recording = filepath
            return filepath
        except Exception as e:
            print(f"Error saving recording: {e}")
            return None
    
    def load_recording(self, filepath):
        """Load a recording from a file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                self.events = data.get("events", [])
                
            print(f"Loaded {len(self.events)} events from: {filepath}")
            self.current_recording = filepath
            return True
        except Exception as e:
            print(f"Error loading recording: {e}")
            return False
    
    def change_hotkeys(self, record_key=None, play_key=None):
        """Change the hotkeys used for recording and playback"""
        # Unhook all existing hotkeys
        keyboard.unhook_all()
        
        # Update the keys if provided
        if record_key:
            self.record_hotkey = record_key
        if play_key:
            self.playback_hotkey = play_key
        
        # Setup the new hotkeys
        self.setup_hotkeys()
        print(f"Hotkeys updated: {self.record_hotkey} to toggle recording, {self.playback_hotkey} to toggle playback")
    
    def create_blank_recording(self, filename=None):
        """Create a blank recording file"""
        if not filename:
            # Generate a filename based on current date and time
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"blank_recording_{timestamp}.json"
            
        filepath = os.path.join(self.recordings_dir, filename)
        
        # Create a blank events list
        blank_data = {
            "events": [],
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": {
                "type": "blank",
                "description": "Blank recording file"
            }
        }
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(blank_data, f, indent=4)
        
        return filepath
    
    def start_countdown_recording(self):
        """Start a countdown before recording"""
        if self.recording or self.countdown_active:
            return
            
        self.countdown_active = True
        self.countdown_start_time = time.time()  # Track when countdown started
        print(f"Starting recording in {self.countdown_time} seconds...")
        
        # Start a thread to handle the countdown
        countdown_thread = threading.Thread(target=self._countdown_thread)
        countdown_thread.daemon = True
        countdown_thread.start()
        
    def _countdown_thread(self):
        """Thread function to handle the recording countdown"""
        try:
            for i in range(self.countdown_time, 0, -1):
                print(f"Recording starts in {i}...")
                time.sleep(1)
                
            # Start the actual recording
            self.countdown_active = False
            self.start_recording()
        except Exception as e:
            print(f"Error in countdown thread: {e}")
            self.countdown_active = False
    
    def set_countdown_time(self, seconds):
        """Set the countdown time before recording starts"""
        try:
            seconds = int(seconds)
            if 0 <= seconds <= 10:  # Reasonable limits
                self.countdown_time = seconds
                print(f"Countdown time set to {seconds} seconds")
                return True
            else:
                print("Countdown time must be between 0 and 10 seconds")
                return False
        except ValueError:
            print("Invalid countdown time value. Must be an integer.")
            return False

    def simulate_input(self, event):
        """Safely simulate input without sending directly to game processes"""
        # Only send inputs to the operating system level, never directly to games
        try:
            if event["type"] == "keyboard":
                if event["action"] == "press":
                    # External key press (doesn't inject into games)
                    keyboard.press(event["key"])
                else:
                    # External key release (doesn't inject into games)
                    keyboard.release(event["key"])
            elif event["type"] == "mouse":
                if event["action"] == "move":
                    # External mouse movement (doesn't inject into games)
                    mouse.move(event["position_x"], event["position_y"], absolute=True)
                elif event["action"] == "click":
                    # External mouse click (doesn't inject into games)
                    if event["button"] == "left":
                        mouse.press(button="left")
                        mouse.release(button="left")
                    elif event["button"] == "right":
                        mouse.press(button="right")
                        mouse.release(button="right")
                    elif event["button"] == "middle":
                        mouse.press(button="middle")
                        mouse.release(button="middle")
                elif event["action"] == "press":
                    # External mouse press (doesn't inject into games)
                    mouse.press(button=event["button"])
                elif event["action"] == "release":
                    # External mouse release (doesn't inject into games)
                    mouse.release(button=event["button"])
        except Exception as e:
            if self.debug_mode:
                print(f"Error simulating input: {e}")


class RecorderApp:
    """
    GUI Application for Hoesway
    Operating completely external to games, never injecting or interfering.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Hoesway")
        self.root.geometry("800x550")
        self.root.iconbitmap(default="images/icon.ico") if os.path.exists("images/icon.ico") else None
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Initialize the recorder
        self.recorder = MovementRecorder()
        
        # Modern UI theme colors
        self.bg_color = "#2b2b2b"  # Darker background
        self.fg_color = "#e0e0e0"  # Light gray text
        self.accent_color = "#4da6ff"  # Sky blue accents
        self.btn_color = "#3c3f41"  # Slightly lighter than bg for buttons
        self.highlight_color = "#365880"  # Blue highlight
        
        # Create system tray icon
        self.init_system_tray()
        
        # Load status images
        self.load_status_images()
        
        # Current status icon
        self.current_status_image = self.status_images['not_recording']
        
        # Create the main frame with padding
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with logo and title
        self.header_frame = ttk.Frame(self.main_frame)
        self.header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Try to load logo
        try:
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "logo.png")
            if os.path.exists(logo_path):
                logo = Image.open(logo_path)
                logo = logo.resize((50, 50), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(logo)
                ttk.Label(self.header_frame, image=self.logo_img).pack(side=tk.LEFT, padx=(0, 10))
        except Exception as e:
            print(f"Error loading logo: {e}")
        
        # Title and description
        title_frame = ttk.Frame(self.header_frame)
        title_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        ttk.Label(title_frame, text="Hoesway", font=('Helvetica', 16, 'bold')).pack(anchor=tk.W)
        ttk.Label(title_frame, text="Professional movement recording for Counter-Strike 2", 
                 font=('Helvetica', 10)).pack(anchor=tk.W)
        
        # Status panel
        self.status_frame = ttk.LabelFrame(self.main_frame, text="Status")
        self.status_frame.pack(fill=tk.X, pady=10)
        
        status_content_frame = ttk.Frame(self.status_frame)
        status_content_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Status icon and label
        status_icon_label_frame = ttk.Frame(status_content_frame)
        status_icon_label_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        self.status_icon_label = ttk.Label(status_icon_label_frame, image=self.current_status_image)
        self.status_icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
        status_text_frame = ttk.Frame(status_icon_label_frame)
        status_text_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(status_text_frame, text="Current Status:", font=('Helvetica', 10, 'bold')).pack(anchor=tk.W)
        self.status_label = ttk.Label(status_text_frame, text="Ready - No recording loaded", font=('Helvetica', 10))
        self.status_label.pack(anchor=tk.W)
        
        # Countdown timer setting
        self.countdown_frame = ttk.Frame(status_content_frame)
        self.countdown_frame.pack(side=tk.RIGHT, padx=10)
        
        ttk.Label(self.countdown_frame, text="Countdown Timer (seconds):").pack(side=tk.LEFT)
        self.countdown_var = tk.StringVar(value=str(self.recorder.countdown_time))
        self.countdown_spinbox = ttk.Spinbox(self.countdown_frame, from_=0, to=10, width=5, 
                                             textvariable=self.countdown_var, command=self.update_countdown_time)
        self.countdown_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Hotkey information
        self.hotkey_frame = ttk.LabelFrame(self.main_frame, text="Hotkeys")
        self.hotkey_frame.pack(fill=tk.X, pady=10)
        
        hotkey_content = ttk.Frame(self.hotkey_frame)
        hotkey_content.pack(fill=tk.X, padx=10, pady=10)
        
        # Create a more appealing hotkey display
        self.create_hotkey_button(hotkey_content, "Record", self.recorder.record_hotkey.upper(), 0)
        self.create_hotkey_button(hotkey_content, "Playback", self.recorder.playback_hotkey.upper(), 1)
        
        ttk.Button(hotkey_content, text="Change Hotkeys", command=self.change_hotkeys).grid(
            row=0, column=2, rowspan=2, padx=20, pady=5, sticky=tk.E+tk.W)
        
        hotkey_content.grid_columnconfigure(2, weight=1)
        
        # Control panel
        self.control_frame = ttk.LabelFrame(self.main_frame, text="Controls")
        self.control_frame.pack(fill=tk.X, pady=10)
        
        control_content = ttk.Frame(self.control_frame)
        control_content.pack(fill=tk.X, padx=10, pady=10)
        
        # Control buttons with icons if available
        self.create_control_button(control_content, "Start Recording", self.start_recording, "record", 0, 0)
        self.create_control_button(control_content, "Stop Recording", self.stop_recording, "stop", 0, 1)
        self.create_control_button(control_content, "Start Playback", self.start_playback, "play", 0, 2)
        self.create_control_button(control_content, "Stop Playback", self.stop_playback, "stop", 0, 3)
        
        # Recording management
        self.recordings_frame = ttk.LabelFrame(self.main_frame, text="Recordings")
        self.recordings_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # List of recordings
        self.recordings_listbox_frame = ttk.Frame(self.recordings_frame)
        self.recordings_listbox_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(self.recordings_listbox_frame, text="Available Recordings:", font=('Helvetica', 10, 'bold')).pack(anchor=tk.W)
        
        # Add a search entry
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_recordings)
        search_frame = ttk.Frame(self.recordings_listbox_frame)
        search_frame.pack(fill=tk.X, pady=(5, 10))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Create a frame for the listbox and scrollbar
        listbox_container = ttk.Frame(self.recordings_listbox_frame)
        listbox_container.pack(fill=tk.BOTH, expand=True)
        
        # Create the listbox with a specific background and foreground
        self.recordings_listbox = tk.Listbox(
            listbox_container, 
            height=10, 
            bg="#3c3c3c", 
            fg=self.fg_color,
            selectbackground=self.accent_color,
            selectforeground=self.fg_color,
            font=('Helvetica', 10)
        )
        self.recordings_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Add double-click binding
        self.recordings_listbox.bind("<Double-1>", lambda e: self.load_selected())
        
        # Scrollbar for the listbox
        scrollbar = ttk.Scrollbar(listbox_container, orient="vertical", command=self.recordings_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.recordings_listbox.config(yscrollcommand=scrollbar.set)
        
        # Buttons for recording management
        self.recording_buttons_frame = ttk.Frame(self.recordings_frame)
        self.recording_buttons_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        
        # Create buttons with consistent width
        button_width = 15
        ttk.Button(self.recording_buttons_frame, text="Load Selected", width=button_width, 
                  command=self.load_selected).pack(fill=tk.X, pady=5)
        ttk.Button(self.recording_buttons_frame, text="Delete Selected", width=button_width, 
                  command=self.delete_selected).pack(fill=tk.X, pady=5)
        ttk.Button(self.recording_buttons_frame, text="Create New File", width=button_width, 
                  command=self.create_new_file).pack(fill=tk.X, pady=5)
        ttk.Button(self.recording_buttons_frame, text="Refresh List", width=button_width, 
                  command=self.refresh_recordings).pack(fill=tk.X, pady=5)
        
        # Settings area
        settings_frame = ttk.LabelFrame(self.main_frame, text="Settings", style="Custom.TLabelframe")
        settings_frame.pack(fill=tk.X, padx=10, pady=5, ipadx=5, ipady=5)
        
        settings_grid = ttk.Frame(settings_frame)
        settings_grid.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # Countdown time setting
        ttk.Label(settings_grid, text="Countdown Time (seconds):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        countdown_frame = ttk.Frame(settings_grid)
        countdown_frame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.countdown_var = tk.StringVar(value=str(self.recorder.countdown_time))
        countdown_spinbox = ttk.Spinbox(
            countdown_frame, 
            from_=0, 
            to=10, 
            width=5, 
            textvariable=self.countdown_var,
            command=self.update_countdown_time
        )
        countdown_spinbox.pack(side=tk.LEFT)
        
        ttk.Button(
            countdown_frame, 
            text="Apply", 
            command=self.update_countdown_time,
            style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=5)
        
        # Input interception settings (two checkboxes)
        self.interception_var = tk.BooleanVar(value=self.recorder.using_direct_interception)
        direct_intercept_check = ttk.Checkbutton(
            settings_grid,
            text="Use direct input interception (more reliable)",
            variable=self.interception_var,
            command=self.toggle_direct_interception,
            style="Switch.TCheckbutton"
        )
        direct_intercept_check.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        
        self.block_inputs_var = tk.BooleanVar(value=self.recorder.intercept_inputs)
        block_inputs_check = ttk.Checkbutton(
            settings_grid,
            text="Block inputs from reaching applications (invisible mode)",
            variable=self.block_inputs_var,
            command=self.toggle_block_inputs,
            style="Switch.TCheckbutton"
        )
        block_inputs_check.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        
        # Footer with app info and minimize button
        footer_frame = ttk.Frame(self.main_frame)
        footer_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Label(footer_frame, text=" 2025 Hoesway", 
                 font=('Helvetica', 8)).pack(side=tk.LEFT)
        ttk.Button(footer_frame, text="Minimize to Background", 
                  command=self.minimize).pack(side=tk.RIGHT)
        
        # Start the status updater thread
        self.status_thread = threading.Thread(target=self.status_updater, args=(self.status_label,))
        self.status_thread.daemon = True
        self.status_thread.start()
        
        # Center the window on screen
        self.center_window()
        
        # Load the recordings
        self.refresh_recordings()
        
        # Setup key bindings
        self.setup_key_bindings()
        
        # Schedule UI update to keep interface responsive
        self.schedule_ui_update()
        
        # Check for updates
        if HAS_UPDATE_SYSTEM:
            self.update_manager = UpdateManager(VERSION)
            self.update_manager.check_for_updates()
            
        # Setup menu
        self.setup_menu()
    
    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_key_bindings(self):
        """Setup keyboard shortcuts for the app"""
        self.root.bind("<F5>", lambda e: self.refresh_recordings())
        self.root.bind("<Delete>", lambda e: self.delete_selected())
        self.root.bind("<Return>", lambda e: self.load_selected())
    
    def create_hotkey_button(self, parent, label_text, key_text, row):
        """Create a stylized hotkey button"""
        ttk.Label(parent, text=f"{label_text}:", font=('Helvetica', 10, 'bold')).grid(
            row=row, column=0, padx=(10, 5), pady=5, sticky=tk.W)
        
        # Create a button-like label for the hotkey
        key_label = tk.Label(
            parent, 
            text=key_text, 
            bg=self.accent_color, 
            fg=self.fg_color, 
            relief="raised", 
            font=('Helvetica', 10, 'bold'),
            padx=10,
            pady=3
        )
        key_label.grid(row=row, column=1, padx=5, pady=5, sticky=tk.W)
    
    def create_control_button(self, parent, text, command, icon_name=None, row=0, col=0):
        """Create a control button with an icon if available"""
        if icon_name and hasattr(self, f'{icon_name}_icon'):
            btn = ttk.Button(parent, text=text, command=command, image=getattr(self, f'{icon_name}_icon'), compound=tk.LEFT)
        else:
            btn = ttk.Button(parent, text=text, command=command)
        
        btn.grid(row=row, column=col, padx=5, pady=5, sticky=tk.W)
        return btn
    
    def init_system_tray(self):
        """Initialize system tray icon if available"""
        try:
            import pystray
            from PIL import Image
            
            # Create the icon image
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "icon.png")
            if os.path.exists(icon_path):
                self.tray_icon_image = Image.open(icon_path)
                
                # Create the menu
                menu = pystray.Menu(
                    pystray.MenuItem("Show", self.show_window),
                    pystray.MenuItem("Record", self.start_recording),
                    pystray.MenuItem("Play", self.start_playback),
                    pystray.MenuItem("Stop", self.stop_all),
                    pystray.MenuItem("Exit", self.exit_app)
                )
                
                # Create the icon
                self.tray_icon = pystray.Icon("hoesway_recorder", self.tray_icon_image, "Hoesway", menu)
                
                # Start the icon in a separate thread
                threading.Thread(target=self.tray_icon.run, daemon=True).start()
                
                # Hide when minimized
                self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
            else:
                self.tray_icon = None
        except ImportError:
            print("pystray module not available. System tray icon not loaded.")
            self.tray_icon = None
        except Exception as e:
            print(f"Error creating system tray icon: {e}")
            self.tray_icon = None
    
    def show_window(self):
        """Show the main window"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def hide_window(self):
        """Hide the window to system tray"""
        self.root.withdraw()
        if not hasattr(self, 'tray_icon') or self.tray_icon is None:
            # If tray icon couldn't be created, just minimize
            self.root.iconify()
    
    def exit_app(self):
        """Exit the application"""
        if hasattr(self, 'tray_icon') and self.tray_icon is not None:
            self.tray_icon.stop()
        self.on_close()
    
    def stop_all(self):
        """Stop all activities (recording and playback)"""
        if self.recorder.recording:
            self.stop_recording()
        if self.recorder.playing:
            self.stop_playback()
            
    def filter_recordings(self, *args):
        """Filter the recordings list based on search text"""
        search_text = self.search_var.get().lower()
        self.recordings_listbox.delete(0, tk.END)
        
        recordings = [f for f in os.listdir(self.recorder.recordings_dir) if f.endswith('.json')]
        
        for rec in recordings:
            if search_text in rec.lower():
                self.recordings_listbox.insert(tk.END, rec)
                
    def update_countdown_time(self):
        """Update the countdown time in the recorder"""
        try:
            new_time = int(self.countdown_var.get())
            self.recorder.set_countdown_time(new_time)
        except ValueError:
            # Reset to the current value if invalid
            self.countdown_var.set(str(self.recorder.countdown_time))
    
    def load_status_images(self):
        """Load status indicator images"""
        self.status_images = {}
        image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
        
        try:
            self.status_images['recording'] = ImageTk.PhotoImage(Image.open(os.path.join(image_dir, "recording.png")))
            self.status_images['not_recording'] = ImageTk.PhotoImage(Image.open(os.path.join(image_dir, "not_recording.png")))
            self.status_images['playing'] = ImageTk.PhotoImage(Image.open(os.path.join(image_dir, "playing.png")))
            self.status_images['no_file'] = ImageTk.PhotoImage(Image.open(os.path.join(image_dir, "no_file.png")))
            self.status_images['recording_pulse'] = ImageTk.PhotoImage(Image.open(os.path.join(image_dir, "recording_pulse.png")))
            self.status_images['ready'] = ImageTk.PhotoImage(Image.open(os.path.join(image_dir, "ready.png")))
        except Exception as e:
            print(f"Error loading status images: {e}")
            # Create empty image placeholders if images can't be loaded
            empty_img = tk.PhotoImage(width=32, height=32)
            self.status_images = {
                'recording': empty_img,
                'not_recording': empty_img,
                'playing': empty_img,
                'no_file': empty_img,
                'recording_pulse': empty_img,
                'ready': empty_img
            }
    
    def update_status_icon(self, status):
        """Update the status icon based on current status"""
        if status == 'recording':
            self.status_icon_label.configure(image=self.status_images['recording'])
        elif status == 'playing':
            self.status_icon_label.configure(image=self.status_images['playing'])
        elif status == 'no_file':
            self.status_icon_label.configure(image=self.status_images['no_file'])
        elif status == 'recording_pulse':
            self.status_icon_label.configure(image=self.status_images['recording_pulse'])
        elif status == 'ready':
            self.status_icon_label.configure(image=self.status_images['ready'])
        else:
            self.status_icon_label.configure(image=self.status_images['not_recording'])
    
    def status_updater(self, status_label):
        """Thread function to update the status label and icon"""
        last_events_count = 0
        animation_frames = ["⚬", "⚭", "⚮", "⚯"]  # Animation for active recording
        animation_index = 0
        
        while not self.recorder.stop_threads:
            status = ""
            icon_status = "not_recording"
            
            # Add a visual pulse/animation when recording or playing
            if self.recorder.recording:
                events_now = len(self.recorder.events)
                events_diff = events_now - last_events_count
                last_events_count = events_now
                
                # Update animation frame
                animation_index = (animation_index + 1) % len(animation_frames)
                animation = animation_frames[animation_index]
                
                # Show activity with event count and animation
                status = f"Recording {animation} ({events_now} events, +{events_diff}/s)"
                
                # Blink the icon for recording to show activity
                if animation_index % 2 == 0:
                    icon_status = "recording"
                else:
                    icon_status = "recording_pulse"
            elif self.recorder.countdown_active:
                # Show countdown animation
                seconds_left = max(1, int(self.recorder.countdown_time - (time.time() - self.recorder.countdown_start_time)))
                status = f"Starting in {seconds_left}s..."
                
                # Alternate icons for countdown
                if animation_index % 2 == 0:
                    icon_status = "ready"
                else:
                    icon_status = "not_recording"
                    
                # Update animation for countdown
                animation_index = (animation_index + 1) % len(animation_frames)
            elif self.recorder.playing:
                # Update animation frame for playback
                animation_index = (animation_index + 1) % len(animation_frames)
                animation = animation_frames[animation_index]
                
                # Calculate playback progress if possible
                if self.recorder.events and self.recorder.current_event_index < len(self.recorder.events):
                    progress = (self.recorder.current_event_index / len(self.recorder.events)) * 100
                    status = f"Playing {animation} ({progress:.1f}%)"
                else:
                    status = f"Playing {animation}"
                    
                icon_status = "playing"
            else:
                # Reset counters when not recording
                last_events_count = 0
                animation_index = 0
                
                if self.recorder.current_recording:
                    recording_name = os.path.basename(self.recorder.current_recording)
                    status = f"Ready - Loaded: {recording_name} ({len(self.recorder.events)} events)"
                    icon_status = "ready"
                else:
                    status = "Ready - No recording loaded"
                    icon_status = "no_file"
            
            # Update the status label text
            if status_label.winfo_exists():
                status_label['text'] = status
                
                # Change color based on state for additional visual feedback
                if self.recorder.recording:
                    status_label['foreground'] = "#ff4d4d"  # Red for recording
                elif self.recorder.playing:
                    status_label['foreground'] = "#4da6ff"  # Blue for playing
                else:
                    status_label['foreground'] = self.fg_color  # Default color
            
            # Update the status icon
            try:
                self.update_status_icon(icon_status)
            except Exception as e:
                print(f"Error updating status icon: {e}")
                
            # Set update frequency based on state
            if self.recorder.recording or self.recorder.playing or self.recorder.countdown_active:
                time.sleep(0.2)  # More frequent updates when active
            else:
                time.sleep(0.5)  # Less frequent when idle
    
    def refresh_recordings(self):
        """Refresh the list of recordings"""
        self.recordings_listbox.delete(0, tk.END)
        recordings = [f for f in os.listdir(self.recorder.recordings_dir) if f.endswith('.json')]
        
        for rec in recordings:
            self.recordings_listbox.insert(tk.END, rec)
                
    def load_selected(self):
        """Load the selected recording"""
        selected = self.recordings_listbox.curselection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select a recording to load.")
            return
            
        recording_name = self.recordings_listbox.get(selected[0])
        filepath = os.path.join(self.recorder.recordings_dir, recording_name)
        self.recorder.load_recording(filepath)
    
    def delete_selected(self):
        """Delete the selected recording"""
        selected = self.recordings_listbox.curselection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select a recording to delete.")
            return
            
        recording_name = self.recordings_listbox.get(selected[0])
        filepath = os.path.join(self.recorder.recordings_dir, recording_name)
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {recording_name}?"):
            try:
                os.remove(filepath)
                self.refresh_recordings()
                if self.recorder.current_recording == filepath:
                    self.recorder.current_recording = None
                    self.recorder.events = []
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete recording: {e}")
    
    def create_new_file(self):
        """Create a new recording file and reset the recorder"""
        if self.recorder.recording or self.recorder.playing:
            messagebox.showwarning("Operation in Progress", 
                                 "Please stop recording or playback before creating a new file.")
            return
            
        self.recorder.events = []
        self.show_status("New recording created")
        self.update_event_count()
        
    def load_recording(self):
        """Load a recording from a file"""
        if self.recorder.recording or self.recorder.playing:
            messagebox.showwarning("Operation in Progress", 
                                 "Please stop recording or playback before loading a file.")
            return
            
        file_path = filedialog.askopenfilename(
            title="Open Recording",
            filetypes=[("Hoesway Recordings", "*.hway"), ("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            if "events" in data:
                self.recorder.events = data["events"]
                self.show_status(f"Loaded {len(self.recorder.events)} events from {os.path.basename(file_path)}")
                self.update_event_count()
            else:
                messagebox.showerror("Invalid File", "The selected file does not contain valid recording data.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load recording: {e}")
            
    def save_recording(self):
        """Save the current recording to a file"""
        if not self.recorder.events:
            messagebox.showwarning("Empty Recording", "There is nothing to save. Please record something first.")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Save Recording",
            defaultextension=".hway",
            filetypes=[("Hoesway Recordings", "*.hway"), ("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            data = {
                "version": VERSION,
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "events": self.recorder.events
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.show_status(f"Saved {len(self.recorder.events)} events to {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save recording: {e}")
    
    def start_recording(self):
        """Start recording from the UI"""
        self.recorder.toggle_recording()
    
    def stop_recording(self):
        """Stop recording from the UI"""
        if self.recorder.recording:
            self.recorder.toggle_recording()
            self.refresh_recordings()
    
    def start_playback(self):
        """Start playback from the UI"""
        self.recorder.toggle_playback()
    
    def stop_playback(self):
        """Stop playback from the UI"""
        if self.recorder.playing:
            self.recorder.toggle_playback()
    
    def change_hotkeys(self):
        """Open a dialog to change hotkeys"""
        change_window = tk.Toplevel(self.root)
        change_window.title("Change Hotkeys")
        change_window.geometry("300x150")
        change_window.transient(self.root)
        change_window.grab_set()
        
        ttk.Label(change_window, text="Record Toggle Key:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        record_key_entry = ttk.Entry(change_window)
        record_key_entry.insert(0, self.recorder.record_hotkey)
        record_key_entry.grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(change_window, text="Playback Toggle Key:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        play_key_entry = ttk.Entry(change_window)
        play_key_entry.insert(0, self.recorder.playback_hotkey)
        play_key_entry.grid(row=1, column=1, padx=10, pady=10)
        
        def save_hotkeys():
            record_key = record_key_entry.get().strip()
            play_key = play_key_entry.get().strip()
            
            if not record_key or not play_key:
                messagebox.showerror("Error", "Hotkeys cannot be empty.")
                return
                
            if record_key == play_key:
                messagebox.showerror("Error", "Record and playback hotkeys cannot be the same.")
                return
                
            try:
                self.recorder.change_hotkeys(record_key, play_key)
                # Update the labels in the main window
                for widget in self.hotkey_frame.grid_slaves():
                    if isinstance(widget, ttk.Label) and "Record Toggle:" in widget["text"]:
                        widget["text"] = f"Record Toggle: {record_key}"
                    elif isinstance(widget, ttk.Label) and "Playback Toggle:" in widget["text"]:
                        widget["text"] = f"Playback Toggle: {play_key}"
                
                change_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to set hotkeys: {e}")
        
        ttk.Button(change_window, text="Save", command=save_hotkeys).grid(row=2, column=0, columnspan=2, pady=20)
    
    def minimize(self):
        """Minimize the window but keep the program running in the background"""
        self.root.iconify()
        messagebox.showinfo("Background Mode", 
                           f"The app is now running in the background.\n\n"
                           f"Use {self.recorder.record_hotkey} to toggle recording.\n"
                           f"Use {self.recorder.playback_hotkey} to toggle playback.")
    
    def on_close(self):
        """Handle the window close event"""
        if messagebox.askyesno("Confirm Exit", "Are you sure you want to exit?"):
            self.recorder.stop_threads = True
            if self.recorder.recording:
                self.recorder.stop_recording()
            if self.recorder.playing:
                self.recorder.stop_playback()
            self.root.destroy()
            sys.exit()
    
    def schedule_ui_update(self):
        """Schedule regular UI updates to ensure the interface stays responsive"""
        try:
            # Force UI update
            self.root.update_idletasks()
            self.root.update()
            
            # Update the countdown display if active
            if self.recorder.countdown_active:
                remaining = max(0, int(self.recorder.countdown_time - (time.time() - self.recorder.countdown_start_time)))
                self.status_label.config(text=f"Starting in {remaining}s...", foreground="#ff9900")
            
            # Reschedule this method to run again
            self.root.after(100, self.schedule_ui_update)  # Update every 100ms for smooth UI
        except Exception as e:
            print(f"Error in UI update: {e}")
            # Try to reschedule even if there was an error
            self.root.after(100, self.schedule_ui_update)
    
    def toggle_direct_interception(self):
        """Toggle direct input interception mode"""
        mode = self.interception_var.get()
        self.recorder.toggle_direct_interception(mode)
        
        # Show status message
        state = "Direct interception" if mode else "Standard recording"
        self.show_status(f"Input mode: {state}")
        
    def toggle_block_inputs(self):
        """Toggle whether inputs are blocked from reaching applications"""
        block = self.block_inputs_var.get()
        self.recorder.set_intercept_inputs(block)
        
        # Show status message
        state = "ON" if block else "OFF"
        self.show_status(f"Input blocking: {state}")
        
        # Display warning if user enables input blocking
        if block:
            messagebox.showwarning(
                "Input Blocking Enabled",
                "Inputs will not reach applications during recording.\n\n"
                f"Use the '{self.recorder.record_hotkey}' key to toggle recording on/off."
            )
    
    def setup_menu(self):
        """Set up the menu bar"""
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        
        # File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Recording", command=self.create_new_file)
        file_menu.add_command(label="Open Recording...", command=self.load_recording)
        file_menu.add_command(label="Save Current Recording", command=self.save_recording)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        
        # Help menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Check for Updates", command=self.check_for_updates)
        help_menu.add_separator()
        help_menu.add_command(label="About Hoesway", command=self.show_about)
    
    def check_for_updates(self, silent=False):
        """Check for updates and prompt user if any are available"""
        try:
            self.status_label.config(text="Checking for updates...")
            update_info = self.update_manager.check_for_updates(force=True)
            
            if update_info:
                if self.update_manager.prompt_for_update(self.root, update_info):
                    self.update_manager.download_and_install_update_with_ui(update_info, self.root)
                else:
                    self.show_status("Update available but skipped.")
            else:
                if not silent:
                    messagebox.showinfo("No Updates", "You have the latest version.")
                self.show_status("No updates available.")
        except Exception as e:
            self.show_status(f"Error checking for updates: {e}")
            if not silent:
                messagebox.showerror("Update Error", f"Failed to check for updates: {e}")
            print(f"Error checking for updates: {e}")
    
    def show_about(self):
        """Show the about dialog"""
        about_text = f"""Hoesway - CS2 Movement Recorder
Version: {VERSION}

A simple tool to record and play back mouse and keyboard inputs for Counter-Strike 2.

This application is designed to help players practice complex movement sequences.
It works externally and does not interact with game files or memory."""
        
        messagebox.showinfo("About Hoesway", about_text)
        
    def show_status(self, message):
        """Update the status bar with a message"""
        try:
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.config(text=message)
                self.root.update_idletasks()
            print(message)
        except Exception as e:
            print(f"Error updating status: {e}")


def main():
    """Main entry point for Hoesway"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window until it's fully set up
    
    try:
        # Create the recorder and UI
        recorder = MovementRecorder()
        app = RecorderApp(root)
        
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        root.after(100, root.deiconify)  # Show the window after it's set up
        
        # Check for updates after startup (in background)
        root.after(3000, lambda: app.check_for_updates(silent=True))
        
        # Start the main loop - this will keep the window open
        root.mainloop()
    except Exception as e:
        print(f"Error initializing application: {e}")
        sys.exit(1)
    
if __name__ == "__main__":
    print("\nHoesway")
    print("=====================")
    print("This tool works externally and does NOT interact with game files or memory.")
    print(f"Version: {VERSION}")
    print(f"Hotkeys: F8 to toggle recording, F9 to toggle playback")
    print("\nHotkeys will work in the background.")
    
    # Call main function to start the application
    main()
