#!/usr/bin/env python3
"""
GeoFS Server
Serve la dashboard HTML e raccoglie dati da GeoFS Bridge via POST /data
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import sys
from datetime import datetime

HOST = "0.0.0.0"
PORT = 8080

latest_data = {
    "altitude": 0,
    "speed": 0,
    "heading": 0,
    "verticalSpeed": 0,
    "latitude": 0,
    "longitude": 0,
    "pitch": 0,
    "roll": 0
}


class Handler(BaseHTTPRequestHandler):

    def send_cors(self):
        """Invia header CORS"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        """Gestisci richieste CORS preflight"""
        self.send_response(204)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        """Gestisci GET: serve HTML e JSON"""
        
        if self.path == "/" or self.path == "":
            # Servi dashboard.html
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                filepath = os.path.join(script_dir, "dashboard.html")
                
                if not os.path.exists(filepath):
                    self.send_error(404, f"dashboard.html non trovato in {script_dir}")
                    return
                
                with open(filepath, "rb") as f:
                    content = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                self.wfile.write(content)
                self.log_message("HTML servito")

            except Exception as e:
                self.send_error(500, f"Errore caricamento dashboard: {str(e)}")
                self.log_message(f"Errore HTML: {str(e)}")

        elif self.path.startswith("/data"):
            # Servi JSON dei dati
            try:
                data = json.dumps(latest_data).encode("utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.send_cors()
                self.end_headers()
                self.wfile.write(data)

            except Exception as e:
                self.send_error(500, str(e))
                self.log_message(f"Errore /data GET: {str(e)}")

        else:
            self.send_error(404)
            self.log_message(f"Path non trovato: {self.path}")

    def do_POST(self):
        """Gestisci POST: ricevi dati da GeoFS Bridge"""
        global latest_data

        if self.path != "/data":
            self.send_error(404)
            return

        try:
            # Leggi il corpo della richiesta
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self.send_error(400, "Content-Length mancante")
                return

            body = self.rfile.read(content_length)
            if not body:
                self.send_error(400, "Body vuoto")
                return

            # Parsa il JSON
            incoming_data = json.loads(body.decode("utf-8"))

            # Inverti latitudine e longitudine se presenti
            if "latitude" in incoming_data and "longitude" in incoming_data:
                incoming_data["latitude"], incoming_data["longitude"] = (
                    incoming_data["longitude"], 
                    incoming_data["latitude"]
                )

            # Aggiorna i dati globali (merge, non sovrascrittura totale)
            latest_data.update(incoming_data)

            # Log
            ts = datetime.now().strftime("%H:%M:%S")
            alt = latest_data.get("altitude", "?")
            lat = latest_data.get("latitude", "?")
            lon = latest_data.get("longitude", "?")
            self.log_message(f"[{ts}] ALT={alt} LAT={lat} LON={lon}")

            # Risposta OK
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors()
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        except json.JSONDecodeError as e:
            self.send_error(400, f"JSON non valido: {str(e)}")
            self.log_message(f"JSON parse error: {str(e)}")

        except Exception as e:
            self.send_error(500, str(e))
            self.log_message(f"Errore /data POST: {str(e)}")

    def log_message(self, format, *args):
        """Personalizza i messaggi di log"""
        # Non loggare ogni singolo GET /data per non inquinare la console
        if "/data" in self.path and self.command == "GET":
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} - {format % args}")


def create_server():
    """Crea il server senza avviarlo, per consentire l'uso da una GUI."""
    return HTTPServer((HOST, PORT), Handler)


def main():
    """Avvia il server"""
    try:
        server = create_server()
        
        print("=" * 50)
        print(" GeoFS Server")
        print("=" * 50)
        print(f"Dashboard: http://localhost:{PORT}/")
        print(f"Endpoint dati: http://localhost:{PORT}/data")
        print()
        print("Premi CTRL+C per terminare.")
        print()
        
        server.serve_forever()

    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Porta {PORT} già in uso!")
            print(f"   Prova un'altra porta: python3 server.py --port 9000")
            sys.exit(1)
        else:
            print(f"Errore: {str(e)}")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nServer terminato.")
        sys.exit(0)


if __name__ == "__main__":
    main()