import json
from pathlib import Path

class I18N:
    def __init__(self, locale: str = "uz"):
        self.locale = locale
        base = Path(__file__).parent / "locales"
        self.data = json.loads((base / f"{locale}.json").read_text(encoding="utf-8"))

    def t(self, key: str, default: str = "") -> str:
        return self.data.get(key, default or key)