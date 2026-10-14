# AquaVanMatic für Home Assistant

Mit dieser Integration steuern und überwachen Sie Ihre AquaVanMatic-Anlage in Home Assistant: Live-Messwerte, Meldungen, Wartungsstände und die Befehle Start, Stop, Rückspülung, Schnellspülung und Desinfektion. Ein fertiges Dashboard ist enthalten.

## Voraussetzungen

- Home Assistant ab Version 2024.8
- Ein MQTT-Broker, mit dem Home Assistant verbunden ist (z. B. das Add-on „Mosquitto broker“ und die Integration „MQTT“)
- [HACS](https://hacs.xyz) (empfohlen; ohne HACS siehe „Manuelle Installation“)
- AquaVanMatic und Home Assistant befinden sich im selben Netzwerk

## 1. AquaVanMatic mit dem MQTT-Broker verbinden

Empfehlung: Legen Sie in Home Assistant einen eigenen Benutzer für die Anlage an, unter **Einstellungen → Personen → Benutzer → Benutzer hinzufügen**, z. B. `aquavanmatic` mit eigenem Passwort. Beim Mosquitto-Add-on kann sich jeder Home-Assistant-Benutzer am Broker anmelden.

Tragen Sie dann in der AquaVanMatic-App unter **Admin → Integration → MQTT** Folgendes ein:

| Feld | Wert |
|---|---|
| Broker-IP | IP-Adresse Ihres Home Assistant, z. B. `192.168.1.50` |
| Port | `1883` |
| Benutzer / Passwort | der eben angelegte Benutzer |

Nach dem Speichern erscheint die Anlage nach wenigen Sekunden unter **Einstellungen → Geräte & Dienste → MQTT** als Gerät „AquaVanMatic &lt;Seriennummer&gt;“.

Messwerte wie Leitfähigkeit, Durchfluss, Produktion und Wartung werden nur übertragen, wenn dort zusätzlich der Haken **MQTT** für die Prozesswerte gesetzt ist. Ohne den Haken sehen Sie nur Betriebszustand, Meldungen und Pumpe.

## 2. Integration installieren

[![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=aquavanmatic&repository=AquaVanMatic-HA&category=integration)

1. Auf den Button oben klicken. HACS öffnet sich mit dem AquaVanMatic-Repository.
2. Auf **Herunterladen** klicken.
3. Home Assistant neu starten (**Einstellungen → System → Neu starten**).

<details>
<summary>Ohne den Button</summary>

HACS öffnen → oben rechts **⋮ → Benutzerdefinierte Repositories** → URL `https://github.com/aquavanmatic/AquaVanMatic-HA`, Typ **Integration** → Hinzufügen. Danach „AquaVanMatic“ suchen und herunterladen.
</details>

## 3. Anlage hinzufügen

Nach dem Neustart meldet Home Assistant unter **Einstellungen → Geräte & Dienste** von selbst: **„Neues Gerät gefunden: AquaVanMatic &lt;Seriennummer&gt;“**. Klicken Sie auf **Hinzufügen** und bestätigen Sie. Seriennummer und IP-Adresse werden automatisch übernommen.

Erscheint keine Meldung, klicken Sie auf diesen Button oder gehen Sie zu **Einstellungen → Geräte & Dienste → Integration hinzufügen → AquaVanMatic**:

[![Integration hinzufügen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=aquavanmatic)

Weitere Anlagen werden danach automatisch erkannt.

## 4. Dashboard anlegen

1. **Einstellungen → Dashboards → Dashboard hinzufügen** und unter „Community-Dashboards“ **AquaVanMatic** auswählen.
2. Titel z. B. „AquaVanMatic“, als **URL** `aquavanmatic-dashboard` eintragen (Home Assistant verlangt einen Bindestrich).
3. **Erstellen** klicken. Das Dashboard erscheint in der Seitenleiste.

Falls die Auswahl „AquaVanMatic“ nach einem Update nicht erscheint oder nicht reagiert: Seite mit **Strg+Umschalt+R** neu laden.

<details>
<summary>Home Assistant älter als 2026.5 (AquaVanMatic steht nicht in der Auswahl)</summary>

1. **Einstellungen → Dashboards → Dashboard hinzufügen → Neues Dashboard von Grund auf**, Name z. B. „AquaVanMatic“.
2. Das neue Dashboard öffnen, dann **✏️ (Bearbeiten) → ⋮ → Raw-Konfigurationseditor**.
3. Den gesamten Inhalt durch diese zwei Zeilen ersetzen und speichern:

```yaml
strategy:
  type: custom:aquavanmatic
```
</details>

Das Dashboard passt sich automatisch an Ihre Anlage an. Haben Sie mehrere Anlagen, bekommt jede einen eigenen Tab.

## Verwendung und Wasserweg

Im Dashboard unter **Wasserweg** stellen Sie direkt ein:

| Einstellung | Auswahl | Hinweis |
|---|---|---|
| Verwendung | Trinkwasser / Duschwasser | nur im Leerlauf änderbar |
| Wasserquelle | Intern / Extern | ein Wechsel setzt die drei Abläufe auf Standard zurück |
| Ablauf Produktion, Ablauf Spülen, Ablauf Desinfektion | Grauwassertank / Außen | „Spülen“ gilt auch für die Rückspülung |

Es gelten dieselben Regeln wie am Bedienfeld der Anlage. Lehnt die Anlage eine Änderung ab, springt die Auswahl auf den tatsächlichen Wert zurück und Home Assistant zeigt den Grund an.

## 5. Entscheidungen und Meldungen

Im Dashboard erscheinen ganz oben zwei Karten, aber nur, wenn es etwas zu tun gibt:

- **Entscheidung erforderlich**: Die Anlage wartet auf eine Entscheidung (z. B. „Tankdaten fehlen – trotzdem fortsetzen?“). Buttons **Trotzdem weiter** und **Abbrechen**.
- **Offene Meldungen**: Liste der Meldungen, die quittiert werden müssen, bevor ein neuer Start möglich ist. Button **Meldungen quittieren**. Quittiert werden genau die angezeigten Meldungen.

Sie können wahlweise dort oder an der Anlage entscheiden und quittieren.

**Optional: Mitteilung aufs Handy** (erfordert die Home-Assistant-App auf dem Handy)

| Vorlage | Import |
|---|---|
| Entscheidung (Aktionen „Trotzdem weiter“/„Abbrechen“) | [![Vorlage importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Faquavanmatic%2FAquaVanMatic-HA%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Faquavanmatic%2Fdecision_notify.yaml) |
| Offene Meldungen (Aktion „Quittieren“) | [![Vorlage importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Faquavanmatic%2FAquaVanMatic-HA%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Faquavanmatic%2Fmessages_notify.yaml) |

1. Auf den Button klicken und die Vorlage importieren.
2. **Automatisierung erstellen**: die passenden Buttons Ihrer Anlage sowie Ihr Handy auswählen, speichern.

Die Mitteilung enthält die Aktionen direkt in der Benachrichtigung. Wird an der Anlage oder im Dashboard entschieden bzw. quittiert, verschwindet sie von selbst.

## Fehlerbehebung

| Problem | Lösung |
|---|---|
| „Keine AquaVanMatic-Anlage gefunden“ | Anlage eingeschaltet? MQTT-Daten in der App richtig? Erscheint das Gerät unter Einstellungen → Geräte & Dienste → MQTT? |
| Dashboard zeigt „Unbekannter Strategietyp“ | Nach Installation/Update Home Assistant neu starten und den Browser mit Strg+F5 neu laden. |
| Buttons melden „REST-Aufruf fehlgeschlagen“ | Die Anlage ist ausgeschaltet oder nicht im Netzwerk erreichbar. |

## Manuelle Installation (ohne HACS)

Den Ordner `custom_components/aquavanmatic` aus dem neuesten Release nach `/config/custom_components/` kopieren (z. B. über das Samba-Add-on), Home Assistant neu starten und mit Schritt 3 weitermachen.

## Updates

Neue Versionen erscheinen in HACS unter **Updates**. Integration und Dashboard werden zusammen aktualisiert. Danach Home Assistant neu starten.
