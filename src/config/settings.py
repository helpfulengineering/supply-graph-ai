import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API settings
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# CORS settings
# Parse comma-separated origins from environment variable or use default
CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS", "*")
if CORS_ORIGINS_ENV == "*":
    # Allow all origins
    CORS_ORIGINS = ["*"]
else:
    # Parse comma-separated list of allowed origins
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_ENV.split(",")]

# API Keys
API_KEYS = os.getenv("API_KEYS", "").split(",")
