import customtkinter as ctk
from src.config_manager import ConfigManager
from src.printer import DymoPrinter


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, config: ConfigManager):
        super().__init__(parent)
        self.title("Paramètres")
        self.geometry("380x160")
        self.resizable(False, False)
        self.grab_set()
        self._config = config
        self._build()

    def _build(self):
        pad = {"padx": 20, "pady": 10}

        ctk.CTkLabel(self, text="Imprimante Dymo :").grid(
            row=0, column=0, sticky="w", **pad)

        printers = DymoPrinter.list_dymo_printers()
        self._usb_var = ctk.StringVar(
            value=self._config.get("usb_printer") or printers[0])
        ctk.CTkOptionMenu(
            self, values=printers, variable=self._usb_var,
            width=200,
        ).grid(row=0, column=1, sticky="ew", **pad)

        ctk.CTkButton(self, text="Enregistrer",
                      command=self._save).grid(
                          row=1, column=0, columnspan=2, pady=16)

    def _save(self):
        self._config.set("usb_printer", self._usb_var.get())
        self._config.set("label_size",   "89x36")
        self._config.save()
        self.grab_release()
        self.destroy()
