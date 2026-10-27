DOMAIN = "aquavanmatic"
PREFIX = "aquamatic_"
VERSION = "1.6.1"  # identisch mit manifest.json halten (Cache-Busting für das Dashboard-JS)

STRATEGY_URL = "/aquavanmatic_static/aquavanmatic-strategy.js"
STATUS_TOPIC = "aquamatic/state/status"

COMMANDS = {
    "start": ("Produktion starten", "mdi:play-circle"),
    "stop": ("Stop", "mdi:stop-circle"),
    "backflush": ("Rückspülung starten", "mdi:autorenew"),
    "quickflush": ("Schnellspülung starten", "mdi:water-sync"),
    "disinfection": ("Desinfektion starten", "mdi:flask-outline"),
}

# Schlüssel = Wert für result=… bei POST /api/decision
DECISIONS = {
    "continue": ("Trotzdem weiter", "mdi:play-circle-outline"),
    "abort": ("Abbrechen", "mdi:close-circle-outline"),
}

# (unique-Suffix, Name, Icon) – POST /api/acknowledge
ACKNOWLEDGE = ("acknowledge", "Meldungen quittieren", "mdi:check-all")

# Auswahlfelder: Zustand aus aquamatic/state/status (field), Setzen per POST (path/data).
_DRAIN = {"gray": "Grauwassertank", "external": "Außen"}
SELECTS = [
    {
        "key": "water_mode", "name": "Verwendung", "icon": "mdi:cup-water",
        "field": "waterMode", "options": {"drinking": "Trinkwasser", "shower": "Duschwasser"},
        "path": "/api/watermode", "data": lambda v: {"mode": v},
        "hint": "Nur im Leerlauf änderbar.",
    },
    {
        "key": "water_source", "name": "Wasserquelle", "icon": "mdi:source-branch",
        "field": "waterSource", "options": {"intern": "Intern", "extern": "Extern"},
        "path": "/api/waterpath/source", "data": lambda v: {"mode": v},
        "hint": "Ein Wechsel setzt die drei Abläufe auf ihre Standardwerte zurück.",
    },
    {
        "key": "drain_production", "name": "Ablauf Produktion", "icon": "mdi:pipe-valve",
        "field": "drainProduction", "options": _DRAIN,
        "path": "/api/waterpath/drain", "data": lambda v: {"process": "production", "target": v},
    },
    {
        # gilt laut Firmware auch für die Rückspülung
        "key": "drain_quickflush", "name": "Ablauf Spülen", "icon": "mdi:pipe-valve",
        "field": "drainQuickFlush", "options": _DRAIN,
        "path": "/api/waterpath/drain", "data": lambda v: {"process": "quickflush", "target": v},
    },
    {
        "key": "drain_disinfection", "name": "Ablauf Desinfektion", "icon": "mdi:pipe-valve",
        "field": "drainDisinfection", "options": _DRAIN,
        "path": "/api/waterpath/drain", "data": lambda v: {"process": "disinfection", "target": v},
    },
]
