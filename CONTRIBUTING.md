# Contributing to Voice Recognition Pi

Wir freuen uns über Ihr Interesse an diesem Projekt! Diese Anleitung hilft Ihnen dabei, einen wertvollen Beitrag zu leisten.

## 🚀 Quick Start für Contributors

1. **Repository forken**
   ```bash
   # Klicken Sie auf "Fork" auf der GitHub-Seite
   git clone https://github.com/IHR-USERNAME/voice-train.git
   cd voice-train
   ```

2. **Development Environment einrichten**
   ```bash
   # Development Scripts ausführen
   ./scripts/setup_dev_env.sh
   
   # Pre-commit Hooks installieren
   pip install pre-commit
   pre-commit install
   ```

3. **Feature Branch erstellen**
   ```bash
   git checkout -b feature/ihre-neue-funktion
   ```

## 📋 Contribution Guidelines

### Code Standards

**Python (Backend)**
```bash
# Code Formatting
black src/
isort src/
flake8 src/

# Type Checking
mypy src/

# Tests
pytest tests/ --cov=src
```

**Kotlin (Android)**
```bash
# Code Formatting
./gradlew ktlintFormat

# Tests
./gradlew test
./gradlew connectedAndroidTest
```

**C# (Windows)**
```bash
# Code Formatting
dotnet format

# Tests
dotnet test --collect:"XPlat Code Coverage"
```

### Commit Messages

