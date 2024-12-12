"""
Global configuration settings for the Asteroid SDK.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Settings:
    def __init__(self):
        print("Initializing settings")

        # Asteroid API settings
        self.api_key = os.getenv('ASTEROID_API_KEY', 'Unused')
        self.api_url = os.getenv('ASTEROID_API_URL')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        # Validate required settings
        if not self.api_key:
            raise ValueError("ASTEROID_API_KEY environment variable is required")
        if not self.api_url:
            raise ValueError("ASTEROID_API_URL environment variable is required")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

settings = Settings()
