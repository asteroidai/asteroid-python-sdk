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
        self.api_key = os.getenv('ASTEROID_API_KEY') # Don't error out if this is not set, user might provide in init
        self.api_url = os.getenv('ASTEROID_API_URL', "https://api.asteroid.ai/api/v1")
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        # Optional integration
        self.langfuse_enabled = (
            os.getenv('LANGFUSE_ENABLED', 'false').lower() in ['true', '1']
        )
        if self.langfuse_enabled:
            if not os.getenv('LANGFUSE_PUBLIC_KEY'):
                raise ValueError("LANGFUSE_PUBLIC_KEY environment variable is required")
            if not os.getenv('LANGFUSE_SECRET_KEY'):
                raise ValueError("LANGFUSE_SECRET_KEY environment variable is required")
            if not os.getenv('LANGFUSE_HOST'):
                raise ValueError("LANGFUSE_HOST environment variable is required")

        # Validate required settings
        if not self.api_url:
            raise ValueError("ASTEROID_API_URL environment variable is required")

settings = Settings()
