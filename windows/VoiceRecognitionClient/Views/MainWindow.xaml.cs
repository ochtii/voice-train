using Microsoft.Extensions.DependencyInjection;
using System.Windows;
using VoiceRecognitionClient.ViewModels;

namespace VoiceRecognitionClient.Views
{
    public partial class MainWindow : Window
    {
        public MainWindow(MainViewModel viewModel)
        {
            InitializeComponent();
            DataContext = viewModel;
            
            // Load window settings
            LoadWindowSettings();
            
            // Handle window events
            Closing += MainWindow_Closing;
            StateChanged += MainWindow_StateChanged;
        }

        private void LoadWindowSettings()
        {
            try
            {
                // Window settings would be loaded from settings service
                Width = 900;
                Height = 700;
                WindowStartupLocation = WindowStartupLocation.CenterScreen;
            }
            catch
            {
                // Use defaults if loading fails
            }
        }

        private void MainWindow_Closing(object sender, System.ComponentModel.CancelEventArgs e)
        {
            try
            {
                // Save window settings
                var viewModel = DataContext as MainViewModel;
                // Save settings logic here
            }
            catch
            {
                // Ignore errors during shutdown
            }
        }

        private void MainWindow_StateChanged(object sender, System.EventArgs e)
        {
            try
            {
                // Handle minimize to tray
                if (WindowState == WindowState.Minimized)
                {
                    ShowInTaskbar = false;
                    Hide();
                }
            }
            catch
            {
                // Ignore errors
            }
        }

        public void ShowFromTray()
        {
            Show();
            ShowInTaskbar = true;
            WindowState = WindowState.Normal;
            Activate();
        }
    }
}