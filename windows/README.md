# Voice Recognition Windows Client

## Übersicht

Windows-Desktop-Anwendung für die Verbindung mit dem Raspberry Pi Zero W Spracherkennungssystem. Unterstützt Echtzeit-Audio-Streaming und Sprechererkennung mit moderner WPF-Benutzeroberfläche.

## Features

- **Moderne WPF-Benutzeroberfläche**: ModernWPF mit Material Design
- **Echtzeit-Audio-Streaming**: NAudio für hochqualitative Mikrofonaufnahme  
- **WebSocket-Verbindung**: Stabile Verbindung zum Raspberry Pi
- **Automatische Geräteerkennung**: Netzwerk-Scan für Raspberry Pi Geräte
- **Audio-Visualisierung**: Live-Pegel-Anzeige und Verlaufsdiagramme
- **Benachrichtigungen**: System-Tray-Integration mit Benachrichtigungen
- **Einstellungsmanagement**: Persistente Benutzereinstellungen
- **Mehrsprachigkeit**: Deutsche Benutzeroberfläche

## Systemanforderungen

### Mindestanforderungen
- Windows 10 Version 1903 (Build 18362) oder höher
- .NET 6.0 Runtime
- 4 GB RAM
- 100 MB freier Speicherplatz
- Mikrofon oder Audio-Eingabegerät
- Netzwerkverbindung (WLAN/Ethernet)

### Empfohlene Anforderungen
- Windows 11
- 8 GB RAM
- USB-Mikrofon oder professionelles Audio-Interface
- Gigabit-Ethernet-Verbindung

## Installation

### Von der Release-Version

