using Microsoft.Extensions.Logging;
using Microsoft.Toolkit.Mvvm.ComponentModel;
using Microsoft.Toolkit.Mvvm.Input;
using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Input;
using VoiceRecognitionClient.Services;

namespace VoiceRecognitionClient.ViewModels
{
    public class MainViewModel : ObservableObject
    {
        private readonly ILogger<MainViewModel> _logger;
        private readonly IAudioService _audioService;
        private readonly IWebSocketService _webSocketService;
        private readonly IDeviceDiscoveryService _deviceDiscoveryService;
        private readonly INotificationService _notificationService;
        private readonly ISettingsService _settingsService;

        // Properties
        private bool _isConnected;
        private bool _isRecording;
        private bool _isDiscovering;
        private double _audioLevel;
        private string _connectionStatus = "Getrennt";
        private string _currentDeviceName = string.Empty;
        private RaspberryPiDevice _selectedDevice;
        private RecognitionResult _lastRecognitionResult;

        public bool IsConnected
        {
            get => _isConnected;
            set => SetProperty(ref _isConnected, value);
        }

        public bool IsRecording
        {
            get => _isRecording;
            set => SetProperty(ref _isRecording, value);
        }

        public bool IsDiscovering
        {
            get => _isDiscovering;
            set => SetProperty(ref _isDiscovering, value);
        }

        public double AudioLevel
        {
            get => _audioLevel;
            set => SetProperty(ref _audioLevel, value);
        }

        public string ConnectionStatus
        {
            get => _connectionStatus;
            set => SetProperty(ref _connectionStatus, value);
        }

        public string CurrentDeviceName
        {
            get => _currentDeviceName;
            set => SetProperty(ref _currentDeviceName, value);
        }

        public RaspberryPiDevice SelectedDevice
        {
            get => _selectedDevice;
            set => SetProperty(ref _selectedDevice, value);
        }

        public RecognitionResult LastRecognitionResult
        {
            get => _lastRecognitionResult;
            set => SetProperty(ref _lastRecognitionResult, value);
        }

        // Collections
        public ObservableCollection<RaspberryPiDevice> DiscoveredDevices { get; } = new();
        public ObservableCollection<AudioDevice> AudioDevices { get; } = new();
        public ObservableCollection<RecognitionResult> RecentResults { get; } = new();

        // Commands
        public ICommand ConnectCommand { get; }
        public ICommand DisconnectCommand { get; }
        public ICommand StartRecordingCommand { get; }
        public ICommand StopRecordingCommand { get; }
        public ICommand DiscoverDevicesCommand { get; }
        public ICommand RefreshAudioDevicesCommand { get; }
        public ICommand OpenSettingsCommand { get; }

        public MainViewModel(
            ILogger<MainViewModel> logger,
            IAudioService audioService,
            IWebSocketService webSocketService,
            IDeviceDiscoveryService deviceDiscoveryService,
            INotificationService notificationService,
            ISettingsService settingsService)
        {
            _logger = logger;
            _audioService = audioService;
            _webSocketService = webSocketService;
            _deviceDiscoveryService = deviceDiscoveryService;
            _notificationService = notificationService;
            _settingsService = settingsService;

            // Initialize commands
            ConnectCommand = new AsyncRelayCommand(ConnectAsync, () => !IsConnected && SelectedDevice != null);
            DisconnectCommand = new AsyncRelayCommand(DisconnectAsync, () => IsConnected);
            StartRecordingCommand = new AsyncRelayCommand(StartRecordingAsync, () => IsConnected && !IsRecording);
            StopRecordingCommand = new AsyncRelayCommand(StopRecordingAsync, () => IsRecording);
            DiscoverDevicesCommand = new AsyncRelayCommand(DiscoverDevicesAsync, () => !IsDiscovering);
            RefreshAudioDevicesCommand = new AsyncRelayCommand(RefreshAudioDevicesAsync);
            OpenSettingsCommand = new RelayCommand(OpenSettings);

            // Subscribe to events
            SubscribeToEvents();

            // Initialize
            InitializeAsync();
        }

        private void SubscribeToEvents()
        {
            // Audio service events
            _audioService.AudioLevelChanged += OnAudioLevelChanged;
            _audioService.AudioDataReceived += OnAudioDataReceived;

            // WebSocket events
            _webSocketService.ConnectionStateChanged += OnConnectionStateChanged;
            _webSocketService.RecognitionResultReceived += OnRecognitionResultReceived;
            _webSocketService.ErrorOccurred += OnWebSocketError;

            // Device discovery events
            _deviceDiscoveryService.DeviceDiscovered += OnDeviceDiscovered;
            _deviceDiscoveryService.DiscoveryCompleted += OnDiscoveryCompleted;
        }

