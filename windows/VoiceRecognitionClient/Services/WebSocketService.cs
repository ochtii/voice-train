using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Newtonsoft.Json;
using System;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using WebSocketSharp;

namespace VoiceRecognitionClient.Services
{
    public interface IWebSocketService
    {
        event EventHandler<ConnectionStateEventArgs>? ConnectionStateChanged;
        event EventHandler<RecognitionResultEventArgs>? RecognitionResultReceived;
        event EventHandler<ErrorEventArgs>? ErrorOccurred;
        
        Task<bool> ConnectAsync(string host, int port);
        Task DisconnectAsync();
        Task SendAudioDataAsync(byte[] audioData);
        Task SendMessageAsync(string message);
        bool IsConnected { get; }
        ConnectionState CurrentState { get; }
        string? LastError { get; }
    }

    public class WebSocketService : IWebSocketService, IDisposable
    {
        private readonly ILogger<WebSocketService> _logger;
        private readonly RaspberryPiSettings _settings;
        
        private WebSocket? _webSocket;
        private CancellationTokenSource? _cancellationTokenSource;
        private ConnectionState _currentState = ConnectionState.Disconnected;
        private string? _lastError;
        private Timer? _heartbeatTimer;
        private DateTime _lastHeartbeat = DateTime.UtcNow;

        public event EventHandler<ConnectionStateEventArgs>? ConnectionStateChanged;
        public event EventHandler<RecognitionResultEventArgs>? RecognitionResultReceived;
        public event EventHandler<ErrorEventArgs>? ErrorOccurred;

        public bool IsConnected => _currentState == ConnectionState.Connected;
        public ConnectionState CurrentState => _currentState;
        public string? LastError => _lastError;

        public WebSocketService(ILogger<WebSocketService> logger, IOptions<VoiceRecognitionSettings> settings)
        {
            _logger = logger;
            _settings = settings.Value.RaspberryPi;
        }

        public async Task<bool> ConnectAsync(string host, int port)
        {
            try
            {
                if (IsConnected)
                {
                    _logger.LogWarning("Already connected, disconnecting first");
                    await DisconnectAsync();
                }

                SetConnectionState(ConnectionState.Connecting);
                _cancellationTokenSource = new CancellationTokenSource();

                var protocol = _settings.Port == 443 ? "wss" : "ws";
                var uri = $"{protocol}://{host}:{port}/ws/audio";
                
                _logger.LogInformation("Connecting to WebSocket: {Uri}", uri);

                await Task.Run(() =>
                {
                    _webSocket = new WebSocket(uri);
                    
                    _webSocket.OnOpen += OnWebSocketOpen;
                    _webSocket.OnMessage += OnWebSocketMessage;
                    _webSocket.OnError += OnWebSocketError;
                    _webSocket.OnClose += OnWebSocketClose;

                    // Configure WebSocket
                    _webSocket.Compression = CompressionMethod.Deflate;
                    _webSocket.WaitTime = TimeSpan.FromSeconds(_settings.ConnectionTimeout);
                    
                    if (!_settings.ValidateCertificates)
                    {
                        _webSocket.SslConfiguration.ServerCertificateValidationCallback = (sender, certificate, chain, sslPolicyErrors) => true;
                    }

                    _webSocket.Connect();
                });

                // Wait for connection to establish or timeout
                var connectTimeout = TimeSpan.FromSeconds(_settings.ConnectionTimeout);
                var startTime = DateTime.UtcNow;
                
                while (!IsConnected && DateTime.UtcNow - startTime < connectTimeout && !_cancellationTokenSource.Token.IsCancellationRequested)
                {
                    await Task.Delay(100, _cancellationTokenSource.Token);
                }

                if (IsConnected)
                {
                    StartHeartbeat();
                    _logger.LogInformation("Successfully connected to WebSocket");
                    return true;
                }
                else
                {
                    SetConnectionState(ConnectionState.Disconnected);
                    _lastError = "Connection timeout";
                    _logger.LogError("Connection timeout after {Timeout} seconds", _settings.ConnectionTimeout);
                    return false;
                }
            }
            catch (Exception ex)
            {
                _lastError = ex.Message;
                SetConnectionState(ConnectionState.Disconnected);
                _logger.LogError(ex, "Error connecting to WebSocket");
                ErrorOccurred?.Invoke(this, new ErrorEventArgs(ex));
                return false;
            }
        }

