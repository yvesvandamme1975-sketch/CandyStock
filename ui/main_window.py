import os, sys, tempfile, time
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

from src.config_manager  import ConfigManager
from src.excel_reader    import ExcelReader
from src.pdf_generator   import PdfGenerator
from src.printer         import DymoPrinter
from src.history_manager import HistoryManager
from src.text_cleaner    import clean_article
from ui.settings_dialog  import SettingsDialog
from ui.mapping_dialog   import MappingDialog

# ── Brand palette ────────────────────────────────────────────────────
P       = "#D4145A"   # CandyStock pink-red
P_DK    = "#B01048"   # primary dark (hover)
NAVY    = "#2D1B3A"   # header background (deep purple)
NAV2    = "#4A2E5A"   # secondary nav buttons
BG      = "#F0EDEF"   # window background
SURFACE = "#FFFFFF"   # panel surface
BORDER  = "#D8DADF"   # dividers / borders
TEXT    = "#2D1B3A"   # primary text
MUTED   = "#717785"   # secondary text
ROW_ALT = "#FAF7FA"   # alternating table row
ROW_SEL = "#FDE8F0"   # selected row tint

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class MainWindow:
    def __init__(self, base_dir: str):
        self._base_dir = base_dir
        self._config   = ConfigManager(os.path.join(base_dir, "config.json"))
        self._history  = HistoryManager(os.path.join(base_dir, "history.json"))
        self._reader           = None
        self._selected_product = None
        self._selected_hist_row = None  # highlighted history row frame
        self._tree_data        = {}     # iid → product dict
        self._iid_to_key       = {}     # iid → stable key
        self._key_to_iid       = {}     # stable key → iid (current view)
        self._checked_keys     = set()  # persistent checked state (stable keys)
        self._suggestion_btns  = []
        self._search_after_id  = None

        # No pre-printed background — blank paper for CandyStock

        self._root = TkinterDnD.Tk()
        ctk.set_appearance_mode("light")
        self._root.title("CandyStock — Impression étiquettes  (v2.1)")
        self._root.geometry("1200x720")
        self._root.configure(bg=BG)

        self._build_ui()
        self._root.after(50, self._prewarm_fonts)   # load fonts before first click

        self._root.drop_target_register(DND_FILES)
        self._root.dnd_bind("<<Drop>>", self._on_file_drop)

        # macOS: bring window to front so first click is not swallowed
        if sys.platform == "darwin":
            self._root.after(150, self._macos_activate)

    def _macos_activate(self):
        try:
            import subprocess, os as _os
            subprocess.Popen([
                "osascript", "-e",
                f"tell application \"System Events\" to set frontmost of "
                f"first process whose unix id is {_os.getpid()} to true"
            ])
        except Exception:
            pass
        self._root.lift()
        self._root.focus_force()

        last = self._config.get("last_excel_path")
        if last and os.path.exists(last):
            self._load_excel(last)

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ───────────────────────────────────────────────────
        header = tk.Frame(self._root, bg=NAVY, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        logo_path = os.path.join(self._base_dir, "assets", "logo.png")
        if os.path.exists(logo_path):
            from PIL import Image, ImageTk
            pil = Image.open(logo_path)
            w, h = pil.size
            dh = 44
            dw = round(w / h * dh)
            pil = pil.resize((dw, dh), Image.LANCZOS)
            photo = ImageTk.PhotoImage(pil)
            lbl = tk.Label(header, image=photo, text="", bg=NAVY)
            lbl._photo = photo   # prevent GC
            lbl.pack(side="left", padx=(12, 8), pady=10)
        else:
            tk.Label(header, text="GoForPrice",
                     font=("Helvetica", 18, "bold"),
                     bg=NAVY, fg="white").pack(side="left", padx=14)

        ctk.CTkButton(
            header, text="📂  Charger Excel",
            command=self._browse_excel,
            width=160, height=36,
            font=ctk.CTkFont("Helvetica", 13, weight="bold"),
            fg_color=P, hover_color=P_DK,
            text_color="white", corner_radius=8,
        ).pack(side="left", padx=(4, 10), pady=14)

        self._file_label = tk.Label(
            header,
            text="Glissez un fichier .xlsx ici ou cliquez Charger",
            font=("Helvetica", 12), bg=NAVY, fg="#8A9BB0")
        self._file_label.pack(side="left", padx=4)

        # "Changer" button — hidden until a file is loaded
        self._change_btn = ctk.CTkButton(
            header, text="↺  Changer",
            command=self._browse_excel,
            width=100, height=28,
            font=ctk.CTkFont("Helvetica", 11),
            fg_color="#2E445A", hover_color="#3E5470",
            text_color="#A0C4FF", corner_radius=6)
        # not packed yet — shown on first successful load

        ctk.CTkButton(
            header, text="⚙  Paramètres",
            command=self._open_settings,
            width=130, height=36,
            font=ctk.CTkFont("Helvetica", 13),
            fg_color=NAV2, hover_color="#3E5470",
            text_color="white", corner_radius=8,
        ).pack(side="right", padx=12, pady=14)

        # ── DnD banner ───────────────────────────────────────────────
        self._dnd_banner = tk.Frame(self._root, bg="#DDE8F8", height=34)
        self._dnd_banner.pack(fill="x")
        self._dnd_banner.pack_propagate(False)
        self._dnd_label = tk.Label(
            self._dnd_banner,
            text="⬇  Glissez votre fichier Excel n'importe où dans la fenêtre",
            font=("Helvetica", 11), bg="#DDE8F8", fg="#4466AA",
            cursor="hand2")
        self._dnd_label.pack(expand=True)
        self._dnd_label.bind("<Button-1>", lambda e: self._browse_excel())

        # ── Body ─────────────────────────────────────────────────────
        body = tk.Frame(self._root, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=8)

        # Left panel (fixed width)
        left = tk.Frame(body, bg=SURFACE,
                        highlightthickness=1, highlightbackground=BORDER)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.configure(width=420)
        left.pack_propagate(False)
        self._build_left(left)

        # Right panel (expands)
        right = tk.Frame(body, bg=SURFACE,
                         highlightthickness=1, highlightbackground=BORDER)
        right.pack(side="left", fill="both", expand=True)
        self._build_right(right)

    def _build_left(self, parent):
        # Search
        tk.Label(parent, text="Recherche article",
                 font=("Helvetica", 11, "bold"),
                 bg=SURFACE, fg=TEXT).pack(anchor="w", padx=12, pady=(12, 4))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        ctk.CTkEntry(
            parent,
            textvariable=self._search_var,
            placeholder_text="🔍  Tapez un nom d'article…",
            height=36, font=ctk.CTkFont("Helvetica", 12),
            corner_radius=8, border_width=1,
        ).pack(fill="x", padx=12)

        # Suggestion dropdown frame
        self._suggest_frame = tk.Frame(
            parent, bg="#FAFAFA",
            highlightthickness=1, highlightbackground=BORDER)
        self._suggest_frame.pack(fill="x", padx=12)

        # ── Treeview product table ────────────────────────────────────
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=(8, 0))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Product.Treeview",
                        background=SURFACE, foreground=TEXT,
                        fieldbackground=SURFACE,
                        font=("Helvetica", 11), rowheight=30)
        style.configure("Product.Treeview.Heading",
                        font=("Helvetica", 10, "bold"),
                        background="#F2F3F5", foreground=MUTED, padding=5)
        style.map("Product.Treeview",
                  background=[("selected", ROW_SEL)],
                  foreground=[("selected", TEXT)])

        tbl_wrap = tk.Frame(parent, bg=SURFACE)
        tbl_wrap.pack(fill="both", expand=True)

        cols = ("check", "article", "pvente")
        self._tree = ttk.Treeview(tbl_wrap, columns=cols, show="headings",
                                  style="Product.Treeview", selectmode="browse")
        self._tree.heading("check",     text="☐")
        self._tree.heading("article",   text="Article")
        self._tree.heading("pvente",    text="Prix HTVA")

        self._tree.column("check",     width=30,  minwidth=30,  anchor="center", stretch=False)
        self._tree.column("article",   width=280, minwidth=100, anchor="w")
        self._tree.column("pvente",    width=90,  minwidth=50,  anchor="e")

        self._tree.tag_configure("even", background=SURFACE)
        self._tree.tag_configure("odd",  background=ROW_ALT)

        tbl_sb = ttk.Scrollbar(tbl_wrap, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=tbl_sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        tbl_sb.pack(side="right", fill="y")

        # Click on row → preview; click on check column → toggle checkbox
        # Click on ☐ heading → toggle select all
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree.bind("<Button-1>", self._on_tree_click)
        self._tree.heading("check", command=self._toggle_select_all)

        # Selection counter
        self._sel_counter = tk.Label(parent, text="",
                                     font=("Helvetica", 10), bg=SURFACE,
                                     fg=MUTED, anchor="w")
        self._sel_counter.pack(fill="x", padx=12, pady=(2, 0))

        # Separator + History
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")
        tk.Label(parent, text="Historique",
                 font=("Helvetica", 11, "bold"),
                 bg=SURFACE, fg=TEXT).pack(anchor="w", padx=12, pady=(8, 4))

        hist_wrap = tk.Frame(parent, bg=SURFACE, height=165)
        hist_wrap.pack(fill="x", pady=(0, 8))
        hist_wrap.pack_propagate(False)

        self._hist_canvas = tk.Canvas(
            hist_wrap, bg=SURFACE, highlightthickness=0)
        self._hist_canvas.pack(fill="both", expand=True, padx=12)

        self._history_frame = tk.Frame(self._hist_canvas, bg=SURFACE)
        self._hist_canvas.create_window(
            (0, 0), window=self._history_frame, anchor="nw")
        self._history_frame.bind(
            "<Configure>",
            lambda e: self._hist_canvas.configure(
                scrollregion=self._hist_canvas.bbox("all")))

        self._refresh_history()

    def _build_right(self, parent):
        # Format label
        tk.Label(parent, text="Format d'impression",
                 font=("Helvetica", 12, "bold"),
                 bg=SURFACE, fg=TEXT).pack(anchor="w", padx=16, pady=(14, 8))

        # Format toggle — custom segmented buttons
        fmt_row = tk.Frame(parent, bg=SURFACE)
        fmt_row.pack(fill="x", padx=16, pady=(0, 12))
        self._format_var = ctk.StringVar(value="label")

        self._btn_label_fmt = ctk.CTkButton(
            fmt_row, text="🏷  Étiquette Dymo",
            command=lambda: self._set_format("label"),
            width=164, height=34,
            font=ctk.CTkFont("Helvetica", 12, weight="bold"),
            fg_color=P, hover_color=P_DK,
            text_color="white", corner_radius=6)
        self._btn_label_fmt.pack(side="left", padx=(0, 4))

        self._btn_a4_fmt = ctk.CTkButton(
            fmt_row, text="📄  Affiche A5",
            command=lambda: self._set_format("a4"),
            width=130, height=34,
            font=ctk.CTkFont("Helvetica", 12),
            fg_color="#E2E4E8", hover_color=BORDER,
            text_color=TEXT, corner_radius=6)
        self._btn_a4_fmt.pack(side="left")

        # Preview area — fixed-size canvas avoids layout recalculation on every render
        preview_bg = tk.Frame(parent, bg="#EDEEF2")
        preview_bg.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self._preview_canvas = tk.Canvas(
            preview_bg, bg="#EDEEF2", highlightthickness=0,
            width=500, height=360)
        self._preview_canvas.pack(expand=True)   # size is fixed — pack just centers it

        self._placeholder = tk.Label(
            preview_bg,
            text="← Sélectionnez un article\npour voir l'aperçu",
            font=("Helvetica", 13), bg="#EDEEF2",
            fg=MUTED, justify="center")
        self._placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # Action buttons
        btn_bar = tk.Frame(parent, bg=SURFACE)
        btn_bar.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkButton(
            btn_bar, text="🖨  Imprimer étiquette",
            command=self._print_label,
            width=190, height=42,
            font=ctk.CTkFont("Helvetica", 13, weight="bold"),
            fg_color=P, hover_color=P_DK,
            corner_radius=8,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_bar, text="📄  Exporter PDF A5",
            command=self._export_pdf,
            width=160, height=42,
            font=ctk.CTkFont("Helvetica", 13),
            fg_color=NAV2, hover_color="#3E5470",
            corner_radius=8,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_bar, text="🖨  Imprimer A5",
            command=self._print_a4,
            width=140, height=42,
            font=ctk.CTkFont("Helvetica", 13),
            fg_color=NAV2, hover_color="#3E5470",
            corner_radius=8,
        ).pack(side="left")

        # Batch action row (uses checkboxes in the article list)
        batch_bar = tk.Frame(parent, bg=SURFACE)
        batch_bar.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(
            batch_bar, text="☑  Étiquettes (sélection)",
            command=self._batch_print_labels,
            width=210, height=36,
            font=ctk.CTkFont("Helvetica", 12),
            fg_color=P, hover_color=P_DK,
            corner_radius=8,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            batch_bar, text="☑  Imprimer A5 (sélection)",
            command=self._batch_print_a4,
            width=210, height=36,
            font=ctk.CTkFont("Helvetica", 12),
            fg_color=NAV2, hover_color="#3E5470",
            corner_radius=8,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            batch_bar, text="✕  Décocher tout",
            command=self._unselect_all,
            width=140, height=36,
            font=ctk.CTkFont("Helvetica", 12),
            fg_color="#888", hover_color="#666",
            corner_radius=8,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            batch_bar, text="⇄  Inverser",
            command=self._invert_selection,
            width=120, height=36,
            font=ctk.CTkFont("Helvetica", 12),
            fg_color="#888", hover_color="#666",
            corner_radius=8,
        ).pack(side="left")

    def _set_format(self, fmt: str):
        self._format_var.set(fmt)
        if fmt == "label":
            self._btn_label_fmt.configure(fg_color=P, text_color="white")
            self._btn_a4_fmt.configure(fg_color="#E2E4E8", text_color=TEXT)
        else:
            self._btn_a4_fmt.configure(fg_color=P, text_color="white")
            self._btn_label_fmt.configure(fg_color="#E2E4E8", text_color=TEXT)
        self._refresh_preview()

    # ── File loading ──────────────────────────────────────────────────

    def _on_file_drop(self, event):
        path = event.data.strip().strip("{}")
        if path.lower().endswith((".xlsx", ".xls")):
            self._load_excel(path)
        else:
            messagebox.showwarning(
                "Format non supporté",
                "Veuillez déposer un fichier Excel (.xlsx ou .xls).")

    def _browse_excel(self):
        path = filedialog.askopenfilename(
            title="Sélectionner le fichier Excel",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")])
        if path:
            self._load_excel(path)

    def _load_excel(self, path: str):
        try:
            self._reader = ExcelReader(
                path, on_mapping_needed=self._ask_mapping)
            self._config.set("last_excel_path", path)
            self._config.save()
            name = os.path.basename(path)
            self._file_label.configure(text=f"✓  {name}", fg="#7EC8A0")
            # Show "Changer" button in header
            self._change_btn.pack(side="left", padx=(2, 0), pady=18)
            # Transform banner into a subtle "replace file" drop zone
            self._dnd_banner.configure(bg="#F0F4E8")
            self._dnd_label.configure(
                text=f"↕  Glisser un nouveau fichier ici pour remplacer  {name}",
                bg="#F0F4E8", fg="#5A7A30")
            self._populate_table(self._reader.all_rows())
            # Auto-select first row so preview is visible immediately
            children = self._tree.get_children()
            if children:
                self._tree.selection_set(children[0])
                self._tree.focus(children[0])
                product = self._tree_data.get(children[0])
                if product:
                    self._select_product(product)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger :\n{e}")

    def _ask_mapping(self, headers, current_mapping):
        dlg = MappingDialog(self._root, headers, current_mapping)
        self._root.wait_window(dlg)
        self._root.focus_force()
        return dlg.result

    # ── Search ────────────────────────────────────────────────────────

    def _on_search_change(self, *_):
        if self._search_after_id:
            self._root.after_cancel(self._search_after_id)
        self._search_after_id = self._root.after(150, self._do_search)

    def _do_search(self):
        self._search_after_id = None
        query = self._search_var.get()
        self._clear_suggestions()
        if not self._reader:
            return
        if query:
            suggestions, results = self._reader.search_with_suggestions(query, limit=8)
            for name in suggestions:
                self._add_suggestion(name)
        else:
            results = self._reader.all_rows()
        self._populate_table(results)

    def _add_suggestion(self, name: str):
        btn = tk.Button(
            self._suggest_frame, text=name,
            anchor="w", relief="flat",
            font=("Helvetica", 11), bg="#FAFAFA", fg=TEXT,
            activebackground=ROW_ALT, cursor="hand2", pady=3,
            command=lambda n=name: self._pick_suggestion(n))
        btn.pack(fill="x", padx=4)
        self._suggestion_btns.append(btn)

    def _clear_suggestions(self):
        for b in self._suggestion_btns:
            b.destroy()
        self._suggestion_btns.clear()

    def _pick_suggestion(self, name: str):
        self._search_var.set(name)
        self._clear_suggestions()

    # ── Table ─────────────────────────────────────────────────────────

    @staticmethod
    def _stable_key(row, idx):
        return (row.get("article", ""), str(row.get("pvente", 0)), idx)

    def _populate_table(self, rows: list):
        tree = self._tree
        tree.delete(*tree.get_children())
        self._tree_data.clear()
        self._iid_to_key.clear()
        self._key_to_iid.clear()
        fp = ExcelReader.format_price

        for i, row in enumerate(rows):
            iid = str(i)
            key = self._stable_key(row, i)
            tag = "even" if i % 2 == 0 else "odd"
            check = "☑" if key in self._checked_keys else "☐"
            tree.insert("", "end", iid=iid, values=(
                check,
                row.get("article", ""),
                fp(row.get("pvente", 0)) + "€",
            ), tags=(tag,))
            self._tree_data[iid] = row
            self._iid_to_key[iid] = key
            self._key_to_iid[key] = iid

        self._update_sel_counter()

    def _on_tree_select(self, event):
        """Row selected → update preview."""
        sel = self._tree.selection()
        if sel:
            iid = sel[0]
            product = self._tree_data.get(iid)
            if product:
                self._select_product(product)

    def _on_tree_click(self, event):
        """Click on check column → toggle checkbox."""
        region = self._tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self._tree.identify_column(event.x)
        if col != "#1":  # first column = check
            return
        iid = self._tree.identify_row(event.y)
        if not iid:
            return
        key = self._iid_to_key.get(iid)
        if not key:
            return
        if key in self._checked_keys:
            self._checked_keys.discard(key)
            self._tree.set(iid, "check", "☐")
        else:
            self._checked_keys.add(key)
            self._tree.set(iid, "check", "☑")
        self._update_sel_counter()

    def _update_sel_counter(self):
        n = len(self._checked_keys)
        if n == 0:
            self._sel_counter.configure(text="")
        else:
            self._sel_counter.configure(
                text=f"{n} produit{'s' if n > 1 else ''} sélectionné{'s' if n > 1 else ''}")

    def _select_product(self, product: dict):
        # Deselect previous history row
        if self._selected_hist_row:
            prev = self._selected_hist_row
            for lbl in getattr(prev, "_text_labels", []):
                try:
                    lbl.configure(bg=SURFACE)
                except Exception:
                    pass
            try:
                prev.configure(bg=SURFACE)
            except Exception:
                pass
            self._selected_hist_row = None
        self._selected_product = product
        # Show preview
        self._placeholder.place_forget()
        self._refresh_preview()

    # ── Preview ───────────────────────────────────────────────────────

    # Fixed canvas dimensions — NEVER call c.configure(width/height) after init.
    # Changing canvas size triggers a full pack-geometry recalculation which is
    # the main source of the perceived delay. Draw centered within fixed bounds.
    _PREV_W = 500
    _PREV_H = 360
    _DRAW_W = 460   # drawing area (20 px margin each side)

    def _prewarm_fonts(self):
        """Force Tkinter to load Arial at all actual preview sizes before first click."""
        RATIO = 1.61
        DW    = self._DRAW_W

        # Label (Dymo 89×36) sizes
        lh      = round(DW * 36 / 89)
        f_pro_l = max(9, round(lh * 0.085))
        sizes_l = {f_pro_l, round(f_pro_l * RATIO), round(round(f_pro_l * RATIO) * RATIO)}

        # A4 landscape sizes
        ah      = round(DW * 210 / 297)
        f_pro_a = max(9, round(ah * 0.065))
        sizes_a = {f_pro_a, round(f_pro_a * RATIO), round(round(f_pro_a * RATIO) * RATIO)}

        c = self._preview_canvas
        for size in sizes_l | sizes_a:
            c.create_text(-999, -999, text=".", font=("Arial", size), anchor="nw")
            c.create_text(-999, -999, text=".", font=("Arial", size, "bold"), anchor="nw")
        c.update_idletasks()
        c.delete("all")

    def _refresh_preview(self):
        if not self._selected_product:
            return
        p  = self._selected_product
        fp = ExcelReader.format_price
        c  = self._preview_canvas
        c.delete("all")
        self._barcode_tk_refs = []  # clear old barcode images

        PW     = self._PREV_W   # 500
        PH     = self._PREV_H   # 360
        DW     = self._DRAW_W   # 460

        # Grey background fill (canvas bg is already #EDEEF2 but items cover it)
        c.create_rectangle(0, 0, PW, PH, fill="#EDEEF2", outline="")

        if self._format_var.get() == "label":
            size = self._config.get_label_size_info()
            lh   = round(DW * size["height_mm"] / size["width_mm"])
            x0   = (PW - DW) // 2
            y0   = max(16, (PH - lh) // 2)

            # Match PDF label proportions (89×36mm, margin=3mm)
            m       = round(lh * 0.083)          # 3/36
            f_title = max(8,  round(lh * 0.12))   # ~11pt on 36mm
            f_price = max(12, round(lh * 0.19))   # ~18pt on 36mm

            c.create_rectangle(x0+3, y0+3, x0+DW+3, y0+lh+3,
                                fill="#C8C8C8", outline="")
            c.create_rectangle(x0, y0, x0+DW, y0+lh,
                                fill="white", outline="#BBBBBB", width=1)

            # Article at top (PDF: page_h - margin - f_title)
            art_id = c.create_text(x0 + DW//2, y0 + m,
                          text=clean_article(p.get("article", "")),
                          font=("Arial", f_title, "bold"),
                          anchor="n", fill="black", width=DW - 2*m,
                          justify="center")
            art_bbox = c.bbox(art_id)
            art_bottom = art_bbox[3] if art_bbox else y0 + m + f_title * 2

            # Barcode at bottom (PDF: by=margin*0.2, width=30/89mm)
            ean = str(p.get("ean", "")).strip()
            barcode_top = y0 + lh - m
            if ean:
                bc_item = self._draw_barcode_on_canvas(c, ean,
                    x0 + DW // 2, y0 + lh - round(lh * 0.02),
                    target_w=round(DW * 0.337), anchor="s")
                if bc_item:
                    bc_bbox = c.bbox(bc_item)
                    if bc_bbox:
                        barcode_top = bc_bbox[1]

            # Price centred between article bottom and barcode top
            price_y = (art_bottom + barcode_top) // 2
            c.create_text(x0 + DW//2, price_y,
                          text=f"{fp(p.get('pvente', 0))}€/HTVA",
                          font=("Arial", f_price, "bold"),
                          anchor="center", fill="black")

        else:  # A5 on left half of A4 landscape — blank paper
            # Preview: left half of A4 landscape (148.5 × 210 mm ratio)
            a5w  = DW - 16
            a5h  = round(a5w * 210 / 148.5)
            if a5h > PH - 16:
                a5h = PH - 16
                a5w = round(a5h * 148.5 / 210)
            x0   = (PW - a5w) // 2
            y0   = max(4, (PH - a5h) // 2)

            # Match PDF proportions (A4 landscape, content on left 148.5mm)
            m       = round(a5w * 0.06)
            f_title = max(12, round(a5h * 0.065))  # ~58pt on 595pt
            f_price = max(16, round(a5h * 0.11))   # ~100pt on 595pt

            # Drop-shadow + white card
            c.create_rectangle(x0+3, y0+3, x0+a5w+3, y0+a5h+3,
                                fill="#C8C8C8", outline="")
            c.create_rectangle(x0, y0, x0+a5w, y0+a5h,
                                fill="white", outline="#BBBBBB", width=1)

            # Article — 20mm from top on 210mm = 9.5%
            c.create_text(x0 + a5w // 2,
                          y0 + round(a5h * 0.095),
                          text=clean_article(p.get("article", "")),
                          font=("Arial", f_title, "bold"),
                          anchor="n", fill="black",
                          width=a5w - 2 * m, justify="center")

            # Price — middle of page, centred
            c.create_text(x0 + a5w // 2,
                          y0 + a5h // 2,
                          text=f"{fp(p.get('pvente', 0))}€/HTVA",
                          font=("Arial", f_price, "bold"),
                          anchor="center", fill="black")

            # Barcode — PDF: bottom at 35mm from bottom = 83.3% from top
            ean = str(p.get("ean", "")).strip()
            if ean:
                self._draw_barcode_on_canvas(c, ean,
                    x0 + a5w // 2, y0 + round(a5h * 0.83),
                    target_w=round(a5w * 0.40), anchor="s")

            # Logo — bottom, centred (PDF: at margin=10mm from bottom)
            logo = self._logo_path()
            if logo and os.path.exists(logo):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(logo)
                    target_w = int(a5w * 0.54)  # 80/148.5 = 54%
                    scale = target_w / img.width
                    target_h = int(img.height * scale)
                    img = img.resize((target_w, target_h), Image.LANCZOS)
                    self._a5_logo_tk = ImageTk.PhotoImage(img)
                    c.create_image(x0 + a5w // 2,
                                   y0 + a5h - round(a5h * 0.048) - target_h // 2,
                                   image=self._a5_logo_tk, anchor="center")
                except Exception:
                    pass

    # ── Barcode helper ────────────────────────────────────────────────

    def _draw_barcode_on_canvas(self, canvas, ean, cx, cy,
                                target_w=120, anchor="center"):
        """Draw an EAN barcode on a tkinter canvas. Returns item id or None."""
        try:
            from src.pdf_generator import _make_barcode_image
            from PIL import ImageTk
            img = _make_barcode_image(ean, module_height=10, font_size=8)
            if not img:
                return None
            scale = target_w / img.width
            new_h = int(img.height * scale)
            img = img.resize((target_w, new_h))
            if not hasattr(self, '_barcode_tk_refs'):
                self._barcode_tk_refs = []
            tk_img = ImageTk.PhotoImage(img)
            self._barcode_tk_refs.append(tk_img)
            item = canvas.create_image(cx, cy, image=tk_img, anchor=anchor)
            return item
        except Exception:
            return None

    # ── History ───────────────────────────────────────────────────────

    def _refresh_history(self):
        for w in self._history_frame.winfo_children():
            w.destroy()
        entries = self._history.list()
        if not entries:
            tk.Label(self._history_frame, text="Aucun historique.",
                     font=("Helvetica", 11), bg=SURFACE,
                     fg=MUTED).pack(pady=6)
            return
        for entry in entries[:20]:
            badge = "ÉTIQ" if entry.get("format") == "label" else "A5"
            bc    = P if badge == "ÉTIQ" else "#16A34A"
            row   = tk.Frame(self._history_frame, bg=SURFACE, cursor="hand2")
            row.pack(fill="x", pady=1)
            tk.Label(row, text=badge, width=5,
                     font=("Helvetica", 9, "bold"),
                     bg=bc, fg="white", pady=2,
                     ).pack(side="left", padx=(0, 6))
            art_lbl = tk.Label(row, text=entry.get("article", ""),
                     font=("Helvetica", 11), bg=SURFACE, fg=TEXT,
                     anchor="w", width=22)
            art_lbl.pack(side="left")
            ts_lbl = tk.Label(row, text=entry.get("timestamp", ""),
                     font=("Helvetica", 9), bg=SURFACE, fg=MUTED)
            ts_lbl.pack(side="right", padx=4)
            row._text_labels = [art_lbl, ts_lbl]
            for w in [row, art_lbl, ts_lbl]:
                w.bind("<Button-1>",
                       lambda e, en=entry, f=row: self._select_from_history(en, f))

    def _select_from_history(self, entry: dict, row_frame=None):
        # Deselect active table row
        self._tree.selection_remove(self._tree.selection())
        # Deselect previous history row
        if self._selected_hist_row:
            prev = self._selected_hist_row
            for lbl in getattr(prev, "_text_labels", []):
                try:
                    lbl.configure(bg=SURFACE)
                except Exception:
                    pass
            try:
                prev.configure(bg=SURFACE)
            except Exception:
                pass
        # Highlight new history row
        self._selected_hist_row = row_frame
        if row_frame:
            for lbl in getattr(row_frame, "_text_labels", []):
                try:
                    lbl.configure(bg=ROW_SEL)
                except Exception:
                    pass
            try:
                row_frame.configure(bg=ROW_SEL)
            except Exception:
                pass
        self._selected_product = entry
        self._placeholder.place_forget()
        self._set_format(entry.get("format", "label"))

    # ── Print / Export ────────────────────────────────────────────────

    def _print_label(self):
        if not self._selected_product:
            messagebox.showwarning("Attention", "Sélectionnez d'abord un article.")
            return
        name = self._config.get("usb_printer")
        if not name or name == "(aucune)":
            # Auto-detect: prefer Dymo/Label printer, else first available
            available = [p for p in DymoPrinter.list_dymo_printers()
                         if p and p != "(aucune)"]
            if not available:
                messagebox.showerror("Erreur",
                    "Aucune imprimante trouvée.\n"
                    "Vérifiez que l'imprimante est branchée et allumée.")
                return
            dymo = [p for p in available
                    if "dymo" in p.lower() or "label" in p.lower()]
            name = dymo[0] if dymo else available[0]
            self._config.set("usb_printer", name)
            self._config.save()
        size = self._config.get_label_size_info()
        logo = self._logo_path()
        tmp_path = os.path.join(tempfile.gettempdir(), "gofp_label.pdf")
        try:
            PdfGenerator.generate_label(
                self._selected_product, tmp_path, logo,
                width_mm=size["width_mm"],
                height_mm=size["height_mm"])
            DymoPrinter.print_label_pdf(tmp_path, printer_name=name)
            self._history.add(self._selected_product, fmt="label")
            self._refresh_history()
            messagebox.showinfo("Succès", "Étiquette envoyée à l'imprimante.")
        except Exception as e:
            messagebox.showerror("Erreur impression", str(e))

    def _export_pdf(self):
        if not self._selected_product:
            messagebox.showwarning("Attention", "Sélectionnez d'abord un article.")
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"{self._selected_product.get('article','')[:30]}.pdf")
        if not save_path:
            return
        logo = self._logo_path()
        try:
            PdfGenerator.generate_a4(self._selected_product, save_path, logo)
            self._history.add(self._selected_product, fmt="a4")
            self._refresh_history()
            messagebox.showinfo("PDF exporté", f"Fichier enregistré :\n{save_path}")
        except Exception as e:
            messagebox.showerror("Erreur PDF", str(e))

    def _print_a4(self):
        if not self._selected_product:
            messagebox.showwarning("Attention", "Sélectionnez d'abord un article.")
            return
        logo = self._logo_path()
        tmp_path = os.path.join(tempfile.gettempdir(), f"gofp_a4_{int(time.time())}.pdf")
        try:
            PdfGenerator.generate_a4(self._selected_product, tmp_path, logo)
            self._history.add(self._selected_product, fmt="a4")
            self._refresh_history()
            DymoPrinter.open_pdf_and_print(tmp_path)
        except Exception as e:
            messagebox.showerror("Erreur impression A4", str(e))

    def _logo_path(self):
        p = os.path.join(self._base_dir, "assets", "logo.png")
        return p if os.path.exists(p) else None

    # ── Batch selection helpers ────────────────────────────────────────

    def _toggle_select_all(self):
        """Toggle all visible rows. Operates only on current view."""
        all_visible_keys = set(self._iid_to_key.values())
        if all_visible_keys <= self._checked_keys:
            # All visible checked → uncheck visible
            self._checked_keys -= all_visible_keys
            for iid in self._tree.get_children():
                self._tree.set(iid, "check", "☐")
        else:
            # Check all visible
            self._checked_keys |= all_visible_keys
            for iid in self._tree.get_children():
                self._tree.set(iid, "check", "☑")
        self._update_sel_counter()

    def _unselect_all(self):
        self._checked_keys.clear()
        for iid in self._tree.get_children():
            self._tree.set(iid, "check", "☐")
        self._update_sel_counter()

    def _invert_selection(self):
        """Invert checked state of all visible rows."""
        for iid in self._tree.get_children():
            key = self._iid_to_key.get(iid)
            if not key:
                continue
            if key in self._checked_keys:
                self._checked_keys.discard(key)
                self._tree.set(iid, "check", "☐")
            else:
                self._checked_keys.add(key)
                self._tree.set(iid, "check", "☑")
        self._update_sel_counter()

    def _get_checked_products(self):
        """Return checked products in display order."""
        return [self._tree_data[iid]
                for iid in self._tree.get_children()
                if self._iid_to_key.get(iid) in self._checked_keys]

    def _batch_print_labels(self):
        products = self._get_checked_products()
        if not products:
            messagebox.showwarning("Attention", "Cochez au moins un article.")
            return
        name = self._config.get("usb_printer")
        if not name or name == "(aucune)":
            available = [p for p in DymoPrinter.list_dymo_printers()
                         if p and p != "(aucune)"]
            if not available:
                messagebox.showerror("Erreur",
                    "Aucune imprimante trouvée.\n"
                    "Vérifiez que l'imprimante est branchée et allumée.")
                return
            dymo = [p for p in available
                    if "dymo" in p.lower() or "label" in p.lower()]
            name = dymo[0] if dymo else available[0]
            self._config.set("usb_printer", name)
            self._config.save()
        size = self._config.get_label_size_info()
        logo = self._logo_path()
        errors = []
        for i, product in enumerate(products):
            try:
                tmp = os.path.join(tempfile.gettempdir(), f"gofp_label_batch_{i}.pdf")
                PdfGenerator.generate_label(
                    product, tmp, logo,
                    width_mm=size["width_mm"],
                    height_mm=size["height_mm"])
                DymoPrinter.print_label_pdf(tmp, printer_name=name)
                self._history.add(product, fmt="label")
            except Exception as e:
                errors.append(f"{product.get('article', '?')}: {e}")
        self._refresh_history()
        if errors:
            messagebox.showerror("Erreurs", "\n".join(errors))
        else:
            messagebox.showinfo("Succès",
                f"{len(products)} étiquette(s) envoyée(s) à l'imprimante.")

    def _batch_print_a4(self):
        products = self._get_checked_products()
        if not products:
            messagebox.showwarning("Attention", "Cochez au moins un article.")
            return
        logo = self._logo_path()
        try:
            import fitz
            merger = fitz.open()
            for i, product in enumerate(products):
                tmp = os.path.join(tempfile.gettempdir(),
                                   f"gofp_a4_batch_{i}.pdf")
                PdfGenerator.generate_a4(product, tmp, logo)
                src = fitz.open(tmp)
                merger.insert_pdf(src)
                src.close()
                self._history.add(product, fmt="a4")
            merged_path = os.path.join(tempfile.gettempdir(), "gofp_a4_batch.pdf")
            merger.save(merged_path)
            merger.close()
            self._refresh_history()
            DymoPrinter.open_pdf_and_print(merged_path)
        except Exception as e:
            messagebox.showerror("Erreur impression A4", str(e))

    def _open_settings(self):
        dlg = SettingsDialog(self._root, self._config)
        self._root.wait_window(dlg)
        self._root.focus_force()

    def run(self):
        self._root.mainloop()
