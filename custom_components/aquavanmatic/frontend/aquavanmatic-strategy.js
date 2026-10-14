/*
 * AquaVanMatic \u2013 Dashboard-Strategy
 *
 * Verwendung im Dashboard (Raw-Konfigurationseditor):
 *   strategy:
 *     type: custom:aquavanmatic
 *   # optional, nur bei mehreren Anlagen und wenn nur eine gezeigt werden soll:
 *   #   device_id: <Ger\u00e4te-ID>
 *
 * Das Dashboard wird bei jedem \u00d6ffnen aus den tats\u00e4chlich vorhandenen Entit\u00e4ten
 * gebaut. Keine Seriennummer steht fest im Code. Bei mehreren Anlagen gibt es
 * pro Anlage eine eigene Ansicht (Tab).
 */

const PLATFORM = "aquavanmatic";

// Entit\u00e4ten werden \u00fcber das Ende ihrer Entity-ID gefunden
// (z. B. sensor.aquavanmatic_2026020042_betriebszustand \u2192 "betriebszustand").
// 1. Suche am Ger\u00e4t (Buttons und MQTT-Sensoren teilen sich normalerweise ein Ger\u00e4t).
// 2. R\u00fcckfall: alle Entit\u00e4ten/Zust\u00e4nde, deren ID die Seriennummer enth\u00e4lt
//    (falls MQTT-Sensoren an einem eigenen Ger\u00e4t h\u00e4ngen oder nicht registriert sind).
function finder(hass, deviceId, serial) {
  const onDevice = Object.values(hass.entities || {})
    .filter((e) => e.device_id === deviceId && !e.hidden)
    .map((e) => e.entity_id);
  const all = [...new Set([...Object.keys(hass.entities || {}), ...Object.keys(hass.states || {})])];
  const marker = serial ? `_${serial}_` : "aquavanmatic_";
  const bySerial = all.filter((id) => id.includes(marker));
  const match = (list, domain, key) =>
    list.find((id) => id.startsWith(domain + ".") && id.endsWith("_" + key));
  return (domain, key) => match(onDevice, domain, key) || match(bySerial, domain, key);
}

function serialOf(hass, deviceId) {
  const device = (hass.devices || {})[deviceId] || {};
  if (device.serial_number) return String(device.serial_number);
  const name = device.name_by_user || device.name || "";
  const fromName = name.match(/\d{10}/);
  if (fromName) return fromName[0];
  const button = Object.values(hass.entities || {}).find(
    (e) => e.device_id === deviceId && e.platform === PLATFORM
  );
  const fromId = button && button.entity_id.match(/_(\d{10})_/);
  return fromId ? fromId[1] : "";
}

const heading = (text, icon, title = false) => ({
  type: "heading",
  heading: text,
  icon,
  ...(title ? { heading_style: "title" } : {}),
});