        public async Task DisconnectAsync()
        {
            try
            {
                SetConnectionState(ConnectionState.Disconnecting);
                
                _cancellationTokenSource?.Cancel();
                StopHeartbeat();

                if (_webSocket != null)
                {
                    await Task.Run(() =>
                    {
                        if (_webSocket.ReadyState == WebSocketState.Open)
                        {
                            _webSocket.Close(CloseStatusCode.Normal, "Client disconnect");
                        }
                        _webSocket = null;
                    });
                }

                SetConnectionState(ConnectionState.Disconnected);
                _logger.LogInformation("Disconnected from WebSocket");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error disconnecting from WebSocket");
                SetConnectionState(ConnectionState.Disconnected);
            }
            finally
            {
                _cancellationTokenSource?.Dispose();
                _cancellationTokenSource = null;
            }
        }

        public async Task SendAudioDataAsync(byte[] audioData)
        {
            try
            {
                if (!IsConnected || _webSocket == null)
                {
                    throw new InvalidOperationException("Not connected to WebSocket");
                }

                await Task.Run(() =>
                {
                    _webSocket.Send(audioData);
                });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error sending audio data");
                ErrorOccurred?.Invoke(this, new ErrorEventArgs(ex));
                throw;
            }
        }

        public async Task SendMessageAsync(string message)
        {
            try
            {
                if (!IsConnected || _webSocket == null)
                {
                    throw new InvalidOperationException("Not connected to WebSocket");
                }

                await Task.Run(() =>
                {
                    _webSocket.Send(message);
                });

                _logger.LogDebug("Sent message: {Message}", message);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error sending message");
                ErrorOccurred?.Invoke(this, new ErrorEventArgs(ex));
                throw;
            }
        }

        private void OnWebSocketOpen(object? sender, EventArgs e)
        {
            SetConnectionState(ConnectionState.Connected);
            _lastError = null;
            _logger.LogInformation("WebSocket connection opened");
        }

