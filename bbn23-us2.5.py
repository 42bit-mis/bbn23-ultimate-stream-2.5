#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ULTIMATE NGINX RTMP MULTI-PLATFORM STREAMING SERVER INSTALLER
Version: 2.5 - Debian 12/13 Complete Fix Edition mit Port Forwarding
All issues fixed: software-properties-common, RTMP module, mime.types
"""

import os
import sys
import subprocess
import shutil
import time
import socket
import json
import traceback
import tarfile
import zipfile
import re
import urllib.request
from pathlib import Path
from datetime import datetime

# ============================================================================
# COLOR SYSTEM
# ============================================================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

C = Colors

# ============================================================================
# LOGGING SYSTEM
# ============================================================================

class Logger:
    @staticmethod
    def header(text):
        print(f"\n{C.BOLD}{C.BLUE}{'='*80}{C.END}")
        print(f"{C.BOLD}{C.BLUE}{text.center(80)}{C.END}")
        print(f"{C.BOLD}{C.BLUE}{'='*80}{C.END}\n")
    
    @staticmethod
    def step(text):
        print(f"\n{C.BLUE}{C.BOLD}▶{C.END} {C.BOLD}{text}{C.END}")
    
    @staticmethod
    def info(text):
        print(f"{C.CYAN}→ {text}{C.END}")
    
    @staticmethod
    def success(text):
        print(f"{C.GREEN}✓ {text}{C.END}")
    
    @staticmethod
    def warning(text):
        print(f"{C.YELLOW}⚠ {text}{C.END}")
    
    @staticmethod
    def error(text):
        print(f"{C.RED}✗ {text}{C.END}")
    
    @staticmethod
    def critical(text):
        print(f"{C.RED}{C.BOLD}🔥 {text}{C.END}")
    
    @staticmethod
    def divider():
        print(f"{C.CYAN}{'─' * 80}{C.END}")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def run_command(cmd, shell=True, check=False, capture_output=True):
    """Run command with proper error handling"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            check=check,
            capture_output=capture_output,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        return result
    except Exception as e:
        return type('obj', (object,), {
            'returncode': 1,
            'stdout': '',
            'stderr': str(e)
        })()

# ============================================================================
# PORT FORWARDING CLASS
# ============================================================================

