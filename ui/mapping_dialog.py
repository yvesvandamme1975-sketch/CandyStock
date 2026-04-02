import customtkinter as ctk
from typing import Dict, List, Optional


class MappingDialog(ctk.CTkToplevel):
    FIELD_LABELS = {
        "article":   "Nom article *",
        "pvente":    "Prix de vente *",
        "ppro":      "Prix pro TTC *",
        "ppro_htva": "Prix pro HTVA *",
        "origine":   "Origine  (optionnel)",
        "p_l":       "Prix/L   (optionnel)",
    }

    def __init__(self, parent, headers: List[str],
                 current_mapping: Dict[str, Optional[str]]):
        super().__init__(parent)
        self.title("Correspondance des colonnes")
        self.geometry("460x380")
        self.resizable(False, False)
        self.grab_set()
        self._headers = ["(ignoré)"] + headers
        self._mapping = dict(current_mapping)
        self.result: Optional[Dict[str, Optional[str]]] = None
        self._vars: Dict[str, ctk.StringVar] = {}
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Associez chaque champ requis (*) à une colonne Excel :",
                     wraplength=420).pack(padx=16, pady=(14, 4))
        frame = ctk.CTkScrollableFrame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=8)
        for key, label in self.FIELD_LABELS.items():
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=label, width=170, anchor="w").pack(side="left")
            current = self._mapping.get(key) or "(ignoré)"
            var = ctk.StringVar(value=current)
            self._vars[key] = var
            ctk.CTkOptionMenu(row, values=self._headers, variable=var,
                              width=230).pack(side="left", padx=8)
        ctk.CTkButton(self, text="Confirmer", command=self._confirm).pack(pady=12)

    def _confirm(self):
        for key, var in self._vars.items():
            val = var.get()
            self._mapping[key] = None if val == "(ignoré)" else val
        self.result = self._mapping
        self.grab_release()
        self.destroy()
