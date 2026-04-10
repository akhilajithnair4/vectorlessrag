from openai import OpenAI
import base64

from llms.base import BaseLLM


class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str,model_name:str="gpt-4-0613"):
        self.api_key = api_key
        self.model_name = model_name
        self.client = OpenAI(api_key=self.api_key)

    def call(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def call_vision(self, prompt: str, image_bytes: bytes) -> str:
        encoded = base64.b64encode(image_bytes).decode()
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}}
                ]
            }]
        )
        return response.choices[0].message.content