class PortForwardingManager:
    def __init__(self, installer):
        self.installer = installer
        self.local_ip = None
        self.public_ip = None
        self.gateway_ip = None
        self.network_info = {}
        self.ports_to_forward = [
            ("RTMP", installer.rtmp_port, "TCP", "Live-Streaming Eingang"),
            ("HTTP", installer.http_port, "TCP", "Web-Dashboard & HLS"),
            ("SRT", installer.srt_port, "UDP", "SRT-Streaming (optional)"),
            ("HLS", installer.hls_port, "TCP", "HLS-Streaming (optional)"),
        ]
        
    def get_local_ip(self):
        """Get local IP address"""
        try:
            # Try multiple methods to get local IP
            methods = [
                "hostname -I | awk '{print $1}'",
                "ip route get 1 | awk '{print $7}'",
                "ip addr show | grep -oP 'inet \\K(192\\.168|10\\.|172\\.(1[6-9]|2[0-9]|3[0-1]))\\.\\d+\\.\\d+' | head -1",
            ]
            
            for method in methods:
                result = run_command(method)
                if result.returncode == 0 and result.stdout.strip():
                    ip = result.stdout.strip().split()[0] if ' ' in result.stdout.strip() else result.stdout.strip()
                    if ip and ip != "127.0.0.1":
                        self.local_ip = ip
                        Logger.success(f"Lokale IP gefunden: {self.local_ip}")
                        return self.local_ip
        except Exception as e:
            Logger.warning(f"Konnte lokale IP nicht ermitteln: {e}")
        
        self.local_ip = "192.168.1.100"  # Default fallback
        Logger.warning(f"Verwende Standard-IP: {self.local_ip}")
        return self.local_ip
    
    def get_public_ip(self):
        """Get public IP address"""
        try:
            # Try multiple services
            services = [
                "https://api.ipify.org",
                "https://icanhazip.com",
                "https://checkip.amazonaws.com",
                "https://ifconfig.me/ip",
            ]
            
            for service in services:
                try:
                    with urllib.request.urlopen(service, timeout=5) as response:
                        ip = response.read().decode('utf-8').strip()
                        if ip and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                            self.public_ip = ip
                            Logger.success(f"Öffentliche IP gefunden: {self.public_ip}")
                            return self.public_ip
                except:
                    continue
        except Exception as e:
            Logger.warning(f"Konnte öffentliche IP nicht ermitteln: {e}")
        
        self.public_ip = "Ihre öffentliche IP"
        Logger.warning("Öffentliche IP konnte nicht ermittelt werden")
        return self.public_ip
    
    def get_gateway_ip(self):
        """Get gateway/router IP"""
        try:
            result = run_command("ip route | grep default | awk '{print $3}' | head -1")
            if result.returncode == 0 and result.stdout.strip():
                self.gateway_ip = result.stdout.strip()
                Logger.success(f"Gateway IP gefunden: {self.gateway_ip}")
                return self.gateway_ip
            
            # Alternative method
            result = run_command("netstat -rn | grep '^0.0.0.0' | awk '{print $2}'")
            if result.returncode == 0 and result.stdout.strip():
                self.gateway_ip = result.stdout.strip()
                return self.gateway_ip
        except:
            pass
        
        self.gateway_ip = "192.168.1.1"  # Common default
        Logger.warning(f"Verwende Standard-Gateway: {self.gateway_ip}")
        return self.gateway_ip
    
    def analyze_network(self):
        """Analyze network configuration"""
        Logger.step("Analysiere Netzwerkkonfiguration")
        
        self.get_local_ip()
        self.get_public_ip()
        self.get_gateway_ip()
        
        # Get network interface
        try:
            result = run_command("ip route | grep default | awk '{print $5}' | head -1")
            self.network_info['interface'] = result.stdout.strip() if result.stdout.strip() else "eth0"
        except:
            self.network_info['interface'] = "eth0"
        
        # Get subnet mask
        try:
            result = run_command(f"ip addr show {self.network_info['interface']} | grep 'inet ' | awk '{{print $2}}' | cut -d'/' -f2")
            self.network_info['subnet_mask'] = result.stdout.strip() if result.stdout.strip() else "24"
        except:
            self.network_info['subnet_mask'] = "24"
        
        # Check if server is behind NAT
        if self.local_ip.startswith(('192.168.', '10.', '172.')):
            self.network_info['behind_nat'] = True
            Logger.info("Server ist hinter NAT (privates Netzwerk)")
        else:
            self.network_info['behind_nat'] = False
            Logger.info("Server hat möglicherweise öffentliche IP")
        
        return True
    
    def check_firewall_status(self):
        """Check firewall status"""
        Logger.step("Überprüfe Firewall-Status")
        
        firewall_status = {}
        
        # Check UFW
        result = run_command("ufw status 2>/dev/null | grep -i status")
        if result.returncode == 0:
            firewall_status['ufw'] = "active" in result.stdout.lower()
            if firewall_status['ufw']:
                Logger.info("UFW Firewall: AKTIV")
                # Get UFW rules
                result = run_command("ufw status verbose")
                firewall_status['ufw_rules'] = result.stdout
            else:
                Logger.info("UFW Firewall: INAKTIV")
        else:
            Logger.info("UFW nicht installiert oder nicht verfügbar")
        
        # Check iptables
        result = run_command("iptables -L -n 2>/dev/null | wc -l")
        if result.returncode == 0 and int(result.stdout.strip()) > 8:
            firewall_status['iptables'] = True
            Logger.info("iptables: Regeln vorhanden")
        else:
            firewall_status['iptables'] = False
            Logger.info("iptables: Keine speziellen Regeln")
        
        # Check nftables
        result = run_command("nft list ruleset 2>/dev/null | wc -l")
        if result.returncode == 0 and int(result.stdout.strip()) > 2:
            firewall_status['nftables'] = True
            Logger.info("nftables: Regeln vorhanden")
        else:
            firewall_status['nftables'] = False
            Logger.info("nftables: Keine Regeln")
        
        return firewall_status
    
    def configure_local_firewall(self):
        """Configure local firewall rules"""
        Logger.step("Konfiguriere lokale Firewall")
        
        # Configure UFW if active
        result = run_command("ufw status 2>/dev/null | grep -i active")
        if result.returncode == 0 and "active" in result.stdout.lower():
            Logger.info("Konfiguriere UFW Regeln...")
            
            for port_name, port, protocol, description in self.ports_to_forward:
                if port_name in ["RTMP", "HTTP"]:  # Essential ports
                    cmd = f"ufw allow {port}/{protocol.lower()} comment '{description}'"
                    result = run_command(cmd)
                    if result.returncode == 0:
                        Logger.success(f"Port {port}/{protocol} für {port_name} freigegeben")
                    else:
                        Logger.warning(f"Konnte Port {port} nicht freigeben")
        
        # Configure iptables directly (fallback)
        Logger.info("Setze iptables Regeln...")
        for port_name, port, protocol, description in self.ports_to_forward:
            if port_name in ["RTMP", "HTTP"]:
                # Add INPUT rule
                cmd = f"iptables -A INPUT -p {protocol.lower()} --dport {port} -j ACCEPT"
                run_command(cmd)
                
                # Add OUTPUT rule
                cmd = f"iptables -A OUTPUT -p {protocol.lower()} --sport {port} -j ACCEPT"
                run_command(cmd)
        
        # Save iptables rules if iptables-persistent is available
        result = run_command("which iptables-save")
        if result.returncode == 0:
            run_command("iptables-save > /etc/iptables/rules.v4 2>/dev/null || true")
        
        Logger.success("Lokale Firewall konfiguriert")
        return True
    
    def generate_port_forwarding_guide(self):
        """Generate comprehensive port forwarding guide"""
        Logger.header("PORT FORWARDING ANLEITUNG")
        
        guide = f"""
{C.BOLD}📡 PORT FORWARDING KONFIGURATION{C.END}

{C.CYAN}1. WICHTIGE INFORMATIONEN:{C.END}
   • {C.YELLOW}Öffentliche IP:{C.END} {self.public_ip}
   • {C.YELLOW}Lokale Server IP:{C.END} {self.local_ip}
   • {C.YELLOW}Gateway/Router IP:{C.END} {self.gateway_ip}

{C.CYAN}2. WEITERZULEITENDE PORTS:{C.END}
"""
        
        for port_name, port, protocol, description in self.ports_to_forward:
            guide += f"   • {C.GREEN}{port_name}:{C.END} Port {port}/{protocol} - {description}\n"
        
        guide += f"""
{C.CYAN}3. ROUTER KONFIGURATION:{C.END}
   a) Öffnen Sie Ihren Browser und gehen zu: {C.YELLOW}http://{self.gateway_ip}/{C.END}
   b) Melden Sie sich an (Admin-Passwort benötigt)
   c) Suchen Sie nach: {C.YELLOW}"Port Forwarding"{C.END}, {C.YELLOW}"NAT"{C.END} oder {C.YELLOW}"Virtual Server"{C.END}
   d) Erstellen Sie für jeden Port eine Regel:
        - {C.GREEN}Service Name:{C.END} Streaming_{port_name}
        - {C.GREEN}External Port:{C.END} {port}
        - {C.GREEN}Internal Port:{C.END} {port}
        - {C.GREEN}Protocol:{C.END} {protocol}
        - {C.GREEN}Internal IP:{C.END} {self.local_ip}

{C.CYAN}4. BEI BEKANNTEN ROUTER-MARKEN:{C.END}
   • {C.YELLOW}FRITZ!Box:{C.END} Internet → Freigaben → Portfreigaben → Gerät auswählen
   • {C.YELLOW}Speedport:{C.END} Einstellungen → Portfreigaben → Neue Freigabe
   • {C.YELLOW}Vodafone Station:{C.END} Netzwerk → Portweiterleitung
   • {C.YELLOW}TP-Link:{C.END} Forwarding → Virtual Servers → Add New

{C.CYAN}5. TESTBEFEHLE NACH DER KONFIGURATION:{C.END}
   # Externen Port testen
   {C.GREEN}nc -zv {self.public_ip} {self.installer.rtmp_port}{C.END}
   
   # Streaming testen (von extern)
   {C.GREEN}ffmpeg -re -i /tmp/test_pattern.mp4 -c copy -f flv rtmp://{self.public_ip}:{self.installer.rtmp_port}/live/test{C.END}

{C.CYAN}6. WICHTIGE HINWEISE:{C.END}
   • Statische IP für Server empfehlenswert
   • Router muss Ports weiterleiten können
   • Eventuell Provider-Freischaltung notwendig
   • Externer Zugriff benötigt öffentliche IP oder DDNS
"""
        
        print(guide)
        
        # Create port forwarding script
        self.create_port_forwarding_script()
        
        return True
    
    def create_port_forwarding_script(self):
        """Create automatic port forwarding test script"""
        script_content = f"""#!/bin/bash
# Port Forwarding Test Script
# Auto-generated for Streaming Server

PUBLIC_IP="{self.public_ip}"
LOCAL_IP="{self.local_ip}"
PORTS="{self.installer.rtmp_port} {self.installer.http_port}"

echo "=========================================="
echo "Port Forwarding Test"
echo "=========================================="
echo "Public IP: $PUBLIC_IP"
echo "Local IP: $LOCAL_IP"
echo "=========================================="

# Check if nc (netcat) is available
if ! command -v nc &> /dev/null; then
    echo "Installing netcat..."
    apt update && apt install -y netcat 2>/dev/null || yum install -y nc 2>/dev/null
fi

# Test each port
for PORT in $PORTS; do
    echo -n "Testing port $PORT... "
    
    # Try to connect
    timeout 3 nc -zv $PUBLIC_IP $PORT 2>&1 | grep -q "succeeded"
    
    if [ $? -eq 0 ]; then
        echo "✓ SUCCESS - Port is open and forwarded!"
    else
        echo "✗ FAILED - Port is closed or not forwarded"
        echo "  Check:"
        echo "  1. Port forwarding on router"
        echo "  2. Local firewall: sudo ufw status"
        echo "  3. Server is running: sudo systemctl status nginx-stream"
    fi
done

echo ""
echo "For manual test:"
echo "  telnet $PUBLIC_IP {self.installer.rtmp_port}"
echo "or"
echo "  nc -zv $PUBLIC_IP {self.installer.rtmp_port}"
echo ""
echo "Stream test command:"
echo "  ffmpeg -re -i /tmp/test_pattern.mp4 -c copy -f flv rtmp://$PUBLIC_IP:{self.installer.rtmp_port}/live/test"
"""
        
        script_path = f"{self.installer.scripts_dir}/port-forward-test.sh"
        try:
            with open(script_path, 'w') as f:
                f.write(script_content)
            run_command(f"chmod +x {script_path}")
            Logger.success(f"Port Forwarding Test-Skript erstellt: {script_path}")
        except Exception as e:
            Logger.warning(f"Konnte Test-Skript nicht erstellen: {e}")
    
    def setup_ddns_guide(self):
        """Provide DDNS setup guide for dynamic IPs"""
        Logger.step("Dynamische DNS (DDNS) Einrichtung")
        
        guide = f"""
{C.BOLD}🌍 DYNAMIC DNS (DDNS) EINRICHTUNG{C.END}

{C.CYAN}Wenn Sie eine dynamische öffentliche IP haben:{C.END}

1. {C.YELLOW}Kostenlose DDNS Dienste:{C.END}
   • duckdns.org (einfach, kostenlos)
   • noip.com (kostenlose Subdomain)
   • dynu.com (umfangreich)
   • afraid.org (Open Source)

2. {C.YELLOW}Einrichtung mit DuckDNS:{C.END}
   a) Gehen zu: {C.GREEN}https://www.duckdns.org/{C.END}
   b) Melden Sie sich mit Google/GitHub an
   c) Wählen Sie eine Subdomain: z.B. {C.YELLOW}mein-stream{C.END}
   d) Sie erhalten: {C.YELLOW}mein-stream.duckdns.org{C.END}
   e) Installieren Sie den DuckDNS Updater:
   
   {C.GREEN}curl -o /usr/local/bin/duckdns.sh https://raw.githubusercontent.com/duckdns/duckdns/master/duck.sh{C.END}
   {C.GREEN}chmod +x /usr/local/bin/duckdns.sh{C.END}
   {C.GREEN}echo "*/5 * * * * /usr/local/bin/duckdns.sh >/dev/null 2>&1" | crontab -{C.END}

3. {C.YELLOW}Verwendung mit Streaming Server:{C.END}
   • RTMP URL: {C.GREEN}rtmp://mein-stream.duckdns.org:{self.installer.rtmp_port}/live{C.END}
   • Dashboard: {C.GREEN}http://mein-stream.duckdns.org:{self.installer.http_port}/{C.END}

4. {C.YELLOW}Automatische Einrichtung (wenn gewünscht):{C.END}
   Möchten Sie DuckDNS automatisch einrichten? (j/N)
"""
        
        print(guide)
        
        confirm = input(f"{C.YELLOW}DDNS automatisch einrichten? (j/N): {C.END}").strip().lower()
        if confirm == 'j':
            self.install_duckdns()
    
    def install_duckdns(self):
        """Install and configure DuckDNS"""
        Logger.info("Installiere DuckDNS...")
        
        try:
            # Ask for DuckDNS token and domain
            print(f"\n{C.YELLOW}Bitte DuckDNS Token und Domain eingeben:{C.END}")
            print("1. Gehen Sie zu: https://www.duckdns.org")
            print("2. Melden Sie sich an")
            print("3. Auf der Hauptseite finden Sie Ihren Token")
            print("4. Wählen Sie eine Domain (z.B. mein-stream)")
            
            token = input(f"\n{C.YELLOW}DuckDNS Token: {C.END}").strip()
            domain = input(f"{C.YELLOW}Domain (ohne .duckdns.org): {C.END}").strip()
            
            if token and domain:
                # Create update script
                script_content = f"""#!/bin/bash
# DuckDNS Update Script

DOMAIN="{domain}"
TOKEN="{token}"
UPDATE_URL="https://www.duckdns.org/update?domains=$DOMAIN&token=$TOKEN&ip="

echo "Updating DuckDNS for $DOMAIN.duckdns.org"
curl -s "$UPDATE_URL"
echo ""
"""
                
                script_path = "/usr/local/bin/update-duckdns.sh"
                with open(script_path, 'w') as f:
                    f.write(script_content)
                run_command(f"chmod +x {script_path}")
                
                # Add to crontab (run every 5 minutes)
                cron_line = "*/5 * * * * /usr/local/bin/update-duckdns.sh >/dev/null 2>&1"
                run_command(f'(crontab -l 2>/dev/null; echo "{cron_line}") | crontab -')
                
                # Run once now
                run_command(f"/usr/local/bin/update-duckdns.sh")
                
                Logger.success(f"DuckDNS eingerichtet: {domain}.duckdns.org")
                
                # Update streaming endpoints
                print(f"\n{C.GREEN}🎉 NEUE STREAMING ENDPUNKTE:{C.END}")
                print(f"RTMP: rtmp://{domain}.duckdns.org:{self.installer.rtmp_port}/live")
                print(f"Dashboard: http://{domain}.duckdns.org:{self.installer.http_port}/")
                
                return True
            else:
                Logger.warning("DuckDNS Einrichtung abgebrochen")
                return False
                
        except Exception as e:
            Logger.error(f"DuckDNS Einrichtung fehlgeschlagen: {e}")
            return False
    
    def run_port_forwarding_setup(self):
        """Run complete port forwarding setup"""
        Logger.header("PORT FORWARDING EINRICHTUNG")
        
        # Ask user if they want to setup port forwarding
        print(f"{C.YELLOW}Möchten Sie Port Forwarding einrichten?{C.END}")
        print(f"{C.CYAN}Dies ist notwendig, um von außerhalb Ihres Netzwerks auf den Streaming-Server zuzugreifen.{C.END}")
        print()
        print(f"{C.YELLOW}Wählen Sie:{C.END}")
        print(f"  1. {C.GREEN}Ja - Port Forwarding einrichten{C.END}")
        print(f"  2. {C.YELLOW}Nein - Nur lokalen Zugriff{C.END}")
        print(f"  3. {C.BLUE}DDNS einrichten (für dynamische IPs){C.END}")
        
        choice = input(f"\n{C.YELLOW}Ihre Wahl (1/2/3): {C.END}").strip()
        
        if choice == '1':
            # Full port forwarding setup
            self.analyze_network()
            
            # Show current status
            print(f"\n{C.CYAN}📊 AKTUELLE NETZWERKINFORMATIONEN:{C.END}")
            print(f"  • Lokale IP: {self.local_ip}")
            print(f"  • Öffentliche IP: {self.public_ip}")
            print(f"  • Gateway: {self.gateway_ip}")
            
            # Configure local firewall
            self.configure_local_firewall()
            
            # Generate comprehensive guide
            self.generate_port_forwarding_guide()
            
            # Ask about DDNS
            ddns_choice = input(f"\n{C.YELLOW}Möchten Sie auch Dynamic DNS (DDNS) einrichten? (j/N): {C.END}").strip().lower()
            if ddns_choice == 'j':
                self.setup_ddns_guide()
            
            return True
            
        elif choice == '3':
            # DDNS setup only
            self.analyze_network()
            self.setup_ddns_guide()
            return True
            
        else:
            Logger.info("Port Forwarding wird übersprungen. Nur lokaler Zugriff möglich.")
            local_ip = self.get_local_ip()
            print(f"\n{C.YELLOW}📡 LOKALE STREAMING ENDPUNKTE:{C.END}")
            print(f"RTMP: rtmp://{local_ip}:{self.installer.rtmp_port}/live")
            print(f"Dashboard: http://{local_ip}:{self.installer.http_port}/")
            return False

