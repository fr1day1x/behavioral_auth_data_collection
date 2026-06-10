# BehaviourAuth

A game-based behavioural authentication prototype developed as part of the Knox College Richter Summer Research Program 2026.

**Researcher:** Kamlesh Kumar  
**Mentor:** Dr. David Bunde, Department of Computer Science, Knox College

---

## Overview

Instead of a password or fingerprint, this system authenticates users by how they interact with a simple reaction game — their timing, accuracy, and motor response patterns.

---

## Setup

```bash
pip install -r requirements.txt
python main.py
```

---

## How It Works

1. **Enroll** — Press E, enter your participant ID, complete 3 rounds of the game
2. **Verify** — Press V, enter your participant ID, complete 1 round

The system compares your live behavioral feature vector against your stored template using Euclidean distance. If the distance is below the threshold, you are authenticated.

---

## Project Structure

```
behaviorauth/
├── game/           # Game interface and behavioral signal recording
├── auth/           # Feature extraction, template storage, matching
├── server/         # Flask API (coming in Week 3)
├── data/           # Encrypted template database (not committed to Git)
├── tests/          # Unit tests
├── main.py         # Entry point
└── config.py       # All tunable parameters
```

---

## Key Parameters (config.py)

| Parameter | Value | Description |
|---|---|---|
| GRID_ROWS / GRID_COLS | 4 / 4 | 4x4 grid, 16 positions |
| TARGETS_PER_ROUND | 12 | Targets per round |
| ROUNDS_PER_ENROLLMENT | 3 | Rounds to build template |
| AUTH_THRESHOLD | 0.35 | Euclidean distance cutoff |
| FEATURE_DIMS | 12 | 4 signals x 3 descriptors |

---

## Notes

- `data/` is excluded from Git — contains encrypted templates and secret key
- IRB approved — Knox College IRB, June 2026
"# behaviorauth" 