function buildView(hass, deviceId, multi) {
  const device = (hass.devices || {})[deviceId] || {};
  const devName = device.name_by_user || device.name || "AquaVanMatic";
  const serial = serialOf(hass, deviceId);
  const find = finder(hass, deviceId, serial);

  const tile = (domain, key, name, icon, color) => {
    const entity = find(domain, key);
    return entity ? { type: "tile", entity, name, icon, ...(color ? { color } : {}) } : null;
  };
  const gauge = (key, name, min, max, segments) => {
    const entity = find("sensor", key);
    return entity
      ? {
          type: "gauge", entity, name, min, max, needle: true,
          segments: segments.map(([from, color]) => ({ from, color })),
        }
      : null;
  };
  const button = (key, name, icon, question) => {
    const entity = find("button", key);
    return entity
      ? {
          type: "button", entity, name, icon, show_state: false,
          tap_action: {
            action: "perform-action",
            perform_action: "button.press",
            target: { entity_id: entity },
            confirmation: { text: question },
          },
        }
      : null;
  };
  // Auswahlfeld (select) als Kachel mit Auswahl direkt in der Kachel.
  const setting = (key, name, icon) => {
    const entity = find("select", key);
    return entity
      ? { type: "tile", entity, name, icon, features: [{ type: "select-options" }] }
      : null;
  };
  const history = (title, hours, items) => {
    const entities = items
      .map(([key, name]) => ({ entity: find("sensor", key), name }))
      .filter((i) => i.entity);
    return entities.length ? { type: "history-graph", title, hours_to_show: hours, entities } : null;
  };
  const clean = (cards) => cards.filter(Boolean);

  // Offene Bedienerentscheidung: Karte erscheint nur, solange eine Entscheidung offen ist.
  // Die Buttons "Trotzdem weiter"/"Abbrechen" der Integration sind genau dann verfuegbar
  // und tragen Frage (question) und Meldungsnummer (code) als Attribute.
  const decisionCard = () => {
    const cont = find("button", "trotzdem_weiter");
    const abort = find("button", "abbrechen");
    if (cont && abort) {
      const pick = (entity, name, icon, color) => ({
        type: "tile", entity, name, icon, color, vertical: true,
        hide_state: true,
        tap_action: {
          action: "perform-action",
          perform_action: "button.press",
          target: { entity_id: entity },
          confirmation: { text: name + "?" },
        },
      });
      return {
        type: "conditional",
        conditions: [{ condition: "state", entity: cont, state_not: "unavailable" }],
        card: {
          type: "vertical-stack",
          cards: [
            {
              type: "markdown",
              content:
                "## \u26a0\ufe0f Entscheidung erforderlich\n\n" +
                `{{ state_attr('${cont}', 'question') or 'Die Anlage wartet auf eine Entscheidung.' }}` +
                `\n\n<sub>Meldung {{ state_attr('${cont}', 'code') }}</sub>`,
            },
            {
              type: "grid", columns: 2, square: false,
              cards: [
                pick(cont, "Trotzdem weiter", "mdi:play-circle-outline", "green"),
                pick(abort, "Abbrechen", "mdi:close-circle-outline", "red"),
              ],
            },
          ],
        },
      };
    }
    // Rueckfall: nur Anzeige ueber die Firmware-Entitaeten
    const pending = find("binary_sensor", "bedienerentscheidung");
    if (!pending) return null;
    const question = find("sensor", "entscheidungsfrage");
    return {
      type: "conditional",
      conditions: [{ condition: "state", entity: pending, state: "on" }],
      card: {
        type: "markdown",
        content:
          "## \u26a0\ufe0f Entscheidung erforderlich\n\n" +
          (question ? `{{ states('${question}') }}` : "Die Anlage wartet auf eine Entscheidung.") +
          "\n\n*Bitte an der Anlage entscheiden.*",
      },
    };
  };

  // Offene, quittierungspflichtige Meldungen: Karte nur, solange welche offen sind.
  const messagesCard = () => {
    const ack = find("button", "meldungen_quittieren");
    if (!ack) return null;
    return {
      type: "conditional",
      conditions: [{ condition: "state", entity: ack, state_not: "unavailable" }],
      card: {
        type: "vertical-stack",
        cards: [
          {
            type: "markdown",
            content:
              "## \u2757 Offene Meldungen ({{ state_attr('" + ack + "', 'open_messages') }})\n\n" +
              "{% for m in state_attr('" + ack + "', 'messages') or [] %}" +
              "- **{{ m.code }}** \u00b7 {{ m.text }}\n{% endfor %}" +
              "\n<sub>Ein neuer Start ist erst nach dem Quittieren m\u00f6glich.</sub>",
          },
          {
            type: "tile", entity: ack, name: "Meldungen quittieren",
            icon: "mdi:check-all", color: "amber", hide_state: true,
            tap_action: {
              action: "perform-action",
              perform_action: "button.press",
              target: { entity_id: ack },
              confirmation: { text: "Angezeigte Meldungen quittieren?" },
            },
          },
        ],
      },
    };
  };

  const sections = [
    {
      type: "grid",
      cards: clean([
        decisionCard(),
        messagesCard(),
        heading("AquaVanMatic", "mdi:water-check", true),
        {
          type: "markdown",
          content: `**WASSERAUFBEREITUNG**${serial ? ` \u00b7 Anlage **${serial}**` : ""}\n\nLive-Messwerte und System\u00fcberwachung`,
        },
        heading("Betriebsstatus", "mdi:state-machine"),
        tile("sensor", "betriebszustand", "Betriebszustand", "mdi:information-outline", "teal"),
        tile("sensor", "statusmeldung", "Statusmeldung", "mdi:message-text-outline"),
        tile("binary_sensor", "storung", "St\u00f6rung", "mdi:alert-circle", "red"),
        tile("sensor", "fehlercode", "Fehlercode", "mdi:alert-outline"),
        tile("binary_sensor", "pumpe", "Pumpe", "mdi:pump"),
        heading("Wasserqualit\u00e4t", "mdi:water-check"),
        gauge("leitfahigkeit_produkt", "Leitf\u00e4higkeit \u00b7 Produkt", 0, 300,
          [[0, "#14b8a6"], [80, "#f59e0b"], [150, "#ef4444"]]),
        tile("sensor", "durchfluss_eingang", "Eingangsdurchfluss", "mdi:water-pump", "cyan"),
        tile("sensor", "durchfluss_produkt", "Produktdurchfluss", "mdi:water-check", "teal"),
        gauge("wirkungsgrad", "Wirkungsgrad", 0, 100,
          [[0, "#ef4444"], [20, "#f59e0b"], [40, "#14b8a6"]]),
      ]),
    },
    {
      type: "grid",
      cards: clean([
        heading("Produktion", "mdi:chart-areaspline", true),
        tile("sensor", "produktion_heute", "Produktion heute", "mdi:water-plus", "cyan"),
        tile("sensor", "produktion_gesamt", "Produktion gesamt", "mdi:counter", "teal"),
        tile("sensor", "gefiltert_heute", "Gefiltert heute", "mdi:filter"),
        tile("sensor", "gefiltert_gesamt", "Gefiltert gesamt", "mdi:filter-check"),
        heading("Pumpen\u00fcberwachung", "mdi:thermometer"),
        gauge("pumpentemperatur", "Pumpentemperatur", 0, 80,
          [[0, "#14b8a6"], [50, "#f59e0b"], [60, "#ef4444"]]),
        heading("Steuerung", "mdi:remote"),
        button("produktion_starten", "Produktion starten", "mdi:play-circle", "Produktion wirklich starten?"),
        button("stop", "Stop", "mdi:stop-circle", "Anlage wirklich stoppen?"),
        button("ruckspulung_starten", "R\u00fccksp\u00fclung starten", "mdi:autorenew", "R\u00fccksp\u00fclung wirklich starten?"),
        button("schnellspulung_starten", "Schnellsp\u00fclung starten", "mdi:water-sync", "Schnellsp\u00fclung wirklich starten?"),
        button("desinfektion_starten", "Desinfektion starten", "mdi:flask-outline", "Desinfektion wirklich starten?"),
        find("select", "verwendung") ? heading("Wasserweg", "mdi:tune") : null,
        setting("verwendung", "Verwendung", "mdi:cup-water"),
        setting("wasserquelle", "Wasserquelle", "mdi:source-branch"),
        setting("ablauf_produktion", "Ablauf Produktion", "mdi:pipe-valve"),
        setting("ablauf_spulen", "Ablauf Sp\u00fclen", "mdi:pipe-valve"),
        setting("ablauf_desinfektion", "Ablauf Desinfektion", "mdi:pipe-valve"),
        find("select", "wasserquelle")
          ? { type: "markdown", content: "<sub>Verwendung nur im Leerlauf \u00e4nderbar. Ein Wechsel der Wasserquelle setzt die Abl\u00e4ufe auf Standard zur\u00fcck.</sub>" }
          : null,
      ]),
    },
    {
      type: "grid",
      cards: clean([
        heading("Wartung", "mdi:tools", true),
        tile("sensor", "filter_restkapazitat", "Filter \u00b7 Restkapazit\u00e4t", "mdi:air-filter", "teal"),
        tile("sensor", "bis_ruckspulung", "Bis zur R\u00fccksp\u00fclung", "mdi:autorenew", "cyan"),
        tile("sensor", "uvc_restlaufzeit", "UVC \u00b7 Restlaufzeit", "mdi:lightbulb-fluorescent-tube"),
        heading("Messwertverlauf", "mdi:chart-line"),
        history("Leitf\u00e4higkeit \u00b7 letzte 12 Stunden", 12, [["leitfahigkeit_produkt", "Leitf\u00e4higkeit"]]),
        history("Durchfluss \u00b7 letzte 6 Stunden", 6,
          [["durchfluss_eingang", "Eingang"], ["durchfluss_produkt", "Produkt"]]),
      ]),
    },
  ];

  return {
    title: multi ? devName : "\u00dcbersicht",
    path: multi ? `anlage-${serial || deviceId}` : "uebersicht",
    icon: "mdi:water-circle",
    type: "sections",
    max_columns: 3,
    sections,
  };
}

