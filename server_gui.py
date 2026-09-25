#!/usr/bin/env python3
"""Interfaccia grafica per avviare e fermare il server GeoFS."""

import contextlib
import io
import os
import queue
import socket
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import _server


class QueueWriter(io.TextIOBase):
    """Writer minimale che porta l'output del server nella console della GUI."""

    def __init__(self, output_queue):
        self.output_queue = output_queue

    def write(self, text):
        if text:
            self.output_queue.put(text)
        return len(text)

    def flush(self):
        return None


class ServerGui:
    def __init__(self, root):
        self.root = root
        self.root.title("GeoFS Server")
        self.root.geometry("720x500")
        self.root.minsize(560, 380)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.set_window_icon()

        self.server = None
        self.server_thread = None
        self.output_queue = queue.Queue()
        self.address_var = tk.StringVar(value=self.local_address())
        self.status_var = tk.StringVar(value="Server disattivato")

        self.build_ui()
        self.root.after(100, self.flush_output)

    @staticmethod
    def local_address():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                address = sock.getsockname()[0]
        except OSError:
            address = "127.0.0.1"
        return f"http://{address}:{_server.PORT}"

    def build_ui(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#eef3f7")
        style.configure("Header.TFrame", background="#16324f")
        style.configure("HeaderTitle.TLabel", background="#16324f", foreground="#ffffff", font=("Segoe UI", 20, "bold"))
        style.configure("HeaderStatus.TLabel", background="#16324f", foreground="#b9c9d8", font=("Segoe UI", 10))
        style.configure("Badge.TLabel", background="#b8c3cc", foreground="#203040", font=("Segoe UI", 9, "bold"), padding=(9, 4))
        style.configure("Online.TLabel", background="#77c69a", foreground="#123d2a", font=("Segoe UI", 9, "bold"), padding=(9, 4))
        style.configure("Card.TLabelframe", background="#ffffff", bordercolor="#d5dee6", relief="solid")
        style.configure("Card.TLabelframe.Label", background="#ffffff", foreground="#16324f", font=("Segoe UI", 10, "bold"))
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Hint.TLabel", background="#ffffff", foreground="#607080", font=("Segoe UI", 9))
        style.configure("Accent.TButton", background="#e56b3f", foreground="#ffffff", font=("Segoe UI", 10, "bold"), padding=(14, 9))
        style.map("Accent.TButton", background=[("active", "#c9532f"), ("disabled", "#a9b4bd")])

        self.root.configure(background="#eef3f7")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        header = ttk.Frame(self.root, style="Header.TFrame", padding=(24, 20))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="GeoFS Server", style="HeaderTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(header, textvariable=self.status_var, style="HeaderStatus.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.status_badge = ttk.Label(header, text="OFFLINE", style="Badge.TLabel")
        self.status_badge.grid(row=0, column=1, sticky="e", padx=(16, 0))
        self.toggle_button = ttk.Button(header, text="Attiva server", style="Accent.TButton", command=self.toggle_server)
        self.toggle_button.grid(row=0, column=2, rowspan=2, padx=(14, 0), ipadx=12, ipady=7)

        info = ttk.LabelFrame(self.root, text="  Indirizzo di rete  ", style="Card.TLabelframe", padding=14)
        info.grid(row=1, column=0, padx=18, pady=(0, 12), sticky="ew")
        info.columnconfigure(0, weight=1)
        address_frame = ttk.Frame(info, style="Card.TFrame")
        address_frame.grid(row=0, column=0, sticky="ew")
        address_frame.columnconfigure(0, weight=1)
        ttk.Entry(address_frame, textvariable=self.address_var, state="readonly", font=("Consolas", 12)).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Label(info, text="Porta 8080 | usa questo indirizzo nella rete locale", style="Hint.TLabel").grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )

        console_frame = ttk.LabelFrame(self.root, text="  Console server Python  ", style="Card.TLabelframe", padding=8)
        console_frame.grid(row=2, column=0, padx=18, pady=(0, 18), sticky="nsew")
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        self.console = tk.Text(
            console_frame,
            height=12,
            state="disabled",
            background="#101418",
            foreground="#d7e3e8",
            insertbackground="#d7e3e8",
            font=("Consolas", 10),
            wrap="word",
        )
        self.console.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(console_frame, command=self.console.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.console.configure(yscrollcommand=scrollbar.set)

    def set_window_icon(self):
        icon_path = self.resource_path(os.path.join("icon", "icon.ico"))
        try:
            self.root.iconbitmap(icon_path)
        except (tk.TclError, OSError):
            pass

    @staticmethod
    def resource_path(relative_path):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def append_console(self, text):
        self.console.configure(state="normal")
        self.console.insert("end", text)
        self.console.see("end")
        self.console.configure(state="disabled")

    def flush_output(self):
        try:
            while True:
                self.append_console(self.output_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self.flush_output)

    def toggle_server(self):
        if self.server is None:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        try:
            self.server = _server.create_server()
        except OSError as error:
            messagebox.showerror("Server non avviato", f"La porta 8080 non è disponibile.\n\n{error}")
            return

        server = self.server
        writer = QueueWriter(self.output_queue)

        def serve():
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                print("=" * 50)
                print(" GeoFS Server")
                print("=" * 50)
                print(f"Dashboard: http://localhost:{_server.PORT}/")
                print(f"Endpoint dati: http://localhost:{_server.PORT}/data")
                print("Server attivo. Premi il pulsante per fermarlo.")
                server.serve_forever()

        self.server_thread = threading.Thread(target=serve, daemon=True)
        self.server_thread.start()
        self.status_var.set("Server attivo su porta 8080")
        self.status_badge.configure(text="ONLINE", style="Online.TLabel")
        self.toggle_button.configure(text="Disattiva server")

    def stop_server(self):
        server = self.server
        self.server = None
        if server is not None:
            server.shutdown()
            server.server_close()
        self.status_var.set("Server disattivato")
        self.status_badge.configure(text="OFFLINE", style="Badge.TLabel")
        self.toggle_button.configure(text="Attiva server")
        self.append_console("Server terminato.\n")

    def close(self):
        if self.server is not None:
            self.stop_server()
        self.root.destroy()


if __name__ == "__main__":
    application = tk.Tk()
    ServerGui(application)
    application.mainloop()