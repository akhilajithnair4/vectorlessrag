import anthropic
import base64
from llms.base import BaseLLM

class ClaudeLLM(BaseLLM):
    def __init__(self, api_key: str, model_name: str = "claude-3-5-sonnet-20241022"):
        self.model_name = model_name
        self.client = anthropic.Anthropic(api_key=api_key)

    def call(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def call_vision(self, prompt: str, image_bytes: bytes) -> str:
        encoded = base64.b64encode(image_bytes).decode()
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": encoded}},
                    {"type": "text", "text": prompt}        
                ]
            }]  
        )
        return response.content[0].text