class AquaVanMaticDashboardStrategy extends HTMLElement {
  static async generate(config, hass) {
    let deviceIds = [
      ...new Set(
        Object.values(hass.entities || {})
          .filter((e) => e.platform === PLATFORM && e.device_id)
          .map((e) => e.device_id)
      ),
    ];
    if (config && config.device_id) {
      deviceIds = deviceIds.filter((id) => id === config.device_id);
    }

    if (!deviceIds.length) {
      return {
        title: "AquaVanMatic",
        views: [{
          title: "AquaVanMatic",
          cards: [{
            type: "markdown",
            content:
              "### Keine AquaVanMatic-Anlage gefunden\n\n" +
              "1. Anlage einschalten und in den Anlagen-Einstellungen den MQTT-Broker eintragen.\n" +
              "2. In Home Assistant unter **Einstellungen \u2192 Ger\u00e4te & Dienste** die Integration **AquaVanMatic** hinzuf\u00fcgen.\n" +
              "3. Diese Seite neu laden.",
          }],
        }],
      };
    }

    const multi = deviceIds.length > 1;
    return {
      title: "AquaVanMatic",
      views: deviceIds.map((id) => buildView(hass, id, multi)),
    };
  }
}

if (!customElements.get("ll-strategy-dashboard-aquavanmatic")) {
  customElements.define("ll-strategy-dashboard-aquavanmatic", AquaVanMaticDashboardStrategy);
}

// Ab Home Assistant 2026.5: \u201eAquaVanMatic\u201c erscheint als Auswahl im Dialog
// \u201eDashboard hinzuf\u00fcgen\u201c. \u00c4ltere Versionen ignorieren das einfach.
window.customStrategies = window.customStrategies || [];
if (!window.customStrategies.some((s) => s.type === "aquavanmatic")) {
  window.customStrategies.push({
    type: "aquavanmatic",
    strategyType: "dashboard",
    name: "AquaVanMatic",
    description: "Messwerte, Meldungen, Wartung und Steuerung Ihrer AquaVanMatic-Anlage.",
    documentationURL: "https://github.com/aquavanmatic/AquaVanMatic-HA",
  });
}
