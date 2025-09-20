using Microsoft.Extensions.Logging;
using System;
using System.Drawing;
using System.Windows.Forms;

namespace VoiceRecognitionClient.Services
{
    public interface INotificationService
    {
        void ShowInfo(string title, string message);
        void ShowWarning(string title, string message);
        void ShowError(string title, string message);
        void ShowSuccess(string title, string message);
        void ShowConnectionStatus(bool isConnected, string deviceName);
        void ShowRecognitionResult(string speakerName, double confidence);
        void Clear();
    }

    public class NotificationService : INotificationService, IDisposable
    {
        private readonly ILogger<NotificationService> _logger;
        private NotifyIcon? _notifyIcon;
        private bool _disposed;

        public NotificationService(ILogger<NotificationService> logger)
        {
            _logger = logger;
            InitializeNotifyIcon();
        }

        private void InitializeNotifyIcon()
        {
            try
            {
                _notifyIcon = new NotifyIcon
                {
                    Icon = SystemIcons.Application,
                    Text = "Voice Recognition Client",
                    Visible = true
                };

                // Create context menu
                var contextMenu = new ContextMenuStrip();
                
                var showItem = new ToolStripMenuItem("Anzeigen");
                showItem.Click += (s, e) => ShowMainWindow();
                
                var exitItem = new ToolStripMenuItem("Beenden");
                exitItem.Click += (s, e) => ExitApplication();
                
                contextMenu.Items.AddRange(new ToolStripItem[] { showItem, new ToolStripSeparator(), exitItem });
                _notifyIcon.ContextMenuStrip = contextMenu;

                _notifyIcon.DoubleClick += (s, e) => ShowMainWindow();

                _logger.LogDebug("NotifyIcon initialized");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error initializing NotifyIcon");
            }
        }

        public void ShowInfo(string title, string message)
        {
            ShowNotification(title, message, ToolTipIcon.Info);
            _logger.LogInformation("Info notification: {Title} - {Message}", title, message);
        }

        public void ShowWarning(string title, string message)
        {
            ShowNotification(title, message, ToolTipIcon.Warning);
            _logger.LogWarning("Warning notification: {Title} - {Message}", title, message);
        }

        public void ShowError(string title, string message)
        {
            ShowNotification(title, message, ToolTipIcon.Error);
            _logger.LogError("Error notification: {Title} - {Message}", title, message);
        }

        public void ShowSuccess(string title, string message)
        {
            ShowNotification(title, message, ToolTipIcon.Info);
            _logger.LogInformation("Success notification: {Title} - {Message}", title, message);
        }

        public void ShowConnectionStatus(bool isConnected, string deviceName)
        {
            if (isConnected)
            {
                ShowSuccess("Verbunden", $"Erfolgreich mit {deviceName} verbunden");
                UpdateIcon(true);
            }
            else
            {
                ShowWarning("Getrennt", $"Verbindung zu {deviceName} getrennt");
                UpdateIcon(false);
            }
        }

        public void ShowRecognitionResult(string speakerName, double confidence)
        {
            var message = $"Sprecher: {speakerName}\nGenauigkeit: {confidence:P1}";
            ShowInfo("Sprecher erkannt", message);
        }

        public void Clear()
        {
            try
            {
                // Clear any existing notifications
                if (_notifyIcon != null)
                {
                    _notifyIcon.Visible = false;
                    _notifyIcon.Visible = true;
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error clearing notifications");
            }
        }

        private void ShowNotification(string title, string message, ToolTipIcon icon)
        {
            try
            {
                if (_notifyIcon != null && !_disposed)
                {
                    _notifyIcon.ShowBalloonTip(5000, title, message, icon);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error showing notification");
            }
        }

        private void UpdateIcon(bool isConnected)
        {
            try
            {
                if (_notifyIcon != null)
                {
                    // You could change the icon based on connection status
                    _notifyIcon.Icon = isConnected ? SystemIcons.Application : SystemIcons.Warning;
                    _notifyIcon.Text = isConnected ? "Voice Recognition - Verbunden" : "Voice Recognition - Getrennt";
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error updating notification icon");
            }
        }

        private void ShowMainWindow()
        {
            try
            {
                var mainWindow = System.Windows.Application.Current?.MainWindow;
                if (mainWindow != null)
                {
                    if (mainWindow.WindowState == System.Windows.WindowState.Minimized)
                    {
                        mainWindow.WindowState = System.Windows.WindowState.Normal;
                    }
                    
                    mainWindow.Show();
                    mainWindow.Activate();
                    mainWindow.Focus();
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error showing main window");
            }
        }

        private void ExitApplication()
        {
            try
            {
                System.Windows.Application.Current?.Shutdown();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error exiting application");
            }
        }

        public void Dispose()
        {
            if (!_disposed)
            {
                try
                {
                    _notifyIcon?.Dispose();
                    _disposed = true;
                    _logger.LogDebug("NotificationService disposed");
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Error disposing NotificationService");
                }
            }
        }
    }
}