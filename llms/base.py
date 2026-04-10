
from abc import abstractmethod,ABC

class BaseLLM(ABC):
    @abstractmethod
    def call(self, prompt: str) -> str:
        pass
    @abstractmethod
    def call_vision(self, image_path: str) -> str:
        pass