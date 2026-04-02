import json, os

DEFAULTS = {
    "usb_printer":     "",
    "label_size":      "89x36",
    "last_excel_path": "",
}

LABEL_SIZES = {
    "89x36":  {"width_mm": 89,  "height_mm": 36, "label": "89mm × 36mm Dymo (défaut)"},
    "60x35":  {"width_mm": 60,  "height_mm": 35, "label": "60mm × 35mm"},
    "50x30":  {"width_mm": 50,  "height_mm": 30, "label": "50mm × 30mm"},
    "100x50": {"width_mm": 100, "height_mm": 50, "label": "100mm × 50mm"},
    "75x50":  {"width_mm": 75,  "height_mm": 50, "label": "75mm × 50mm"},
}

class ConfigManager:
    def __init__(self, config_path: str):
        self._path = config_path
        self._data = dict(DEFAULTS)
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._data.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass

    def get(self, key: str):
        return self._data.get(key)

    def set(self, key: str, value):
        self._data[key] = value

    def save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get_label_size_info(self) -> dict:
        key = self._data.get("label_size", "60x35")
        return LABEL_SIZES.get(key, LABEL_SIZES["60x35"])
