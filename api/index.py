# Vercel serverless function entry point
import sys
import os

# Get the parent directory (project root)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add parent directory to path so we can import app
sys.path.insert(0, ROOT_DIR)

# Set working directory to project root
os.chdir(ROOT_DIR)

from app import app

# Vercel expects the app to be named 'app' or 'application'
application = app
