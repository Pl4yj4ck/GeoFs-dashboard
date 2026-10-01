#!/usr/bin/env python3
"""
GeoFS Server
Serve la dashboard HTML e raccoglie dati da GeoFS Bridge via POST /data
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import csv
from collections import defaultdict, deque
import io
import json
import os
import re
import sys
from datetime import datetime
from threading import Lock
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

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
latest_data_lock = Lock()
autopilot_commands = deque(maxlen=8)
autopilot_commands_lock = Lock()
ourairports_cache = {"expires": 0, "airport_codes": {}, "runways": {}, "frequencies": {}}
ourairports_cache_lock = Lock()
OURAIRPORTS_BASE = "https://davidmegginson.github.io/ourairports-data/"


def load_ourairports_record(ident):
    """Return cached OurAirports details for a code when AWC has no airport record."""
    global ourairports_cache

    with ourairports_cache_lock:
        if ourairports_cache["expires"] <= time.time():
            airport_codes = {}
            runways = defaultdict(list)
            frequencies = defaultdict(list)

            for filename in ("airports.csv", "runways.csv", "airport-frequencies.csv"):
                request = Request(
                    OURAIRPORTS_BASE + filename,
                    headers={"User-Agent": "GeoFS Dashboard/1.0"},
                )
                with urlopen(request, timeout=30) as response:
                    content = response.read(25 * 1024 * 1024 + 1)
                if len(content) > 25 * 1024 * 1024:
                    raise ValueError(f"Dataset OurAirports troppo grande: {filename}")
                rows = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))

                if filename == "airports.csv":
                    for row in rows:
                        code = (row.get("ident") or "").strip().upper()
                        if not code:
                            continue
                        airport = {
                            "icaoId": row.get("icao_code") or code,
                            "ident": code,
                            "iataId": row.get("iata_code") or None,
                            "name": row.get("name") or None,
                            "state": row.get("iso_region") or None,
                            "country": row.get("iso_country") or None,
                            "type": row.get("type") or None,
                            "lat": row.get("latitude_deg") or None,
                            "lon": row.get("longitude_deg") or None,
                            "elevationFt": row.get("elevation_ft") or None,
                            "source": "OurAirports",
                        }
                        for alias in (code, row.get("icao_code"), row.get("gps_code"), row.get("iata_code"), row.get("local_code")):
                            if alias:
                                airport_codes[alias.strip().upper()] = airport

                elif filename == "runways.csv":
                    for row in rows:
                        code = (row.get("airport_ident") or "").strip().upper()
                        if not code:
                            continue
                        length = row.get("length_ft") or ""
                        width = row.get("width_ft") or ""
                        dimension = ""
                        if length and width:
                            dimension = f"{round(float(length))}x{round(float(width))}"
                        runway_id = "/".join(part for part in (row.get("le_ident"), row.get("he_ident")) if part)
                        runways[code].append({
                            "id": runway_id,
                            "dimension": dimension,
                            "surface": row.get("surface") or "",
                            "closed": row.get("closed") == "1",
                            "le_heading_degT": row.get("le_heading_degT") or None,
                            "he_heading_degT": row.get("he_heading_degT") or None,
                        })

                else:
                    for row in rows:
                        code = (row.get("airport_ident") or "").strip().upper()
                        if not code:
                            continue
                        frequencies[code].append({
                            "type": row.get("type") or None,
                            "description": row.get("description") or None,
                            "frequency_mhz": row.get("frequency_mhz") or None,
                        })

            ourairports_cache = {
                "expires": time.time() + 6 * 60 * 60,
                "airport_codes": airport_codes,
                "runways": dict(runways),
                "frequencies": dict(frequencies),
            }

        airport = ourairports_cache["airport_codes"].get(ident.strip().upper())
        if not airport:
            return None
        record = dict(airport)
        record["runways"] = list(ourairports_cache["runways"].get(record["ident"], []))
        record["freqs"] = list(ourairports_cache["frequencies"].get(record["ident"], []))
        return record


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

        parsed_path = urlparse(self.path)

        if parsed_path.path == "/command":
            with autopilot_commands_lock:
                commands = list(autopilot_commands)
                autopilot_commands.clear()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_cors()
            self.end_headers()
            self.wfile.write(json.dumps({"commands": commands}).encode("utf-8"))
            return

        if parsed_path.path == "/aviation":
            self.serve_aviation_data(parsed_path.query)
            return
        
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

        elif self.path == "/icon/planefavicon.svg":
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                filepath = os.path.join(script_dir, "icon", "planefavicon.svg")

                if not os.path.exists(filepath):
                    self.send_error(404, "planefavicon.svg non trovato")
                    return

                with open(filepath, "rb") as f:
                    content = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(content)
                self.log_message("Favicon servito")

            except Exception as e:
                self.send_error(500, f"Errore caricamento favicon: {str(e)}")
                self.log_message(f"Errore favicon: {str(e)}")

        elif self.path.startswith("/data"):
            # Servi JSON dei dati
            try:
                with latest_data_lock:
                    data = json.dumps(latest_data).encode("utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.send_cors()
                self.end_headers()
                self.wfile.write(data)

            except (BrokenPipeError, ConnectionAbortedError):
                return
            except Exception as e:
                self.send_error(500, str(e))
                self.log_message(f"Errore /data GET: {str(e)}")

        else:
            self.send_error(404)
            self.log_message(f"Path non trovato: {self.path}")

    def serve_aviation_data(self, query_string):
        """Proxy limitato ai prodotti JSON AWC usati dalla dashboard."""
        params = parse_qs(query_string)
        product = params.get("product", [""])[0]
        if product not in {"airport", "stationinfo", "metar", "taf"}:
            self.send_error(400, "Prodotto aeronautico non valido")
            return
        if set(params) - {"product", "ids", "bbox"}:
            self.send_error(400, "Parametri non validi")
            return

        ids = params.get("ids", [""])[0].strip().upper()
        bbox = params.get("bbox", [""])[0].strip()
        if ids and (bbox or not re.fullmatch(r"[A-Z0-9]{3,8}", ids)):
            self.send_error(400, "Identificativo stazione non valido")
            return
        if bbox:
            try:
                bounds = [float(value) for value in bbox.split(",")]
                if (len(bounds) != 4 or bounds[0] < -90 or bounds[2] > 90 or
                        bounds[1] < -180 or bounds[3] > 180 or
                        bounds[0] > bounds[2] or bounds[1] > bounds[3]):
                    raise ValueError("limiti fuori intervallo")
            except ValueError:
                self.send_error(400, "Riquadro geografico non valido")
                return
        if not ids and not (product == "stationinfo" and bbox):
            self.send_error(400, "Specificare una stazione o un riquadro")
            return

        api_params = {"format": "json"}
        if ids:
            api_params["ids"] = ids
        if bbox:
            api_params["bbox"] = bbox
        url = "https://aviationweather.gov/api/data/" + product + "?" + urlencode(api_params)
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "GeoFS Dashboard/1.0"})

        try:
            with urlopen(request, timeout=15) as response:
                content = response.read(5 * 1024 * 1024 + 1)
                if len(content) > 5 * 1024 * 1024:
                    self.send_error(502, "Risposta aeronautica troppo grande")
                    return
                status = response.status
                if product == "airport" and ids:
                    airport_records = [] if status == 204 else json.loads(content.decode("utf-8"))
                    airport = airport_records[0] if airport_records else None
                    if not airport or not airport.get("runways") or not airport.get("freqs"):
                        try:
                            fallback = load_ourairports_record(ids)
                        except Exception as error:
                            fallback = None
                            self.log_message(f"Fallback OurAirports non disponibile: {error}")
                        if fallback:
                            if airport:
                                for field in ("runways", "freqs"):
                                    if not airport.get(field):
                                        airport[field] = fallback[field]
                                if not airport.get("elev") and fallback.get("elevationFt"):
                                    airport["elevationFt"] = fallback["elevationFt"]
                                airport["source"] = "AWC + OurAirports"
                            else:
                                airport_records = [fallback]
                            content = json.dumps(airport_records).encode("utf-8")
                            status = 200
                if status == 204:
                    content = b"[]"
                    status = 200
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Content-Length", str(len(content)))
                self.send_cors()
                self.end_headers()
                self.wfile.write(content)
        except (BrokenPipeError, ConnectionAbortedError):
            return
        except HTTPError as error:
            self.send_error(error.code, "Il servizio aeronautico ha rifiutato la richiesta")
        except (URLError, TimeoutError) as error:
            self.send_error(502, f"Servizio aeronautico non raggiungibile: {error}")

    def do_POST(self):
        """Gestisci POST: ricevi dati da GeoFS Bridge"""
        global latest_data

        if self.path == "/command":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)
                payload = json.loads(body.decode("utf-8"))
                if not isinstance(payload, dict) or payload.get("command") != "toggle_autopilot":
                    self.send_error(400, "Comando non supportato")
                    return

                with autopilot_commands_lock:
                    autopilot_commands.append(payload["command"])

                self.send_response(202)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_cors()
                self.end_headers()
                self.wfile.write(b'{"ok":true}')
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                self.send_error(400, f"JSON non valido: {str(e)}")
            except Exception as e:
                self.send_error(500, str(e))
                self.log_message(f"Errore /command POST: {str(e)}")
            return

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
            with latest_data_lock:
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
    return ThreadingHTTPServer((HOST, PORT), Handler)


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