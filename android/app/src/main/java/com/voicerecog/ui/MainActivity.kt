package com.voicerecog.android.ui

import android.Manifest
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.voicerecog.android.service.AudioStreamingService
import com.voicerecog.android.ui.theme.VoiceRecognitionClientTheme
import com.voicerecog.android.viewmodel.MainViewModel
import dagger.hilt.android.AndroidEntryPoint
import timber.log.Timber

/**
 * Main activity for the Voice Recognition Android client
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels()

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.all { it.value }
        if (allGranted) {
            Timber.i("All permissions granted")
            viewModel.onPermissionsGranted()
        } else {
            Timber.w("Some permissions denied: $permissions")
            viewModel.onPermissionsDenied()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Request necessary permissions
        requestPermissions()
        
        setContent {
            VoiceRecognitionClientTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    MainScreen(viewModel = viewModel)
                }
            }
        }
    }

    private fun requestPermissions() {
        val permissions = arrayOf(
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.BLUETOOTH,
            Manifest.permission.BLUETOOTH_ADMIN,
            Manifest.permission.BLUETOOTH_CONNECT,
            Manifest.permission.BLUETOOTH_SCAN,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        )
        
        permissionLauncher.launch(permissions)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(viewModel: MainViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    
    Column(
        modifier = Modifier.fillMaxSize()
    ) {
        // Top App Bar
        TopAppBar(
            title = { Text("Voice Recognition") },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer
            )
        )
        
        // Main content
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Connection Status Card
            item {
                ConnectionStatusCard(
                    connectionState = uiState.connectionState,
                    onConnectClick = { viewModel.connectToRaspberryPi() },
                    onDisconnectClick = { viewModel.disconnect() }
                )
            }
            
            // Audio Streaming Card
            item {
                AudioStreamingCard(
                    isStreaming = uiState.isStreaming,
                    audioLevel = uiState.audioLevel,
                    onStartStreaming = { 
                        val intent = Intent(context, AudioStreamingService::class.java)
                        intent.action = AudioStreamingService.ACTION_START_STREAMING
                        context.startForegroundService(intent)
                        viewModel.startAudioStreaming()
                    },
                    onStopStreaming = {
                        val intent = Intent(context, AudioStreamingService::class.java)
                        intent.action = AudioStreamingService.ACTION_STOP_STREAMING
                        context.stopService(intent)
                        viewModel.stopAudioStreaming()
                    }
                )
            }
            
            // Recognition Results Card
            item {
                RecognitionResultsCard(
                    currentSpeaker = uiState.currentSpeaker,
                    confidence = uiState.confidence,
                    recentResults = uiState.recentResults
                )
            }
            
            // Device List Card
            item {
                DeviceListCard(
                    devices = uiState.availableDevices,
                    connectedDevice = uiState.connectedDevice,
                    onScanDevices = { viewModel.scanForDevices() },
                    onConnectDevice = { device -> viewModel.connectToDevice(device) }
                )
            }
            
            // Settings Card
            item {
                SettingsCard(
                    settings = uiState.settings,
                    onUpdateSettings = { settings -> viewModel.updateSettings(settings) }
                )
            }
        }
    }
}

@Composable
fun ConnectionStatusCard(
    connectionState: String,
    onConnectClick: () -> Unit,
    onDisconnectClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Connection Status",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                
                Icon(
                    imageVector = when (connectionState) {
                        "connected" -> Icons.Default.CheckCircle
                        "connecting" -> Icons.Default.Refresh
                        else -> Icons.Default.Cancel
                    },
                    contentDescription = connectionState,
                    tint = when (connectionState) {
                        "connected" -> MaterialTheme.colorScheme.primary
                        "connecting" -> MaterialTheme.colorScheme.secondary
                        else -> MaterialTheme.colorScheme.error
                    }
                )
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = "Status: ${connectionState.capitalize()}",
                style = MaterialTheme.typography.bodyMedium
            )
            
            Spacer(modifier = Modifier.height(12.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = onConnectClick,
                    enabled = connectionState != "connected" && connectionState != "connecting",
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Connect")
                }
                
                OutlinedButton(
                    onClick = onDisconnectClick,
                    enabled = connectionState == "connected",
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Disconnect")
                }
            }
        }
    }
}

@Composable
fun AudioStreamingCard(
    isStreaming: Boolean,
    audioLevel: Float,
    onStartStreaming: () -> Unit,
    onStopStreaming: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Audio Streaming",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                
                Icon(
                    imageVector = if (isStreaming) Icons.Default.Mic else Icons.Default.MicOff,
                    contentDescription = if (isStreaming) "Streaming" else "Not streaming",
                    tint = if (isStreaming) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline
                )
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            if (isStreaming) {
                Text(
                    text = "Audio Level:",
                    style = MaterialTheme.typography.bodySmall
                )
                
                LinearProgressIndicator(
                    progress = audioLevel,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 8.dp)
                )
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            
            Button(
                onClick = if (isStreaming) onStopStreaming else onStartStreaming,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (isStreaming) "Stop Streaming" else "Start Streaming")
            }
        }
    }
}

@Composable
fun RecognitionResultsCard(
    currentSpeaker: String?,
    confidence: Float,
    recentResults: List<String>
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = "Recognition Results",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            if (currentSpeaker != null) {
                Text(
                    text = "Current Speaker: $currentSpeaker",
                    style = MaterialTheme.typography.bodyMedium
                )
                
                Text(
                    text = "Confidence: ${(confidence * 100).toInt()}%",
                    style = MaterialTheme.typography.bodySmall
                )
            } else {
                Text(
                    text = "No speaker detected",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.outline
                )
            }
            
            if (recentResults.isNotEmpty()) {
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "Recent Results:",
                    style = MaterialTheme.typography.bodySmall,
                    fontWeight = FontWeight.Medium
                )
                
                recentResults.take(3).forEach { result ->
                    Text(
                        text = "• $result",
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(start = 8.dp)
                    )
                }
            }
        }
    }
}

@Composable
fun DeviceListCard(
    devices: List<String>,
    connectedDevice: String?,
    onScanDevices: () -> Unit,
    onConnectDevice: (String) -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Available Devices",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                
                IconButton(onClick = onScanDevices) {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = "Scan for devices"
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            if (devices.isEmpty()) {
                Text(
                    text = "No devices found. Tap refresh to scan.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.outline
                )
            } else {
                devices.forEach { device ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = device,
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier.weight(1f)
                        )
                        
                        if (device == connectedDevice) {
                            Text(
                                text = "Connected",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.primary
                            )
                        } else {
                            TextButton(
                                onClick = { onConnectDevice(device) }
                            ) {
                                Text("Connect")
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun SettingsCard(
    settings: Map<String, Any>,
    onUpdateSettings: (Map<String, Any>) -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = "Settings",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            // Auto-connect setting
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Auto-connect on startup",
                    style = MaterialTheme.typography.bodyMedium
                )
                
                Switch(
                    checked = settings["auto_connect"] as? Boolean ?: false,
                    onCheckedChange = { checked ->
                        onUpdateSettings(settings.toMutableMap().apply {
                            put("auto_connect", checked)
                        })
                    }
                )
            }
            
            // Background streaming setting
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Background streaming",
                    style = MaterialTheme.typography.bodyMedium
                )
                
                Switch(
                    checked = settings["background_streaming"] as? Boolean ?: false,
                    onCheckedChange = { checked ->
                        onUpdateSettings(settings.toMutableMap().apply {
                            put("background_streaming", checked)
                        })
                    }
                )
            }
        }
    }
}