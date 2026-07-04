#!/usr/bin/env python3
"""
System Information Fetch Script (like neofetch)
Displays system info, network connection status, and speed
"""

import os
import sys
import platform
import subprocess
import re
import psutil
import time
from datetime import datetime

class SystemInfo:
    def __init__(self):
        self.info = {}
        self.colors = {
            'reset': '\033[0m',
            'bold': '\033[1m',
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'purple': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m'
        }
    
    def get_os_info(self):
        """Get operating system information"""
        try:
            if platform.system() == "Linux":
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            return line.split('=')[1].strip().strip('"')
            elif platform.system() == "Darwin":
                return f"macOS {platform.mac_ver()[0]}"
            elif platform.system() == "Windows":
                return f"Windows {platform.version()}"
        except:
            return platform.system()
        return platform.system()
    
    def get_kernel_info(self):
        """Get kernel information"""
        return platform.release()
    
    def get_cpu_info(self):
        """Get CPU information"""
        try:
            if platform.system() == "Linux":
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            cpu_name = line.split(':')[1].strip()
                            break
            elif platform.system() == "Darwin":
                cpu_name = os.popen('sysctl -n machdep.cpu.brand_string').read().strip()
            else:
                cpu_name = platform.processor()
            
            if not cpu_name:
                cpu_name = "Unknown CPU"
            
            cores = psutil.cpu_count()
            physical_cores = psutil.cpu_count(logical=False)
            
            return f"{cpu_name} ({physical_cores} physical / {cores} logical cores)"
        except:
            return "Unknown CPU"
    
    def get_memory_info(self):
        """Get memory information"""
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024**3)
        used_gb = mem.used / (1024**3)
        percent = mem.percent
        return f"{used_gb:.1f}GB / {total_gb:.1f}GB ({percent}%)"
    
    def get_disk_info(self):
        """Get disk information"""
        try:
            disk = psutil.disk_usage('/')
            total_gb = disk.total / (1024**3)
            used_gb = disk.used / (1024**3)
            percent = disk.percent
            return f"{used_gb:.1f}GB / {total_gb:.1f}GB ({percent}%)"
        except:
            return "N/A"
    
    def get_uptime(self):
        """Get system uptime"""
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def get_shell(self):
        """Get current shell"""
        return os.environ.get('SHELL', 'Unknown').split('/')[-1]
    
    def get_terminal(self):
        """Get terminal emulator"""
        return os.environ.get('TERM', 'Unknown')
    
    def get_hostname(self):
        """Get hostname"""
        return platform.node()
    
    def get_user(self):
        """Get current user"""
        return os.environ.get('USER', os.environ.get('USERNAME', 'Unknown'))
    
    def get_gpu_info(self):
        """Get GPU information"""
        try:
            if platform.system() == "Linux":
                # Try to get NVIDIA GPU info
                try:
                    result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                                          capture_output=True, text=True)
                    if result.stdout:
                        return result.stdout.strip().split('\n')[0]
                except:
                    pass
                
                # Try to get AMD GPU info
                try:
                    result = subprocess.run(['lspci', '|', 'grep', '-i', 'VGA'], 
                                          shell=True, capture_output=True, text=True)
                    if result.stdout:
                        # Extract GPU name from lspci output
                        gpu_line = result.stdout.strip().split('\n')[0]
                        if 'AMD' in gpu_line or 'Radeon' in gpu_line:
                            return gpu_line.split(':')[2].strip()
                except:
                    pass
                
                return "Integrated Graphics"
            elif platform.system() == "Darwin":
                try:
                    result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], 
                                          capture_output=True, text=True)
                    for line in result.stdout.split('\n'):
                        if 'Chipset Model' in line:
                            return line.split(':')[1].strip()
                except:
                    return "Apple GPU"
            else:
                return "N/A"
        except:
            return "Unknown GPU"
    
    def get_network_info(self):
        """Get network interface information and connection speed"""
        network_info = {}
        try:
            # Get network interfaces and their speeds
            net_io = psutil.net_io_counters(pernic=True)
            
            for interface, stats in net_io.items():
                # Skip loopback
                if interface == 'lo':
                    continue
                
                # Get interface speed (Linux)
                speed = "Unknown"
                if platform.system() == "Linux":
                    try:
                        with open(f'/sys/class/net/{interface}/speed', 'r') as f:
                            speed_val = f.read().strip()
                            if speed_val != '-1':
                                speed = f"{speed_val} Mbps"
                    except:
                        pass
                
                # Get connection status
                status = "Unknown"
                if platform.system() == "Linux":
                    try:
                        with open(f'/sys/class/net/{interface}/operstate', 'r') as f:
                            status = f.read().strip()
                    except:
                        pass
                
                # Get IP address
                ip_address = "N/A"
                try:
                    import socket
                    import fcntl
                    import struct
                    if platform.system() == "Linux":
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        ip_address = socket.inet_ntoa(fcntl.ioctl(
                            s.fileno(),
                            0x8915,
                            struct.pack('256s', interface.encode()[:15])
                        )[20:24])
                except:
                    pass
                
                network_info[interface] = {
                    'speed': speed,
                    'status': status,
                    'ip': ip_address,
                    'bytes_sent': stats.bytes_sent,
                    'bytes_recv': stats.bytes_recv
                }
            
            return network_info
        except Exception as e:
            return {'error': str(e)}
    
    def get_connection_speed(self):
        """Get current network connection speed"""
        try:
            # Get initial network stats
            net_io = psutil.net_io_counters()
            initial_sent = net_io.bytes_sent
            initial_recv = net_io.bytes_recv
            
            # Wait 1 second
            time.sleep(1)
            
            # Get final network stats
            net_io = psutil.net_io_counters()
            final_sent = net_io.bytes_sent
            final_recv = net_io.bytes_recv
            
            # Calculate speeds
            download_speed = final_recv - initial_recv
            upload_speed = final_sent - initial_sent
            
            # Convert to human readable format
            download_speed_human = self.bytes_to_human(download_speed) + "/s"
            upload_speed_human = self.bytes_to_human(upload_speed) + "/s"
            
            return {
                'download': download_speed_human,
                'upload': upload_speed_human,
                'download_bytes': download_speed,
                'upload_bytes': upload_speed
            }
        except Exception as e:
            return {'error': str(e)}
    
    def bytes_to_human(self, bytes_value):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"
    
    def get_all_info(self):
        """Get all system information"""
        self.info = {
            'User': self.get_user(),
            'Hostname': self.get_hostname(),
            'OS': self.get_os_info(),
            'Kernel': self.get_kernel_info(),
            'CPU': self.get_cpu_info(),
            'GPU': self.get_gpu_info(),
            'Memory': self.get_memory_info(),
            'Disk': self.get_disk_info(),
            'Uptime': self.get_uptime(),
            'Shell': self.get_shell(),
            'Terminal': self.get_terminal()
        }
        
        # Get network info
        self.info['Network'] = self.get_network_info()
        
        # Get connection speed
        self.info['Connection Speed'] = self.get_connection_speed()
        
        return self.info
    
    def display_info(self):
        """Display system information in a nice format"""
        info = self.get_all_info()
        
        # ASCII art (you can replace with your own)
        ascii_art = """
        ╭─────────────────────────╮
        │  ███████╗██╗  ██╗███████╗ │
        │  ██╔════╝██║  ██║██╔════╝ │
        │  ███████╗███████║███████╗ │
        │  ╚════██║██╔══██║╚════██║ │
        │  ███████║██║  ██║███████║ │
        │  ╚══════╝╚═╝  ╚═╝╚══════╝ │
        ╰─────────────────────────╯
        """
        
        print(self.colors['cyan'] + ascii_art + self.colors['reset'])
        print(self.colors['bold'] + "System Information" + self.colors['reset'])
        print("=" * 50)
        
        # Display basic info
        print(f"{self.colors['green']}User:{self.colors['reset']}       {info['User']}")
        print(f"{self.colors['green']}Hostname:{self.colors['reset']}   {info['Hostname']}")
        print(f"{self.colors['green']}OS:{self.colors['reset']}         {info['OS']}")
        print(f"{self.colors['green']}Kernel:{self.colors['reset']}     {info['Kernel']}")
        print(f"{self.colors['green']}Uptime:{self.colors['reset']}     {info['Uptime']}")
        print(f"{self.colors['green']}Shell:{self.colors['reset']}      {info['Shell']}")
        print(f"{self.colors['green']}Terminal:{self.colors['reset']}   {info['Terminal']}")
        print()
        
        # Hardware info
        print(f"{self.colors['yellow']}Hardware:{self.colors['reset']}")
        print(f"  {self.colors['blue']}CPU:{self.colors['reset']}        {info['CPU']}")
        print(f"  {self.colors['blue']}GPU:{self.colors['reset']}        {info['GPU']}")
        print(f"  {self.colors['blue']}Memory:{self.colors['reset']}     {info['Memory']}")
        print(f"  {self.colors['blue']}Disk:{self.colors['reset']}       {info['Disk']}")
        print()
        
        # Network info
        print(f"{self.colors['yellow']}Network Interfaces:{self.colors['reset']}")
        if isinstance(info['Network'], dict) and 'error' not in info['Network']:
            for interface, data in info['Network'].items():
                print(f"  {self.colors['cyan']}{interface}:{self.colors['reset']}")
                print(f"    Status: {data['status']}")
                print(f"    Speed: {data['speed']}")
                if data['ip'] != "N/A":
                    print(f"    IP: {data['ip']}")
                print(f"    Bytes Sent: {self.bytes_to_human(data['bytes_sent'])}")
                print(f"    Bytes Recv: {self.bytes_to_human(data['bytes_recv'])}")
        else:
            print(f"  {self.colors['red']}Network info unavailable{self.colors['reset']}")
        print()
        
        # Connection speed
        print(f"{self.colors['yellow']}Connection Speed (1s average):{self.colors['reset']}")
        if isinstance(info['Connection Speed'], dict) and 'error' not in info['Connection Speed']:
            print(f"  {self.colors['green']}↓ Download:{self.colors['reset']} {info['Connection Speed']['download']}")
            print(f"  {self.colors['green']}↑ Upload:{self.colors['reset']}   {info['Connection Speed']['upload']}")
        else:
            print(f"  {self.colors['red']}Speed info unavailable{self.colors['reset']}")
        
        print()
        print(self.colors['cyan'] + "─" * 50 + self.colors['reset'])

def main():
    """Main function"""
    try:
        system = SystemInfo()
        system.display_info()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
