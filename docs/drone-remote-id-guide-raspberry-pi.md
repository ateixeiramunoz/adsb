# Remote ID & DJI DroneID Capture Guide - Raspberry Pi

> **Purpose**: Complete guide for setting up drone Remote ID and DJI DroneID capture on Raspberry Pi Linux systems.
>
> **Last Updated**: December 2024
>
> **Author**: Auto-generated documentation for ADS-B integration project

---

## Table of Contents

1. [Overview](#overview)
2. [Understanding the Protocols](#understanding-the-protocols)
3. [Hardware Requirements](#hardware-requirements)
4. [Software Requirements](#software-requirements)
5. [Raspberry Pi Initial Setup](#raspberry-pi-initial-setup)
6. [Wi-Fi Adapter Setup for Monitor Mode](#wi-fi-adapter-setup-for-monitor-mode)
7. [Installing RemoteIDReceiver](#installing-remoteidreceiver)
8. [DJI DroneID with SDR (OcuSync)](#dji-droneid-with-sdr-ocusync)
9. [Integration with ADS-B Pipeline](#integration-with-ads-b-pipeline)
10. [Running as a Service](#running-as-a-service)
11. [Troubleshooting](#troubleshooting)
12. [Legal Considerations](#legal-considerations)
13. [References & Sources](#references--sources)

---

## Overview

This guide covers two types of drone identification broadcasts:

| Protocol | Frequency | Encryption | Drones Covered |
|----------|-----------|------------|----------------|
| **Remote ID (ASD-STAN/FAA)** | 2.4 GHz Wi-Fi | None | All compliant drones (2023+) |
| **DJI DroneID (Wi-Fi)** | 2.4 GHz Wi-Fi | None | Older DJI (Phantom 4, Mavic Pro/Air v1, Spark) |
| **DJI DroneID (OcuSync)** | 2.4/5.8 GHz | None* | Newer DJI (Mini 2/3/4, Mavic 3, Air 2S) |

> *Contrary to popular belief, DJI DroneID is **NOT encrypted**. This was confirmed by security researchers in the [NDSS 2023 paper](https://mschloegel.me/paper/schiller23dronesecurity.pdf).

### What Data Can Be Captured?

**Standard Remote ID:**
- Drone serial number / session ID
- Drone GPS position (lat, lon, altitude)
- Drone velocity and heading
- Operator location (if broadcast)
- Timestamp

**DJI DroneID (Additional):**
- Drone serial number
- Drone GPS position
- **Operator/Controller GPS position** (always broadcast)
- Home point (takeoff location)
- Height above ground
- Flight speed and heading

---

## Understanding the Protocols

### Remote ID (ASD-STAN / ASTM F3411 / FAA)

Remote ID is the **regulatory standard** mandated by:
- **FAA** (USA) - Required since September 2023
- **EU** (Europe) - Required since January 2024
- **Other countries** - Varying timelines

Broadcasts use **Wi-Fi Neighbor Awareness Networking (NAN)** or **Bluetooth 5.x Long Range**.

### DJI DroneID

DJI implemented their own identification system before regulations existed:

1. **Wi-Fi Mode**: Older drones broadcast via Wi-Fi beacon frames
2. **OcuSync Mode**: Newer drones embed ID in their proprietary radio link

The protocol was reverse-engineered by researchers at Ruhr University Bochum ([DroneSecurity project](https://github.com/RUB-SysSec/DroneSecurity)).

---

## Hardware Requirements

### Essential Hardware

#### Raspberry Pi

| Option | Price | Notes |
|--------|-------|-------|
| [Raspberry Pi 4 Model B (4GB)](https://www.amazon.com/Raspberry-Model-2019-Quad-Bluetooth/dp/B07TC2BK1X/) | ~$55 | Recommended minimum |
| [Raspberry Pi 4 Model B (8GB)](https://www.amazon.com/Raspberry-Pi-Computer-Suitable-Workstation/dp/B0899VXM8F/) | ~$75 | Better for running multiple services |
| [Raspberry Pi 5 (8GB)](https://www.amazon.com/Raspberry-Pi-Quad-core-Cortex-A76-Processor/dp/B0CTQ3BQLS/) | ~$80 | Best performance |

#### Power Supply

| Option | Price | Notes |
|--------|-------|-------|
| [Official Pi 4 Power Supply (USB-C 5.1V 3A)](https://www.amazon.com/Raspberry-Pi-USB-C-Power-Supply/dp/B07W8XHMJZ/) | ~$8 | Required for stable operation |
| [Official Pi 5 Power Supply (27W)](https://www.amazon.com/Raspberry-Pi-USB-C-Power-Supply/dp/B0CN356DQK/) | ~$12 | For Pi 5 only |

#### MicroSD Card

| Option | Price | Notes |
|--------|-------|-------|
| [SanDisk 64GB Extreme](https://www.amazon.com/SanDisk-Extreme-microSDXC-Memory-Adapter/dp/B09X7CRKRZ/) | ~$12 | Good balance |
| [Samsung EVO Select 128GB](https://www.amazon.com/SAMSUNG-Adapter-microSDXC-MB-ME128KA-AM/dp/B09B1HMJ9Z/) | ~$15 | More storage for logs |

### Wi-Fi Adapters for Monitor Mode

> **CRITICAL**: The Raspberry Pi's built-in Wi-Fi (BCM43455) does **NOT** reliably support monitor mode. You need an external USB adapter.

#### Recommended Adapters (Tested & Working)

| Adapter | Chipset | Band | Amazon Link | Price | Notes |
|---------|---------|------|-------------|-------|-------|
| **Alfa AWUS036ACHM** | MT7610U | 2.4/5 GHz | [Amazon](https://www.amazon.com/Alfa-AWUS036ACHM-802-11ac-Range-Adapter/dp/B08SJBV1N3/) | ~$40 | **Best choice** - excellent Linux support |
| **Alfa AWUS036ACH** | RTL8812AU | 2.4/5 GHz | [Amazon](https://www.amazon.com/Alfa-Long-Range-Dual-Band-Wireless-External/dp/B00VEEBOPG/) | ~$50 | High power, needs driver install |
| **Panda PAU09 N600** | RT5572 | 2.4/5 GHz | [Amazon](https://www.amazon.com/Panda-Wireless-PAU09-Adapter-Antennas/dp/B01LY35HGO/) | ~$35 | Good plug-and-play support |
| **Alfa AWUS036NHA** | AR9271 | 2.4 GHz only | [Amazon](https://www.amazon.com/Alfa-AWUS036NHA-Wireless-USB-Adaptor/dp/B004Y6MIXS/) | ~$30 | Classic choice, 2.4 GHz only |
| **TP-Link Archer T2U Plus** | RTL8821AU | 2.4/5 GHz | [Amazon](https://www.amazon.com/TP-Link-Archer-T2U-Plus-Wireless/dp/B07P5PRK7J/) | ~$20 | Budget option, needs driver |

#### Adapter Selection Guide

```
Remote ID Capture Only?
├── Yes → Any 2.4 GHz adapter works (Alfa AWUS036NHA is cheapest)
└── No, also want 5 GHz scanning?
    └── Get dual-band: Alfa AWUS036ACHM (best) or Panda PAU09
```

### SDR Hardware for DJI OcuSync (Newer Drones)

> **Note**: RTL-SDR cannot decode OcuSync - it requires >10 MHz bandwidth. RTL-SDR only provides 2.4 MHz.

| Hardware | Bandwidth | Amazon/Source | Price | Notes |
|----------|-----------|---------------|-------|-------|
| **AntSDR E200** | 56 MHz | [CrowdSupply](https://www.crowdsupply.com/microphase/antsdr-e200) | ~$299 | **Turnkey solution** with firmware |
| **ADALM-PLUTO (PlutoSDR)** | 20 MHz | [Amazon](https://www.amazon.com/Analog-Devices-ADALM-PLUTO-Portable-Learning/dp/B074GDY3XH/) | ~$230 | Requires software setup |
| **HackRF One** | 20 MHz | [Amazon](https://www.amazon.com/NooElec-Software-Defined-Antenna-Adapter/dp/B01K1CCHR0/) | ~$340 | General purpose SDR |
| **LimeSDR Mini 2.0** | 30.72 MHz | [CrowdSupply](https://www.crowdsupply.com/lime-micro/limesdr-mini-2) | ~$299 | High quality, complex setup |

#### SDR Selection Guide

```
Budget Priority?
├── Yes → PlutoSDR (~$230) + proto17/dji_droneid software
└── No, want easiest setup?
    └── AntSDR E200 (~$299) with pre-built firmware
```

### Optional but Recommended

| Item | Purpose | Amazon Link | Price |
|------|---------|-------------|-------|
| [USB 3.0 Hub (Powered)](https://www.amazon.com/Sabrent-Individual-Switches-Included-HB-UMP3/dp/B00TPMEOYM/) | Multiple USB devices | Amazon | ~$25 |
| [Weatherproof Enclosure](https://www.amazon.com/LeMotech-Dustproof-Waterproof-Electrical-150mmx110mmx70mm/dp/B075X17M4P/) | Outdoor deployment | Amazon | ~$15 |
| [PoE HAT for Pi 4](https://www.amazon.com/Raspberry-Power-Over-Ethernet-PoE-HAT/dp/B082ZLDMZ6/) | Single cable power/network | Amazon | ~$20 |
| [External Antenna (RP-SMA)](https://www.amazon.com/Alfa-AOA-2409TF-2-4GHz-Omni-Directional-Antenna/dp/B003LRMW8S/) | Extended range | Amazon | ~$20 |

---

## Software Requirements

### Operating System

**Recommended**: Raspberry Pi OS (64-bit) Lite or Desktop
- Download: https://www.raspberrypi.com/software/operating-systems/

### Required Packages

```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Essential tools
sudo apt install -y \
    git \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    dkms \
    bc \
    libncurses5-dev \
    libssl-dev \
    aircrack-ng \
    iw \
    wireless-tools \
    net-tools \
    tcpdump \
    wireshark-common \
    tshark

# Docker (for RemoteIDReceiver)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

---

## Raspberry Pi Initial Setup

### Step 1: Flash the OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Select **Raspberry Pi OS (64-bit) Lite**
3. Click the gear icon to pre-configure:
   - Hostname: `drone-receiver` (or your choice)
   - Enable SSH
   - Set username/password
   - Configure Wi-Fi (for initial setup only)
4. Flash to SD card

### Step 2: First Boot Configuration

```bash
# SSH into your Pi
ssh pi@drone-receiver.local

# Update system
sudo apt update && sudo apt full-upgrade -y

# Set timezone
sudo raspi-config nonint do_change_timezone America/New_York

# Expand filesystem (if not automatic)
sudo raspi-config nonint do_expand_rootfs

# Reboot
sudo reboot
```

### Step 3: Disable Built-in Wi-Fi (Optional)

If using external adapter only, disable internal Wi-Fi to avoid conflicts:

```bash
# Add to /boot/config.txt
echo "dtoverlay=disable-wifi" | sudo tee -a /boot/config.txt

# Or blacklist the driver
echo "blacklist brcmfmac" | sudo tee /etc/modprobe.d/disable-wifi.conf
```

---

## Wi-Fi Adapter Setup for Monitor Mode

### Step 1: Identify Your Adapter

```bash
# Plug in your USB Wi-Fi adapter
lsusb

# Example output:
# Bus 001 Device 004: ID 0e8d:7610 MediaTek Inc. MT7610U

# Check interface name
ip link show
# Look for wlan1 or similar
```

### Step 2: Install Drivers (If Needed)

#### For Alfa AWUS036ACHM (MT7610U) - Usually works out of box

```bash
# Check if already working
iwconfig wlan1
# If it shows "Mode:Managed", you're good
```

#### For Alfa AWUS036ACH / TP-Link (RTL8812AU)

```bash
# Install DKMS driver
sudo apt install -y dkms git bc
git clone https://github.com/aircrack-ng/rtl8812au.git
cd rtl8812au
sudo make dkms_install
```

#### For Panda PAU09 (RT5572) - Usually works out of box

```bash
# Should work automatically with rt2800usb driver
lsmod | grep rt2800
```

### Step 3: Test Monitor Mode

```bash
# Find your wireless interface
IFACE=$(iw dev | grep Interface | awk '{print $2}' | grep -v wlan0 | head -1)
echo "Using interface: $IFACE"

# Bring interface down
sudo ip link set $IFACE down

# Set monitor mode
sudo iw dev $IFACE set type monitor

# Bring interface up
sudo ip link set $IFACE up

# Verify
iwconfig $IFACE
# Should show "Mode:Monitor"

# Test packet capture (Ctrl+C to stop)
sudo tcpdump -i $IFACE -c 100

# Return to managed mode
sudo ip link set $IFACE down
sudo iw dev $IFACE set type managed
sudo ip link set $IFACE up
```

### Step 4: Create Helper Scripts

Create `/usr/local/bin/monitor-mode-on`:

```bash
sudo tee /usr/local/bin/monitor-mode-on << 'EOF'
#!/bin/bash
IFACE="${1:-wlan1}"
CHANNEL="${2:-6}"

echo "[*] Enabling monitor mode on $IFACE (channel $CHANNEL)"
sudo ip link set $IFACE down
sudo iw dev $IFACE set type monitor
sudo ip link set $IFACE up
sudo iw dev $IFACE set channel $CHANNEL
echo "[+] Monitor mode enabled"
iwconfig $IFACE
EOF
sudo chmod +x /usr/local/bin/monitor-mode-on
```

Create `/usr/local/bin/monitor-mode-off`:

```bash
sudo tee /usr/local/bin/monitor-mode-off << 'EOF'
#!/bin/bash
IFACE="${1:-wlan1}"

echo "[*] Disabling monitor mode on $IFACE"
sudo ip link set $IFACE down
sudo iw dev $IFACE set type managed
sudo ip link set $IFACE up
echo "[+] Managed mode restored"
iwconfig $IFACE
EOF
sudo chmod +x /usr/local/bin/monitor-mode-off
```

Usage:
```bash
# Enable monitor mode on wlan1, channel 6
sudo monitor-mode-on wlan1 6

# Disable monitor mode
sudo monitor-mode-off wlan1
```

---

## Installing RemoteIDReceiver

### Step 1: Clone Repository

```bash
cd /opt
sudo git clone https://github.com/cyber-defence-campus/RemoteIDReceiver.git
sudo chown -R $USER:$USER RemoteIDReceiver
cd RemoteIDReceiver/Receiver
```

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env
```

Key settings to modify:
```ini
# Your Wi-Fi interface (external adapter)
WIFI_INTERFACE=wlan1

# Map configuration (use free tiles)
FRONTEND_MAP_STYLE=free

# Database path
DATABASE_PATH=./data/drones.db
```

### Step 3: Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 4: Build Frontend (Docker)

```bash
# Make sure Docker is running
sudo systemctl start docker

# Build frontend
docker-compose up build-frontend
```

### Step 5: Run the Receiver

```bash
# Activate virtual environment
source venv/bin/activate

# Run with sudo (required for monitor mode)
sudo $(which python3) ./backend/dronesniffer/main.py -p 8080
```

### Step 6: Access Web Interface

Open in browser: `http://<raspberry-pi-ip>:8080`

---

## DJI DroneID with SDR (OcuSync)

This section covers decoding DJI DroneID from **newer drones** (Mini 2/3/4, Mavic 3, Air 2S) using SDR.

### Understanding DJI DroneID

DJI drones broadcast identification data that includes:

| Data Field | Description | Always Present |
|------------|-------------|----------------|
| Serial Number | Unique drone identifier | Yes |
| Drone Latitude | Current GPS position | Yes |
| Drone Longitude | Current GPS position | Yes |
| Drone Altitude | Height (barometric + GPS) | Yes |
| **Operator Latitude** | Controller/phone GPS | **Yes** |
| **Operator Longitude** | Controller/phone GPS | **Yes** |
| Home Point | Takeoff location | Yes |
| Speed | Ground speed | Yes |
| Heading | Direction of travel | Yes |
| Height AGL | Height above ground level | Yes |

> **Key Finding**: The operator position is ALWAYS transmitted - this is how DJI Aeroscope works.

### DJI DroneID Protocol Details

```
Frequency:      2.4 GHz and 5.8 GHz bands
Modulation:     OFDM (similar to Wi-Fi)
Bandwidth:      10 MHz (why RTL-SDR won't work)
Update Rate:    ~1 Hz
Range:          Up to several kilometers (depends on environment)
Encryption:     NONE (despite what DJI claims)
```

### Which Drones Use Which Protocol?

| Drone Model | Protocol | Capture Method |
|-------------|----------|----------------|
| Phantom 4 Pro/V2 | Wi-Fi | Monitor mode adapter |
| Mavic Pro | Wi-Fi | Monitor mode adapter |
| Mavic Air (v1) | Wi-Fi | Monitor mode adapter |
| Spark | Wi-Fi | Monitor mode adapter |
| **Mini 2** | OcuSync 2.0 | **SDR required** |
| **Mini 3/3 Pro** | OcuSync 3.0 | **SDR required** |
| **Mini 4 Pro** | OcuSync 4.0 | **SDR required** |
| **Mavic 3 series** | OcuSync 3.0 | **SDR required** |
| **Air 2/2S** | OcuSync 2.0 | **SDR required** |
| **Air 3** | OcuSync 4.0 | **SDR required** |
| **Avata/Avata 2** | OcuSync | **SDR required** |
| **FPV** | OcuSync 3.0 | **SDR required** |

---

### Option A: AntSDR E200 (Easiest - Recommended)

The AntSDR E200 is a turnkey solution with pre-built firmware for DJI DroneID detection.

#### Hardware Requirements

- [AntSDR E200](https://www.crowdsupply.com/microphase/antsdr-e200) (~$299)
- 2.4 GHz antenna (SMA connector)
- USB-C cable
- Ethernet cable (optional, for network output)

#### Step 1: Initial Hardware Setup

```bash
# Connect AntSDR E200 to Raspberry Pi via USB-C
# The device will appear as a network interface

# Verify connection
ip addr show
# Look for usb0 or similar with IP 192.168.1.10 or 192.168.2.1

# Default AntSDR IP is usually 192.168.1.10
ping 192.168.1.10
```

#### Step 2: Flash DJI DroneID Firmware

```bash
# Clone the firmware repository
cd /opt
git clone https://github.com/alphafox02/antsdr_dji_droneid.git
cd antsdr_dji_droneid

# Read the README carefully for your hardware revision
cat README.md

# The firmware files are in the releases or firmware directory
ls -la firmware/

# Connect to AntSDR via SSH (default password varies by firmware)
ssh root@192.168.1.10

# On the AntSDR, you'll flash the new firmware
# Follow specific instructions for your hardware revision
```

#### Step 3: Configure Network Output

The AntSDR can output decoded DroneID data via:
- **Serial port** (USB)
- **Network** (UDP/TCP)
- **Kismet integration**

```bash
# Configure output to your Raspberry Pi
# Edit configuration on AntSDR
ssh root@192.168.1.10

# Typical configuration file location
nano /etc/droneid/config.ini

# Example configuration:
# [output]
# type = udp
# host = 192.168.1.100  # Your Pi's IP
# port = 4242
```

#### Step 4: Create a Receiver Script

Create `/opt/dji-droneid/receiver.py` on your Raspberry Pi:

```python
#!/usr/bin/env python3
"""
DJI DroneID UDP Receiver
Receives decoded DroneID data from AntSDR E200
"""

import socket
import json
from datetime import datetime

UDP_IP = "0.0.0.0"
UDP_PORT = 4242

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print(f"[*] Listening for DJI DroneID on UDP port {UDP_PORT}")

    while True:
        data, addr = sock.recvfrom(4096)
        try:
            # Parse the incoming data (format depends on firmware)
            decoded = data.decode('utf-8')
            print(f"\n[{datetime.now().isoformat()}] Received from {addr}:")
            print(decoded)

            # If JSON format:
            try:
                drone_data = json.loads(decoded)
                print(f"  Drone Serial: {drone_data.get('serial', 'N/A')}")
                print(f"  Drone Position: {drone_data.get('drone_lat')}, {drone_data.get('drone_lon')}")
                print(f"  Operator Position: {drone_data.get('pilot_lat')}, {drone_data.get('pilot_lon')}")
            except json.JSONDecodeError:
                pass

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
```

#### Step 5: Run the Receiver

```bash
chmod +x /opt/dji-droneid/receiver.py
python3 /opt/dji-droneid/receiver.py
```

#### Step 6: Kismet Integration (Optional)

The AntSDR firmware can integrate with Kismet for visualization:

```bash
# Install Kismet on Raspberry Pi
sudo apt install -y kismet

# Configure Kismet to receive from AntSDR
# Add to /etc/kismet/kismet.conf:
# source=tcp://192.168.1.10:3501

# Run Kismet
kismet
```

---

### Option B: PlutoSDR + proto17/dji_droneid

A more affordable option using the ADALM-PLUTO SDR.

#### Hardware Requirements

- [ADALM-PLUTO (PlutoSDR)](https://www.amazon.com/Analog-Devices-ADALM-PLUTO-Portable-Learning/dp/B074GDY3XH/) (~$230)
- 2.4 GHz antenna
- USB cable

#### Step 1: Install PlutoSDR Drivers

```bash
# Install IIO libraries
sudo apt update
sudo apt install -y \
    libiio-dev \
    libiio-utils \
    libad9361-dev \
    libxml2-dev \
    bison \
    flex \
    cmake \
    git \
    build-essential

# Install Python bindings
pip3 install pyadi-iio

# Verify PlutoSDR connection
iio_info -s
# Should show: "usb= [Analog Devices Inc. PlutoSDR..."

# Check PlutoSDR details
iio_attr -a -C
```

#### Step 2: Expand PlutoSDR Bandwidth (Important!)

By default, PlutoSDR is limited to 6 MHz bandwidth. DJI DroneID needs ~10 MHz.

```bash
# SSH into PlutoSDR (default: root/analog)
ssh root@192.168.2.1

# Edit config to increase bandwidth
fw_setenv attr_name compatible
fw_setenv attr_val ad9361
fw_setenv maxcpus

# Or use the config file method
nano /mnt/jffs2/etc/device_config

# Add/modify:
# ad936x_ext_band_enable=1

# Reboot PlutoSDR
reboot

# After reboot, verify increased bandwidth
iio_attr -a -C ad9361-phy rx_path_rates
```

#### Step 3: Install GNU Radio (for signal processing)

```bash
# Install GNU Radio
sudo apt install -y gnuradio gnuradio-dev

# Install gr-iio for PlutoSDR support
sudo apt install -y gr-iio

# Verify installation
gnuradio-companion --version
```

#### Step 4: Clone and Setup proto17/dji_droneid

```bash
cd /opt
git clone https://github.com/proto17/dji_droneid.git
cd dji_droneid

# This project uses MATLAB/Octave for demodulation
# Install Octave as free alternative
sudo apt install -y octave octave-signal octave-communications

# Check the available scripts
ls -la matlab/

# The key files:
# - updated_rx.m: Main receiver script
# - DroneID demodulation functions
```

#### Step 5: Capture IQ Samples

```bash
# Capture raw IQ samples from PlutoSDR
# DJI DroneID is around 2.4 GHz

# Using iio-oscilloscope (GUI)
sudo apt install -y iio-oscilloscope
osc

# Or capture via command line
iio_readdev -b 1048576 -s 10000000 ad9361-phy > capture.raw

# Parameters:
# -b: Buffer size
# -s: Number of samples
# Tune to ~2.4 GHz, 10 MHz sample rate
```

#### Step 6: Process Samples with Octave

```bash
cd /opt/dji_droneid/matlab

# Start Octave
octave

# In Octave:
>> pkg load signal
>> pkg load communications
>> run('updated_rx.m')
```

#### Step 7: Alternative - Use samples2djidroneid

A simpler tool based on proto17's work:

```bash
cd /opt
git clone https://github.com/anarkiwi/samples2djidroneid.git
cd samples2djidroneid

# Install dependencies
pip3 install -r requirements.txt

# Process captured samples
python3 samples2djidroneid.py --input capture.raw
```

---

### Option C: DroneSecurity Research Tool

The original academic research implementation from Ruhr University Bochum.

#### Step 1: Clone Repository

```bash
cd /opt
git clone https://github.com/RUB-SysSec/DroneSecurity.git
cd DroneSecurity
```

#### Step 2: Read the Research Paper

Before using, read the paper to understand the protocol:
- [Drone Security and the Mysterious Case of DJI's DroneID (NDSS 2023)](https://mschloegel.me/paper/schiller23dronesecurity.pdf)

#### Step 3: Setup Environment

```bash
# Install dependencies
pip3 install -r requirements.txt

# The decoder can process captured samples
# See README for specific usage
```

#### Expected Output

When successfully decoding DJI DroneID, you'll see data like:

```
=== DJI DroneID Frame Detected ===
Timestamp: 2024-12-14T15:30:45.123Z
Serial Number: 1A2B3C4D5E6F7890

Drone Position:
  Latitude:  40.7128° N
  Longitude: -74.0060° W
  Altitude:  150.5 m (GPS)
  Height:    45.2 m (AGL)

Operator Position:
  Latitude:  40.7115° N
  Longitude: -74.0055° W

Flight Data:
  Speed:     12.5 m/s
  Heading:   275°
  Home Lat:  40.7115° N
  Home Lon:  -74.0055° W
=====================================
```

---

### DJI DroneID Troubleshooting

#### No Signals Detected

```bash
# Check SDR is receiving
# Use a spectrum analyzer or SDR# to verify 2.4 GHz activity

# Verify antenna connection
# Make sure antenna is connected to RX port, not TX

# Check frequency - DJI uses 2.4 GHz band
# Try different center frequencies: 2.4, 2.42, 2.44, 2.46 GHz
```

#### Weak/Corrupted Signals

```bash
# Increase sample rate if possible
# Use a better antenna (directional for more gain)
# Move closer to the drone/operator
# Check for interference from Wi-Fi networks
```

#### PlutoSDR Not Recognized

```bash
# Check USB connection
lsusb | grep Analog
# Should show: "Analog Devices, Inc. PlutoSDR"

# Check network interface
ip addr show usb0

# Reset PlutoSDR
# Unplug, wait 5 seconds, replug

# Check kernel messages
dmesg | tail -20
```

#### AntSDR Connection Issues

```bash
# Default IP varies by firmware
# Try common defaults:
ping 192.168.1.10
ping 192.168.2.1
ping 192.168.3.1

# Reset to defaults (check AntSDR documentation)
# Usually involves holding reset button during boot
```

---

### DJI DroneID vs Standard Remote ID

| Feature | DJI DroneID | Standard Remote ID |
|---------|-------------|-------------------|
| Operator location | Always included | Optional |
| Serial number | Always included | Always included |
| Encryption | None | None |
| Frequency | 2.4/5.8 GHz OcuSync | 2.4 GHz Wi-Fi/BLE |
| Capture method | SDR (10+ MHz BW) | Monitor mode Wi-Fi |
| Range | Several km | ~1 km |
| Drones covered | DJI only | All compliant drones |

---

## Integration with ADS-B Pipeline

### Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  RTL-SDR        │     │  Wi-Fi Adapter  │     │  AntSDR E200    │
│  (1090 MHz)     │     │  (2.4 GHz)      │     │  (2.4/5.8 GHz)  │
│  ADS-B          │     │  Remote ID      │     │  DJI OcuSync    │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         NATS Server                              │
│  Subjects:                                                       │
│  - adsb.position.v1     (aircraft)                              │
│  - remoteid.drone.v1    (standard Remote ID)                    │
│  - dji.droneid.v1       (DJI DroneID)                           │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Your Apps      │
│  - Map display  │
│  - Logging      │
│  - Alerts       │
└─────────────────┘
```

### Creating a Remote ID Publisher

Create `apps/remoteid_sender.py`:

```python
#!/usr/bin/env python3
"""
Remote ID sender that captures drone broadcasts and publishes to NATS.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# You'll need to adapt RemoteIDReceiver's parsing logic
# or create a bridge from their WebSocket output

from apps.bus_nats import NatsPublisher

REMOTEID_SUBJECT = os.getenv("REMOTEID_SUBJECT", "remoteid.drone.v1")
SOURCE_ID = os.getenv("REMOTEID_SOURCE_ID", "REMOTEID_RECEIVER_01")


def build_remoteid_event(drone_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a standardized Remote ID event."""
    return {
        "eventType": "remoteid.drone.v1",
        "source": SOURCE_ID,
        "tsUnixMs": int(datetime.now(timezone.utc).timestamp() * 1000),
        "drone": {
            "serialNumber": drone_data.get("serial_number"),
            "sessionId": drone_data.get("session_id"),
            "uasType": drone_data.get("uas_type"),
        },
        "position": {
            "lat": drone_data.get("lat"),
            "lon": drone_data.get("lon"),
            "altitudeM": drone_data.get("altitude_m"),
            "heightAgl": drone_data.get("height_agl"),
            "speedMs": drone_data.get("speed_ms"),
            "heading": drone_data.get("heading"),
        },
        "operator": {
            "lat": drone_data.get("operator_lat"),
            "lon": drone_data.get("operator_lon"),
            "altitudeM": drone_data.get("operator_altitude_m"),
        },
        "raw": drone_data.get("raw_frame"),
    }


async def main():
    publisher = NatsPublisher(subject=REMOTEID_SUBJECT)
    await publisher.connect()

    # TODO: Integrate with RemoteIDReceiver's output
    # This could be:
    # 1. Direct scapy packet capture
    # 2. WebSocket connection to RemoteIDReceiver
    # 3. Reading from a named pipe or socket

    print(f"[remoteid] Publishing to {REMOTEID_SUBJECT}")

    # Example: Bridge from RemoteIDReceiver WebSocket
    # async with websockets.connect("ws://localhost:8080/ws") as ws:
    #     async for message in ws:
    #         data = json.loads(message)
    #         event = build_remoteid_event(data)
    #         await publisher.publish(event)


if __name__ == "__main__":
    asyncio.run(main())
```

### Unified Event Schema

Consider creating a unified schema for all aerial vehicles:

```python
# Event types
EVENT_TYPES = {
    "adsb": "adsb.position.v1",      # Manned aircraft (ADS-B)
    "remoteid": "remoteid.drone.v1",  # Standard Remote ID drones
    "dji": "dji.droneid.v1",          # DJI drones
}

# Common fields all events should have
COMMON_FIELDS = [
    "eventType",
    "source",
    "tsUnixMs",
    "position.lat",
    "position.lon",
]
```

---

## Running as a Service

### SystemD Service for RemoteIDReceiver

Create `/etc/systemd/system/remoteid-receiver.service`:

```ini
[Unit]
Description=Remote ID Drone Receiver
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/RemoteIDReceiver/Receiver
Environment=PATH=/opt/RemoteIDReceiver/Receiver/venv/bin:/usr/bin
ExecStartPre=/usr/local/bin/monitor-mode-on wlan1 6
ExecStart=/opt/RemoteIDReceiver/Receiver/venv/bin/python ./backend/dronesniffer/main.py -p 8080
ExecStopPost=/usr/local/bin/monitor-mode-off wlan1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable remoteid-receiver
sudo systemctl start remoteid-receiver

# Check status
sudo systemctl status remoteid-receiver

# View logs
sudo journalctl -u remoteid-receiver -f
```

### Channel Hopping (Optional)

For better coverage, create a channel hopping script:

```bash
sudo tee /usr/local/bin/channel-hop << 'EOF'
#!/bin/bash
IFACE="${1:-wlan1}"
CHANNELS="1 6 11 36 40 44 48"

while true; do
    for ch in $CHANNELS; do
        sudo iw dev $IFACE set channel $ch
        sleep 0.5
    done
done
EOF
sudo chmod +x /usr/local/bin/channel-hop
```

---

## Troubleshooting

### Monitor Mode Won't Enable

```bash
# Check if interface exists
ip link show

# Check if driver is loaded
lsmod | grep -E "(mt76|rtl88|ath9k|rt2800)"

# Check for errors
dmesg | tail -50

# Try with airmon-ng
sudo airmon-ng check kill
sudo airmon-ng start wlan1
```

### No Packets Captured

```bash
# Verify monitor mode is active
iwconfig wlan1 | grep Mode

# Check channel
iwconfig wlan1 | grep Channel

# Test with tcpdump
sudo tcpdump -i wlan1 -c 10 -vv

# Ensure you're on correct channel (try 1, 6, 11)
sudo iw dev wlan1 set channel 6
```

### Permission Denied

```bash
# RemoteIDReceiver requires root for raw sockets
sudo python3 ./backend/dronesniffer/main.py

# Or add capabilities
sudo setcap cap_net_raw,cap_net_admin=eip $(which python3)
```

### Driver Installation Failed

```bash
# Install kernel headers
sudo apt install -y raspberrypi-kernel-headers

# Reinstall driver
cd rtl8812au
sudo make clean
sudo make
sudo make install
```

### USB Adapter Not Recognized

```bash
# Check USB power
lsusb
dmesg | grep -i usb

# Try powered USB hub
# Some adapters draw too much power for Pi's USB ports
```

---

## Legal Considerations

### Legality by Jurisdiction

| Country | Remote ID Capture | DJI DroneID Capture |
|---------|-------------------|---------------------|
| **USA** | Legal (publicly broadcast) | Legal (publicly broadcast) |
| **EU** | Legal (publicly broadcast) | Legal (publicly broadcast) |
| **UK** | Legal (publicly broadcast) | Legal (publicly broadcast) |

**Important Notes:**

1. **Passive Reception**: Capturing publicly broadcast radio signals is generally legal
2. **No Jamming**: Never attempt to jam, interfere with, or disrupt drone communications
3. **No Spoofing**: Creating fake Remote ID broadcasts may violate regulations
4. **Privacy**: Consider local privacy laws regarding operator location data
5. **Purpose**: Use for safety, research, or authorized security testing only

### Ethical Use Cases

- Airspace safety monitoring
- Security research
- Counter-UAS detection (authorized)
- Academic research
- Hobbyist tracking of own drones

---

## References & Sources

### Official Documentation

- [FAA Remote ID Rule](https://www.faa.gov/uas/getting_started/remote_id)
- [ASTM F3411 Standard](https://www.astm.org/f3411-22a.html)
- [ASD-STAN Remote ID](https://www.asd-stan.org/)

### GitHub Repositories

| Repository | Description | Link |
|------------|-------------|------|
| RemoteIDReceiver | Wi-Fi Remote ID + DJI DroneID receiver | [GitHub](https://github.com/cyber-defence-campus/RemoteIDReceiver) |
| proto17/dji_droneid | DJI DroneID demodulator (SDR) | [GitHub](https://github.com/proto17/dji_droneid) |
| RUB-SysSec/DroneSecurity | Original DJI DroneID research | [GitHub](https://github.com/RUB-SysSec/DroneSecurity) |
| alphafox02/antsdr_dji_droneid | AntSDR E200 firmware | [GitHub](https://github.com/alphafox02/antsdr_dji_droneid) |
| opendroneid | Open Drone ID implementations | [GitHub](https://github.com/opendroneid) |
| anarkiwi/samples2djidroneid | Decode DJI DroneID from samples | [GitHub](https://github.com/anarkiwi/samples2djidroneid) |

### Research Papers

- [Drone Security and the Mysterious Case of DJI's DroneID (NDSS 2023)](https://mschloegel.me/paper/schiller23dronesecurity.pdf)

### Hardware Vendors

- [Alfa Network](https://www.alfa.com.tw/) - Wi-Fi adapters
- [CrowdSupply - AntSDR](https://www.crowdsupply.com/microphase/antsdr-e200) - SDR hardware
- [Analog Devices - PlutoSDR](https://www.analog.com/en/design-center/evaluation-hardware-and-software/evaluation-boards-kits/adalm-pluto.html)

### Community Resources

- [RTL-SDR Blog](https://www.rtl-sdr.com/tag/drone/) - Drone detection articles
- [sUAS News - DIY Aeroscope](https://www.suasnews.com/2023/03/diy-dji-aeroscope-to-find-drone-operator-locations/)

---

## Appendix A: Quick Reference Commands

```bash
# Enable monitor mode
sudo ip link set wlan1 down
sudo iw dev wlan1 set type monitor
sudo ip link set wlan1 up
sudo iw dev wlan1 set channel 6

# Disable monitor mode
sudo ip link set wlan1 down
sudo iw dev wlan1 set type managed
sudo ip link set wlan1 up

# Check interface status
iwconfig wlan1

# Capture packets to file
sudo tcpdump -i wlan1 -w capture.pcap

# List wireless interfaces
iw dev

# Show interface capabilities
iw phy phy0 info | grep -A 10 "Supported interface modes"
```

---

## Appendix B: Compatible Drone List

### Remote ID (ASD-STAN) Compatible
- All drones manufactured after Sept 2023 (USA) / Jan 2024 (EU)
- Most commercial drones with firmware updates

### DJI DroneID (Wi-Fi Mode)
- Phantom 4 series
- Mavic Pro / Mavic Air (v1)
- Spark
- Older Inspire models

### DJI DroneID (OcuSync) - Requires SDR
- Mini 2 / Mini 3 / Mini 4 Pro
- Mavic 3 series
- Air 2 / Air 2S / Air 3
- Avata / Avata 2
- FPV

---

*Document generated for ADS-B integration project. For updates, check the repository.*
