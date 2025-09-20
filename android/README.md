# Voice Recognition Android Client

## Overview

Android application for streaming audio to the Raspberry Pi Zero W voice recognition system. Supports real-time audio streaming via Bluetooth SCO and WiFi WebSocket connections.

## Features

- **Real-time Audio Streaming**: Continuous microphone recording with low latency
- **Bluetooth SCO Support**: Primary audio streaming method to Raspberry Pi
- **WiFi WebSocket Fallback**: Alternative connection when Bluetooth is unavailable
- **Background Operation**: Foreground service for uninterrupted audio streaming
- **Device Discovery**: Automatic discovery of Raspberry Pi devices
- **Connection Management**: Robust connection handling with automatic reconnection
- **Material Design 3 UI**: Modern, intuitive user interface
- **Real-time Audio Visualization**: Live audio level monitoring

## Technical Stack

- **Language**: Kotlin
- **UI**: Jetpack Compose with Material Design 3
- **Architecture**: MVVM with Repository pattern
- **Dependency Injection**: Dagger Hilt
- **Networking**: OkHttp3 with WebSocket support
- **Audio**: Android AudioRecord API
- **Background Tasks**: WorkManager
- **Local Storage**: Room database and DataStore

## Requirements

### Minimum Requirements
- Android 8.0 (API level 26)
- Microphone access
- 50MB storage space
- 100MB RAM

### Recommended Requirements
- Android 10+ (API level 29)
- Bluetooth 4.0+ support
- WiFi connectivity
- 2GB RAM

## Permissions

The app requires the following permissions:

### Essential Permissions
- `RECORD_AUDIO` - For microphone access
- `BLUETOOTH` - For Bluetooth SCO connections
- `BLUETOOTH_CONNECT` - For device pairing (Android 12+)
- `INTERNET` - For WiFi connections to Raspberry Pi
- `FOREGROUND_SERVICE` - For background audio streaming

### Optional Permissions
- `ACCESS_FINE_LOCATION` - For Bluetooth device discovery
- `BLUETOOTH_SCAN` - For discovering nearby Bluetooth devices

## Installation

### From Source

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/voice-recog-pi.git
   cd voice-recog-pi/android
   ```

2. **Open in Android Studio**
   - Open Android Studio
   - Choose "Open an existing project"
   - Navigate to the `android` directory

3. **Build and install**
   ```bash
   ./gradlew assembleDebug
   adb install app/build/outputs/apk/debug/app-debug.apk
   ```

### Release APK

Download the latest release APK from the [Releases page](https://github.com/your-org/voice-recog-pi/releases).

## Configuration

### Default Settings

The app comes with sensible defaults but can be configured:

```kotlin
// In BuildConfig (build.gradle)
PI_DEFAULT_HOST = "192.168.1.100"
PI_DEFAULT_PORT = 8000