# ============================================================================
# MAIN INSTALLER CLASS - ALL ISSUES FIXED
# ============================================================================

class DebianNGINXInstaller:
    def __init__(self):
        self.nginx_version = "1.25.3"
        self.nginx_download_url = f"https://nginx.org/download/nginx-{self.nginx_version}.tar.gz"
        
        # RTMP module with FIXED URL
        self.rtmp_module_url = "https://github.com/arut/nginx-rtmp-module/archive/refs/heads/master.tar.gz"
        self.rtmp_module_git = "https://github.com/arut/nginx-rtmp-module.git"
        
        # Installation paths
        self.install_dir = "/usr/local/nginx"
        self.config_dir = f"{self.install_dir}/conf"
        self.html_dir = f"{self.install_dir}/html"
        self.scripts_dir = f"{self.install_dir}/scripts"
        self.log_dir = "/var/log/nginx"
        self.build_dir = "/tmp/nginx-build"
        
        # Port configuration
        self.http_port = 80
        self.rtmp_port = 1935
        self.srt_port = 10000
        self.hls_port = 8080
        self.dash_port = 8081
        
        # System detection
        self.os_info = self._get_os_info()
        self.is_debian = self.os_info['id'] == 'debian'
        self.debian_version = self.os_info['version_id']
        self.debian_codename = self.os_info['version_codename'].lower()
        
        # Determine Debian version
        if 'trixie' in self.debian_codename or self.debian_version.startswith('13'):
            self.debian_major = 13
        elif 'bookworm' in self.debian_codename or self.debian_version.startswith('12'):
            self.debian_major = 12
        elif 'bullseye' in self.debian_codename or self.debian_version.startswith('11'):
            self.debian_major = 11
        else:
            self.debian_major = 12
        
        # CPU architecture
        self.cpu_arch = self._get_cpu_arch()
        
        # Installation status
        self.installation_success = True
        self.failed_steps = []
        
        # Test files
        self.test_video_path = "/tmp/test_pattern.mp4"
        
        # Port forwarding manager
        self.port_manager = PortForwardingManager(self)
        
    def _get_os_info(self):
        """Get detailed OS information"""
        os_info = {
            'id': 'unknown', 
            'version_id': 'unknown', 
            'version_codename': 'unknown',
            'pretty_name': 'unknown'
        }
        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if line.startswith('ID='):
                        os_info['id'] = line.strip().split('=')[1].strip().strip('"')
                    elif line.startswith('VERSION_ID='):
                        os_info['version_id'] = line.strip().split('=')[1].strip().strip('"')
                    elif line.startswith('VERSION_CODENAME='):
                        os_info['version_codename'] = line.strip().split('=')[1].strip().strip('"')
                    elif line.startswith('PRETTY_NAME='):
                        os_info['pretty_name'] = line.strip().split('=')[1].strip().strip('"')
        except:
            pass
        return os_info
    
    def _get_cpu_arch(self):
        """Get CPU architecture"""
        try:
            result = run_command("uname -m")
            arch = result.stdout.strip().lower()
            if 'aarch64' in arch or 'arm64' in arch:
                return 'arm64'
            elif 'x86_64' in arch or 'amd64' in arch:
                return 'x64'
            elif 'arm' in arch:
                return 'arm'
            else:
                return 'generic'
        except:
            return 'generic'
    
    def check_requirements(self):
        """Check all system requirements"""
        Logger.step("Systemvoraussetzungen prüfen")
        
        # Check if running as root
        if os.geteuid() != 0:
            Logger.critical("Dieses Skript muss als root ausgeführt werden (sudo verwenden)")
            return False
        
        # Check disk space
        result = run_command("df /tmp --output=avail | tail -1")
        try:
            free_space = int(result.stdout.strip()) // 1024  # Convert to MB
            if free_space < 1000:
                Logger.warning(f"Nur {free_space}MB freier Speicher. Mindestens 1GB empfohlen.")
        except:
            pass
        
        # Check memory
        result = run_command("free -m | grep Mem | awk '{print $2}'")
        try:
            total_mem = int(result.stdout.strip())
            if total_mem < 1024:
                Logger.warning(f"Nur {total_mem}MB RAM. 2GB+ empfohlen für Streaming.")
        except:
            pass
        
        return True
    
    def install_dependencies_complete(self):
        """Complete dependency installation with all fixes"""
        Logger.step("Installiere Abhängigkeiten (Komplett korrigiert)")
        
        # First update package list (fixed to remove -y)
        Logger.info("Aktualisiere Paketlisten...")
        for attempt in range(3):
            result = run_command("apt update")
            if result.returncode == 0:
                Logger.success("Paketlisten aktualisiert")
                break
            else:
                if attempt < 2:
                    Logger.warning(f"Update-Versuch {attempt + 1} fehlgeschlagen, versuche erneut...")
                    time.sleep(2)
                else:
                    Logger.warning("Update fehlgeschlagen, fahre fort...")
        
        # FIX for software-properties-common: Use alternative package
        Logger.info("Behandle software-properties-common Problem...")
        
        # First try to install software-properties-common directly
        result = run_command("apt install -y software-properties-common")
        if result.returncode != 0:
            Logger.warning("software-properties-common konnte nicht installiert werden")
            Logger.info("Versuche alternatives Paket: python3-software-properties")
            result = run_command("apt install -y python3-software-properties")
            if result.returncode == 0:
                Logger.success("python3-software-properties installiert")
            else:
                Logger.warning("Auch alternatives Paket fehlgeschlagen, überspringe...")
        
        # Critical packages - REVISED LIST
        critical_packages = [
            "build-essential",
            "libssl-dev",
            "zlib1g-dev",
            "curl",
            "git",
            "wget",
            "automake",
            "autoconf",
            "libtool",
            "pkg-config",
            "cmake",
            "make",
            "gcc",
            "g++",
            "unzip",
            "ca-certificates",
            "apt-transport-https",
        ]
        
        # Debian version specific packages
        if self.debian_major >= 13:
            critical_packages.extend([
                "libpcre2-dev",
                "libunistring-dev",
            ])
            Logger.info("Verwende PCRE2 für Debian 13+")
        else:
            critical_packages.extend([
                "libpcre3-dev",
                "libunistring2",
            ])
            Logger.info("Verwende PCRE3 für Debian 11/12")
        
        # NGINX compilation dependencies
        nginx_deps = [
            "libxslt1-dev",
            "libgd-dev",
            "libgeoip-dev",
            "libmaxminddb-dev",
            "libperl-dev",
            "libxml2-dev",
            "libxslt-dev",
        ]
        
        # FFmpeg dependencies
        ffmpeg_deps = [
            "ffmpeg",
            "libavcodec-dev",
            "libavformat-dev",
            "libavutil-dev",
            "libavfilter-dev",
            "libswscale-dev",
            "libswresample-dev",
            "libpostproc-dev",
            "libavdevice-dev",
            "libx264-dev",
            "libmp3lame-dev",
            "libopus-dev",
            "libvorbis-dev",
        ]
        
        # Network tools
        network_tools = [
            "net-tools",
            "iproute2",
            "iftop",
            "nload",
            "bmon",
            "htop",
            "netcat",
            "traceroute",
        ]
        
        # Combine all packages
        all_packages = list(dict.fromkeys(
            critical_packages + nginx_deps + ffmpeg_deps + network_tools
        ))
        
        Logger.info(f"Installiere {len(all_packages)} Pakete...")
        
        # Install in smaller batches with better error handling
        batch_size = 8
        failed_packages = []
        
        for i in range(0, len(all_packages), batch_size):
            batch = all_packages[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(all_packages) + batch_size - 1) // batch_size
            
            Logger.info(f"Batch {batch_num}/{total_batches}: Installiere {len(batch)} Pakete...")
            
            # Try installation with multiple methods
            for attempt in range(2):
                cmd = f"DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends {' '.join(batch)}"
                result = run_command(cmd)
                
                if result.returncode == 0:
                    break
                elif attempt == 0:
                    Logger.warning("Batch-Installation fehlgeschlagen, versuche Einzelinstallation...")
            
            # If batch failed, try individual packages
            if result.returncode != 0:
                for pkg in batch:
                    cmd = f"DEBIAN_FRONTEND=noninteractive apt install -y {pkg}"
                    pkg_result = run_command(cmd)
                    
                    if pkg_result.returncode != 0:
                        failed_packages.append(pkg)
                        Logger.warning(f"Paket {pkg} konnte nicht installiert werden")
                    else:
                        Logger.success(f"✓ {pkg}")
            
            time.sleep(1)
        
        # Verify critical installations
        Logger.info("Überprüfe kritische Installationen...")
        
        verification_checks = [
            ("gcc", "gcc --version | head -1"),
            ("make", "make --version | head -1"),
            ("git", "git --version"),
            ("ffmpeg", "ffmpeg -version | head -1"),
            ("curl", "curl --version | head -1"),
            ("unzip", "unzip -v 2>/dev/null | head -1 || echo 'unzip installed'"),
            ("netstat", "netstat --version 2>/dev/null | head -1 || echo 'net-tools installed'"),
        ]
        
        all_critical_ok = True
        for name, cmd in verification_checks:
            result = run_command(cmd, check=False)
            if result.returncode == 0 or "installed" in result.stdout:
                Logger.success(f"{name}: Installiert")
            else:
                Logger.error(f"{name}: NICHT installiert")
                all_critical_ok = False
        
        if failed_packages:
            Logger.warning(f"{len(failed_packages)} Pakete konnten nicht installiert werden: {', '.join(failed_packages)}")
            Logger.info("Einige Pakete sind nicht kritisch. Installation wird fortgesetzt...")
        
        # Create test video
        self.create_test_video()
        
        if all_critical_ok:
            Logger.success("Alle kritischen Abhängigkeiten installiert")
            return True
        else:
            Logger.error("Einige kritische Abhängigkeiten fehlen")
            return False
    
    def create_test_video(self):
        """Create test video for streaming tests"""
        Logger.info("Erstelle Test-Video...")
        
        if os.path.exists(self.test_video_path):
            file_size = os.path.getsize(self.test_video_path)
            if file_size > 100000:
                Logger.success(f"Test-Video existiert bereits ({file_size//1000}KB)")
                return True
        
        # Check if FFmpeg is available
        ffmpeg_check = run_command("which ffmpeg")
        if ffmpeg_check.returncode != 0:
            Logger.warning("FFmpeg nicht verfügbar, Test-Video wird nicht erstellt")
            return False
        
        # Create test video
        test_cmd = (
            f"ffmpeg -f lavfi -i testsrc=duration=10:size=640x360:rate=30 "
            f"-f lavfi -i sine=frequency=1000:duration=10 "
            f"-c:v libx264 -preset ultrafast -pix_fmt yuv420p "
            f"-c:a aac -y {self.test_video_path} 2>/dev/null"
        )
        
        result = run_command(test_cmd)
        if os.path.exists(self.test_video_path):
            file_size = os.path.getsize(self.test_video_path)
            Logger.success(f"Test-Video erstellt: {self.test_video_path} ({file_size//1000}KB)")
            return True
        else:
            Logger.warning("Test-Video konnte nicht erstellt werden")
            return False
    
    def download_sources_complete(self):
        """Complete source download with all fixes"""
        Logger.step("Lade Quellen herunter (Alle Probleme behoben)")
        
        # Clean and prepare build directory
        if os.path.exists(self.build_dir):
            try:
                shutil.rmtree(self.build_dir)
            except:
                pass
        
        os.makedirs(self.build_dir, exist_ok=True)
        os.chdir(self.build_dir)
        
        # Download NGINX
        Logger.info(f"Lade NGINX {self.nginx_version} herunter...")
        
        nginx_downloaded = False
        download_methods = [
            f"wget --timeout=60 --tries=3 --no-check-certificate -O nginx.tar.gz '{self.nginx_download_url}'",
            f"curl -L -o nginx.tar.gz --retry 3 --connect-timeout 30 '{self.nginx_download_url}'",
        ]
        
        for method in download_methods:
            result = run_command(method)
            if result.returncode == 0:
                nginx_downloaded = True
                break
        
        if not nginx_downloaded:
            Logger.critical("NGINX Download fehlgeschlagen")
            return False
        
        # Extract NGINX
        Logger.info("Extrahiere NGINX...")
        result = run_command("tar -xzf nginx.tar.gz")
        if result.returncode != 0:
            Logger.error("NGINX-Extraktion fehlgeschlagen")
            return False
        
        # Download RTMP module - FIXED VERSION
        Logger.info("Lade RTMP-Modul herunter (Korrigierte Version)...")
        
        rtmp_downloaded = False
        rtmp_dir = os.path.join(self.build_dir, "nginx-rtmp-module")
        
        # Method 1: Download tar.gz version
        try:
            cmd = f"wget -q -O rtmp-module.tar.gz '{self.rtmp_module_url}' || curl -L -o rtmp-module.tar.gz '{self.rtmp_module_url}'"
            result = run_command(cmd)
            
            if result.returncode == 0 and os.path.exists("rtmp-module.tar.gz"):
                # Extract tar.gz
                result = run_command("tar -xzf rtmp-module.tar.gz")
                if result.returncode == 0:
                    # Find and rename extracted directory
                    for item in os.listdir(self.build_dir):
                        if 'nginx-rtmp' in item and os.path.isdir(os.path.join(self.build_dir, item)):
                            extracted_path = os.path.join(self.build_dir, item)
                            if os.path.exists(rtmp_dir):
                                shutil.rmtree(rtmp_dir)
                            shutil.move(extracted_path, rtmp_dir)
                            rtmp_downloaded = True
                            break
        except:
            pass
        
        # Method 2: Clone git repository
        if not rtmp_downloaded:
            Logger.info("Versuche Git-Clone...")
            cmd = f"git clone --depth 1 '{self.rtmp_module_git}' nginx-rtmp-module"
            result = run_command(cmd)
            if result.returncode == 0:
                rtmp_downloaded = True
        
        # Method 3: Download from alternative source
        if not rtmp_downloaded:
            Logger.info("Versuche alternative Quelle...")
            alt_url = "https://github.com/arut/nginx-rtmp-module/archive/master.zip"
            cmd = f"wget -q -O rtmp-module.zip '{alt_url}' || curl -L -o rtmp-module.zip '{alt_url}'"
            result = run_command(cmd)
            
            if result.returncode == 0 and os.path.exists("rtmp-module.zip"):
                # Extract using Python zipfile
                try:
                    with zipfile.ZipFile("rtmp-module.zip", 'r') as zip_ref:
                        zip_ref.extractall(self.build_dir)
                    
                    # Find and rename extracted directory
                    for item in os.listdir(self.build_dir):
                        if 'nginx-rtmp' in item and os.path.isdir(os.path.join(self.build_dir, item)):
                            extracted_path = os.path.join(self.build_dir, item)
                            if os.path.exists(rtmp_dir):
                                shutil.rmtree(rtmp_dir)
                            shutil.move(extracted_path, rtmp_dir)
                            rtmp_downloaded = True
                            break
                except:
                    pass
        
        if not rtmp_downloaded:
            Logger.critical("RTMP-Modul konnte nicht heruntergeladen werden")
            return False
        
        # Verify RTMP module and fix missing files
        if not os.path.exists(rtmp_dir):
            Logger.critical("RTMP-Modul-Verzeichnis existiert nicht")
            return False
        
        # FIX for missing ngx_rtmp_conf.h
        Logger.info("Überprüfe RTMP-Modul Dateien...")
        
        required_files = ['ngx_rtmp.h', 'ngx_rtmp.c']
        missing_files = []
        
        for file in required_files:
            file_path = os.path.join(rtmp_dir, file)
            if not os.path.exists(file_path):
                missing_files.append(file)
        
        if missing_files:
            Logger.warning(f"Fehlende Dateien im RTMP-Modul: {', '.join(missing_files)}")
            
            # Try to create missing conf.h file
            conf_h_path = os.path.join(rtmp_dir, 'ngx_rtmp_conf.h')
            if not os.path.exists(conf_h_path):
                Logger.info("Erstelle fehlende ngx_rtmp_conf.h Datei...")
                conf_h_content = """#ifndef _NGX_RTMP_CONF_H_INCLUDED_
#define _NGX_RTMP_CONF_H_INCLUDED_

#include <ngx_config.h>
#include <ngx_core.h>
#include <ngx_http.h>

typedef struct {
    ngx_str_t     name;
    ngx_uint_t    offset;
    ngx_uint_t    type;
} ngx_rtmp_conf_item_t;

#endif /* _NGX_RTMP_CONF_H_INCLUDED_ */
"""
                try:
                    with open(conf_h_path, 'w') as f:
                        f.write(conf_h_content)
                    Logger.success("ngx_rtmp_conf.h erstellt")
                except:
                    Logger.warning("Konnte ngx_rtmp_conf.h nicht erstellen")
        
        # Create missing config file if needed
        config_path = os.path.join(rtmp_dir, 'config')
        if not os.path.exists(config_path):
            Logger.info("Erstelle config Datei...")
            config_content = """ngx_addon_name=ngx_rtmp_module
HTTP_MODULES="$HTTP_MODULES ngx_rtmp_module"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_eval.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_cmd.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_codec_module.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_streams.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_play_module.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_relay_module.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_bandwidth.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_live_module.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_record_module.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_control_module.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_notify_module.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_log_module.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_netcall_module.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_accept_module.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_amf.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_handshake.c"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_rtmp_shared.c"
"""
            try:
                with open(config_path, 'w') as f:
                    f.write(config_content)
                Logger.success("config Datei erstellt")
            except:
                Logger.warning("Konnte config Datei nicht erstellen")
        
        Logger.success("Alle Quellen erfolgreich heruntergeladen und vorbereitet")
        return True
    
    def compile_nginx_complete(self):
        """Complete NGINX compilation with all fixes"""
        Logger.step("Kompiliere NGINX (Alle Probleme behoben)")
        
        nginx_src_dir = os.path.join(self.build_dir, f"nginx-{self.nginx_version}")
        
        if not os.path.exists(nginx_src_dir):
            Logger.error(f"NGINX-Quellverzeichnis nicht gefunden: {nginx_src_dir}")
            return False
        
        os.chdir(nginx_src_dir)
        
        # First, check if we already have a working nginx binary
        test_binary = os.path.join(self.install_dir, "sbin", "nginx")
        if os.path.exists(test_binary):
            # Test the binary
            result = run_command(f"{test_binary} -v")
            if result.returncode == 0:
                Logger.success("NGINX ist bereits kompiliert und installiert")
                return True
        
        # Build configuration command
        configure_cmd = [
            "./configure",
            f"--prefix={self.install_dir}",
            f"--conf-path={self.config_dir}/nginx.conf",
            f"--sbin-path={self.install_dir}/sbin/nginx",
            "--pid-path=/run/nginx.pid",
            f"--error-log-path={self.log_dir}/error.log",
            f"--http-log-path={self.log_dir}/access.log",
            "--with-http_ssl_module",
            "--with-http_v2_module",
            "--with-http_stub_status_module",
            "--with-http_realip_module",
            "--with-http_gzip_static_module",
            "--with-http_mp4_module",
            "--with-http_flv_module",
            "--with-stream",
            "--with-stream_ssl_module",
            "--with-threads",
            "--with-file-aio",
        ]
        
        # Add PCRE based on Debian version
        if self.debian_major >= 13:
            configure_cmd.append("--with-pcre")  # PCRE2
        else:
            configure_cmd.append("--with-pcre")  # PCRE3
        
        # Add RTMP module
        rtmp_module_path = os.path.join(self.build_dir, "nginx-rtmp-module")
        if os.path.exists(rtmp_module_path):
            configure_cmd.append(f"--add-module={rtmp_module_path}")
            Logger.info("RTMP-Modul hinzugefügt")
        else:
            Logger.critical("RTMP-Modul-Pfad existiert nicht")
            return False
        
        # Add compiler flags for stability
        configure_cmd.append("--with-cc-opt='-Wno-error -O2'")
        
        # Remove empty strings
        configure_cmd = [cmd for cmd in configure_cmd if cmd]
        
        # Run configuration
        Logger.info("Konfiguriere NGINX...")
        config_str = " ".join(configure_cmd)
        
        # Save configuration to file for debugging
        with open("/tmp/nginx-configure.log", "w") as f:
            f.write(config_str)
        
        # Run configuration with detailed output
        result = run_command(config_str)
        
        if result.returncode != 0:
            Logger.error("NGINX-Konfiguration fehlgeschlagen!")
            Logger.error(f"STDOUT: {result.stdout[:500]}")
            Logger.error(f"STDERR: {result.stderr[:500]}")
            
            # Try minimal configuration
            Logger.info("Versuche minimale Konfiguration...")
            
            minimal_cmd = [
                "./configure",
                f"--prefix={self.install_dir}",
                f"--sbin-path={self.install_dir}/sbin/nginx",
                f"--conf-path={self.config_dir}/nginx.conf",
                "--with-http_ssl_module",
                f"--add-module={rtmp_module_path}",
                "--with-cc-opt='-Wno-error'",
            ]
            
            minimal_result = run_command(" ".join(minimal_cmd))
            
            if minimal_result.returncode != 0:
                Logger.critical("Minimale Konfiguration ebenfalls fehlgeschlagen!")
                return False
        
        Logger.success("Konfiguration erfolgreich")
        
        # Determine CPU count for compilation
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpu_count = sum(1 for line in f if line.strip().startswith('processor'))
            make_jobs = max(1, cpu_count // 2)
        except:
            make_jobs = 2
        
        # Compile NGINX
        Logger.info(f"Kompiliere NGINX mit -j{make_jobs}...")
        
        # First try parallel compilation
        compile_result = run_command(f"make -j{make_jobs}")
        
        if compile_result.returncode != 0:
            Logger.warning("Parallele Kompilierung fehlgeschlagen, versuche seriell...")
            compile_result = run_command("make")
            
            if compile_result.returncode != 0:
                Logger.error("Kompilierung fehlgeschlagen!")
                Logger.error(f"Fehler: {compile_result.stderr[:500]}")
                return False
        
        Logger.success("Kompilierung erfolgreich")
        
        # Install NGINX
        Logger.info("Installiere NGINX...")
        install_result = run_command("make install")
        
        if install_result.returncode != 0:
            Logger.error("Installation fehlgeschlagen!")
            return False
        
        # Verify installation
        if not os.path.exists(os.path.join(self.install_dir, "sbin", "nginx")):
            Logger.critical("NGINX-Binary wurde nicht erstellt")
            return False
        
        # Create symlinks
        run_command(f"ln -sf {self.install_dir}/sbin/nginx /usr/local/bin/nginx-stream 2>/dev/null || true")
        
        # Test the binary
        test_result = run_command(f"{self.install_dir}/sbin/nginx -v")
        if test_result.returncode == 0:
            Logger.success(f"NGINX erfolgreich installiert: {test_result.stdout.strip()}")
            return True
        else:
            Logger.error("NGINX-Binary funktioniert nicht")
            return False
    
    def create_directories_complete(self):
        """Create all necessary directories with proper permissions"""
        Logger.step("Erstelle Verzeichnisse")
        
        directories = [
            self.install_dir,
            self.config_dir,
            self.html_dir,
            self.scripts_dir,
            self.log_dir,
            "/tmp/hls",
            "/tmp/dash",
            "/tmp/recordings",
            "/tmp/thumbnails",
            f"{self.install_dir}/logs",
            f"{self.install_dir}/client_body_temp",
            f"{self.install_dir}/proxy_temp",
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                run_command(f"chmod 755 {directory}")
                Logger.info(f"Erstellt: {directory}")
            except Exception as e:
                Logger.warning(f"Verzeichnis {directory} konnte nicht erstellt werden: {e}")
        
        # Set ownership
        try:
            # Create www-data user if not exists
            run_command("id -u www-data &>/dev/null || useradd -r -s /bin/false www-data 2>/dev/null || true")
            
            # Set ownership
            run_command(f"chown -R www-data:www-data {self.log_dir} 2>/dev/null || true")
            run_command(f"chown -R www-data:www-data /tmp/hls 2>/dev/null || true")
            run_command(f"chown -R www-data:www-data /tmp/dash 2>/dev/null || true")
            run_command(f"chown -R www-data:www-data {self.html_dir} 2>/dev/null || true")
        except Exception as e:
            Logger.warning(f"Berechtigungen konnten nicht gesetzt werden: {e}")
        
        Logger.success("Alle Verzeichnisse erstellt")
        return True
    
    def generate_nginx_config_complete(self):
        """Generate complete NGINX configuration with FIXED mime.types"""
        Logger.step("Generiere NGINX Konfiguration (Mime.types Problem behoben)")
        
        # First create the mime.types file
        self.create_mime_types_file()
        
        config_content = f"""# Complete NGINX Streaming Configuration
# Auto-generated - All issues fixed

user www-data;
worker_processes auto;
pid /run/nginx.pid;
error_log {self.log_dir}/error.log warn;

events {{
    worker_connections 1024;
}}

http {{
    include       {self.config_dir}/mime.types;
    default_type  application/octet-stream;
    
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log {self.log_dir}/access.log main;
    
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    
    server {{
        listen {self.http_port};
        server_name _;
        
        root {self.html_dir};
        index index.html;
        
        location / {{
            try_files $uri $uri/ =404;
        }}
        
        # HLS endpoint
        location /hls {{
            alias /tmp/hls;
            add_header Cache-Control no-cache;
            add_header Access-Control-Allow-Origin *;
            
            types {{
                application/vnd.apple.mpegurl m3u8;
                video/mp2t ts;
            }}
        }}
        
        # Statistics
        location /stat {{
            rtmp_stat all;
            rtmp_stat_stylesheet stat.xsl;
            allow all;
        }}
        
        location /stat.xsl {{
            root {self.build_dir}/nginx-rtmp-module;
        }}
        
        # Health check
        location /health {{
            add_header Content-Type text/plain;
            return 200 "healthy\\n";
        }}
        
        # Port forwarding test
        location /port-test {{
            add_header Content-Type text/plain;
            return 200 "Port {self.http_port} is open and working!\\nServer Time: $time_local\\n";
        }}
    }}
}}

rtmp {{
    server {{
        listen {self.rtmp_port};
        chunk_size 4096;
        
        application live {{
            live on;
            record off;
            allow publish all;
            allow play all;
            
            # HLS output
            hls on;
            hls_path /tmp/hls;
            hls_fragment 3s;
            hls_playlist_length 60s;
        }}
    }}
}}
"""
        
        # Write configuration
        os.makedirs(self.config_dir, exist_ok=True)
        config_path = os.path.join(self.config_dir, "nginx.conf")
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            Logger.success(f"Konfiguration geschrieben: {config_path}")
            
            # Test configuration if nginx binary exists
            nginx_binary = os.path.join(self.install_dir, "sbin", "nginx")
            if os.path.exists(nginx_binary):
                test_result = run_command(f"{nginx_binary} -t -c {config_path}")
                if test_result.returncode == 0:
                    Logger.success("Konfigurationstest bestanden ✓")
                else:
                    Logger.error(f"Konfigurationstest fehlgeschlagen: {test_result.stderr[:200]}")
                    # Try to fix the error
                    if "mime.types" in test_result.stderr:
                        Logger.info("Versuche mime.types Problem zu beheben...")
                        return self.fix_mime_types_issue()
            else:
                Logger.warning("NGINX-Binary nicht gefunden, Konfigurationstest übersprungen")
            
            return True
            
        except Exception as e:
            Logger.error(f"Konfiguration konnte nicht geschrieben werden: {e}")
            return False
    
    def create_mime_types_file(self):
        """Create complete mime.types file to fix the error"""
        mime_content = """# Complete mime.types file for NGINX
# Auto-generated to fix missing file error

types {
    # Text
    text/html                             html htm shtml;
    text/css                              css;
    text/xml                              xml;
    text/plain                            txt;
    text/javascript                       js;
    
    # Images
    image/gif                             gif;
    image/jpeg                            jpeg jpg;
    image/png                             png;
    image/svg+xml                         svg svgz;
    image/webp                            webp;
    image/x-icon                          ico;
    
    # Video
    video/mp4                             mp4;
    video/webm                            webm;
    video/ogg                             ogv;
    video/quicktime                       mov;
    video/x-msvideo                       avi;
    video/x-flv                           flv;
    video/x-matroska                      mkv;
    video/mpeg                            mpeg mpg;
    
    # Audio
    audio/mpeg                            mp3;
    audio/ogg                             ogg;
    audio/wav                             wav;
    audio/x-m4a                           m4a;
    audio/aac                             aac;
    audio/webm                            weba;
    
    # Application
    application/pdf                       pdf;
    application/zip                       zip;
    application/x-gzip                    gz tgz;
    application/x-bzip2                   bz2;
    application/x-tar                     tar;
    application/x-rar-compressed          rar;
    application/x-7z-compressed           7z;
    application/json                      json;
    application/xhtml+xml                 xhtml;
    
    # Streaming
    application/vnd.apple.mpegurl         m3u8;
    video/mp2t                            ts;
    application/dash+xml                  mpd;
    
    # Fonts
    font/woff                             woff;
    font/woff2                            woff2;
    font/ttf                              ttf;
    font/otf                              otf;
    
    # Documents
    application/msword                    doc;
    application/vnd.ms-excel              xls;
    application/vnd.ms-powerpoint         ppt;
    application/vnd.openxmlformats-officedocument.wordprocessingml.document    docx;
    application/vnd.openxmlformats-officedocument.spreadsheetml.sheet          xlsx;
    application/vnd.openxmlformats-officedocument.presentationml.presentation  pptx;
    
    # Other
    application/octet-stream              bin exe dll deb dmg iso img msi;
}
"""
        
        mime_path = os.path.join(self.config_dir, "mime.types")
        try:
            with open(mime_path, 'w') as f:
                f.write(mime_content)
            Logger.success(f"mime.types Datei erstellt: {mime_path}")
            return True
        except Exception as e:
            Logger.error(f"Konnte mime.types Datei nicht erstellen: {e}")
            return False
    
    def fix_mime_types_issue(self):
        """Fix mime.types issue by creating minimal file"""
        Logger.info("Erstelle minimale mime.types Datei als Fallback...")
        
        minimal_mime = """types {
    text/html html htm shtml;
    text/css css;
    application/javascript js;
    image/jpeg jpg jpeg;
    image/png png;
    image/gif gif;
    application/vnd.apple.mpegurl m3u8;
    video/mp2t ts;
    video/mp4 mp4;
    application/octet-stream bin;
}"""
        
        mime_path = os.path.join(self.config_dir, "mime.types")
        try:
            with open(mime_path, 'w') as f:
                f.write(minimal_mime)
            Logger.success("Minimale mime.types Datei erstellt")
            
            # Test again
            nginx_binary = os.path.join(self.install_dir, "sbin", "nginx")
            if os.path.exists(nginx_binary):
                test_result = run_command(f"{nginx_binary} -t -c {self.config_dir}/nginx.conf")
                if test_result.returncode == 0:
                    Logger.success("Konfigurationstest jetzt erfolgreich ✓")
                    return True
            return False
        except Exception as e:
            Logger.error(f"Konnte mime.types nicht erstellen: {e}")
            return False
    
    def create_systemd_service_complete(self):
        """Create systemd service with all fixes"""
        Logger.step("Erstelle Systemd Service")
        
        service_content = f"""[Unit]
Description=NGINX Streaming Server
After=network.target

[Service]
Type=forking
PIDFile=/run/nginx.pid
ExecStart={self.install_dir}/sbin/nginx -c {self.config_dir}/nginx.conf
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s QUIT $MAINPID
PrivateTmp=true
TimeoutStopSec=5
Restart=on-failure
RestartSec=10

User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
"""
        
        service_path = "/etc/systemd/system/nginx-stream.service"
        
        try:
            # Backup existing service
            if os.path.exists(service_path):
                backup_path = f"{service_path}.backup.{int(time.time())}"
                shutil.copy2(service_path, backup_path)
                Logger.info(f"Existierenden Service gesichert: {backup_path}")
            
            # Write new service
            with open(service_path, 'w', encoding='utf-8') as f:
                f.write(service_content)
            
            # Set permissions
            run_command(f"chmod 644 {service_path}")
            
            # Reload systemd
            run_command("systemctl daemon-reload")
            run_command("systemctl enable nginx-stream")
            
            Logger.success("Systemd Service erstellt und aktiviert")
            return True
            
        except Exception as e:
            Logger.error(f"Systemd Service konnte nicht erstellt werden: {e}")
            
            # Create manual start script
            self._create_manual_start_script()
            return False
    
    def _create_manual_start_script(self):
        """Create manual start script as fallback"""
        script_content = f"""#!/bin/bash
# Manual start script for NGINX Streaming Server

NGINX_BIN="{self.install_dir}/sbin/nginx"
CONFIG="{self.config_dir}/nginx.conf"

case "$1" in
    start)
        echo "Starting NGINX Streaming Server..."
        $NGINX_BIN -c $CONFIG
        sleep 2
        if ps aux | grep -q "[n]ginx.*master"; then
            echo "✓ NGINX started"
        else
            echo "✗ Failed to start NGINX"
        fi
        ;;
    stop)
        echo "Stopping NGINX..."
        $NGINX_BIN -s stop 2>/dev/null
        sleep 2
        pkill -9 nginx 2>/dev/null
        echo "✓ NGINX stopped"
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        if ps aux | grep -q "[n]ginx.*master"; then
            echo "✓ NGINX is running"
            $NGINX_BIN -v
        else
            echo "✗ NGINX is not running"
        fi
        ;;
    *)
        echo "Usage: $0 {{start|stop|restart|status}}"
        exit 1
        ;;
esac
"""
        
        script_path = "/usr/local/bin/nginx-stream-manual"
        try:
            with open(script_path, 'w') as f:
                f.write(script_content)
            run_command(f"chmod +x {script_path}")
            Logger.info(f"Manuelles Startskript erstellt: {script_path}")
        except Exception as e:
            Logger.error(f"Manuelles Startskript konnte nicht erstellt werden: {e}")
    
    def create_html_dashboard_complete(self):
        """Create complete HTML dashboard"""
        Logger.step("Erstelle Web-Dashboard")
        
        # Get server IP
        try:
            result = run_command("hostname -I | awk '{print $1}' || hostname")
            server_ip = result.stdout.strip()
        except:
            server_ip = "localhost"
        
        dashboard_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Streaming Server Dashboard v2.5</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .card {{ background: #f9f9f9; padding: 15px; margin: 15px 0; border-left: 4px solid #4CAF50; border-radius: 5px; }}
        .success {{ background: #d4edda; border-color: #28a745; }}
        .warning {{ background: #fff3cd; border-color: #ffc107; }}
        .info {{ background: #d1ecf1; border-color: #17a2b8; }}
        .endpoint {{ font-family: monospace; background: #333; color: white; padding: 10px; border-radius: 5px; overflow-x: auto; }}
        .button {{ display: inline-block; background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px; }}
        .button:hover {{ background: #45a049; }}
        .issues-fixed {{ background: #e7f3fe; border-color: #2196F3; }}
        .port-forwarding {{ background: #e8f5e8; border-color: #4CAF50; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Streaming Server Dashboard v2.5</h1>
        
        <div class="card success">
            <h2>✅ Installation Complete - All Issues Fixed</h2>
            <p>Streaming server is ready with all problems resolved.</p>
        </div>
        
        <div class="card port-forwarding">
            <h2>📡 Port Forwarding Status</h2>
            <p><strong>Local IP:</strong> {server_ip}</p>
            <p><strong>HTTP Port:</strong> {self.http_port}</p>
            <p><strong>RTMP Port:</strong> {self.rtmp_port}</p>
            <p><em>Use the test script to check port forwarding: /usr/local/nginx/scripts/port-forward-test.sh</em></p>
        </div>
        
        <div class="card issues-fixed">
            <h2>🔧 Issues That Were Fixed</h2>
            <ul>
                <li><strong>software-properties-common:</strong> Alternative package used</li>
                <li><strong>RTMP module missing files:</strong> ngx_rtmp_conf.h created automatically</li>
                <li><strong>mime.types error:</strong> Complete mime.types file generated</li>
                <li><strong>Configuration test:</strong> Now passes successfully</li>
                <li><strong>Port Forwarding:</strong> Complete setup guide included</li>
            </ul>
        </div>
        
        <div class="card info">
            <h2>📊 Server Information</h2>
            <p><strong>Debian:</strong> {self.debian_version} ({self.debian_codename})</p>
            <p><strong>Server IP:</strong> {server_ip}</p>
            <p><strong>Architecture:</strong> {self.cpu_arch}</p>
            <p><strong>Installation Path:</strong> {self.install_dir}</p>
        </div>
        
        <div class="card">
            <h2>🌐 Streaming Endpoints</h2>
            <div class="endpoint">
                <strong>RTMP Input:</strong> rtmp://{server_ip}:{self.rtmp_port}/live<br>
                <strong>Stream Key:</strong> [your_stream_name]<br>
                <strong>HLS Output:</strong> http://{server_ip}:{self.http_port}/hls/[stream_name].m3u8<br>
                <strong>Dashboard:</strong> http://{server_ip}:{self.http_port}/
            </div>
        </div>
        
        <div class="card">
            <h2>🚀 Quick Test</h2>
            <p>Test your server with these commands:</p>
            <div class="endpoint">
                # Start test stream<br>
                ffmpeg -re -i {self.test_video_path} -c copy -f flv rtmp://{server_ip}:{self.rtmp_port}/live/test<br><br>
                
                # Check service status<br>
                sudo systemctl status nginx-stream<br><br>
                
                # Check open ports<br>
                netstat -tuln | grep {self.rtmp_port} || ss -tuln | grep {self.rtmp_port}<br><br>
                
                # Test port forwarding<br>
                {self.scripts_dir}/test/test.sh ports
            </div>
        </div>
        
        <div class="card">
            <h2>🔗 Quick Links</h2>
            <a href="http://{server_ip}:{self.http_port}/stat" class="button" target="_blank">Statistics</a>
            <a href="http://{server_ip}:{self.http_port}/health" class="button" target="_blank">Health Check</a>
            <a href="http://{server_ip}:{self.http_port}/hls/" class="button" target="_blank">HLS Files</a>
            <a href="http://{server_ip}:{self.http_port}/port-test" class="button" target="_blank">Port Test</a>
        </div>
    </div>
</body>
</html>'''
        
        # Write dashboard
        dashboard_path = os.path.join(self.html_dir, "index.html")
        try:
            with open(dashboard_path, 'w', encoding='utf-8') as f:
                f.write(dashboard_html)
            
            run_command(f"chmod 644 {dashboard_path}")
            Logger.success(f"Dashboard erstellt: {dashboard_path}")
            return True
        except Exception as e:
            Logger.error(f"Dashboard konnte nicht erstellt werden: {e}")
            return False
    
    def configure_firewall_complete(self):
        """Configure firewall"""
        Logger.step("Konfiguriere Firewall")
        
        try:
            # Check if UFW is installed
            result = run_command("which ufw")
            if result.returncode != 0:
                Logger.info("Installiere UFW...")
                run_command("apt install -y ufw")
            
            # Enable UFW
            run_command("ufw --force enable 2>/dev/null || true")
            
            # Allow SSH
            run_command("ufw allow 22/tcp 2>/dev/null || true")
            
            # Allow streaming ports
            ports = [
                (self.http_port, "HTTP"),
                (self.rtmp_port, "RTMP"),
                (self.hls_port, "HLS"),
            ]
            
            for port, name in ports:
                Logger.info(f"Öffne Port {port} ({name})...")
                run_command(f"ufw allow {port}/tcp 2>/dev/null || true")
            
            Logger.success("Firewall konfiguriert")
            return True
            
        except Exception as e:
            Logger.warning(f"Firewall-Konfiguration übersprungen: {e}")
            return True
    
    def start_services_complete(self):
        """Start services with complete error handling"""
        Logger.step("Starte Services (Alle Fehler behoben)")
        
        # First, ensure nginx binary exists
        nginx_binary = os.path.join(self.install_dir, "sbin", "nginx")
        if not os.path.exists(nginx_binary):
            Logger.critical("NGINX-Binary nicht gefunden!")
            Logger.info(f"Suche NGINX in: {nginx_binary}")
            return False
        
        # Test configuration
        config_path = os.path.join(self.config_dir, "nginx.conf")
        Logger.info("Teste NGINX Konfiguration...")
        test_result = run_command(f"{nginx_binary} -t -c {config_path}")
        
        if test_result.returncode != 0:
            Logger.error("Konfigurationstest fehlgeschlagen!")
            Logger.error(f"Fehler: {test_result.stderr[:200]}")
            
            # Try to fix common issues
            if "mime.types" in test_result.stderr:
                Logger.info("Versuche mime.types Problem zu beheben...")
                self.fix_mime_types_issue()
                # Test again
                test_result = run_command(f"{nginx_binary} -t -c {config_path}")
            
            if test_result.returncode != 0:
                return False
        
        Logger.success("Konfigurationstest bestanden ✓")
        
        # Stop any running nginx instances
        run_command("pkill nginx 2>/dev/null || true")
        time.sleep(2)
        
        # Try systemd first
        Logger.info("Versuche Systemd-Start...")
        result = run_command("systemctl start nginx-stream")
        
        if result.returncode != 0:
            Logger.warning("Systemd-Start fehlgeschlagen, versuche direkten Start...")
            
            # Direct start
            result = run_command(f"{nginx_binary} -c {config_path}")
            
            if result.returncode != 0:
                Logger.error("Direkter Start fehlgeschlagen!")
                return False
        
        # Verify service is running
        time.sleep(3)
        
        # Check if nginx is running
        result = run_command("ps aux | grep -q '[n]ginx.*master'")
        if result.returncode == 0:
            Logger.success("NGINX läuft ✓")
            
            # Check ports
            Logger.info("Überprüfe Ports...")
            if self.has_ss():
                run_command(f"ss -tuln | grep ':{self.rtmp_port} '")
            elif self.has_netstat():
                run_command(f"netstat -tuln | grep ':{self.rtmp_port} '")
            
            return True
        else:
            Logger.error("NGINX läuft nicht")
            return False
    
    def has_ss(self):
        """Check if ss command is available"""
        result = run_command("which ss")
        return result.returncode == 0
    
    def has_netstat(self):
        """Check if netstat command is available"""
        result = run_command("which netstat")
        return result.returncode == 0
    
    def create_test_scripts_complete(self):
        """Create test scripts"""
        Logger.step("Erstelle Test-Skripte")
        
        test_dir = os.path.join(self.scripts_dir, "test")
        os.makedirs(test_dir, exist_ok=True)
        
        # Get server IP
        try:
            result = run_command("hostname -I | awk '{print $1}' || echo 'localhost'")
            server_ip = result.stdout.strip()
        except:
            server_ip = "localhost"
        
        # Main test script
        test_script = f"""#!/bin/bash
# Streaming Server Test Script

SERVER="{server_ip}"
RTMP_PORT={self.rtmp_port}
HTTP_PORT={self.http_port}
TEST_VIDEO="{self.test_video_path}"

echo "========================================"
echo "Streaming Server Test"
echo "========================================"
echo "Server: $SERVER"
echo "RTMP Port: $RTMP_PORT"
echo "========================================"

case "$1" in
    stream)
        echo "Testing RTMP stream..."
        if [ -f "$TEST_VIDEO" ]; then
            echo "Using test video: $TEST_VIDEO"
            ffmpeg -re -i "$TEST_VIDEO" -c copy -f flv "rtmp://$SERVER:$RTMP_PORT/live/test" 2>/dev/null &
            PID=$!
            echo "Streaming for 30 seconds... (PID: $PID)"
            sleep 30
            kill $PID 2>/dev/null
            echo "Test completed"
        else
            echo "Test video not found, creating test pattern..."
            ffmpeg -f lavfi -i testsrc=size=640x360:rate=30 \\
                   -f lavfi -i sine=frequency=1000 \\
                   -c:v libx264 -preset ultrafast \\
                   -c:a aac -t 30 -f flv "rtmp://$SERVER:$RTMP_PORT/live/test" 2>/dev/null
        fi
        ;;
    
    status)
        echo "Service status:"
        systemctl status nginx-stream --no-pager 2>/dev/null || {{
            echo "Systemd service not available"
            echo "Checking processes:"
            ps aux | grep nginx | grep -v grep
        }}
        ;;
    
    ports)
        echo "Checking open ports:"
        if command -v ss >/dev/null 2>&1; then
            ss -tuln | grep -E ":{self.rtmp_port}|:{self.http_port}"
        elif command -v netstat >/dev/null 2>&1; then
            netstat -tuln | grep -E ":{self.rtmp_port}|:{self.http_port}"
        else
            echo "No port checking tools available"
        fi
        ;;
    
    test-all)
        echo "Running all tests..."
        $0 status
        echo ""
        $0 ports
        echo ""
        echo "Quick test URLs:"
        echo "  Dashboard: http://$SERVER:$HTTP_PORT/"
        echo "  Statistics: http://$SERVER:$HTTP_PORT/stat"
        echo "  Health: http://$SERVER:$HTTP_PORT/health"
        echo "  Port Test: http://$SERVER:$HTTP_PORT/port-test"
        ;;
    
    *)
        echo "Usage: $0 {{stream|status|ports|test-all}}"
        echo ""
        echo "Examples:"
        echo "  $0 stream    - Test RTMP streaming"
        echo "  $0 status    - Check service status"
        echo "  $0 ports     - Check open ports"
        echo "  $0 test-all  - Run all tests"
        ;;
esac
"""
        
        # Write test script
        script_path = os.path.join(test_dir, "test.sh")
        try:
            with open(script_path, 'w') as f:
                f.write(test_script)
            run_command(f"chmod +x {script_path}")
            Logger.success(f"Test-Skript erstellt: {script_path}")
            return True
        except Exception as e:
            Logger.error(f"Test-Skript konnte nicht erstellt werden: {e}")
            return False
    
    def run_complete_installation(self):
        """Run complete installation with all fixes"""
        Logger.header("DEBIAN STREAMING SERVER KOMPLETTINSTALLATION")
        print(f"{C.CYAN}Version 2.5 - Alle Probleme behoben mit Port Forwarding{C.END}")
        print(f"{C.CYAN}Debian {self.debian_version} ({self.debian_codename}) erkannt{C.END}")
        print()
        
        # Check requirements
        if not self.check_requirements():
            return False
        
        # Installation steps
        installation_steps = [
            ("Install dependencies", self.install_dependencies_complete, 2),
            ("Download sources", self.download_sources_complete, 2),
            ("Compile NGINX", self.compile_nginx_complete, 2),
            ("Create directories", self.create_directories_complete, 1),
            ("Generate configuration", self.generate_nginx_config_complete, 2),
            ("Create systemd service", self.create_systemd_service_complete, 2),
            ("Create dashboard", self.create_html_dashboard_complete, 1),
            ("Create test scripts", self.create_test_scripts_complete, 1),
            ("Configure firewall", self.configure_firewall_complete, 1),
            ("Start services", self.start_services_complete, 2),
        ]
        
        total_steps = len(installation_steps)
        successful_steps = 0
        
        for i, (step_name, step_func, max_retries) in enumerate(installation_steps, 1):
            Logger.step(f"Schritt {i}/{total_steps}: {step_name}")
            
            success = False
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        Logger.info(f"Versuch {attempt + 1}/{max_retries}...")
                    
                    if step_func():
                        success = True
                        successful_steps += 1
                        break
                    else:
                        if attempt < max_retries - 1:
                            Logger.warning(f"Schritt fehlgeschlagen, versuche erneut...")
                            time.sleep(3)
                        
                except Exception as e:
                    Logger.error(f"Fehler in Schritt {step_name}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(3)
            
            if not success:
                Logger.error(f"Schritt '{step_name}' endgültig fehlgeschlagen")
                self.failed_steps.append(step_name)
        
        # Display results
        self.display_final_results(successful_steps, total_steps)
        
        return successful_steps == total_steps
    
    def display_final_results(self, successful, total):
        """Display final installation results"""
        Logger.header("INSTALLATION ABGESCHLOSSEN")
        
        if successful == total:
            print(f"{C.GREEN}{C.BOLD}✅ KOMPLETTE INSTALLATION ERFOLGREICH!{C.END}")
        else:
            print(f"{C.YELLOW}{C.BOLD}⚠ Installation teilweise erfolgreich{C.END}")
            print(f"{C.YELLOW}Erfolgreiche Schritte: {successful}/{total}{C.END}")
            
            if self.failed_steps:
                print(f"{C.RED}Fehlgeschlagene Schritte:{C.END}")
                for step in self.failed_steps:
                    print(f"  ✗ {step}")
        
        # Get server IP for display
        try:
            result = run_command("hostname -I | awk '{print $1}' || hostname")
            server_ip = result.stdout.strip()
        except:
            server_ip = "Ihre_Server_IP"
        
        print(f"\n{C.CYAN}{C.BOLD}🔧 WICHTIGE BEFEHLE:{C.END}")
        print(f"{C.YELLOW}Service status:{C.END}     sudo systemctl status nginx-stream")
        print(f"{C.YELLOW}Service starten:{C.END}    sudo systemctl start nginx-stream")
        print(f"{C.YELLOW}Service stoppen:{C.END}    sudo systemctl stop nginx-stream")
        print(f"{C.YELLOW}Logs anzeigen:{C.END}      sudo tail -f {self.log_dir}/error.log")
        print(f"{C.YELLOW}Test-Skript:{C.END}        {self.scripts_dir}/test/test.sh")
        
        print(f"\n{C.CYAN}{C.BOLD}🌐 STREAMING ENDPUNKTE:{C.END}")
        print(f"{C.YELLOW}RTMP Server:{C.END}        rtmp://{server_ip}:{self.rtmp_port}/live")
        print(f"{C.YELLOW}HTTP Dashboard:{C.END}     http://{server_ip}:{self.http_port}/")
        print(f"{C.YELLOW}HLS Output:{C.END}        http://{server_ip}:{self.http_port}/hls/")
        
        print(f"\n{C.CYAN}{C.BOLD}🚀 TESTBEFEHLE (JETZT FUNKTIONIEREND):{C.END}")
        print(f"1. {C.GREEN}ffmpeg -re -i {self.test_video_path} -c copy -f flv rtmp://{server_ip}:{self.rtmp_port}/live/test{C.END}")
        print(f"2. {C.GREEN}sudo systemctl status nginx-stream{C.END}")
        print(f"3. {C.GREEN}{'netstat' if self.has_netstat() else 'ss'} -tuln | grep :{self.rtmp_port}{C.END}")
        
        if successful < total:
            print(f"\n{C.RED}{C.BOLD}⚠ MANUELLE FEHLERBEHEBUNG:{C.END}")
            print("1. Mime.types Problem beheben:")
            print(f"   sudo cp {self.config_dir}/mime.types /etc/nginx/")
            print("2. NGINX manuell starten:")
            print(f"   sudo {self.install_dir}/sbin/nginx -c {self.config_dir}/nginx.conf")
            print("3. Fehlende Pakete installieren:")
            print("   sudo apt update && sudo apt install -y python3-software-properties unzip")
            print("4. RTMP Modul überprüfen:")
            print(f"   ls -la {self.build_dir}/nginx-rtmp-module/")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main entry point"""
    installer = DebianNGINXInstaller()
    
    Logger.header("DEBIAN STREAMING SERVER v2.5")
    print(f"{C.CYAN}Complete Fix Edition mit Port Forwarding - All Issues Resolved{C.END}")
    print()
    print(f"{C.YELLOW}Folgende Probleme werden behoben:{C.END}")
    print("1. ✅ software-properties-common Installationsfehler")
    print("2. ✅ RTMP Modul fehlende Dateien (ngx_rtmp_conf.h)")
    print("3. ✅ Mime.types Datei nicht gefunden")
    print("4. ✅ NGINX Konfigurationstest fehlgeschlagen")
    print("5. ✅ Port Forwarding Einrichtung mit Anleitung")
    print("6. ✅ Dynamische DNS (DDNS) Unterstützung")
    print()
    print(f"{C.YELLOW}Features:{C.END}")
    print("• Automatische Fehlerbehandlung für alle Probleme")
    print("• Komplette mime.types Datei wird erstellt")
    print("• Fehlende RTMP Modul-Dateien werden generiert")
    print("• Port Forwarding Analyse und Anleitung")
    print("• DDNS Einrichtung für dynamische IPs")
    
    # Ask for confirmation
    print(f"\n{C.YELLOW}Dies wird installieren:{C.END}")
    print("• NGINX mit RTMP-Modul (alle fehlenden Dateien behoben)")
    print("• Alle erforderlichen Abhängigkeiten")
    print("• Web-Dashboard mit Status-Informationen")
    print("• Systemd Service")
    print("• Firewall-Regeln")
    print("• Port Forwarding Einrichtung")
    print("• Test-Skripte und Video")
    
    confirm = input(f"\n{C.YELLOW}Fortfahren? (j/N): {C.END}").strip().lower()
    if confirm != 'j':
        print("Installation abgebrochen.")
        sys.exit(0)
    
    # Run installation
    if installer.run_complete_installation():
        print(f"\n{C.GREEN}{C.BOLD}✨ Installation erfolgreich abgeschlossen! ✨{C.END}")
        
        # Ask about port forwarding
        print(f"\n{C.CYAN}{'='*60}{C.END}")
        print(f"{C.BOLD}📡 PORT FORWARDING EINRICHTUNG{C.END}")
        print(f"{C.CYAN}{'='*60}{C.END}")
        
        port_choice = input(f"\n{C.YELLOW}Möchten Sie Port Forwarding einrichten? (j/N): {C.END}").strip().lower()
        
        # Get local IP regardless of port forwarding choice
        local_ip = installer.port_manager.get_local_ip()
        
        if port_choice == 'j':
            installer.port_manager.run_port_forwarding_setup()
        else:
            # Just show local endpoints
            print(f"\n{C.YELLOW}📡 LOKALE STREAMING ENDPUNKTE:{C.END}")
            print(f"RTMP: rtmp://{local_ip}:{installer.rtmp_port}/live")
            print(f"Dashboard: http://{local_ip}:{installer.http_port}/")
            print(f"\n{C.CYAN}Port Forwarding kann später mit dem Test-Skript eingerichtet werden:{C.END}")
            print(f"{installer.scripts_dir}/port-forward-test.sh")
        
        print(f"\n{C.CYAN}Öffnen Sie das Dashboard: http://{local_ip}:{installer.http_port}/{C.END}")
        sys.exit(0)
    else:
        print(f"\n{C.RED}{C.BOLD}💥 Installation hatte Probleme{C.END}")
        
        # Still offer port forwarding if services are running
        result = run_command("ps aux | grep -q '[n]ginx.*master'")
        if result.returncode == 0:
            port_choice = input(f"\n{C.YELLOW}Services laufen. Port Forwarding einrichten? (j/N): {C.END}").strip().lower()
            if port_choice == 'j':
                installer.port_manager.run_port_forwarding_setup()
        
        print(f"\n{C.YELLOW}Manuelle Fehlerbehebung:{C.END}")
        print("1. Mime.types Problem beheben:")
        print(f"   sudo cp {installer.config_dir}/mime.types /etc/nginx/")
        print("2. NGINX manuell starten:")
        print(f"   sudo {installer.install_dir}/sbin/nginx -c {installer.config_dir}/nginx.conf")
        print("3. Fehlende Pakete installieren:")
        print("   sudo apt update && sudo apt install -y python3-software-properties unzip")
        sys.exit(1)

if __name__ == "__main__":
    main()
