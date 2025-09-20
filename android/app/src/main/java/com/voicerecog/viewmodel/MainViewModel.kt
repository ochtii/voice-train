package com.voicerecog.android.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.voicerecog.android.repository.AudioRepository
import com.voicerecog.android.repository.DeviceRepository
import com.voicerecog.android.repository.SettingsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject

/**
 * Main ViewModel for the Voice Recognition Android client
 */
@HiltViewModel
class MainViewModel @Inject constructor(
    private val audioRepository: AudioRepository,
    private val deviceRepository: DeviceRepository,
    private val settingsRepository: SettingsRepository
) : ViewModel() {

    data class UiState(
        val connectionState: String = "disconnected",
        val isStreaming: Boolean = false,
        val audioLevel: Float = 0f,
        val currentSpeaker: String? = null,
        val confidence: Float = 0f,
        val recentResults: List<String> = emptyList(),
        val availableDevices: List<String> = emptyList(),
        val connectedDevice: String? = null,
        val settings: Map<String, Any> = emptyMap(),
        val permissionsGranted: Boolean = false,
        val isLoading: Boolean = false,
        val errorMessage: String? = null
    )

    private val _uiState = MutableStateFlow(UiState())
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    init {
        observeConnectionState()
        observeAudioLevel()
        observeRecognitionResults()
        observeDeviceList()
        loadSettings()
    }

    private fun observeConnectionState() {
        viewModelScope.launch {
            deviceRepository.connectionState
                .collect { state ->
                    _uiState.update { currentState ->
                        currentState.copy(connectionState = state)
                    }
                }
        }
    }

    private fun observeAudioLevel() {
        viewModelScope.launch {
            audioRepository.audioLevel
                .collect { level ->
                    _uiState.update { currentState ->
                        currentState.copy(audioLevel = level)
                    }
                }
        }
    }

    private fun observeRecognitionResults() {
        viewModelScope.launch {
            deviceRepository.recognitionResults
                .collect { result ->
                    _uiState.update { currentState ->
                        val newResults = listOf(result.speakerName) + currentState.recentResults
                        currentState.copy(
                            currentSpeaker = result.speakerName,
                            confidence = result.confidence,
                            recentResults = newResults.take(10) // Keep last 10 results
                        )
                    }
                }
        }
    }

    private fun observeDeviceList() {
        viewModelScope.launch {
            deviceRepository.availableDevices
                .collect { devices ->
                    _uiState.update { currentState ->
                        currentState.copy(availableDevices = devices)
                    }
                }
        }
    }

    private fun loadSettings() {
        viewModelScope.launch {
            settingsRepository.getAllSettings()
                .collect { settings ->
                    _uiState.update { currentState ->
                        currentState.copy(settings = settings)
                    }
                }
        }
    }

    fun onPermissionsGranted() {
        Timber.i("Permissions granted")
        _uiState.update { it.copy(permissionsGranted = true) }
        
        // Auto-connect if enabled
        val autoConnect = _uiState.value.settings["auto_connect"] as? Boolean ?: false
        if (autoConnect) {
            connectToRaspberryPi()
        }
    }

    fun onPermissionsDenied() {
        Timber.w("Permissions denied")
        _uiState.update { 
            it.copy(
                permissionsGranted = false,
                errorMessage = "Audio and Bluetooth permissions are required for the app to function"
            )
        }
    }

    fun connectToRaspberryPi() {
        viewModelScope.launch {
            try {
                _uiState.update { it.copy(isLoading = true, errorMessage = null) }
                
                val success = deviceRepository.connectToRaspberryPi()
                if (!success) {
                    _uiState.update { 
                        it.copy(
                            errorMessage = "Failed to connect to Raspberry Pi",
                            isLoading = false
                        )
                    }
                }
            } catch (e: Exception) {
                Timber.e(e, "Error connecting to Raspberry Pi")
                _uiState.update { 
                    it.copy(
                        errorMessage = "Connection error: ${e.message}",
                        isLoading = false
                    )
                }
            } finally {
                _uiState.update { it.copy(isLoading = false) }
            }
        }
    }

    fun disconnect() {
        viewModelScope.launch {
            try {
                deviceRepository.disconnect()
                stopAudioStreaming()
            } catch (e: Exception) {
                Timber.e(e, "Error disconnecting")
            }
        }
    }

    fun startAudioStreaming() {
        if (!_uiState.value.permissionsGranted) {
            _uiState.update { it.copy(errorMessage = "Audio permission required") }
            return
        }
        
        if (_uiState.value.connectionState != "connected") {
            _uiState.update { it.copy(errorMessage = "Must be connected to Raspberry Pi first") }
            return
        }

        viewModelScope.launch {
            try {
                audioRepository.startStreaming()
                _uiState.update { it.copy(isStreaming = true, errorMessage = null) }
                Timber.i("Audio streaming started")
            } catch (e: Exception) {
                Timber.e(e, "Error starting audio streaming")
                _uiState.update { 
                    it.copy(errorMessage = "Failed to start audio streaming: ${e.message}")
                }
            }
        }
    }

    fun stopAudioStreaming() {
        viewModelScope.launch {
            try {
                audioRepository.stopStreaming()
                _uiState.update { it.copy(isStreaming = false) }
                Timber.i("Audio streaming stopped")
            } catch (e: Exception) {
                Timber.e(e, "Error stopping audio streaming")
            }
        }
    }

    fun scanForDevices() {
        viewModelScope.launch {
            try {
                _uiState.update { it.copy(isLoading = true) }
                deviceRepository.scanForDevices()
            } catch (e: Exception) {
                Timber.e(e, "Error scanning for devices")
                _uiState.update { 
                    it.copy(errorMessage = "Failed to scan for devices: ${e.message}")
                }
            } finally {
                _uiState.update { it.copy(isLoading = false) }
            }
        }
    }

    fun connectToDevice(deviceId: String) {
        viewModelScope.launch {
            try {
                _uiState.update { it.copy(isLoading = true) }
                val success = deviceRepository.connectToDevice(deviceId)
                if (success) {
                    _uiState.update { it.copy(connectedDevice = deviceId) }
                } else {
                    _uiState.update { 
                        it.copy(errorMessage = "Failed to connect to device: $deviceId")
                    }
                }
            } catch (e: Exception) {
                Timber.e(e, "Error connecting to device")
                _uiState.update { 
                    it.copy(errorMessage = "Connection error: ${e.message}")
                }
            } finally {
                _uiState.update { it.copy(isLoading = false) }
            }
        }
    }

    fun updateSettings(newSettings: Map<String, Any>) {
        viewModelScope.launch {
            try {
                settingsRepository.updateSettings(newSettings)
                Timber.i("Settings updated: $newSettings")
            } catch (e: Exception) {
                Timber.e(e, "Error updating settings")
                _uiState.update { 
                    it.copy(errorMessage = "Failed to update settings: ${e.message}")
                }
            }
        }
    }

    fun clearErrorMessage() {
        _uiState.update { it.copy(errorMessage = null) }
    }

    override fun onCleared() {
        super.onCleared()
        Timber.d("MainViewModel cleared")
    }
}