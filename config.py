"""
Configuration settings for Smart Email Assistant.
Loads environment variables and provides centralized configuration.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project root directory
ROOT_DIR = Path(__file__).parent

# Google OAuth 2.0 Settings
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8080/')
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/contacts.readonly'
]

# Token storage
TOKEN_PATH = ROOT_DIR / 'credentials' / 'token.json'
CREDENTIALS_PATH = ROOT_DIR / 'credentials' / 'credentials.json'

# LLM Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
LLM_MODEL = os.getenv('LLM_MODEL', 'gemini-1.5-pro')
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.7'))

# Vector Store Configuration
CHROMA_PERSIST_DIR = ROOT_DIR / 'data' / 'chroma'
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-ada-002')

# Email Search Configuration
MAX_SEARCH_RESULTS = int(os.getenv('MAX_SEARCH_RESULTS', '10'))
EMAIL_CONTEXT_WINDOW = int(os.getenv('EMAIL_CONTEXT_WINDOW', '5'))

# Guardrails Configuration
PII_THRESHOLD = float(os.getenv('PII_THRESHOLD', '0.8'))
ENABLE_PII_VALIDATION = os.getenv('ENABLE_PII_VALIDATION', 'true').lower() == 'true'

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = ROOT_DIR / 'logs' / 'smart_email.log'

# Create necessary directories
(ROOT_DIR / 'credentials').mkdir(exist_ok=True)
(ROOT_DIR / 'data' / 'chroma').mkdir(parents=True, exist_ok=True)
(ROOT_DIR / 'logs').mkdir(exist_ok=True)
