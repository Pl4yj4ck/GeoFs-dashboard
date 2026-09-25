// ==UserScript==
// @name         GeoFS Tablet Bridge
// @namespace    GeoFS-Tablet
// @version      2.0
// @description  Invia tutti i dati disponibili di GeoFS al server della dashboard
// @match        https://www.geo-fs.com/*
// @match        https://geo-fs.com/*
// @match        https://beta.geo-fs.com/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
  "use strict";

  console.log(
    "%c[GeoFS Tablet] Userscript caricato",
    "color:#00ff88;font-weight:bold"
  );

  const SERVER = "http://127.0.0.1:8080/data";
  let bridgeStarted = false;
  let lastSentData = {};
  let lastWeatherFetch = 0;

  function startBridge() {
    if (bridgeStarted) return;

    if (
      typeof geofs === "undefined" ||
      !geofs.aircraft ||
      !geofs.aircraft.instance
    ) {
      console.log("[GeoFS Tablet] GeoFS non ancora pronto...");
      setTimeout(startBridge, 1000);
      return;
    }

    bridgeStarted = true;
    console.log(
      "%c[GeoFS Tablet] BRIDGE ATTIVO - Tutti i dati",
      "background:#00aa55;color:white;font-size:16px"
    );

    // Fetch meteo ogni 5 secondi (meno frequente dei dati aereo)
    async function fetchWeather() {
      try {
        const a = geofs.aircraft.instance;
        if (!a || !a.llaLocation) return;
        
        const lat = a.llaLocation[1];
        const lon = a.llaLocation[0];
        
        // Chiedi il meteo al server di GeoFS
        const url = `https://weather.geo-fs.com/?lat=${lat}&lon=${lon}`;
        const res = await fetch(url, { 
          headers: { "Accept": "application/json" },
          mode: "cors"
        });
        
        if (!res.ok) return;
        const wx = await res.json();
        
        // La risposta contiene: windSpeedMS, windDirection
        if (wx && wx.windDirection !== undefined && wx.windSpeedMS !== undefined) {
          window._geofsWeather = {
            direction: Number(wx.windDirection) || null,
            speed: Number(wx.windSpeedMS) || null
          };
        }
      } catch (e) {
        // Silenzio, il server meteo potrebbe non essere raggiungibile
      }
    }

    setInterval(fetchWeather, 5000);

    setInterval(() => {
      try {
        const a = geofs.aircraft.instance;
        if (!a) return;

        // === POSIZIONE ===
        const lla = a.llaLocation || [];
        const lon = Number(lla[0]) || null;
        const lat = Number(lla[1]) || null;
        const alt = Number(lla[2]) || null;

        // === VELOCITÀ ===
        const tas = Number(a.trueAirSpeed) || null;
        const gs = Number(a.groundSpeed) || null;
        const mach = Number(a.mach) || null;
        const vscalar = Number(a.velocityScalar) || null;

        // === ASSETTO ===
        // htr è [heading, pitch, roll]
        const htr = Array.isArray(a.htr) ? a.htr : null;
        let heading = null, pitch = null, roll = null;
        
        if (htr && Array.isArray(htr) && htr.length >= 3) {
          heading = Number(htr[0]) || null;
          pitch = Number(htr[1]) || null;
          roll = Number(htr[2]) || null;
        }
        
        // Se non trovati in htr, cerca nei campi diretti (per sicurezza)
        if (heading === null) heading = Number(a.heading) || (a.HDG ? Number(a.HDG) : null);
        if (pitch === null) pitch = Number(a.pitch) || null;
        if (roll === null) roll = Number(a.roll) || null;
        
        const vdir = Array.isArray(a.velocityDirection) ? a.velocityDirection
                  : (Array.isArray(a.airVelocityDirection) ? a.airVelocityDirection : null);

        // === AERODINAMICA ===
        const aoa = Number(a.angleOfAttackDeg) || Number(a.angleOfAttack) || null;
        const airborne = typeof a.airborne === "boolean" ? a.airborne : null;
        const crashed = typeof a.crashed === "boolean" ? a.crashed : null;
        const stalling = typeof a.stalling === "boolean" ? a.stalling : null;
        const groundContact = typeof a.groundContact === "boolean" ? a.groundContact : null;
        const waterContact = typeof a.waterContact === "boolean" ? a.waterContact : null;

        // === CONTROLLI ===
        const brakesOn = typeof a.brakesOn === "boolean" ? a.brakesOn : null;

        // === MOTORI ===
        const engine = a.engine && typeof a.engine === "object" ? a.engine : null;
        let rpm = null, rpmLeft = null, rpmRight = null;
        let thrust = null, thrustLeft = null;
        let engineOn = null;

        if (engine) {
          rpm = Number(engine.rpm) || null;
          rpmLeft = Number(engine.rpmLeft) || null;
          rpmRight = Number(engine.rpmRight) || null;
          thrust = Number(engine.thrust) || null;
          thrustLeft = Number(engine.thrustLeft) || null;
          engineOn = typeof engine.on === "boolean" ? engine.on : null;
        }

        // === DATI PRECEDENTI (per velocità verticale) ===
        if (!window._prevAlt) window._prevAlt = { alt, t: Date.now() };
        let verticalSpeed = null;
        if (alt !== null && alt !== window._prevAlt.alt) {
          const dt = (Date.now() - window._prevAlt.t) / 60000; // minuti
          if (dt > 0.05) {
            verticalSpeed = (alt - window._prevAlt.alt) / dt; // ft/min
            window._prevAlt = { alt, t: Date.now() };
          }
        }

        // === NAVIGAZIONE (se disponibile) ===
        const nav = geofs.navigation || {};
        const navHeading = Number(nav.HDG) || null;
        const adfCourse = Number(nav.ADFManCourse) || null;

        // === COSTRUISCI PAYLOAD (solo campi non null) ===
        const data = {};

        // Posizione
        if (lon !== null) data.longitude = lon;
        if (lat !== null) data.latitude = lat;
        if (alt !== null) data.altitude = alt;

        // Velocità
        if (tas !== null) data.trueAirSpeed = tas;
        if (gs !== null) data.groundSpeed = gs;
        if (mach !== null) data.mach = mach;
        if (vscalar !== null) data.velocityScalar = vscalar;
        if (verticalSpeed !== null) data.verticalSpeed = verticalSpeed;

        // Assetto
        if (htr !== null) data.htr = htr;
        if (pitch !== null) data.pitch = pitch;
        if (roll !== null) data.roll = roll;
        if (heading !== null) data.heading = heading;
        if (navHeading !== null) data.navHeading = navHeading;
        if (vdir !== null) data.velocityDirection = vdir;

        // Aerodinamica
        if (aoa !== null) data.angleOfAttack = aoa;
        if (airborne !== null) data.airborne = airborne;
        if (crashed !== null) data.crashed = crashed;
        if (stalling !== null) data.stalling = stalling;
        if (groundContact !== null) data.groundContact = groundContact;
        if (waterContact !== null) data.waterContact = waterContact;

        // Controlli
        if (brakesOn !== null) data.brakesOn = brakesOn;

        // Motori
        if (rpm !== null) data.rpm = rpm;
        if (rpmLeft !== null) data.rpmLeft = rpmLeft;
        if (rpmRight !== null) data.rpmRight = rpmRight;
        if (thrust !== null) data.thrust = thrust;
        if (thrustLeft !== null) data.thrustLeft = thrustLeft;
        if (engineOn !== null) data.engineOn = engineOn;

        // Navigazione
        if (adfCourse !== null) data.adfCourse = adfCourse;

        // === VENTO (da weatherServer) ===
        if (window._geofsWeather) {
          if (window._geofsWeather.direction !== null) data.windDirection = window._geofsWeather.direction;
          if (window._geofsWeather.speed !== null) data.windSpeed = window._geofsWeather.speed;
        }

        // === INVIA SOLO SE CI SONO CAMBIAMENTI ===
        const dataStr = JSON.stringify(data);
        if (dataStr === JSON.stringify(lastSentData)) {
          return; // Nessun cambio, non inviare
        }
        lastSentData = data;

        fetch(SERVER, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: dataStr
        }).catch(() => {
          // Server non disponibile, ignora silenziosamente
        });

      } catch (error) {
        console.error("[GeoFS Tablet] Errore:", error);
      }
    }, 200);
  }

  startBridge();
})();