// Audio settings
SAMPLE_RATE = 16000 Hz
AUDIO_FORMAT = PCM 16-bit
CHANNELS = Mono
```

### Runtime Configuration

Settings can be changed from within the app:

1. **Auto-connect**: Automatically connect to Raspberry Pi on app startup
2. **Background streaming**: Continue streaming when app is in background
3. **Audio quality**: Adjust sample rate and bit depth
4. **Connection timeout**: Set connection retry intervals

## Usage

### First Time Setup

1. **Grant Permissions**
   - Allow microphone access
   - Enable Bluetooth permissions
   - Grant location access for device discovery

2. **Connect to Raspberry Pi**
   - Ensure Raspberry Pi is on the same network
   - Tap "Scan" to discover devices
   - Select your Raspberry Pi from the list
   - Tap "Connect"

3. **Start Audio Streaming**
   - Once connected, tap "Start Streaming"
   - Grant foreground service permission
   - Audio level indicator should show activity

### Daily Usage

1. **Quick Connect**
   - Open the app
   - If auto-connect is enabled, connection happens automatically
   - Otherwise, tap "Connect" button

2. **Monitor Recognition**
   - View real-time speaker recognition results
   - Check confidence levels
   - Review recent recognition history

3. **Background Operation**
   - Enable background streaming in settings
   - App will continue working when minimized
   - Notification shows streaming status

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to Raspberry Pi
- **Solution**: Check that both devices are on the same WiFi network
- **Solution**: Verify Raspberry Pi is running the voice recognition service
- **Solution**: Check firewall settings on Raspberry Pi

**Problem**: Bluetooth pairing fails
- **Solution**: Ensure Bluetooth is enabled on both devices
- **Solution**: Clear Bluetooth cache: Settings > Apps > Bluetooth > Storage > Clear Cache
- **Solution**: Remove existing pairing and re-pair devices

### Audio Issues

**Problem**: No audio level detected
- **Solution**: Grant microphone permission in Android settings
- **Solution**: Check if another app is using the microphone
- **Solution**: Restart the app and try again

**Problem**: Poor audio quality
- **Solution**: Move closer to the microphone
- **Solution**: Reduce background noise
- **Solution**: Check network connectivity for WiFi streaming

### Performance Issues

**Problem**: App crashes or freezes
- **Solution**: Restart the app
- **Solution**: Clear app cache: Settings > Apps > Voice Recognition > Storage > Clear Cache
- **Solution**: Update to the latest version

**Problem**: High battery usage
- **Solution**: Disable background streaming when not needed
- **Solution**: Reduce audio sample rate in settings
- **Solution**: Use Bluetooth instead of WiFi when possible

## Development

### Project Structure

```
android/
├── app/
│   ├── src/main/java/com/voicerecog/
│   │   ├── ui/                    # Compose UI screens
│   │   ├── viewmodel/             # ViewModels
│   │   ├── service/               # Background services
│   │   ├── repository/            # Data repositories
│   │   ├── network/               # Network clients
│   │   ├── bluetooth/             # Bluetooth management
│   │   ├── audio/                 # Audio processing
│   │   └── data/                  # Data models
│   └── src/test/                  # Unit tests
├── build.gradle                   # App-level build config
└── settings.gradle               # Project settings
```

### Building

```bash
# Debug build
./gradlew assembleDebug

# Release build
./gradlew assembleRelease

# Run tests
./gradlew test

# Run instrumented tests
./gradlew connectedAndroidTest
```

### Testing

The project includes comprehensive tests:

- **Unit Tests**: ViewModel logic, repositories, utility functions
- **Instrumented Tests**: UI interactions, database operations
- **Integration Tests**: End-to-end audio streaming workflows

```bash
# Run all tests
./gradlew test connectedAndroidTest

# Run specific test class
./gradlew test --tests="MainViewModelTest"

# Run with coverage
./gradlew testDebugUnitTestCoverage
```

### Code Style

The project follows Kotlin coding conventions:

```bash
# Format code
./gradlew ktlintFormat

# Check style
./gradlew ktlintCheck
```

### Adding Features

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-audio-codec
   ```

2. **Implement Feature**
   - Add UI components in `ui/` package
   - Add business logic in `viewmodel/` or `repository/`
   - Add network/data layer changes as needed

3. **Add Tests**
   - Unit tests for new logic
   - UI tests for new screens
   - Integration tests for complex workflows

4. **Update Documentation**
   - Update this README if needed
   - Add inline code documentation
   - Update API documentation

## API Integration

The app communicates with the Raspberry Pi backend via:

### WebSocket API

```kotlin
// Real-time audio streaming
ws://raspberry-pi-ip:8000/ws/audio

// Dashboard updates
ws://raspberry-pi-ip:8000/ws/dashboard
```

### REST API

```kotlin
// Authentication
POST /auth/login
GET /auth/verify

// Device management
GET /devices/list
POST /devices/pair

// Recognition status
GET /recognition/status
POST /recognition/start
```

## Security

### Data Protection
- Audio data is streamed in real-time, not stored locally
- Authentication tokens are stored securely using EncryptedSharedPreferences
- Network communication uses TLS encryption

### Permissions
- Microphone access is only used for voice recognition
- Location access is only used for Bluetooth device discovery
- No personal data is collected or transmitted

## Performance Optimization

### Audio Processing
- Uses native AudioRecord for low-latency recording
- Efficient buffer management to prevent memory leaks
- Adaptive quality based on network conditions

### Network Optimization
- WebSocket connection pooling
- Automatic reconnection with exponential backoff
- Bandwidth monitoring and adjustment

### Battery Optimization
- Foreground service for legitimate background work
- CPU-efficient audio processing algorithms
- Intelligent connection management

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/voice-recog-pi/issues)
- **Documentation**: [Wiki](https://github.com/your-org/voice-recog-pi/wiki)
- **Community**: [Discord](https://discord.gg/voice-recog)