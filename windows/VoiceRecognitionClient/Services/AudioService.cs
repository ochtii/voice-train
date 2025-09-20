using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using NAudio.Wave;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace VoiceRecognitionClient.Services
{
    public interface IAudioService
    {
        event EventHandler<AudioDataEventArgs>? AudioDataReceived;
        event EventHandler<AudioLevelEventArgs>? AudioLevelChanged;
        event EventHandler<AudioDeviceEventArgs>? AudioDeviceChanged;
        
        Task<IEnumerable<AudioDevice>> GetInputDevicesAsync();
        Task StartRecordingAsync(int deviceId = -1);
        Task StopRecordingAsync();
        Task SetInputDeviceAsync(int deviceId);
        bool IsRecording { get; }
        AudioDevice? CurrentDevice { get; }
        double CurrentLevel { get; }
    }

    public class AudioService : IAudioService, IDisposable
    {
        private readonly ILogger<AudioService> _logger;
        private readonly AudioSettings _audioSettings;
        
        private WaveInEvent? _waveIn;
        private CancellationTokenSource? _cancellationTokenSource;
        private bool _isRecording;
        private int _currentDeviceId = -1;
        private double _currentLevel;
        private readonly object _lockObject = new();

        public event EventHandler<AudioDataEventArgs>? AudioDataReceived;
        public event EventHandler<AudioLevelEventArgs>? AudioLevelChanged;
        public event EventHandler<AudioDeviceEventArgs>? AudioDeviceChanged;

        public bool IsRecording 
        { 
            get 
            { 
                lock (_lockObject) 
                { 
                    return _isRecording; 
                } 
            } 
        }

        public AudioDevice? CurrentDevice { get; private set; }
        
        public double CurrentLevel 
        { 
            get 
            { 
                lock (_lockObject) 
                { 
                    return _currentLevel; 
                } 
            } 
        }

        public AudioService(ILogger<AudioService> logger, IOptions<VoiceRecognitionSettings> settings)
        {
            _logger = logger;
            _audioSettings = settings.Value.Audio;
            
            _logger.LogInformation("AudioService initialized with settings: SampleRate={SampleRate}, BitDepth={BitDepth}, Channels={Channels}", 
                _audioSettings.SampleRate, _audioSettings.BitDepth, _audioSettings.Channels);
        }

        public async Task<IEnumerable<AudioDevice>> GetInputDevicesAsync()
        {
            try
            {
                var devices = new List<AudioDevice>();
                
                await Task.Run(() =>
                {
                    for (int i = 0; i < WaveIn.DeviceCount; i++)
                    {
                        var capabilities = WaveIn.GetCapabilities(i);
                        devices.Add(new AudioDevice
                        {
                            Id = i,
                            Name = capabilities.ProductName,
                            Channels = capabilities.Channels,
                            IsDefault = i == 0
                        });
                    }
                });

                _logger.LogInformation("Found {DeviceCount} audio input devices", devices.Count);
                return devices;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error getting audio input devices");
                throw new AudioServiceException("Fehler beim Abrufen der Audiogeräte", ex);
            }
        }

        public async Task StartRecordingAsync(int deviceId = -1)
        {
            try
            {
                if (IsRecording)
                {
                    _logger.LogWarning("Already recording, stopping current session");
                    await StopRecordingAsync();
                }

                lock (_lockObject)
                {
                    _cancellationTokenSource = new CancellationTokenSource();
                }

                await Task.Run(() =>
                {
                    var waveFormat = new WaveFormat(_audioSettings.SampleRate, _audioSettings.BitDepth, _audioSettings.Channels);
                    
                    _waveIn = deviceId >= 0 ? new WaveInEvent { DeviceNumber = deviceId } : new WaveInEvent();
                    
                    _waveIn.WaveFormat = waveFormat;
                    _waveIn.BufferMilliseconds = _audioSettings.DeviceLatency;
                    _waveIn.DataAvailable += OnDataAvailable;
                    _waveIn.RecordingStopped += OnRecordingStopped;

                    _currentDeviceId = deviceId >= 0 ? deviceId : 0;
                    UpdateCurrentDevice();

                    _waveIn.StartRecording();
                    
                    lock (_lockObject)
                    {
                        _isRecording = true;
                    }
                });

                _logger.LogInformation("Started recording with device {DeviceId}", _currentDeviceId);
                AudioDeviceChanged?.Invoke(this, new AudioDeviceEventArgs(CurrentDevice));
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error starting audio recording");
                throw new AudioServiceException("Fehler beim Starten der Audioaufnahme", ex);
            }
        }

        public async Task StopRecordingAsync()
        {
            try
            {
                _cancellationTokenSource?.Cancel();

                await Task.Run(() =>
                {
                    _waveIn?.StopRecording();
                    _waveIn?.Dispose();
                    _waveIn = null;
                    
                    lock (_lockObject)
                    {
                        _isRecording = false;
                        _currentLevel = 0;
                    }
                });

                _cancellationTokenSource?.Dispose();
                _cancellationTokenSource = null;

                _logger.LogInformation("Stopped audio recording");
                AudioLevelChanged?.Invoke(this, new AudioLevelEventArgs(0));
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error stopping audio recording");
                throw new AudioServiceException("Fehler beim Stoppen der Audioaufnahme", ex);
            }
        }

        public async Task SetInputDeviceAsync(int deviceId)
        {
            try
            {
                bool wasRecording = IsRecording;
                
                if (wasRecording)
                {
                    await StopRecordingAsync();
                }

                _currentDeviceId = deviceId;
                UpdateCurrentDevice();

                if (wasRecording)
                {
                    await StartRecordingAsync(deviceId);
                }

                _logger.LogInformation("Changed input device to {DeviceId}", deviceId);
                AudioDeviceChanged?.Invoke(this, new AudioDeviceEventArgs(CurrentDevice));
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error setting input device {DeviceId}", deviceId);
                throw new AudioServiceException($"Fehler beim Wechseln des Audiogeräts {deviceId}", ex);
            }
        }

        private void OnDataAvailable(object? sender, WaveInEventArgs e)
        {
            try
            {
                if (_cancellationTokenSource?.Token.IsCancellationRequested == true)
                    return;

                // Calculate audio level
                double level = CalculateAudioLevel(e.Buffer, e.BytesRecorded);
                
                lock (_lockObject)
                {
                    _currentLevel = level;
                }

                // Fire events
                AudioDataReceived?.Invoke(this, new AudioDataEventArgs(e.Buffer, e.BytesRecorded, level));
                AudioLevelChanged?.Invoke(this, new AudioLevelEventArgs(level));
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing audio data");
            }
        }

        private void OnRecordingStopped(object? sender, StoppedEventArgs e)
        {
            lock (_lockObject)
            {
                _isRecording = false;
                _currentLevel = 0;
            }

            if (e.Exception != null)
            {
                _logger.LogError(e.Exception, "Recording stopped due to error");
            }
            else
            {
                _logger.LogInformation("Recording stopped normally");
            }

            AudioLevelChanged?.Invoke(this, new AudioLevelEventArgs(0));
        }

        private double CalculateAudioLevel(byte[] buffer, int bytesRecorded)
        {
            if (bytesRecorded == 0) return 0;

            long sum = 0;
            int sampleCount = bytesRecorded / 2; // 16-bit samples

            for (int i = 0; i < bytesRecorded; i += 2)
            {
                if (i + 1 < bytesRecorded)
                {
                    short sample = (short)((buffer[i + 1] << 8) | buffer[i]);
                    sum += Math.Abs(sample);
                }
            }

            double average = sampleCount > 0 ? (double)sum / sampleCount : 0;
            double level = average / short.MaxValue * 100; // Convert to percentage
            
            return Math.Min(100, level);
        }

        private void UpdateCurrentDevice()
        {
            try
            {
                if (_currentDeviceId >= 0 && _currentDeviceId < WaveIn.DeviceCount)
                {
                    var capabilities = WaveIn.GetCapabilities(_currentDeviceId);
                    CurrentDevice = new AudioDevice
                    {
                        Id = _currentDeviceId,
                        Name = capabilities.ProductName,
                        Channels = capabilities.Channels,
                        IsDefault = _currentDeviceId == 0
                    };
                }
                else
                {
                    CurrentDevice = null;
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error updating current device info");
                CurrentDevice = null;
            }
        }

        public void Dispose()
        {
            try
            {
                StopRecordingAsync().Wait(5000);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error disposing AudioService");
            }
            finally
            {
                _waveIn?.Dispose();
                _cancellationTokenSource?.Dispose();
            }
        }
    }

    // Event Args
    public class AudioDataEventArgs : EventArgs
    {
        public byte[] Data { get; }
        public int BytesRecorded { get; }
        public double Level { get; }

        public AudioDataEventArgs(byte[] data, int bytesRecorded, double level)
        {
            Data = data;
            BytesRecorded = bytesRecorded;
            Level = level;
        }
    }

    public class AudioLevelEventArgs : EventArgs
    {
        public double Level { get; }

        public AudioLevelEventArgs(double level)
        {
            Level = level;
        }
    }

    public class AudioDeviceEventArgs : EventArgs
    {
        public AudioDevice? Device { get; }

        public AudioDeviceEventArgs(AudioDevice? device)
        {
            Device = device;
        }
    }

    // Models
    public class AudioDevice
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public int Channels { get; set; }
        public bool IsDefault { get; set; }
    }

    // Exceptions
    public class AudioServiceException : Exception
    {
        public AudioServiceException(string message) : base(message) { }
        public AudioServiceException(string message, Exception innerException) : base(message, innerException) { }
    }
}