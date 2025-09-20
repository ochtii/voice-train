using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using System;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;

namespace VoiceRecognitionClient.Services
{
    public interface ISettingsService
    {
        Task<T> GetSettingAsync<T>(string key, T defaultValue = default(T));
        Task SetSettingAsync<T>(string key, T value);
        Task<UserSettings> LoadUserSettingsAsync();
        Task SaveUserSettingsAsync(UserSettings settings);
        Task ResetToDefaultsAsync();
        event EventHandler<SettingsChangedEventArgs> SettingsChanged;
    }

    public class SettingsService : ISettingsService
    {
        private readonly ILogger<SettingsService> _logger;
        private readonly IConfiguration _configuration;
        private readonly string _settingsFilePath;
        private UserSettings _userSettings;

        public event EventHandler<SettingsChangedEventArgs> SettingsChanged;

        public SettingsService(ILogger<SettingsService> logger, IConfiguration configuration)
        {
            _logger = logger;
            _configuration = configuration;
            _settingsFilePath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "VoiceRecognitionClient",
                "settings.json");
            
            _userSettings = new UserSettings();
            InitializeAsync().Wait();
        }

        private async Task InitializeAsync()
        {
            try
            {
                // Ensure settings directory exists
                var settingsDir = Path.GetDirectoryName(_settingsFilePath);
                if (!string.IsNullOrEmpty(settingsDir) && !Directory.Exists(settingsDir))
                {
                    Directory.CreateDirectory(settingsDir);
                }

                // Load existing settings or create defaults
                _userSettings = await LoadUserSettingsAsync();
                _logger.LogInformation("Settings initialized from {Path}", _settingsFilePath);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error initializing settings");
                _userSettings = CreateDefaultSettings();
            }
        }

        public async Task<T> GetSettingAsync<T>(string key, T defaultValue = default(T))
        {
            try
            {
                // First check user settings
                var userValue = GetUserSetting<T>(key);
                if (userValue != null && !userValue.Equals(default(T)))
                {
                    return userValue;
                }

                // Then check configuration
                var configValue = _configuration[key];
                if (configValue != null)
                {
                    if (typeof(T) == typeof(string))
                    {
                        return (T)(object)configValue;
                    }
                    
                    if (typeof(T) == typeof(int) && int.TryParse(configValue, out int intValue))
                    {
                        return (T)(object)intValue;
                    }
                    
                    if (typeof(T) == typeof(bool) && bool.TryParse(configValue, out bool boolValue))
                    {
                        return (T)(object)boolValue;
                    }
                    
                    if (typeof(T) == typeof(double) && double.TryParse(configValue, out double doubleValue))
                    {
                        return (T)(object)doubleValue;
                    }
                }

                return defaultValue;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error getting setting {Key}", key);
                return defaultValue;
            }
        }

        public async Task SetSettingAsync<T>(string key, T value)
        {
            try
            {
                var oldValue = GetUserSetting<T>(key);
                SetUserSetting(key, value);
                
                await SaveUserSettingsAsync(_userSettings);
                
                SettingsChanged?.Invoke(this, new SettingsChangedEventArgs(key, oldValue, value));
                _logger.LogDebug("Setting updated: {Key} = {Value}", key, value);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error setting {Key} to {Value}", key, value);
                throw;
            }
        }

