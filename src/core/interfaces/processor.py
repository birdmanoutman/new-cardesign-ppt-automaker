from abc import ABC, abstractmethod
from typing import Dict, List

class IImageProcessor(ABC):
    @abstractmethod
    def process_image(self, image_path: str) -> Dict:
        pass

    @abstractmethod
    def create_thumbnail(self, image_path: str) -> str:
        pass