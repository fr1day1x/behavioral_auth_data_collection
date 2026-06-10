# ─── GRID ────────────────────────────────────────────────────
GRID_ROWS = 4
GRID_COLS = 4
GRID_TOTAL = GRID_ROWS * GRID_COLS  # 16 possible positions

# ─── ROUND SETTINGS ──────────────────────────────────────────
TARGETS_PER_ROUND = 12       # how many targets light up per round
ROUNDS_PER_ENROLLMENT = 3    # rounds in an enrollment session
ROUNDS_PER_VERIFICATION = 1  # rounds in a verification attempt

# ─── TIMING (seconds) ────────────────────────────────────────
TARGET_VISIBLE_DURATION = 1.5     # how long target stays lit
DELAY_MIN = 0.5                   # min delay between targets
DELAY_MAX = 1.5                   # max delay between targets

# ─── DISPLAY ─────────────────────────────────────────────────
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 700
CIRCLE_RADIUS = 40
GRID_PADDING = 100               # padding from window edge
BACKGROUND_COLOR = (30, 30, 30)
CIRCLE_INACTIVE = (80, 80, 80)
CIRCLE_ACTIVE = (0, 200, 100)
CIRCLE_HIT = (0, 255, 160)
CIRCLE_MISS = (200, 50, 50)

# ─── FEATURE VECTOR ──────────────────────────────────────────
FEATURE_DIMS = 12  # 4 signals x 3 descriptors (mean, std, median)

# ─── AUTHENTICATION ──────────────────────────────────────────
AUTH_THRESHOLD = 0.35  # Euclidean distance threshold (tune during testing)

# ─── STORAGE ─────────────────────────────────────────────────
DB_PATH = "data/templates/templates.db"
ENCRYPTION_KEY_PATH = "data/secret.key"
