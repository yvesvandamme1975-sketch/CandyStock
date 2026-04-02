import json, os
from datetime import datetime
from typing import List, Dict

MAX_ENTRIES = 100
KEEP_KEYS = ("article", "pvente", "ppro", "ppro_htva", "origine", "p_l")


class HistoryManager:
    def __init__(self, history_path: str):
        self._path = history_path
        self._entries: List[Dict] = []
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    self._entries = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._entries = []

    def add(self, product: dict, fmt: str) -> None:
        entry = {k: product.get(k) for k in KEEP_KEYS}
        entry["format"]    = fmt
        entry["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._entries.insert(0, entry)
        if len(self._entries) > MAX_ENTRIES:
            self._entries = self._entries[:MAX_ENTRIES]
        self._save()

    def list(self) -> List[Dict]:
        return list(self._entries)

    def _save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, indent=2, ensure_ascii=False)
