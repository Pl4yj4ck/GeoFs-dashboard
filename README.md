# GeoFS Dashboard

A local flight dashboard for GeoFS. The project includes a small Python HTTP server, a browser userscript that forwards simulator telemetry to the server, and a web dashboard with a live map and flight data.

## Features

- Live position, altitude, speed, heading, attitude, engine, and flight-status data.
- A map with the aircraft position and track.
- Optional weather data retrieved from the GeoFS weather service.
- A setup page for the data URL, display units, and dashboard settings.
- A Windows GUI and an optional one-file Windows executable.

## Requirements

- Windows 10 or later is recommended for the included `.bat` scripts and executable build.
- Python 3.10 or later with Tkinter for running the Python GUI. The standard Windows Python installer normally includes Tkinter.
- A supported browser with the Tampermonkey extension to run the GeoFS bridge userscript.
- An internet connection for GeoFS, the weather service, Leaflet, and online map tiles. The dashboard has a canvas map fallback if Leaflet cannot be loaded.

Running the server from Python uses only the Python standard library. Building the executable also requires PyInstaller and Pillow; `crea_exe.bat` installs them.

## Run from source

1. Download or clone this repository and extract it.
2. Install Python if it is not already installed. During installation, enable the option to add Python to `PATH`.
3. Open PowerShell or Command Prompt in the project folder.
4. Start the graphical server:

   ```powershell
   python server_gui.py
   ```

5. In the GeoFS Server window, click **Attiva server**. The server listens on port `8080`.
6. On the same computer, open <http://127.0.0.1:8080/> in a browser.

The server can also be started without the GUI:

```powershell
python _server.py
```

## Install the GeoFS bridge

The dashboard needs the userscript to send it data.

1. Install Tampermonkey from <https://www.tampermonkey.net/> in the browser where you use GeoFS.
2. Open the Tampermonkey dashboard and choose **Create a new script**.
3. Replace the editor contents with the contents of [`script_tampermonkey.user.js`](script_tampermonkey.user.js), then save the script.
4. To run the script, you need to modify the extension's settings from the Chrome Web Store and change the **Allow user scripts** option. Go to `chrome://extensions/?id=dhdgffkkebhmkfjojejmpbldmpobfkfo`, open the extension details, and enable **Allow user scripts**.
5. Start the Python server and open GeoFS at one of the supported `geo-fs.com` addresses. Make sure the userscript is enabled.
6. Open the dashboard. Its connection indicator should change from **DISCONNECTED** to **CONNECTED** after GeoFS has loaded and telemetry is being received.

By default, the userscript sends telemetry to `http://127.0.0.1:8080/data`. This is correct when the browser running GeoFS and the server are on the same computer.

### View the dashboard on another device

You can view the dashboard on a tablet or another device on the same trusted local network:

1. Keep the server running on the computer that runs GeoFS.
2. Find that computer's local IPv4 address. The GUI displays an address, or run `ipconfig` in Command Prompt.
3. On the other device, open `http://<computer-ip>:8080/`, replacing `<computer-ip>` with the server computer's address.
4. If the dashboard cannot connect, open **SETUP** and set **Indirizzo dei dati** to `http://<computer-ip>:8080/data`, then save the settings. Allow Python through Windows Firewall on a **private** network if Windows asks.

Dashboard settings are saved in the browser's local storage on that device. Use **SETUP** to adjust units, map options, or the data URL.

## Build the Windows executable

From the project folder, run:

```bat
crea_exe.bat
```

The script installs or updates PyInstaller and builds a windowed, one-file executable at `dist\GeoFS_Server.exe`, using the existing `icon\icon.ico`. The generated `build/` and `dist/` folders are local build output and are excluded from Git by `.gitignore`.

To keep build packages separate from other Python projects, create and activate a virtual environment in Command Prompt before running the batch file:

```bat
py -m venv .venv
.venv\Scripts\activate.bat
crea_exe.bat
```

The executable bundles the dashboard and can be run without installing Python on the target computer. Windows may show a security warning for an unsigned executable; only run builds you trust.

## Privacy and network security

- The server binds to `0.0.0.0:8080`, so it is reachable from other devices on the local network. It has no authentication or HTTPS, and it allows cross-origin requests. Do not expose port `8080` to the public internet or use the server on an untrusted network.
- The userscript sends simulator data, including latitude, longitude, and altitude, to the configured server. The server keeps the latest values in memory and prints position values to its console log.
- The userscript requests weather data from `weather.geo-fs.com` using the simulated aircraft's latitude and longitude.
- The dashboard loads Leaflet from `unpkg.com` and map tiles from OpenStreetMap or Esri. Those services may receive network requests from your browser when the dashboard is used.
- This project is not affiliated with or endorsed by GeoFS or its operators.

## Project files

- `_server.py`: HTTP server and telemetry endpoint.
- `server_gui.py`: Tkinter GUI for starting and stopping the server.
- `dashboard.html`: browser dashboard.
- `script_tampermonkey.user.js`: GeoFS userscript that sends telemetry.
- `crea_exe.bat` and `GeoFS_Server.spec`: Windows executable build files.
- `geofs_dashboard.bat`: optional command-line server launcher.
- `icon/icon.ico`: application icon used by the build process and GUI.

## Credits and license

- Project code and dashboard: developed with assistance from GitHub Copilot.

