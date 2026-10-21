"""Central configuration for Dayglass."""

APP_NAME = "Dayglass"
APP_VERSION = "0.1.0"

# Initial dimensions of the floating panel, in logical pixels.
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 600

# Resizing limits.
MIN_WINDOW_WIDTH = 360
MAX_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 520

# A short sample list for the first UI milestone.
# Real tasks will be loaded from SQLite in a later milestone.
DEMO_TASKS = [
    "Review today's priorities",
    "Work on the data science project",
    "Practise Python",
    "Plan tomorrow",
]
