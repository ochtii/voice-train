using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using System;
using System.IO;
using System.Windows;
using VoiceRecognitionClient.Services;
using VoiceRecognitionClient.ViewModels;
using VoiceRecognitionClient.Views;

namespace VoiceRecognitionClient
{
    public partial class App : Application
    {
        private IHost? _host;

        protected override void OnStartup(StartupEventArgs e)
        {
            _host = Host.CreateDefaultBuilder()
                .ConfigureAppConfiguration((context, config) =>
                {
                    config.SetBasePath(Directory.GetCurrentDirectory())
                          .AddJsonFile("appsettings.json", optional: false, reloadOnChange: true);
                })
                .ConfigureServices((context, services) =>
                {
                    // Configuration
                    services.Configure<VoiceRecognitionSettings>(
                        context.Configuration.GetSection("VoiceRecognition"));

                    // Services
                    services.AddSingleton<IAudioService, AudioService>();
                    services.AddSingleton<IWebSocketService, WebSocketService>();
                    services.AddSingleton<IDeviceDiscoveryService, DeviceDiscoveryService>();
                    services.AddSingleton<INotificationService, NotificationService>();
                    services.AddSingleton<ISettingsService, SettingsService>();

                    // ViewModels
                    services.AddTransient<MainViewModel>();
                    services.AddTransient<SettingsViewModel>();
                    services.AddTransient<DeviceListViewModel>();

                    // Views
                    services.AddSingleton<MainWindow>();
                })
                .ConfigureLogging(logging =>
                {
                    logging.AddConsole();
                    logging.AddDebug();
                    logging.AddFile("Logs/app-{Date}.log");
                })
                .Build();

            var mainWindow = _host.Services.GetRequiredService<MainWindow>();
            mainWindow.Show();

            base.OnStartup(e);
        }

        protected override void OnExit(ExitEventArgs e)
        {
            _host?.Dispose();
            base.OnExit(e);
        }

        private void Application_DispatcherUnhandledException(object sender, 
            System.Windows.Threading.DispatcherUnhandledExceptionEventArgs e)
        {
            var logger = _host?.Services.GetService<ILogger<App>>();
            logger?.LogError(e.Exception, "Unhandled exception occurred");

            MessageBox.Show(
                $"Ein unerwarteter Fehler ist aufgetreten:\n{e.Exception.Message}",
                "Fehler",
                MessageBoxButton.OK,
                MessageBoxImage.Error);

            e.Handled = true;
        }
    }

    public class VoiceRecognitionSettings
    {
        public RaspberryPiSettings RaspberryPi { get; set; } = new();
        public AudioSettings Audio { get; set; } = new();
        public UISettings UI { get; set; } = new();
        public SecuritySettings Security { get; set; } = new();
    }

    public class RaspberryPiSettings
    {
        public string DefaultHost { get; set; } = "192.168.1.100";
        public int Port { get; set; } = 8000;
        public int ConnectionTimeout { get; set; } = 30;
        public int ReconnectDelay { get; set; } = 5000;
        public int MaxReconnectAttempts { get; set; } = 10;
    }

    public class AudioSettings
    {
        public int SampleRate { get; set; } = 16000;
        public int BitDepth { get; set; } = 16;
        public int Channels { get; set; } = 1;
        public int BufferSize { get; set; } = 4096;
        public int DeviceLatency { get; set; } = 20;
    }

    public class UISettings
    {
        public string Theme { get; set; } = "Dark";
        public bool AutoConnect { get; set; } = true;
        public bool MinimizeToTray { get; set; } = true;
        public bool ShowNotifications { get; set; } = true;
    }

    public class SecuritySettings
    {
        public bool EnableTLS { get; set; } = true;
        public bool ValidateCertificates { get; set; } = false;
        public string ApiKey { get; set; } = string.Empty;
    }
}