Wir verwenden [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: neue Feature-Implementierung
fix: Bug-Fix
docs: Dokumentation aktualisiert
style: Code-Formatierung (keine logischen Änderungen)
refactor: Code-Refactoring
test: Tests hinzugefügt oder geändert
chore: Build-Prozess oder Auxiliary Tools
```

**Beispiele:**
```bash
feat(backend): add WebSocket heartbeat mechanism
fix(android): resolve Bluetooth connection timeout
docs(readme): update installation instructions
test(windows): add unit tests for AudioService
```

### Pull Request Process

1. **Vorbereitung**
   - Branch ist aktuell mit main
   - Alle Tests bestehen
   - Code Quality Checks sind erfolgreich
   - Dokumentation ist aktualisiert

2. **PR erstellen**
   - Aussagekräftiger Titel
   - Detaillierte Beschreibung der Änderungen
   - Screenshots/Videos für UI-Änderungen
   - Verlinkte Issues

3. **Review Process**
   - Mindestens 1 Approval von einem Maintainer
   - Alle CI/CD Checks müssen bestehen
   - Keine Merge-Konflikte

4. **Merge**
   - Squash and Merge für Feature Branches
   - Merge Commit für Release Branches

## 🐛 Bug Reports

### Bevor Sie einen Bug melden

- [ ] Suchen Sie in bestehenden Issues
- [ ] Reproduzieren Sie das Problem
- [ ] Sammeln Sie System-Informationen
- [ ] Erstellen Sie ein Minimal Reproduction Example

### Bug Report Template

```markdown
**Beschreibung**
Eine klare Beschreibung des Problems.

**Reproduktion**
Schritte zur Reproduktion:
1. Gehen Sie zu '...'
2. Klicken Sie auf '...'
3. Scrollen Sie nach unten zu '...'
4. Siehe Fehler

**Erwartetes Verhalten**
Was sollte eigentlich passieren.

**Screenshots**
Falls zutreffend, fügen Sie Screenshots hinzu.

**System-Informationen:**
- OS: [z.B. Windows 11, Ubuntu 22.04, Android 13]
- Browser [z.B. Chrome 120, Safari 17]
- Version [z.B. 1.0.0]

**Zusätzlicher Kontext**
Weitere relevante Informationen.

**Logs**
```
Relevante Log-Ausgaben hier einfügen
```
```

## ✨ Feature Requests

### Feature Request Template

```markdown
**Ist Ihr Feature Request mit einem Problem verbunden?**
Eine klare Beschreibung des Problems. Ex. Ich bin immer frustriert, wenn [...]

**Beschreiben Sie die gewünschte Lösung**
Eine klare Beschreibung dessen, was Sie sich wünschen.

**Beschreiben Sie Alternativen**
Eine klare Beschreibung alternativer Lösungen oder Features, die Sie in Betracht gezogen haben.

**Zusätzlicher Kontext**
Weitere relevante Informationen oder Screenshots zum Feature Request.

**Aufwand-Schätzung**
- [ ] Kleines Feature (< 1 Tag)
- [ ] Mittleres Feature (1-3 Tage) 
- [ ] Großes Feature (> 3 Tage)

**Priorität**
- [ ] Nice to have
- [ ] Wichtig
- [ ] Kritisch
```

## 🏗️ Development Setup

### Voraussetzungen

**Allgemein:**
- Git 2.30+
- Docker 20.10+
- VS Code (empfohlen)

**Backend (Python):**
- Python 3.11+
- Poetry oder pip
- Redis (für Caching)
- PostgreSQL (optional)

**Android:**
- Android Studio 2023.3+
- Android SDK 34+
- Java 17+

**Windows:**
- .NET 6.0 SDK
- Visual Studio 2022 (empfohlen)

**Web UI:**
- Node.js 18+
- npm 9+

### Projekt Setup

```bash
# 1. Repository klonen
git clone https://github.com/ochtii/voice-train.git
cd voice-train

# 2. Backend Setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Android Setup
cd ../android
./gradlew build

# 4. Windows Setup
cd ../windows
dotnet restore
dotnet build

# 5. Web UI Setup
cd ../webui
npm install

# 6. Pre-commit Hooks
pip install pre-commit
pre-commit install
```

### Development Commands

```bash
# Backend starten
cd backend && python main.py

# Android App installieren
cd android && ./gradlew installDebug

# Windows App starten
cd windows && dotnet run

# Web UI starten
cd webui && npm start

# Alle Tests ausführen
./scripts/run_tests.sh

# Code Quality Check
./scripts/check_code_quality.sh
```

## 🧪 Testing

### Test-Kategorien

1. **Unit Tests**: Einzelne Funktionen/Methoden
2. **Integration Tests**: Komponenten-Interaktionen  
3. **E2E Tests**: Vollständige User Workflows
4. **Performance Tests**: Latenz, Durchsatz, Ressourcenverbrauch

### Test Guidelines

- **AAA Pattern**: Arrange, Act, Assert
- **Descriptive Names**: Test-Namen beschreiben das gewünschte Verhalten
- **Isolation**: Tests sind unabhängig voneinander
- **Repeatability**: Tests liefern konsistente Ergebnisse

**Beispiel (Python):**
```python
def test_audio_processor_should_extract_mfcc_features_from_audio_chunk():
    # Arrange
    processor = AudioProcessor(sample_rate=16000)
    audio_chunk = generate_test_audio_chunk(duration=1.0, frequency=440)
    
    # Act
    features = processor.extract_mfcc_features(audio_chunk)
    
    # Assert
    assert features.shape == (13, 99)  # 13 MFCC coefficients, ~99 frames
    assert not np.isnan(features).any()
    assert features.dtype == np.float32
```

### Test Coverage

Wir streben folgende Test Coverage an:
- **Backend**: > 90%
- **Android**: > 80%
- **Windows**: > 80%
- **Web UI**: > 75%

## 📝 Dokumentation

### Code-Dokumentation

**Python (Google Style):**
```python
def extract_mfcc_features(self, audio_chunk: np.ndarray) -> np.ndarray:
    """Extract MFCC features from audio chunk.
    
    Args:
        audio_chunk: Audio data as numpy array with shape (samples,)
        
    Returns:
        MFCC features with shape (n_mfcc, n_frames)
        
    Raises:
        ValueError: If audio_chunk is empty or has wrong dimensions
        
    Example:
        >>> processor = AudioProcessor()
        >>> audio = np.random.randn(16000)  # 1 second at 16kHz
        >>> features = processor.extract_mfcc_features(audio)
        >>> features.shape
        (13, 99)
    """
```

**Kotlin (KDoc):**
```kotlin
/**
 * Streams audio data to the Raspberry Pi via WebSocket connection.
 *
 * @param audioData Raw audio data as ByteArray
 * @param sampleRate Audio sample rate in Hz
 * @return Result indicating success or failure
 * @throws NetworkException If connection is not established
 * 
 * @sample
 * ```kotlin
 * val audioData = recorder.getAudioData()
 * val result = streamAudio(audioData, 16000)
 * if (result.isSuccess) {
 *     println("Audio sent successfully")
 * }
 * ```
 */
```

### README-Updates

Bei Änderungen an APIs oder Features:
- Haupt-README aktualisieren
- Komponenten-spezifische READMEs aktualisieren
- Code-Beispiele testen
- Screenshots/Videos aktualisieren

## 🏷️ Release Process

### Versioning

Wir verwenden [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking Changes
- **MINOR**: Neue Features (rückwärtskompatibel)
- **PATCH**: Bug Fixes

### Release Checklist

- [ ] Alle Tests bestehen
- [ ] Dokumentation ist aktuell
- [ ] CHANGELOG.md aktualisiert
- [ ] Version in allen package.json/pubspec.yaml/.csproj erhöht
- [ ] Git Tag erstellt
- [ ] Release Notes geschrieben
- [ ] Deployment getestet

## 🤝 Community

### Kommunikation

- **GitHub Issues**: Bug Reports, Feature Requests
- **GitHub Discussions**: Allgemeine Fragen, Ideen
- **Discord**: Real-time Chat (Link im README)
- **Email**: security@voice-recog.example.com (nur für Sicherheitsprobleme)

### Code of Conduct

Wir folgen dem [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/):

- **Be Respectful**: Respektieren Sie unterschiedliche Meinungen
- **Be Collaborative**: Arbeiten Sie konstruktiv zusammen
- **Be Inclusive**: Fördern Sie eine einladende Umgebung
- **Be Professional**: Halten Sie Diskussionen sachlich

### Recognition

Contributors werden in folgenden Bereichen anerkannt:
- **README Contributors Section**
- **Release Notes Mentions**
- **Annual Contributor Awards**
- **Conference Speaking Opportunities**

## ❓ FAQ

**Q: Wie kann ich als Anfänger beitragen?**
A: Schauen Sie nach Issues mit dem Label "good first issue" oder "help wanted". Diese sind speziell für neue Contributors geeignet.

**Q: Muss ich alle Tests lokal ausführen?**
A: Die wichtigsten Tests sollten lokal laufen. CI/CD führt alle Tests automatisch aus.

**Q: Wie lange dauert ein Review?**
A: Typischerweise 1-3 Werktage. Komplexe PRs können länger dauern.

**Q: Kann ich an mehreren Features gleichzeitig arbeiten?**
A: Ja, aber erstellen Sie separate Branches und PRs für jedes Feature.

**Q: Was passiert, wenn mein PR abgelehnt wird?**
A: Sie erhalten detailliertes Feedback und können Änderungen vornehmen oder eine Diskussion starten.

## 📞 Hilfe bekommen

Wenn Sie Hilfe benötigen:

1. **Dokumentation lesen**: README, Wiki, Code-Kommentare
2. **Issues durchsuchen**: Vielleicht wurde Ihr Problem schon gelöst
3. **Discussion erstellen**: Für allgemeine Fragen
4. **Issue erstellen**: Für konkrete Probleme
5. **Discord beitreten**: Für schnelle Hilfe

---

**Vielen Dank für Ihren Beitrag! 🎉**

*Zusammen machen wir Voice Recognition für alle zugänglich.*