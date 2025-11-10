
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Speech service configuration
speech_region = os.getenv("SPEECH_REGION", "eastus2")
speech_key = os.getenv("SPEECH_KEY")
speech_language = os.getenv("SPEECH_LANGUAGE", "tr-TR")
speech_voice = os.getenv("SPEECH_VOICE", "en-US-CoraMultilingualNeural")
speech_voice_2 = os.getenv("SPEECH_VOICE_2", "tr-TR-EmelNeural")

# OpenAI configuration
openai_endpoint = os.getenv("OPENAI_ENDPOINT")
openai_key = os.getenv("OPENAI_KEY")

# Validate required environment variables
required_vars = ["SPEECH_KEY", "OPENAI_ENDPOINT", "OPENAI_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")