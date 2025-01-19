"""
Global configuration settings for the Asteroid SDK.
"""

import os
from dotenv import load_dotenv
import logging
# Load environment variables from .env file if present
load_dotenv()

class Settings:
    def __init__(self):
        logging.info("Initializing Asteroid SDK settings")

        # Asteroid API settings
        self.api_key = os.getenv('ASTEROID_API_KEY')
        self.api_url = os.getenv('ASTEROID_API_URL', "https://api.asteroid.ai/api/v1")
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        # Validate required settings
        if not self.api_key:
            raise ValueError("ASTEROID_API_KEY environment variable is required")
        if not self.api_url:
            raise ValueError("ASTEROID_API_URL environment variable is required")

settings = Settings()