1. **Download**
   - Laden Sie die neueste `VoiceRecognitionClient.exe` von der [Releases-Seite](https://github.com/your-org/voice-recog-pi/releases) herunter

2. **Installation**
   ```powershell
   # Keine Installation erforderlich - Portable Executable
   .\VoiceRecognitionClient.exe
   ```

3. **Erste Einrichtung**
   - Beim ersten Start werden automatisch Standardeinstellungen erstellt
   - Die Anwendung fordert Mikrofon-Berechtigung an

### Aus dem Quellcode

1. **Voraussetzungen installieren**
   ```powershell
   # .NET 6 SDK installieren
   winget install Microsoft.DotNet.SDK.6
   
   # Git installieren (falls nicht vorhanden)
   winget install Git.Git
   ```

2. **Repository klonen**
   ```powershell
   git clone https://github.com/your-org/voice-recog-pi.git
   cd voice-recog-pi\windows\VoiceRecognitionClient
   ```

3. **Abhängigkeiten installieren**
   ```powershell
   dotnet restore
   ```

4. **Kompilieren und ausführen**
   ```powershell
   # Debug-Version
   dotnet run
   
   # Release-Version erstellen
   dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true
   ```

## Konfiguration

### Automatische Konfiguration

Die Anwendung versucht automatisch:
- Raspberry Pi Geräte im lokalen Netzwerk zu finden
- Das Standard-Mikrofon zu verwenden
- Optimale Audio-Einstellungen zu setzen

### Manuelle Konfiguration

Bearbeiten Sie `appsettings.json` für erweiterte Einstellungen:

```json
{
  "VoiceRecognition": {
    "RaspberryPi": {
      "DefaultHost": "192.168.1.100",
      "Port": 8000,
      "ConnectionTimeout": 30,
      "ReconnectDelay": 5000,
      "MaxReconnectAttempts": 10
    },
    "Audio": {
      "SampleRate": 16000,
      "BitDepth": 16,
      "Channels": 1,
      "BufferSize": 4096,
      "DeviceLatency": 20
    },
    "UI": {
      "Theme": "Dark",
      "AutoConnect": true,
      "MinimizeToTray": true,
      "ShowNotifications": true
    }
  }
}
```

### Benutzereinstellungen

Gespeichert in: `%APPDATA%\VoiceRecognitionClient\settings.json`

- **Zuletzt verbundenes Gerät**: Automatische Wiederverbindung
- **Audio-Gerät-Auswahl**: Bevorzugtes Mikrofon
- **Fensterposition und -größe**: UI-Status wird gespeichert
- **Erweiterte Audio-Einstellungen**: Abtastrate, Puffergröße, etc.

## Verwendung

### Erste Verbindung

1. **Anwendung starten**
   - Doppelklick auf `VoiceRecognitionClient.exe`
   - Bei Windows Defender-Warnung: "Trotzdem ausführen" wählen

2. **Raspberry Pi suchen**
   - Klick auf "Suchen" in der Geräte-Sektion
   - Warten auf automatische Geräteerkennung
   - Gerät aus der Liste auswählen

3. **Verbindung herstellen**
   - Klick auf "Verbinden"
   - Warten auf Bestätigung in der Statusleiste

4. **Audio-Aufnahme starten**
   - Audio-Gerät auswählen (falls nicht automatisch erkannt)
   - Klick auf "▶ Start"
   - Audio-Pegel sollte Aktivität anzeigen

### Tägliche Nutzung

1. **Schnellverbindung**
   - Anwendung startet mit gespeicherten Einstellungen
   - Bei aktivierter Auto-Connect: Automatische Verbindung
   - Andernfalls: Klick auf "Verbinden"

2. **Sprechererkennung überwachen**
   - Erkennungsergebnisse erscheinen in Echtzeit
   - Vertrauensgrad wird als Fortschrittsbalken angezeigt
   - Verlauf zeigt letzte 50 Erkennungen

3. **System Tray Integration**
   - Minimieren zur System-Tray mit Rechtsklick → "Minimieren"
   - Benachrichtigungen bei Sprechererkennung
   - Doppelklick auf Tray-Icon zum Wiederherstellen

### Erweiterte Features

1. **Audio-Visualisierung**
   - Echtzeit-Pegel-Anzeige
   - Historischer Pegel-Verlauf
   - Stumm-Erkennung

2. **Mehrere Raspberry Pi Geräte**
   - Gleichzeitiges Verwalten mehrerer Geräte
   - Schnelles Umschalten zwischen Geräten
   - Geräte-Status-Überwachung

3. **Erweiterte Audio-Einstellungen**
   - Verschiedene Audio-Geräte testen
   - Abtastrate anpassen für bessere Qualität
   - Latenz-Optimierung

## Fehlerbehebung

### Verbindungsprobleme

**Problem**: Kann nicht zu Raspberry Pi verbinden
- **Lösung**: Prüfen Sie, ob beide Geräte im selben Netzwerk sind
- **Lösung**: Firewall-Einstellungen auf dem Raspberry Pi prüfen
- **Lösung**: Port 8000 ist auf dem Raspberry Pi zugänglich

**Problem**: Verbindung bricht ab
- **Lösung**: WLAN-Stabilität prüfen
- **Lösung**: Auto-Reconnect in Einstellungen aktivieren
- **Lösung**: Näher zum WLAN-Router bewegen

### Audio-Probleme

**Problem**: Kein Audio-Signal erkannt
- **Lösung**: Mikrofon-Berechtigung in Windows-Einstellungen prüfen
- **Lösung**: Anderes Mikrofon in der Dropdown-Liste auswählen
- **Lösung**: Mikrofon-Pegel in Windows-Sound-Einstellungen erhöhen

**Problem**: Schlechte Audio-Qualität
- **Lösung**: Hintergrundgeräusche reduzieren
- **Lösung**: Näher zum Mikrofon sprechen
- **Lösung**: USB-Mikrofon anstatt eingebautes Mikrofon verwenden

### Anwendungsprobleme

**Problem**: Anwendung startet nicht
- **Lösung**: .NET 6.0 Runtime installieren
- **Lösung**: Windows-Updates installieren
- **Lösung**: Als Administrator ausführen

**Problem**: Hohe CPU-/Speichernutzung
- **Lösung**: Audio-Puffergröße in Einstellungen reduzieren
- **Lösung**: Andere Anwendungen schließen
- **Lösung**: Anwendung neu starten

**Problem**: UI reagiert nicht
- **Lösung**: Anwendung über Task-Manager beenden und neu starten
- **Lösung**: Einstellungsdatei löschen: `%APPDATA%\VoiceRecognitionClient\settings.json`
- **Lösung**: Windows-Kompatibilitätsmodus testen

## Entwicklung

### Projektstruktur

```
VoiceRecognitionClient/
├── App.xaml/App.xaml.cs          # Application entry point
├── Views/
│   ├── MainWindow.xaml/cs         # Main application window
│   └── SettingsWindow.xaml/cs     # Settings dialog
├── ViewModels/
│   ├── MainViewModel.cs           # Main window logic
│   └── SettingsViewModel.cs       # Settings logic
├── Services/
│   ├── AudioService.cs            # NAudio wrapper
│   ├── WebSocketService.cs        # WebSocket client
│   ├── DeviceDiscoveryService.cs  # Network device discovery
│   ├── NotificationService.cs     # System notifications
│   └── SettingsService.cs         # Configuration management
├── Models/                        # Data models
├── Converters/                    # XAML value converters
└── Assets/                        # Images, icons, etc.
```

### Architektur

- **MVVM Pattern**: Model-View-ViewModel für saubere Trennung
- **Dependency Injection**: Microsoft.Extensions.DependencyInjection
- **Modern WPF**: Moderne UI-Komponenten und Themes
- **NAudio**: Professionelle Audio-Verarbeitung
- **WebSocket Sharp**: Stabile WebSocket-Implementierung

### Build-Prozess

```powershell
# Development build
dotnet build

# Run tests
dotnet test

# Create release package
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true

# Create installer (optional)
# Using Advanced Installer, Inno Setup, or WiX Toolset
```

### Debugging

1. **Visual Studio**
   ```powershell
   # Open in Visual Studio
   start VoiceRecognitionClient.sln
   ```

2. **VS Code**
   ```powershell
   # Open in VS Code
   code .
   ```

3. **Command Line Debugging**
   ```powershell
   # Enable detailed logging
   $env:DOTNET_LOGGING_LEVEL="Debug"
   dotnet run
   ```

### Tests

```powershell
# Run all tests
dotnet test

# Run with coverage
dotnet test --collect:"XPlat Code Coverage"

# Run specific test category
dotnet test --filter Category=Integration
```

## Performance-Optimierung

### Audio-Performance
- **Puffergröße**: Kleinere Puffer = weniger Latenz, höhere CPU-Last
- **Abtastrate**: 16kHz für Spracherkennung optimal
- **Mono-Audio**: Reduziert Bandbreite um 50%

### Netzwerk-Performance
- **WebSocket-Komprimierung**: Automatisch aktiviert
- **Adaptive Qualität**: Dynamische Anpassung bei schlechter Verbindung
- **Connection Pooling**: Wiederverwendung von Verbindungen

### UI-Performance
- **Virtualisierung**: Große Listen werden virtualisiert
- **Background Threading**: UI bleibt responsiv
- **Speicher-Management**: Automatische Garbage Collection

## Sicherheit

### Datenübertragung
- **TLS-Verschlüsselung**: Alle Netzwerkverbindungen verschlüsselt
- **Zertifikat-Validierung**: Optionale Zertifikatsprüfung
- **API-Schlüssel**: Sichere Authentifizierung

### Lokale Daten
- **Verschlüsselte Einstellungen**: Sensitive Daten verschlüsselt gespeichert
- **Kein Audio-Cache**: Audio wird nicht lokal gespeichert
- **Sichere Löschung**: Temporäre Daten werden sicher überschrieben

### Berechtigungen
- **Mikrofon-Zugriff**: Nur bei aktiver Nutzung
- **Netzwerk-Zugriff**: Nur zu konfigurierten Raspberry Pi Geräten
- **Dateisystem**: Nur in Anwendungsordnern

## Lizenz

MIT License - siehe LICENSE-Datei für Details.

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/voice-recog-pi/issues)
- **Dokumentation**: [Wiki](https://github.com/your-org/voice-recog-pi/wiki)
- **Community**: [Discord](https://discord.gg/voice-recog)
- **Email**: support@voice-recog.example.com

## Beitragen

1. Repository forken
2. Feature-Branch erstellen (`git checkout -b feature/neues-feature`)
3. Änderungen committen (`git commit -am 'Neues Feature hinzugefügt'`)
4. Branch pushen (`git push origin feature/neues-feature`)
5. Pull Request erstellen

## Changelog

### Version 1.0.0
- Erste stabile Version
- Grundlegende Spracherkennungsfunktionalität
- Moderne WPF-UI
- Automatische Geräteerkennung
- System-Tray-Integration

### Geplante Features
- **Multi-Speaker-Training**: Training neuer Sprecher über UI
- **Audio-Effekte**: Rauschunterdrückung, Echo-Cancellation
- **Cloud-Sync**: Synchronisation von Einstellungen zwischen Geräten
- **Plugin-System**: Erweiterbare Funktionalität
- **Dark/Light Theme**: Automatischer Theme-Wechsel