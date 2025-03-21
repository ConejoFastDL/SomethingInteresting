# Hoesway

A non-intrusive external application for recording and playing back mouse and keyboard movements for Counter-Strike 2.

## Features

- Records all keyboard and mouse inputs (key presses, mouse movement, clicks, and scroll)
- Plays back recordings with adjustable speed
- Operates completely externally to the game (does not access game files or memory)
- Safe to use (no risk of triggering anti-cheat systems)

## Requirements

- Python 3.6+
- Required Python packages (see requirements.txt)

## Installation

1. Make sure you have Python installed
2. Install the required packages:

```
pip install -r requirements.txt
```

## Usage

1. Run the program:

```
python cs2_movement_recorder.py
```

2. Choose from the menu options:
   - Start Recording: Records all keyboard and mouse inputs until you press Esc
   - Play Recording: Play back a previously recorded sequence
   - List Recordings: View all saved recordings
   - Exit: Close the program

3. During recording:
   - Press Esc to stop recording
   - After stopping, you can name your recording or use an auto-generated timestamp

4. During playback:
   - Ensure you switch to your game window during the 3-second countdown
   - Press Esc to stop playback at any time
   - You can adjust playback speed (1.0 = normal speed, 2.0 = double speed, etc.)

## Notes

- All recordings are saved in the "recordings" folder
- The program does not interact with game files or memory in any way
- Always use responsibly and in accordance with game terms of service
