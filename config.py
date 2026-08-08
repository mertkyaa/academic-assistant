from dotenv import load_dotenv
import os

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ACTIVE_MODEL = "claude-haiku-4-5"
SEMANTIC_SCHOLAR_KEY = os.getenv("SEMANTIC_SCHOLAR_KEY")

def validate_config():
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY was not found")
    print(f"Config loaded. Model: {ACTIVE_MODEL}")



if __name__ == "__main__":
    validate_config()    