        private void OnWebSocketMessage(object? sender, MessageEventArgs e)
        {
            try
            {
                _lastHeartbeat = DateTime.UtcNow;

                if (e.IsText)
                {
                    ProcessTextMessage(e.Data);
                }
                else if (e.IsBinary)
                {
                    ProcessBinaryMessage(e.RawData);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing WebSocket message");
                ErrorOccurred?.Invoke(this, new ErrorEventArgs(ex));
            }
        }

        private void OnWebSocketError(object? sender, WebSocketSharp.ErrorEventArgs e)
        {
            _lastError = e.Message;
            _logger.LogError("WebSocket error: {Message}", e.Message);
            ErrorOccurred?.Invoke(this, new ErrorEventArgs(new Exception(e.Message)));
        }

        private void OnWebSocketClose(object? sender, CloseEventArgs e)
        {
            SetConnectionState(ConnectionState.Disconnected);
            _logger.LogInformation("WebSocket connection closed: {Reason}", e.Reason);

            if (!e.WasClean)
            {
                _logger.LogWarning("WebSocket closed unexpectedly, attempting reconnect");
                _ = Task.Run(AttemptReconnect);
            }
        }

        private void ProcessTextMessage(string message)
        {
            try
            {
                var jsonMessage = JsonConvert.DeserializeObject<WebSocketMessage>(message);
                
                switch (jsonMessage?.Type?.ToLowerInvariant())
                {
                    case "recognition_result":
                        var result = JsonConvert.DeserializeObject<RecognitionResult>(jsonMessage.Data?.ToString() ?? "{}");
                        if (result != null)
                        {
                            RecognitionResultReceived?.Invoke(this, new RecognitionResultEventArgs(result));
                        }
                        break;

                    case "ping":
                        _ = SendMessageAsync(JsonConvert.SerializeObject(new WebSocketMessage { Type = "pong" }));
                        break;

                    case "error":
                        var errorMsg = jsonMessage.Data?.ToString() ?? "Unknown error";
                        _logger.LogError("Server error: {Error}", errorMsg);
                        ErrorOccurred?.Invoke(this, new ErrorEventArgs(new Exception(errorMsg)));
                        break;

                    default:
                        _logger.LogDebug("Received unknown message type: {Type}", jsonMessage?.Type);
                        break;
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing text message: {Message}", message);
            }
        }

        private void ProcessBinaryMessage(byte[] data)
        {
            _logger.LogDebug("Received binary message of {Size} bytes", data.Length);
            // Handle binary messages if needed
        }

        private void SetConnectionState(ConnectionState newState)
        {
            if (_currentState != newState)
            {
                var oldState = _currentState;
                _currentState = newState;
                
                _logger.LogInformation("Connection state changed: {OldState} -> {NewState}", oldState, newState);
                ConnectionStateChanged?.Invoke(this, new ConnectionStateEventArgs(oldState, newState));
            }
        }

        private void StartHeartbeat()
        {
            StopHeartbeat();
            
            _heartbeatTimer = new Timer(HeartbeatCallback, null, TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(30));
            _logger.LogDebug("Started heartbeat timer");
        }

        private void StopHeartbeat()
        {
            _heartbeatTimer?.Dispose();
            _heartbeatTimer = null;
            _logger.LogDebug("Stopped heartbeat timer");
        }

        private void HeartbeatCallback(object? state)
        {
            try
            {
                if (IsConnected)
                {
                    var timeSinceLastHeartbeat = DateTime.UtcNow - _lastHeartbeat;
                    
                    if (timeSinceLastHeartbeat > TimeSpan.FromMinutes(2))
                    {
                        _logger.LogWarning("No heartbeat received for {Duration}, connection may be dead", timeSinceLastHeartbeat);
                        _ = Task.Run(AttemptReconnect);
                    }
                    else
                    {
                        _ = SendMessageAsync(JsonConvert.SerializeObject(new WebSocketMessage { Type = "ping" }));
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in heartbeat callback");
            }
        }

        private async Task AttemptReconnect()
        {
            try
            {
                _logger.LogInformation("Attempting to reconnect...");
                
                for (int attempt = 1; attempt <= _settings.MaxReconnectAttempts; attempt++)
                {
                    if (_cancellationTokenSource?.Token.IsCancellationRequested == true)
                        break;

                    _logger.LogInformation("Reconnect attempt {Attempt}/{MaxAttempts}", attempt, _settings.MaxReconnectAttempts);
                    
                    await Task.Delay(_settings.ReconnectDelay, _cancellationTokenSource?.Token ?? CancellationToken.None);
                    
                    // Use last known connection details
                    var success = await ConnectAsync(_settings.DefaultHost, _settings.Port);
                    
                    if (success)
                    {
                        _logger.LogInformation("Reconnection successful after {Attempts} attempts", attempt);
                        return;
                    }
                }

                _logger.LogError("Failed to reconnect after {MaxAttempts} attempts", _settings.MaxReconnectAttempts);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error during reconnection attempts");
            }
        }

        public void Dispose()
        {
            try
            {
                DisconnectAsync().Wait(5000);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error disposing WebSocketService");
            }
            finally
            {
                StopHeartbeat();
                _cancellationTokenSource?.Dispose();
                _webSocket = null;
            }
        }
    }

    // Enums
    public enum ConnectionState
    {
        Disconnected,
        Connecting,
        Connected,
        Disconnecting,
        Reconnecting
    }

    // Event Args
    public class ConnectionStateEventArgs : EventArgs
    {
        public ConnectionState OldState { get; }
        public ConnectionState NewState { get; }

        public ConnectionStateEventArgs(ConnectionState oldState, ConnectionState newState)
        {
            OldState = oldState;
            NewState = newState;
        }
    }

    public class RecognitionResultEventArgs : EventArgs
    {
        public RecognitionResult Result { get; }

        public RecognitionResultEventArgs(RecognitionResult result)
        {
            Result = result;
        }
    }

    // Models
    public class WebSocketMessage
    {
        [JsonProperty("type")]
        public string Type { get; set; } = string.Empty;

        [JsonProperty("data")]
        public object? Data { get; set; }

        [JsonProperty("timestamp")]
        public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    }

    public class RecognitionResult
    {
        [JsonProperty("speaker_id")]
        public string SpeakerId { get; set; } = string.Empty;

        [JsonProperty("speaker_name")]
        public string SpeakerName { get; set; } = string.Empty;

        [JsonProperty("confidence")]
        public double Confidence { get; set; }

        [JsonProperty("timestamp")]
        public DateTime Timestamp { get; set; }

        [JsonProperty("audio_duration")]
        public double AudioDuration { get; set; }

        [JsonProperty("processing_time")]
        public double ProcessingTime { get; set; }

        [JsonProperty("features")]
        public RecognitionFeatures? Features { get; set; }
    }

    public class RecognitionFeatures
    {
        [JsonProperty("mfcc_features")]
        public double[]? MfccFeatures { get; set; }

        [JsonProperty("energy_level")]
        public double EnergyLevel { get; set; }

        [JsonProperty("voice_activity")]
        public bool VoiceActivity { get; set; }

        [JsonProperty("frequency_stats")]
        public FrequencyStats? FrequencyStats { get; set; }
    }

    public class FrequencyStats
    {
        [JsonProperty("fundamental_frequency")]
        public double FundamentalFrequency { get; set; }

        [JsonProperty("spectral_centroid")]
        public double SpectralCentroid { get; set; }

        [JsonProperty("spectral_bandwidth")]
        public double SpectralBandwidth { get; set; }

        [JsonProperty("spectral_rolloff")]
        public double SpectralRolloff { get; set; }
    }
}