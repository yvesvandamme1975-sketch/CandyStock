import difflib
from typing import Dict, List, Optional

SYNONYMS: Dict[str, List[str]] = {
    "article":   ["article", "nom", "libellé", "libelle", "désignation",
                  "designation", "description", "produit"],
    "pvente":    ["pvente", "pv ", "prix vente", "prix de vente",
                  "selling price", "vente"],
    "ppro":      ["ppro", "pprottc", "ppro ttc", "prix pro ttc", "pro ttc"],
    "ppro_htva": ["ppro htva", "pprohtva", "ppro_htva", "prix pro htva",
                  "pro htva", "ppht"],
    "origine":   ["origine", "origin", "pays", "country"],
    "p_l":       ["p/l", "p_l", "prix/litre", "prix litre", "prix/l", "pl"],
    "pa_htva":   ["pa htva", "pa_htva", "prix achat", "pa 2026", "pa htva 2026"],
    "taux_tva":  ["taux tva", "taux_tva", "tva", "vat"],
    "ean":       ["ean", "barcode", "code barre", "code-barre"],
}

REQUIRED = ["article", "pvente", "ppro", "ppro_htva"]


class ColumnMapper:
    @staticmethod
    def auto_map(headers: List[str]) -> Dict[str, Optional[str]]:
        used: set = set()
        mapping: Dict[str, Optional[str]] = {k: None for k in SYNONYMS}
        headers_lower = [h.lower().strip() if h else "" for h in headers]

        def _assign(key, header):
            mapping[key] = header
            used.add(header)

        # Pass 1 — exact + synonym substring
        for key, synonyms in SYNONYMS.items():
            for i, hl in enumerate(headers_lower):
                if headers[i] in used:
                    continue
                if hl in synonyms or any(syn in hl for syn in synonyms):
                    _assign(key, headers[i])
                    break

        # Pass 2 — fuzzy fallback
        all_syn_flat = {syn: key for key, syns in SYNONYMS.items() for syn in syns}
        for key in SYNONYMS:
            if mapping[key] is not None:
                continue
            for i, hl in enumerate(headers_lower):
                if headers[i] in used:
                    continue
                matches = difflib.get_close_matches(
                    hl, all_syn_flat.keys(), n=1, cutoff=0.75)
                if matches and all_syn_flat[matches[0]] == key:
                    _assign(key, headers[i])
                    break

        return mapping

    @staticmethod
    def missing_required(mapping: Dict[str, Optional[str]]) -> List[str]:
        return [k for k in REQUIRED if not mapping.get(k)]

    @staticmethod
    def apply(mapping: Dict[str, Optional[str]], raw_row: dict) -> dict:
        inv = {v: k for k, v in mapping.items() if v is not None}
        return {inv.get(h, h): val for h, val in raw_row.items()}
