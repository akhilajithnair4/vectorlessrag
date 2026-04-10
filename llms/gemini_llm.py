from google import genai
from google.genai import types
import PIL.Image
import io

from llms.base import BaseLLM

class GeminiLLM(BaseLLM):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)

    def call(self, prompt: str):
        response = self.client.models.generate_content(model=self.model_name, contents=prompt)
        return response.text

    def call_vision(self, prompt: str, image_bytes: bytes) -> str:
        image = PIL.Image.open(io.BytesIO(image_bytes))
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[prompt, image]
        )
        return response.text