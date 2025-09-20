using Microsoft.Extensions.Logging;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Threading.Tasks;

namespace VoiceRecognitionClient.Services
{
    public interface IDeviceDiscoveryService
    {
        event EventHandler<DeviceDiscoveredEventArgs>? DeviceDiscovered;
        event EventHandler<DiscoveryCompletedEventArgs>? DiscoveryCompleted;
        
        Task<IEnumerable<RaspberryPiDevice>> DiscoverDevicesAsync();
        Task<RaspberryPiDevice?> FindDeviceAsync(string hostname);
        bool IsDiscovering { get; }
    }

    public class DeviceDiscoveryService : IDeviceDiscoveryService
    {
        private readonly ILogger<DeviceDiscoveryService> _logger;
        private bool _isDiscovering;

        public event EventHandler<DeviceDiscoveredEventArgs>? DeviceDiscovered;
        public event EventHandler<DiscoveryCompletedEventArgs>? DiscoveryCompleted;

        public bool IsDiscovering => _isDiscovering;

        public DeviceDiscoveryService(ILogger<DeviceDiscoveryService> logger)
        {
            _logger = logger;
        }

        public async Task<IEnumerable<RaspberryPiDevice>> DiscoverDevicesAsync()
        {
            if (_isDiscovering)
            {
                _logger.LogWarning("Discovery already in progress");
                return Enumerable.Empty<RaspberryPiDevice>();
            }

            _isDiscovering = true;
            var devices = new List<RaspberryPiDevice>();

            try
            {
                _logger.LogInformation("Starting device discovery");

                // Get local network interfaces
                var networkInterfaces = NetworkInterface.GetAllNetworkInterfaces()
                    .Where(ni => ni.OperationalStatus == OperationalStatus.Up &&
                                ni.NetworkInterfaceType != NetworkInterfaceType.Loopback)
                    .ToList();

                var discoveryTasks = new List<Task>();

                foreach (var networkInterface in networkInterfaces)
                {
                    var ipProperties = networkInterface.GetIPProperties();
                    var unicastAddresses = ipProperties.UnicastAddresses
                        .Where(ua => ua.Address.AddressFamily == AddressFamily.InterNetwork)
                        .ToList();

                    foreach (var unicastAddress in unicastAddresses)
                    {
                        var subnet = GetSubnet(unicastAddress.Address, unicastAddress.IPv4Mask);
                        if (subnet != null)
                        {
                            discoveryTasks.Add(ScanSubnetAsync(subnet, devices));
                        }
                    }
                }

                // Also try common hostnames
                var commonHostnames = new[]
                {
                    "raspberrypi.local",
                    "raspberrypi",
                    "voicerecog.local",
                    "voice-pi.local",
                    "pi.local"
                };

                foreach (var hostname in commonHostnames)
                {
                    discoveryTasks.Add(CheckHostnameAsync(hostname, devices));
                }

                await Task.WhenAll(discoveryTasks);

                _logger.LogInformation("Discovery completed, found {DeviceCount} devices", devices.Count);
                DiscoveryCompleted?.Invoke(this, new DiscoveryCompletedEventArgs(devices));

                return devices;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error during device discovery");
                throw new DeviceDiscoveryException("Fehler bei der Geräteerkennung", ex);
            }
            finally
            {
                _isDiscovering = false;
            }
        }

        public async Task<RaspberryPiDevice?> FindDeviceAsync(string hostname)
        {
            try
            {
                _logger.LogInformation("Looking for device: {Hostname}", hostname);

                var device = await CheckHostnameAsync(hostname);
                
                if (device != null)
                {
                    _logger.LogInformation("Found device: {Device}", device.Name);
                }
                else
                {
                    _logger.LogWarning("Device not found: {Hostname}", hostname);
                }

                return device;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error finding device {Hostname}", hostname);
                return null;
            }
        }

