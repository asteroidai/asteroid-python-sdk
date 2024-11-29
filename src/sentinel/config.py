"""
Global configuration settings for the Sentinel SDK.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Settings:
    def __init__(self):
        # Sentinel API settings
        self.api_key = os.getenv('SENTINEL_API_KEY')
        self.api_url = os.getenv('SENTINEL_API_URL', 'https://api.sentinel.entropy-labs.ai')
        
        # OpenAI settings
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Validate required settings
        if not self.api_key:
            raise ValueError("SENTINEL_API_KEY environment variable is required")
        if not self.api_url:
            raise ValueError("SENTINEL_API_URL environment variable is required")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

settings = Settings()
