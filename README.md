# OpenCV MOBA Legends

A small top-down MOBA-style arcade game built with Python and OpenCV. You control one hero with finger gestures through your webcam, push lanes with allied minions, destroy enemy towers, and defeat the enemy base.

## Setup

```powershell
cd "E:\AI INTERNSHIP\opencv"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python moba_legends_opencv.py
```

The game opens on a rules screen. Click `START GAME` or press `Enter`, choose one of five heroes, then click Play or press `Enter` again.

## Controls

- Move your index finger away from the center of the webcam preview: Move hero
- Pinch thumb + index finger: Basic attack
- Raise index + middle fingers: Skill shot
- Raise index + middle + ring fingers: Area burst
- Open palm: Dash
- Make a fist: Regenerate a small amount of health
- `W A S D`: Keyboard movement fallback
- `Space`, `Q`, `E`, `R`: Keyboard action fallback
- `F`: Dash fallback
- `P`: Pause
- `C`: Switch camera if the wrong webcam opens
- `Enter`: Start from the rules screen
- `1` to `5`: Pick a hero on the selection screen
- `Esc`: Quit

Keep your hand visible in the `Hand Control Camera` window. The small center box is the neutral zone; moving your index finger outside it moves the hero. If the wrong camera opens or the preview is black, press `C`.

## Objective

Stay with your allied minions, destroy all enemy towers, then destroy the enemy starting base. The match only ends after a team loses its towers and starting base.

Return to your starting base to refill your hero's HP. If your hero dies, it respawns at your starting base after a short delay.

After victory, click `PLAY AGAIN` to restart with the same hero or `EXIT` to close the game.
