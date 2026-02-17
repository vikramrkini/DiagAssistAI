import json
from pathlib import Path

TEMPLATES_PATH = Path(__file__).resolve().parent.parent / "templates" / "specialties.json"


class SpecialtyTemplateStore:
    def __init__(self) -> None:
        self._templates = json.loads(TEMPLATES_PATH.read_text())

    def get(self, specialty: str) -> dict:
        return self._templates.get(specialty, self._templates["general"])


specialty_store = SpecialtyTemplateStore()
