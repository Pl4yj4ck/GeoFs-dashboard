#!/usr/bin/env python3
"""Interfaccia grafica elegante e minimale a tema Aviazione per il Server GeoFS."""

import contextlib
import io
import os
import queue
import socket
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk

try:
    import _server
    PORT = getattr(_server, "PORT", 8080)
except ImportError:
    # Fallback se il modulo _server non è nella stessa cartella durante i test
    class MockServer:
        PORT = 8080

        def create_server(self):
            class Dummy:
                def serve_forever(self):
                    pass

                def shutdown(self):
                    pass

                def server_close(self):
                    pass

            return Dummy()

    _server = MockServer()
    PORT = 8080


class QueueWriter(io.TextIOBase):
    """Redireziona gli output del server nella console integrata."""

    def __init__(self, output_queue):
        self.output_queue = output_queue

    def write(self, text):
        if text:
            self.output_queue.put(text)
        return len(text)

    def flush(self):
        return None


class AviationServerGUI:
    # ==============================================================
    # TEMI A TEMA AVIAZIONE
    # ==============================================================

    # Tema Notturno / Cockpit HUD Mode
    THEME_COCKPIT = {
        "bg": "#0B131F",
        "panel": "#111C2B",
        "panel_light": "#17263B",
        "border": "#1E324D",
        "text": "#E0ECF8",
        "muted": "#5C768D",
        "accent": "#38BDF8",
        "accent_hover": "#0284C7",
        "hud_green": "#22C55E",
        "green_subtle": "#052E16",
        "alert_red": "#EF4444",
        "red_hover": "#DC2626",
        "console_bg": "#070D14",
        "console_text": "#7DD3FC",
        "btn_secondary": "#1E293B",
    }

    # Tema Diurno / Daylight Flight Mode
    THEME_DAYLIGHT = {
        "bg": "#F0F4F8",
        "panel": "#FFFFFF",
        "panel_light": "#E2E8F0",
        "border": "#CBD5E1",
        "text": "#0F172A",
        "muted": "#64748B",
        "accent": "#0284C7",
        "accent_hover": "#0369A1",
        "hud_green": "#16A34A",
        "green_subtle": "#DCFCE7",
        "alert_red": "#DC2626",
        "red_hover": "#B91C1C",
        "console_bg": "#1E293B",
        "console_text": "#BAE6FD",
        "btn_secondary": "#E2E8F0",
    }

    def __init__(self, root):
        self.root = root
        self.root.title("GeoFS Flight Server")
        self.root.geometry("900x640")
        self.root.minsize(720, 520)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        # Tema iniziale
        self.colors = self.THEME_DAYLIGHT.copy()

        self.set_window_icon()

        self.server = None
        self.server_thread = None
        self.output_queue = queue.Queue()

        self.ipv4_address = self.get_ipv4_with_port()

        self.address_var = tk.StringVar(
            value=self.ipv4_address
        )

        self.status_var = tk.StringVar(
            value="SYSTEM READY"
        )

        self.build_ui()
        self.apply_theme()

        self.root.after(100, self.flush_output)

    # ==============================================================
    # UTILITY NETWORK & SYSTEM
    # ==============================================================

    @staticmethod
    def get_ipv4_with_port():
        """Ottiene l'IP IPv4 locale e aggiunge la porta :8080."""

        ip = "127.0.0.1"

        try:
            with socket.socket(
                socket.AF_INET,
                socket.SOCK_DGRAM
            ) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]

        except OSError:
            pass

        return f"{ip}:{PORT}"

    @staticmethod
    def resource_path(relative_path):
        base_path = getattr(
            sys,
            "_MEIPASS",
            os.path.dirname(os.path.abspath(__file__)),
        )

        return os.path.join(
            base_path,
            relative_path,
        )

    def set_window_icon(self):
        icon_path = self.resource_path(
            os.path.join("icon", "GeoFS_Server.ico")
        )

        try:
            self.root.iconbitmap(icon_path)
        except (tk.TclError, OSError):
            pass

    # ==============================================================
    # UI CONSTRUCTION
    # ==============================================================

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        # ==========================================================
        # TOP ACCENT
        # ==========================================================

        self.top_accent = tk.Frame(
            self.root,
            height=4,
        )

        self.top_accent.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        self.top_accent.grid_propagate(False)

        # ==========================================================
        # TOP BAR / BARRA AVIONICA
        # ==========================================================

        self.header = tk.Frame(
            self.root,
            height=75,
        )

        self.header.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        self.header.grid_propagate(False)
        self.header.columnconfigure(0, weight=1)

        # ----------------------------------------------------------
        # Logo / Titolo
        # ----------------------------------------------------------

        self.title_box = tk.Frame(
            self.header,
            bg=self.colors["panel"],
            bd=0,
            highlightthickness=0,
        )

        self.title_box.grid(
            row=0,
            column=0,
            sticky="w",
            padx=28,
            pady=16,
        )

        self.title_icon = tk.Label(
            self.title_box,
            text="✈",
            font=("Segoe UI Symbol", 18, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["accent"],
            borderwidth=0,
            highlightthickness=0,
        )

        self.title_icon.pack(side="left")

        self.title_label = tk.Label(
            self.title_box,
            text="GeoFS AVIONICS",
            font=("Segoe UI", 15, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["text"],
            borderwidth=0,
            highlightthickness=0,
        )

        self.title_label.pack(side="left")

        self.status_sublabel = tk.Label(
            self.title_box,
            textvariable=self.status_var,
            font=("Segoe UI", 8, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            borderwidth=0,
            highlightthickness=0,
        )

        self.status_sublabel.pack(
            side="left",
            padx=(12, 12),
        )

        # ----------------------------------------------------------
        # Controlli Header
        # ----------------------------------------------------------

        self.controls = tk.Frame(
            self.header,
            bg=self.colors["panel"],
            bd=0,
            highlightthickness=0,
        )

        self.controls.grid(
            row=0,
            column=1,
            sticky="e",
            padx=28,
        )

        # Tasto Accensione Server
        self.toggle_button = tk.Button(
            self.controls,
            text="⚡  ENG START",
            command=self.toggle_server,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            bd=0,
            borderwidth=0,
            highlightthickness=0,
            padx=16,
            pady=8,
            cursor="hand2",
        )

        self.toggle_button.pack(
            side="left"
        )

        # ==========================================================
        # AREA CENTRALE
        # ==========================================================

        self.content = tk.Frame(
            self.root,
            bd=0,
            highlightthickness=0,
        )

        self.content.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=28,
            pady=(24, 20),
        )

        self.content.columnconfigure(
            0,
            weight=1,
        )

        self.content.rowconfigure(
            1,
            weight=1,
        )

        # ==========================================================
        # PANNELLO NETWORK
        # ==========================================================

        self.network_card = tk.Frame(
            self.content,
            bd=0,
            relief="flat",
            highlightthickness=1,
        )

        self.network_card.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 16),
        )

        self.network_card.columnconfigure(
            1,
            weight=1,
        )

        self.network_label = tk.Label(
            self.network_card,
            text="NETWORK ENDPOINT",
            font=("Segoe UI", 8, "bold"),
            borderwidth=0,
            highlightthickness=0,
        )

        self.network_label.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=18,
            pady=(14, 0),
        )

        self.net_icon = tk.Label(
            self.network_card,
            text="📡",
            font=("Segoe UI Emoji", 12),
            borderwidth=0,
            highlightthickness=0,
        )

        self.net_icon.grid(
            row=1,
            column=0,
            padx=(18, 8),
            pady=(8, 16),
        )

        # ----------------------------------------------------------
        # Indirizzo IPv4
        # ----------------------------------------------------------

        self.address_entry = tk.Entry(
            self.network_card,
            textvariable=self.address_var,
            font=("Consolas", 13, "bold"),
            relief="flat",
            bd=0,
            state="readonly",
            highlightthickness=0,
        )

        self.address_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=6,
            pady=(8, 16),
        )

        # ==========================================================
        # TASTI AZIONE RAPIDA IP
        # ==========================================================

        # IMPORTANTE:
        # Questo Frame ora usa lo stesso colore del network_card.
        # In questo modo non rimangono bordi/strisce di colore
        # diverso attorno ai pulsanti.

        self.btn_box = tk.Frame(
            self.network_card,
            bg=self.colors["panel"],
            bd=0,
            highlightthickness=0,
        )

        self.btn_box.grid(
            row=1,
            column=2,
            padx=14,
            pady=(8, 16),
        )

        self.open_button = tk.Button(
            self.btn_box,
            text="Apri",
            command=self.open_browser,
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            bd=0,
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2",
            padx=10,
            pady=5,
        )

        self.open_button.pack(
            side="left",
            padx=3,
        )

        self.copy_button = tk.Button(
            self.btn_box,
            text="Copia IP",
            command=self.copy_address,
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            bd=0,
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2",
            padx=10,
            pady=5,
        )

        self.copy_button.pack(
            side="left",
            padx=3,
        )

        # ==========================================================
        # PANNELLO TERMINALE DI BORDO
        # ==========================================================

        self.console_card = tk.Frame(
            self.content,
            bd=0,
            relief="flat",
            highlightthickness=1,
        )

        self.console_card.grid(
            row=1,
            column=0,
            sticky="nsew",
        )

        self.console_card.columnconfigure(
            0,
            weight=1,
        )

        self.console_card.rowconfigure(
            1,
            weight=1,
        )

        # ----------------------------------------------------------
        # Header console
        # ----------------------------------------------------------

        self.console_header = tk.Frame(
            self.console_card,
            height=32,
            bd=0,
            highlightthickness=0,
        )

        self.console_header.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        self.console_header.grid_propagate(False)

        self.console_title = tk.Label(
            self.console_header,
            text="  FLIGHT DATA TELEMETRY LOG",
            font=("Segoe UI", 8, "bold"),
            borderwidth=0,
            highlightthickness=0,
        )

        self.console_title.pack(
            side="left",
            padx=12,
            pady=6,
        )

        # ----------------------------------------------------------
        # Console container
        # ----------------------------------------------------------

        self.console_container = tk.Frame(
            self.console_card,
            bd=0,
            highlightthickness=0,
        )

        self.console_container.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=1,
            pady=(0, 1),
        )

        self.console_container.columnconfigure(
            0,
            weight=1,
        )

        self.console_container.rowconfigure(
            0,
            weight=1,
        )

        self.console = tk.Text(
            self.console_container,
            state="disabled",
            relief="flat",
            bd=0,
            font=("Consolas", 9),
            wrap="word",
            padx=12,
            pady=10,
            highlightthickness=0,
        )

        self.console.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        scrollbar = ttk.Scrollbar(
            self.console_container,
            command=self.console.yview,
        )

        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.console.configure(
            yscrollcommand=scrollbar.set
        )

        # ==========================================================
        # FOOTER
        # ==========================================================

        self.footer = tk.Frame(
            self.root,
            height=26,
            bd=0,
            highlightthickness=0,
        )

        self.footer.grid(
            row=3,
            column=0,
            sticky="ew",
        )

        self.footer.grid_propagate(False)

        self.footer_left = tk.Label(
            self.footer,
            text=f"GeoFS Telemetry Server • Port {PORT}",
            font=("Segoe UI", 8),
            borderwidth=0,
            highlightthickness=0,
        )

        self.footer_left.pack(
            side="left",
            padx=20,
        )

        self.footer_right = tk.Label(
            self.footer,
            text="SYS OK",
            font=("Segoe UI", 8, "bold"),
            borderwidth=0,
            highlightthickness=0,
        )

        self.footer_right.pack(
            side="right",
            padx=20,
        )

    # ==============================================================
    # TEMI E STILI
    # ==============================================================

    def apply_theme(self):
        c = self.colors

        # ==========================================================
        # ROOT
        # ==========================================================

        self.root.configure(
            bg=c["bg"]
        )

        self.top_accent.configure(
            bg=c["accent"]
        )

        # ==========================================================
        # HEADER
        # ==========================================================

        self.header.configure(
            bg=c["panel"]
        )

        # IMPORTANTE:
        # Tutti i Frame dentro l'header devono avere lo stesso
        # colore, altrimenti si vedono "pezzi" di colore diverso.

        self.title_box.configure(
            bg=c["panel"]
        )

        self.controls.configure(
            bg=c["panel"]
        )

        self.title_icon.configure(
            bg=c["panel"],
            fg=c["accent"],
        )

        self.title_label.configure(
            bg=c["panel"],
            fg=c["text"],
        )

        # ----------------------------------------------------------
        # Status
        # ----------------------------------------------------------

        if self.server is None:
            self.status_sublabel.configure(
                bg=c["panel"],
                fg=c["muted"],
            )
        else:
            self.status_sublabel.configure(
                bg=c["panel"],
                fg=c["hud_green"],
            )

        # ----------------------------------------------------------
        # Server button
        # ----------------------------------------------------------

        if self.server is None:
            self.toggle_button.configure(
                text="⚡ ENG START",
                bg=c["accent"],
                fg="#FFFFFF",
                activebackground=c["accent_hover"],
                activeforeground="#FFFFFF",
            )

        else:
            self.toggle_button.configure(
                text="🛑 ENG STOP",
                bg=c["alert_red"],
                fg="#FFFFFF",
                activebackground=c["red_hover"],
                activeforeground="#FFFFFF",
            )

        # ==========================================================
        # CONTENT
        # ==========================================================

        self.content.configure(
            bg=c["bg"]
        )

        # ==========================================================
        # NETWORK CARD
        # ==========================================================

        self.network_card.configure(
            bg=c["panel"],
            highlightbackground=c["border"],
            highlightcolor=c["border"],
        )

        self.network_label.configure(
            bg=c["panel"],
            fg=c["muted"],
        )

        self.net_icon.configure(
            bg=c["panel"],
            fg=c["accent"],
        )

        self.address_entry.configure(
            bg=c["panel"],
            fg=c["accent"],
            readonlybackground=c["panel"],
        )

        # ----------------------------------------------------------
        # QUISTA È LA CORREZIONE DEL PROBLEMA
        # ----------------------------------------------------------

        self.btn_box.configure(
            bg=c["panel"]
        )

        # ----------------------------------------------------------
        # Pulsanti Apri / Copia
        # ----------------------------------------------------------

        for btn in (
            self.copy_button,
            self.open_button,
        ):
            btn.configure(
                bg=c["btn_secondary"],
                fg=c["text"],
                activebackground=c["border"],
                activeforeground=c["text"],
            )

        # ==========================================================
        # CONSOLE
        # ==========================================================

        self.console_card.configure(
            bg=c["panel"],
            highlightbackground=c["border"],
            highlightcolor=c["border"],
        )

        self.console_header.configure(
            bg=c["panel"]
        )

        self.console_title.configure(
            bg=c["panel"],
            fg=c["muted"],
        )

        self.console_container.configure(
            bg=c["console_bg"]
        )

        self.console.configure(
            bg=c["console_bg"],
            fg=c["console_text"],
            insertbackground=c["console_text"],
            selectbackground=c["border"],
            selectforeground=c["text"],
        )

        # ==========================================================
        # FOOTER
        # ==========================================================

        self.footer.configure(
            bg=c["panel"]
        )

        self.footer_left.configure(
            bg=c["panel"],
            fg=c["muted"],
        )

        self.footer_right.configure(
            bg=c["panel"],
            fg=c["hud_green"],
        )

    # ==============================================================
    # AZIONI INTERFACCIA
    # ==============================================================

    def open_browser(self):
        url = f"http://{self.address_var.get()}"
        webbrowser.open(url)

    def copy_address(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(
            self.address_var.get()
        )

        original_text = self.copy_button.cget(
            "text"
        )

        self.copy_button.configure(
            text="✓ Copiato",
            bg=self.colors["green_subtle"],
            fg=self.colors["hud_green"],
        )

        self.root.after(
            1500,
            lambda: self.copy_button.configure(
                text=original_text,
                bg=self.colors["btn_secondary"],
                fg=self.colors["text"],
            ),
        )

    def append_console(self, text):
        self.console.configure(
            state="normal"
        )

        self.console.insert(
            "end",
            text
        )

        self.console.see(
            "end"
        )

        self.console.configure(
            state="disabled"
        )

    def flush_output(self):
        try:
            while True:
                self.append_console(
                    self.output_queue.get_nowait()
                )

        except queue.Empty:
            pass

        self.root.after(
            100,
            self.flush_output
        )

    # ==============================================================
    # GESTIONE SERVER
    # ==============================================================

    def toggle_server(self):
        if self.server is None:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        try:
            self.server = _server.create_server()

        except OSError as error:
            messagebox.showerror(
                "Errore Avvio",
                f"La porta {PORT} non è disponibile.\n\n"
                f"{error}",
            )
            return

        server = self.server
        writer = QueueWriter(
            self.output_queue
        )

        def serve():
            with contextlib.redirect_stdout(writer), \
                    contextlib.redirect_stderr(writer):

                print("=" * 50)
                print(
                    " ✈ GeoFS Avionics Telemetry Server"
                )
                print("=" * 50)
                print(
                    f" ► Network Address: "
                    f"http://{self.ipv4_address}/"
                )
                print(
                    f" ► Local Address:   "
                    f"http://localhost:{PORT}/"
                )
                print(
                    " ► Server Status:   ACTIVE"
                )
                print("=" * 50)

                server.serve_forever()

        self.server_thread = threading.Thread(
            target=serve,
            daemon=True,
        )

        self.server_thread.start()

        self.status_var.set(
            f"ONLINE • PORT {PORT}"
        )

        self.apply_theme()

    def stop_server(self):
        server = self.server
        self.server = None

        if server is not None:
            threading.Thread(
                target=server.shutdown,
                daemon=True,
            ).start()

            server.server_close()

        self.status_var.set(
            "SYSTEM READY"
        )

        self.append_console(
            "\n[INFO] Engine shutdown completed.\n"
        )

        self.apply_theme()

    def close(self):
        if self.server is not None:
            self.stop_server()

        self.root.destroy()


if __name__ == "__main__":
    application = tk.Tk()
    AviationServerGUI(application)
    application.mainloop()