        private async void InitializeAsync()
        {
            try
            {
                await RefreshAudioDevicesAsync();
                await LoadSettingsAsync();
                
                if (await _settingsService.GetSettingAsync("AutoConnect", true))
                {
                    await DiscoverDevicesAsync();
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error during initialization");
                _notificationService.ShowError("Initialisierungsfehler", ex.Message);
            }
        }

        private async Task LoadSettingsAsync()
        {
            try
            {
                var settings = await _settingsService.LoadUserSettingsAsync();
                var lastDevice = settings.LastConnectedDevice;
                
                if (!string.IsNullOrEmpty(lastDevice))
                {
                    var device = DiscoveredDevices.FirstOrDefault(d => d.IpAddress == lastDevice);
                    if (device != null)
                    {
                        SelectedDevice = device;
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error loading settings");
            }
        }

        private async Task ConnectAsync()
        {
            try
            {
                if (SelectedDevice == null)
                {
                    _notificationService.ShowWarning("Kein Gerät ausgewählt", "Bitte wählen Sie ein Gerät aus der Liste aus.");
                    return;
                }

                ConnectionStatus = "Verbindung wird hergestellt...";
                
                var success = await _webSocketService.ConnectAsync(SelectedDevice.IpAddress, SelectedDevice.Port);
                
                if (success)
                {
                    IsConnected = true;
                    CurrentDeviceName = SelectedDevice.DisplayName;
                    ConnectionStatus = $"Verbunden mit {CurrentDeviceName}";
                    
                    await _settingsService.SetSettingAsync("LastConnectedDevice", SelectedDevice.IpAddress);
                    _notificationService.ShowConnectionStatus(true, CurrentDeviceName);
                    
                    _logger.LogInformation("Connected to {Device}", CurrentDeviceName);
                }
                else
                {
                    ConnectionStatus = "Verbindung fehlgeschlagen";
                    _notificationService.ShowError("Verbindungsfehler", $"Konnte nicht zu {SelectedDevice.DisplayName} verbinden");
                }
            }
            catch (Exception ex)
            {
                ConnectionStatus = "Verbindungsfehler";
                _logger.LogError(ex, "Error connecting to device");
                _notificationService.ShowError("Verbindungsfehler", ex.Message);
            }
            finally
            {
                RefreshCommands();
            }
        }

        private async Task DisconnectAsync()
        {
            try
            {
                if (IsRecording)
                {
                    await StopRecordingAsync();
                }

                await _webSocketService.DisconnectAsync();
                
                IsConnected = false;
                ConnectionStatus = "Getrennt";
                CurrentDeviceName = string.Empty;
                
                _notificationService.ShowConnectionStatus(false, "Gerät");
                _logger.LogInformation("Disconnected from device");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error disconnecting from device");
                _notificationService.ShowError("Trennungsfehler", ex.Message);
            }
            finally
            {
                RefreshCommands();
            }
        }

        private async Task StartRecordingAsync()
        {
            try
            {
                await _audioService.StartRecordingAsync();
                IsRecording = true;
                
                _notificationService.ShowInfo("Aufnahme gestartet", "Audioaufnahme läuft");
                _logger.LogInformation("Audio recording started");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error starting audio recording");
                _notificationService.ShowError("Aufnahmefehler", ex.Message);
            }
            finally
            {
                RefreshCommands();
            }
        }

        private async Task StopRecordingAsync()
        {
            try
            {
                await _audioService.StopRecordingAsync();
                IsRecording = false;
                AudioLevel = 0;
                
                _notificationService.ShowInfo("Aufnahme gestoppt", "Audioaufnahme beendet");
                _logger.LogInformation("Audio recording stopped");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error stopping audio recording");
                _notificationService.ShowError("Stoppfehler", ex.Message);
            }
            finally
            {
                RefreshCommands();
            }
        }

        private async Task DiscoverDevicesAsync()
        {
            try
            {
                IsDiscovering = true;
                DiscoveredDevices.Clear();
                
                _logger.LogInformation("Starting device discovery");
                var devices = await _deviceDiscoveryService.DiscoverDevicesAsync();
                
                foreach (var device in devices)
                {
                    DiscoveredDevices.Add(device);
                }

                if (DiscoveredDevices.Count == 0)
                {
                    _notificationService.ShowWarning("Keine Geräte gefunden", "Es wurden keine Raspberry Pi Geräte im Netzwerk gefunden.");
                }
                else
                {
                    _notificationService.ShowSuccess("Geräte gefunden", $"{DiscoveredDevices.Count} Gerät(e) gefunden");
                    
                    if (SelectedDevice == null && DiscoveredDevices.Count > 0)
                    {
                        SelectedDevice = DiscoveredDevices.First();
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error during device discovery");
                _notificationService.ShowError("Suchfehler", ex.Message);
            }
            finally
            {
                IsDiscovering = false;
                RefreshCommands();
            }
        }

        private async Task RefreshAudioDevicesAsync()
        {
            try
            {
                AudioDevices.Clear();
                
                var devices = await _audioService.GetInputDevicesAsync();
                foreach (var device in devices)
                {
                    AudioDevices.Add(device);
                }

                _logger.LogInformation("Refreshed audio devices, found {Count} devices", AudioDevices.Count);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error refreshing audio devices");
                _notificationService.ShowError("Audiofehler", "Konnte Audiogeräte nicht laden");
            }
        }

        private void OpenSettings()
        {
            // This would open a settings window
            _logger.LogInformation("Opening settings");
        }

        // Event handlers
        private void OnAudioLevelChanged(object sender, AudioLevelEventArgs e)
        {
            AudioLevel = e.Level;
        }

        private async void OnAudioDataReceived(object sender, AudioDataEventArgs e)
        {
            try
            {
                if (IsConnected && _webSocketService.IsConnected)
                {
                    await _webSocketService.SendAudioDataAsync(e.Data[..e.BytesRecorded]);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error sending audio data");
            }
        }

        private void OnConnectionStateChanged(object sender, ConnectionStateEventArgs e)
        {
            System.Windows.Application.Current.Dispatcher.Invoke(() =>
            {
                IsConnected = e.NewState == ConnectionState.Connected;
                
                ConnectionStatus = e.NewState switch
                {
                    ConnectionState.Connecting => "Verbindung wird hergestellt...",
                    ConnectionState.Connected => $"Verbunden mit {CurrentDeviceName}",
                    ConnectionState.Disconnecting => "Verbindung wird getrennt...",
                    ConnectionState.Disconnected => "Getrennt",
                    ConnectionState.Reconnecting => "Verbindung wird wiederhergestellt...",
                    _ => "Unbekannt"
                };
                
                RefreshCommands();
            });
        }

        private void OnRecognitionResultReceived(object sender, RecognitionResultEventArgs e)
        {
            System.Windows.Application.Current.Dispatcher.Invoke(() =>
            {
                LastRecognitionResult = e.Result;
                RecentResults.Insert(0, e.Result);
                
                // Keep only last 50 results
                while (RecentResults.Count > 50)
                {
                    RecentResults.RemoveAt(RecentResults.Count - 1);
                }
                
                _notificationService.ShowRecognitionResult(e.Result.SpeakerName, e.Result.Confidence);
                _logger.LogInformation("Recognition result: {Speaker} ({Confidence:P1})", 
                    e.Result.SpeakerName, e.Result.Confidence);
            });
        }

        private void OnWebSocketError(object sender, ErrorEventArgs e)
        {
            System.Windows.Application.Current.Dispatcher.Invoke(() =>
            {
                _notificationService.ShowError("WebSocket Fehler", e.Message);
                _logger.LogError("WebSocket error: {Error}", e.Message);
            });
        }

        private void OnDeviceDiscovered(object sender, DeviceDiscoveredEventArgs e)
        {
            System.Windows.Application.Current.Dispatcher.Invoke(() =>
            {
                DiscoveredDevices.Add(e.Device);
                _logger.LogDebug("Device discovered: {Device}", e.Device.DisplayName);
            });
        }

        private void OnDiscoveryCompleted(object sender, DiscoveryCompletedEventArgs e)
        {
            System.Windows.Application.Current.Dispatcher.Invoke(() =>
            {
                IsDiscovering = false;
                RefreshCommands();
                _logger.LogInformation("Device discovery completed, found {Count} devices", e.Devices.Count());
            });
        }

        private void RefreshCommands()
        {
            (ConnectCommand as AsyncRelayCommand)?.NotifyCanExecuteChanged();
            (DisconnectCommand as AsyncRelayCommand)?.NotifyCanExecuteChanged();
            (StartRecordingCommand as AsyncRelayCommand)?.NotifyCanExecuteChanged();
            (StopRecordingCommand as AsyncRelayCommand)?.NotifyCanExecuteChanged();
            (DiscoverDevicesCommand as AsyncRelayCommand)?.NotifyCanExecuteChanged();
        }
    }
}