        private async Task ScanSubnetAsync(string subnet, List<RaspberryPiDevice> devices)
        {
            try
            {
                _logger.LogDebug("Scanning subnet: {Subnet}", subnet);

                var baseAddress = subnet.Split('/')[0];
                var parts = baseAddress.Split('.');
                var baseIp = $"{parts[0]}.{parts[1]}.{parts[2]}";

                var scanTasks = new List<Task>();

                // Scan common IP ranges (1-254)
                for (int i = 1; i <= 254; i++)
                {
                    var ip = $"{baseIp}.{i}";
                    scanTasks.Add(CheckIpAddressAsync(ip, devices));

                    // Limit concurrent scans
                    if (scanTasks.Count >= 50)
                    {
                        await Task.WhenAll(scanTasks);
                        scanTasks.Clear();
                    }
                }

                if (scanTasks.Count > 0)
                {
                    await Task.WhenAll(scanTasks);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error scanning subnet {Subnet}", subnet);
            }
        }

        private async Task CheckIpAddressAsync(string ipAddress, List<RaspberryPiDevice>? devices = null)
        {
            try
            {
                // First, ping the device
                using var ping = new Ping();
                var reply = await ping.SendPingAsync(ipAddress, 1000);

                if (reply.Status == IPStatus.Success)
                {
                    var device = await ProbeDeviceAsync(ipAddress);
                    if (device != null)
                    {
                        lock (devices ?? new List<RaspberryPiDevice>())
                        {
                            devices?.Add(device);
                        }
                        
                        DeviceDiscovered?.Invoke(this, new DeviceDiscoveredEventArgs(device));
                        _logger.LogInformation("Discovered device: {Device} at {IP}", device.Name, device.IpAddress);
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogDebug("Error checking IP {IP}: {Error}", ipAddress, ex.Message);
            }
        }

        private async Task CheckHostnameAsync(string hostname, List<RaspberryPiDevice>? devices = null)
        {
            try
            {
                var device = await CheckHostnameAsync(hostname);
                if (device != null)
                {
                    lock (devices ?? new List<RaspberryPiDevice>())
                    {
                        devices?.Add(device);
                    }
                    
                    DeviceDiscovered?.Invoke(this, new DeviceDiscoveredEventArgs(device));
                }
            }
            catch (Exception ex)
            {
                _logger.LogDebug("Error checking hostname {Hostname}: {Error}", hostname, ex.Message);
            }
        }

        private async Task<RaspberryPiDevice?> CheckHostnameAsync(string hostname)
        {
            try
            {
                // Try to resolve hostname
                var hostEntry = await System.Net.Dns.GetHostEntryAsync(hostname);
                var ipAddress = hostEntry.AddressList
                    .FirstOrDefault(addr => addr.AddressFamily == AddressFamily.InterNetwork)
                    ?.ToString();

                if (!string.IsNullOrEmpty(ipAddress))
                {
                    return await ProbeDeviceAsync(ipAddress, hostname);
                }
            }
            catch (Exception ex)
            {
                _logger.LogDebug("Error resolving hostname {Hostname}: {Error}", hostname, ex.Message);
            }

            return null;
        }

        private async Task<RaspberryPiDevice?> ProbeDeviceAsync(string ipAddress, string? hostname = null)
        {
            try
            {
                // Try to connect to the voice recognition service
                using var client = new TcpClient();
                client.ReceiveTimeout = 3000;
                client.SendTimeout = 3000;

                await client.ConnectAsync(ipAddress, 8000);

                if (client.Connected)
                {
                    // Try to get device info via HTTP
                    var deviceInfo = await GetDeviceInfoAsync(ipAddress);
                    
                    return new RaspberryPiDevice
                    {
                        Name = deviceInfo?.Name ?? hostname ?? $"Raspberry Pi ({ipAddress})",
                        IpAddress = ipAddress,
                        Hostname = hostname,
                        Port = 8000,
                        IsOnline = true,
                        LastSeen = DateTime.Now,
                        DeviceInfo = deviceInfo,
                        MacAddress = await GetMacAddressAsync(ipAddress)
                    };
                }
            }
            catch (Exception ex)
            {
                _logger.LogDebug("Error probing device {IP}: {Error}", ipAddress, ex.Message);
            }

            return null;
        }

        private async Task<DeviceInfo?> GetDeviceInfoAsync(string ipAddress)
        {
            try
            {
                using var httpClient = new System.Net.Http.HttpClient();
                httpClient.Timeout = TimeSpan.FromSeconds(5);

                var response = await httpClient.GetAsync($"http://{ipAddress}:8000/system/info");
                
                if (response.IsSuccessStatusCode)
                {
                    var json = await response.Content.ReadAsStringAsync();
                    return System.Text.Json.JsonSerializer.Deserialize<DeviceInfo>(json);
                }
            }
            catch (Exception ex)
            {
                _logger.LogDebug("Error getting device info from {IP}: {Error}", ipAddress, ex.Message);
            }

            return null;
        }

        private async Task<string?> GetMacAddressAsync(string ipAddress)
        {
            try
            {
                // Try to get MAC address from ARP table
                var processStartInfo = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = "arp",
                    Arguments = $"-a {ipAddress}",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    CreateNoWindow = true
                };

                using var process = System.Diagnostics.Process.Start(processStartInfo);
                if (process != null)
                {
                    var output = await process.StandardOutput.ReadToEndAsync();
                    await process.WaitForExitAsync();

                    // Parse ARP output for MAC address
                    var lines = output.Split('\n');
                    foreach (var line in lines)
                    {
                        if (line.Contains(ipAddress))
                        {
                            var parts = line.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                            if (parts.Length >= 2)
                            {
                                var macCandidate = parts[1];
                                if (IsMacAddress(macCandidate))
                                {
                                    return macCandidate.ToUpperInvariant();
                                }
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogDebug("Error getting MAC address for {IP}: {Error}", ipAddress, ex.Message);
            }

            return null;
        }

        private static bool IsMacAddress(string input)
        {
            return System.Text.RegularExpressions.Regex.IsMatch(
                input, 
                @"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$");
        }

        private static string? GetSubnet(System.Net.IPAddress ipAddress, System.Net.IPAddress subnetMask)
        {
            try
            {
                var ipBytes = ipAddress.GetAddressBytes();
                var maskBytes = subnetMask.GetAddressBytes();
                var networkBytes = new byte[4];

                for (int i = 0; i < 4; i++)
                {
                    networkBytes[i] = (byte)(ipBytes[i] & maskBytes[i]);
                }

                var networkAddress = new System.Net.IPAddress(networkBytes);
                
                // Calculate CIDR notation
                int cidr = 0;
                foreach (byte b in maskBytes)
                {
                    cidr += System.Numerics.BitOperations.PopCount(b);
                }

                return $"{networkAddress}/{cidr}";
            }
            catch
            {
                return null;
            }
        }
    }

    // Event Args
    public class DeviceDiscoveredEventArgs : EventArgs
    {
        public RaspberryPiDevice Device { get; }

        public DeviceDiscoveredEventArgs(RaspberryPiDevice device)
        {
            Device = device;
        }
    }

    public class DiscoveryCompletedEventArgs : EventArgs
    {
        public IEnumerable<RaspberryPiDevice> Devices { get; }

        public DiscoveryCompletedEventArgs(IEnumerable<RaspberryPiDevice> devices)
        {
            Devices = devices;
        }
    }

    // Models
    public class RaspberryPiDevice
    {
        public string Name { get; set; } = string.Empty;
        public string IpAddress { get; set; } = string.Empty;
        public string? Hostname { get; set; }
        public int Port { get; set; } = 8000;
        public bool IsOnline { get; set; }
        public DateTime LastSeen { get; set; }
        public DeviceInfo? DeviceInfo { get; set; }
        public string? MacAddress { get; set; }

        public string DisplayName => !string.IsNullOrEmpty(DeviceInfo?.Name) ? DeviceInfo.Name : Name;
        public string ConnectionString => $"{IpAddress}:{Port}";
    }

    public class DeviceInfo
    {
        public string Name { get; set; } = string.Empty;
        public string Version { get; set; } = string.Empty;
        public string Model { get; set; } = string.Empty;
        public string SerialNumber { get; set; } = string.Empty;
        public SystemStatus Status { get; set; } = new();
        public AudioCapabilities Audio { get; set; } = new();
    }

    public class SystemStatus
    {
        public double CpuUsage { get; set; }
        public double MemoryUsage { get; set; }
        public double Temperature { get; set; }
        public double DiskUsage { get; set; }
        public TimeSpan Uptime { get; set; }
        public bool IsRecording { get; set; }
        public int ActiveConnections { get; set; }
    }

    public class AudioCapabilities
    {
        public string[] SupportedFormats { get; set; } = Array.Empty<string>();
        public int[] SupportedSampleRates { get; set; } = Array.Empty<int>();
        public int MaxChannels { get; set; }
        public string AudioDevice { get; set; } = string.Empty;
        public bool HasMicrophone { get; set; }
    }

    // Exceptions
    public class DeviceDiscoveryException : Exception
    {
        public DeviceDiscoveryException(string message) : base(message) { }
        public DeviceDiscoveryException(string message, Exception innerException) : base(message, innerException) { }
    }
}