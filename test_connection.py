import anthropic
from config import ANTHROPIC_API_KEY,ACTIVE_MODEL,validate_config


validate_config()

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

response = client.messages.create(
    model=ACTIVE_MODEL,
    max_tokens = 256,
    messages=[
        {"role": "user", "content": "Hello, Who are you and what to do?"}
    ]
)

print(response.content[0].text)