from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseTool(ABC):
    @abstractmethod
    def _get_service(self, credentials: Dict):
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        pass
