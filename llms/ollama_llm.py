import requests
from llms.base import BaseLLM
import base64

class OllamaLLM(BaseLLM):
    def __init__(self, model_name: str, ollama_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.ollama_url = ollama_url

    def call_vision(self, prompt: str,image_bytes) -> str:
            encoded = base64.b64encode(image_bytes).decode()
            response = requests.post(
                f"{self.ollama_url}/api/generate/",
                json={"prompt": prompt,
                      "model":self.model_name,
                      "images":[encoded],
                      "stream":False}
            )
            if response.status_code != 200:
                raise Exception(f"Error calling Ollama API: {response.status_code} - {response.text}")  
            
            return response.json().get("response")
    
        
    def call(self, prompt: str) -> str:
            reponse = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "prompt": prompt,
                    "model":self.model_name
                    }
            )
            if reponse.status_code == 200:
                return reponse.json().get("response")
            else:
                raise Exception(f"Error calling Ollama API: {reponse.status_code} - {reponse.text}")
