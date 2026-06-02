# 🎮 Finger MOBA Arena

> **A webcam-controlled kingdom battle built with Python & OpenCV**

Control your hero using real hand gestures captured by your webcam — no keyboard or mouse required. Push lanes with allied minions, destroy enemy towers, and defeat the enemy crystal to win!

---

## 📸 Screenshots

### 🏠 Main Menu
![Main Menu](screenshots/menu.png)

*Title screen with game instructions and controls overview*

### 🦸 Hero Selection
![Hero Selection](screenshots/hero_select.png)

*Choose from five anime-inspired fighters — each with unique stats, weapons, and playstyle*

### ⚔️ Gameplay
![Gameplay](screenshots/gameplay.png)

*Live match with real-time webcam hand-tracking (bottom right), minimap (top right), gold counter, and skill HUD*

---

## ✨ Features

- 🖐️ **Real-time hand gesture control** via OpenCV and webcam
- 🧙 **5 unique heroes** — Aiko, Ren, Mika, Sora, and Kuro — each with different stats and weapons
- 🏰 **Full MOBA loop** — lanes, allied minions, towers, and a base crystal to destroy
- ⚔️ **Multiple abilities** — basic attacks, skill shots, area bursts, and dashes
- 🗺️ **Mini-map** for situational awareness
- 💰 **Gold & leveling system**
- ⌨️ **Keyboard fallback** controls fully supported

---

## 🦸 Heroes

| Hero | Class | Playstyle |
|------|-------|-----------|
| **Aiko** | Blade Dancer | Fast assassin |
| **Ren** | Crystal Mage | Long range skill |
| **Mika** | Sun Guardian | Tank fighter |
| **Sora** | Storm Archer | Mobile marksman |
| **Kuro** | Shadow Ronin | Burst duelist |

---

## 🖐️ Gesture Controls

| Gesture | Action |
|---------|--------|
| Move index finger | Guide hero |
| Pinch thumb + index finger | Basic attack |
| Two fingers (index + middle) | Q — skill shot |
| Three fingers | E — area burst |
| Open palm | Dash |
| Fist | Regenerate HP |

> 💡 Keep your hand visible in the **Hand Control Camera** window. The small center box is the **neutral zone** — moving your index finger outside it moves the hero.

---

## ⌨️ Keyboard Fallback

| Key | Action |
|-----|--------|
| `W A S D` | Move hero |
| `Space` / `Q` / `E` / `R` | Skills |
| `F` | Dash |
| `P` | Pause |
| `C` | Switch camera |
| `1` – `5` | Pick hero on selection screen |
| `Enter` | Confirm / Start |
| `Esc` | Quit |

---

## 🚀 Setup & Installation

**1. Clone the repository**
```bash
git clone https://github.com/ompreet-s/moba-arena.git
cd moba-arena
```

**2. Create and activate a virtual environment**
```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Run the game**
```bash
python moba_legends_opencv.py
```

---

## 🎯 How to Play

1. The game opens on the **title screen** — click `START GAME` or press `Enter`
2. On the **hero selection screen**, click a hero card, then click **Play** (or press `Enter`)
3. Keep your **hand visible** in the webcam preview — move your index finger outside the neutral zone to move the hero
4. If the wrong camera opens or the preview is black, press **`C`** to switch cameras
5. Push the lane alongside your allied minions, destroy all **enemy towers**, then destroy the **enemy crystal** to win!
6. Return to your **starting base** to refill HP. If you die, you respawn after a short delay
7. After victory, click **PLAY AGAIN** to restart or **EXIT** to close

---

## 🛠️ Tech Stack

- **Python 3**
- **OpenCV** — webcam capture & computer vision
- **Pygame** — 2D game rendering
- **MediaPipe** — hand landmark & gesture detection

---

## 📁 Project Structure

```
moba-arena/
├── moba_legends_opencv.py   # Main game file (all-in-one)
├── requirements.txt          # Python dependencies
├── screenshots/              # README screenshots
└── README.md
```

---

## 📄 License

This project is open source. Feel free to fork, modify, and build upon it!

---

> Made with ❤️ using Python & OpenCV
