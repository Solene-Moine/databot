from typing import Any, Dict, List

class Content:

    def __init__(self, main_content: Any, expanders: List[Dict] = None):
        self.main_content: Any = main_content
        self.expanders: List[Dict] = expanders if expanders is not None else []
