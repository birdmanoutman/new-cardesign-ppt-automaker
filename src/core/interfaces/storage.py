from abc import ABC, abstractmethod
from typing import Dict, List

class IStorageProvider(ABC):
    @abstractmethod
    def save_image(self, image_data: Dict) -> str:
        pass

    @abstractmethod
    def get_image(self, image_id: str) -> Dict:
        pass 