        public async Task<UserSettings> LoadUserSettingsAsync()
        {
            try
            {
                if (File.Exists(_settingsFilePath))
                {
                    var json = await File.ReadAllTextAsync(_settingsFilePath);
                    var settings = JsonSerializer.Deserialize<UserSettings>(json);
                    
                    if (settings != null)
                    {
                        _logger.LogDebug("Loaded user settings from {Path}", _settingsFilePath);
                        return settings;
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error loading user settings from {Path}", _settingsFilePath);
            }

            // Return defaults if loading failed
            var defaultSettings = CreateDefaultSettings();
            await SaveUserSettingsAsync(defaultSettings);
            return defaultSettings;
        }

        public async Task SaveUserSettingsAsync(UserSettings settings)
        {
            try
            {
                _userSettings = settings;
                
                var options = new JsonSerializerOptions
                {
                    WriteIndented = true,
                    PropertyNamingPolicy = JsonNamingPolicy.CamelCase
                };
                
                var json = JsonSerializer.Serialize(settings, options);
                await File.WriteAllTextAsync(_settingsFilePath, json);
                
                _logger.LogDebug("Saved user settings to {Path}", _settingsFilePath);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error saving user settings to {Path}", _settingsFilePath);
                throw;
            }
        }

        public async Task ResetToDefaultsAsync()
        {
            try
            {
                var defaultSettings = CreateDefaultSettings();
                await SaveUserSettingsAsync(defaultSettings);
                
                _logger.LogInformation("Settings reset to defaults");
                SettingsChanged?.Invoke(this, new SettingsChangedEventArgs("*", _userSettings, defaultSettings));
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error resetting settings to defaults");
                throw;
            }
        }

        private T GetUserSetting<T>(string key)
        {
            try
            {
                var properties = typeof(UserSettings).GetProperties();
                foreach (var property in properties)
                {
                    if (property.Name.Equals(key, StringComparison.OrdinalIgnoreCase))
                    {
                        var value = property.GetValue(_userSettings);
                        if (value is T typedValue)
                        {
                            return typedValue;
                        }
                    }
                }

                // Check nested objects
                if (key.Contains("."))
                {
                    var parts = key.Split('.');
                    object current = _userSettings;
                    
                    foreach (var part in parts)
                    {
                        if (current == null) break;
                        
                        var property = current.GetType().GetProperty(part);
                        if (property == null) break;
                        
                        current = property.GetValue(current);
                    }
                    
                    if (current is T nestedValue)
                    {
                        return nestedValue;
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error getting user setting {Key}", key);
            }

            return default(T);
        }

        private void SetUserSetting<T>(string key, T value)
        {
            try
            {
                var properties = typeof(UserSettings).GetProperties();
                foreach (var property in properties)
                {
                    if (property.Name.Equals(key, StringComparison.OrdinalIgnoreCase) && property.CanWrite)
                    {
                        property.SetValue(_userSettings, value);
                        return;
                    }
                }

                // Handle nested properties
                if (key.Contains("."))
                {
                    var parts = key.Split('.');
                    object current = _userSettings;
                    
                    for (int i = 0; i < parts.Length - 1; i++)
                    {
                        if (current == null) return;
                        
                        var property = current.GetType().GetProperty(parts[i]);
                        if (property == null) return;
                        
                        current = property.GetValue(current);
                    }
                    
                    if (current != null)
                    {
                        var finalProperty = current.GetType().GetProperty(parts[^1]);
                        if (finalProperty != null && finalProperty.CanWrite)
                        {
                            finalProperty.SetValue(current, value);
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error setting user setting {Key} to {Value}", key, value);
            }
        }

        private UserSettings CreateDefaultSettings()
        {
            var defaults = _configuration.GetSection("VoiceRecognition").Get<VoiceRecognitionSettings>();
            
            return new UserSettings
            {
                LastConnectedDevice = defaults?.RaspberryPi?.DefaultHost ?? "192.168.1.100",
                LastConnectedPort = defaults?.RaspberryPi?.Port ?? 8000,
                AutoConnect = defaults?.UI?.AutoConnect ?? true,
                MinimizeToTray = defaults?.UI?.MinimizeToTray ?? true,
                ShowNotifications = defaults?.UI?.ShowNotifications ?? true,
                Theme = defaults?.UI?.Theme ?? "Dark",
                AudioSettings = new UserAudioSettings
                {
                    SelectedDeviceId = -1,
                    SampleRate = defaults?.Audio?.SampleRate ?? 16000,
                    BitDepth = defaults?.Audio?.BitDepth ?? 16,
                    Channels = defaults?.Audio?.Channels ?? 1,
                    BufferSize = defaults?.Audio?.BufferSize ?? 4096,
                    AutoAdjustGain = true,
                    NoiseReduction = true
                },
                SecuritySettings = new UserSecuritySettings
                {
                    RememberCredentials = false,
                    EncryptLocalData = true,
                    ApiKey = string.Empty
                },
                WindowSettings = new WindowSettings
                {
                    Width = 800,
                    Height = 600,
                    Left = 100,
                    Top = 100,
                    WindowState = "Normal"
                }
            };
        }
    }

    // Event Args
    public class SettingsChangedEventArgs : EventArgs
    {
        public string Key { get; }
        public object OldValue { get; }
        public object NewValue { get; }

        public SettingsChangedEventArgs(string key, object oldValue, object newValue)
        {
            Key = key;
            OldValue = oldValue;
            NewValue = newValue;
        }
    }

    // Models
    public class UserSettings
    {
        public string LastConnectedDevice { get; set; } = string.Empty;
        public int LastConnectedPort { get; set; } = 8000;
        public bool AutoConnect { get; set; } = true;
        public bool MinimizeToTray { get; set; } = true;
        public bool ShowNotifications { get; set; } = true;
        public string Theme { get; set; } = "Dark";
        public UserAudioSettings AudioSettings { get; set; } = new();
        public UserSecuritySettings SecuritySettings { get; set; } = new();
        public WindowSettings WindowSettings { get; set; } = new();
    }

    public class UserAudioSettings
    {
        public int SelectedDeviceId { get; set; } = -1;
        public int SampleRate { get; set; } = 16000;
        public int BitDepth { get; set; } = 16;
        public int Channels { get; set; } = 1;
        public int BufferSize { get; set; } = 4096;
        public bool AutoAdjustGain { get; set; } = true;
        public bool NoiseReduction { get; set; } = true;
    }

    public class UserSecuritySettings
    {
        public bool RememberCredentials { get; set; } = false;
        public bool EncryptLocalData { get; set; } = true;
        public string ApiKey { get; set; } = string.Empty;
    }

    public class WindowSettings
    {
        public double Width { get; set; } = 800;
        public double Height { get; set; } = 600;
        public double Left { get; set; } = 100;
        public double Top { get; set; } = 100;
        public string WindowState { get; set; } = "Normal";
    }
}