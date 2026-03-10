# bbn23-ultimate-stream-2.5
The script is an automatic all-in-one installer for a complete streaming server on Debian 11/12/13 with all bug fixes and port forwarding features.

📋 Summary: Debian NGINX RTMP Streaming Server Installer v2.5
This script is an all-in-one automatic installer for a complete streaming server on Debian 11/12/13, featuring comprehensive bug fixes and port forwarding functionalities.

🎯 CORE FEATURES

1. Automatic Installation

NGINX with RTMP module (compiled from source)

FFmpeg for video transcoding

All dependencies (build-essential, SSL, PCRE, etc.)

Systemd Service for automatic startup

Firewall configuration (UFW/iptables)

2. STREAMING PROTOCOLS

✅ RTMP – Live Input (Port 1935)

✅ HLS – HTTP Live Streaming (Port 80)

✅ DASH – Dynamic Adaptive Streaming (Port 8081)

✅ SRT – Secure Reliable Transport (Port 10000)

3. INTEGRATED BUG FIXES

Problem	Solution
software-properties-common	Alternative packages + automatic installation
Missing ngx_rtmp_conf.h	Automatically generated
mime.types not found	Complete mime.types file is created
Configuration test fails	Automatic repair + fallback

🌐 NETWORK & PORT FORWARDING

Automatic Network Analysis

Identifies local IP, public IP, and gateway.

Detects if the server is running behind NAT.

Analyzes firewall status (UFW, iptables, nftables).

Port Forwarding Features

Interactive prompts after installation.

Router-specific guides for:

FRITZ!Box, Speedport, Vodafone Station, TP-Link, and General Routers.

Testing script for port forwarding verification.

DDNS Support

Setup for dynamic IPs.

DuckDNS Integration with automatic Cron jobs for IP updates.

Alternative services: No-IP, Dynu, Afraid.org.

📊 WEB DASHBOARD

The script creates a comprehensive HTML dashboard featuring:

Server Information (Debian version, architecture).

Streaming Endpoints (RTMP, HLS, HTTP).

Status Display (summary of resolved issues).

Quick Links to:

/stat – RTMP statistics

/health – Health check

/hls/ – HLS files

/port-test – Port test

🛠️ TEST SCRIPTS

Main Test Script (/usr/local/nginx/scripts/test/test.sh)

Bash

./test.sh stream    # Tests RTMP streaming
./test.sh status    # Shows service status
./test.sh ports     # Checks open ports
./test.sh test-all  # Runs all tests

Port Forwarding Test (/usr/local/nginx/scripts/port-forward-test.sh)

Checks if ports are reachable from the outside.

Provides diagnostics for failed connections.

🔧 SYSTEM INTEGRATION

Systemd Service

Bash

sudo systemctl start nginx-stream
sudo systemctl stop nginx-stream
sudo systemctl status nginx-stream
sudo systemctl enable nginx-stream

Manual Start Script (Fallback)
/usr/local/bin/nginx-stream-manual {start|stop|restart|status}

Firewall Rules

Automatically opens Ports 80 (HTTP), 1935 (RTMP), and 8080 (HLS).

SSH (Port 22) remains open.

UFW is installed and configured.

🎥 TEST VIDEO

Automatically creates a test video using FFmpeg:

Path: /tmp/test_pattern.mp4

Specs: 10 seconds, 640x360 resolution, H.264 + AAC codec.

📦 INSTALLED COMPONENTS

Component	Version/Purpose
NGINX	1.25.3 with RTMP module
FFmpeg	Latest version
RTMP-Module	arut/nginx-rtmp-module
build-essential	Compiler tools
OpenSSL	SSL/TLS support
PCRE	Regular expression support
UFW	Firewall management

🚀 POST-INSTALLATION COMMANDS

Bash
# Check service status
systemctl status nginx-stream

# View logs
tail -f /var/log/nginx/error.log

# Start test stream
ffmpeg -re -i /tmp/test_pattern.mp4 -c copy -f flv rtmp://SERVER_IP:1935/live/test

# Open Dashboard
http://SERVER_IP:80/

# Test Port Forwarding
/usr/local/nginx/scripts/port-forward-test.sh

🎯 TARGET AUDIENCE

Streaming Enthusiasts – Build your own streaming server.

Content Creators – Independent streaming platform.

Developers – Test environment for streaming protocols.

Administrators – Professional streaming service.

Clubs/Organizations – Internal live broadcasts.

💡 SPECIAL FEATURES

100% Automated – No manual intervention required.

Self-healing – Automatically detects and fixes issues.

Multi-platform – Supports all common streaming protocols.

User-friendly – Color-coded output and clear instructions.

Professional – Systemd integration and robust firewall rules.
