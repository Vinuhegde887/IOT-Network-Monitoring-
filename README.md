# 📡 Enhanced IoT Network Monitor

A real-time IoT network monitoring dashboard that provides insightful visualizations for signal strength (RSSI), latency, packet loss, throughput, and QoS for various protocols like MQTT, HTTP, UDP, TCP, SMTP, and ICMP.

## 🔧 Project Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/enhanced-iot-monitor.git
cd enhanced-iot-monitor
```

### 2. Create & Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### 3. Install Dependencies
```bash
pip install flask flask-socketio requests
pip install numpy --prefer-binary
pip3 install network
```

## 🚀 Run the Server

Make sure you have a `app.py` or similar Flask app that serves the frontend and emits/receives WebSocket data.

```bash
python app.py
```

The server will start running on: **http://localhost:5000**

## 🌐 Web Dashboard

The HTML dashboard provides:

### 📈 Live charts for:
- RSSI
- Latency
- Packet Loss
- Throughput

### ✅ Additional Features:
- Node health indicators (Online, Warning, Offline)
- 🔀 Protocol filtering (MQTT, TCP, UDP, HTTP, ICMP, SMTP)
- 🧠 QoS prediction & display
- 📤 CSV export & printable reports

The dashboard UI uses Bootstrap 5 and Chart.js with real-time updates via Socket.IO.

## 📡 Supported Protocols

- MQTT
- TCP
- UDP
- HTTP
- SMTP
- ICMP

## 📦 Folder Structure

```
enhanced-iot-monitor/
├── __pycache__/                       # Compiled Python files
├── templates/                         # HTML templates for Flask
│   ├── index.html                     # Main dashboard UI
│   └── optimization.html             # Optimization interface
├── static/                            # (Optional) CSS/JS assets (if separated)
├── network_data                       # Python file (e.g., data model or processor)
├── network_data.xlsx                  # Excel data file (sample or export)
├── app                                # Main Flask app entry point
├── Discete-Queing-Modeling            # Python script (queue modeling)
├── advanced_optimization              # Python script for advanced techniques
├── optimization_routes                # Flask routes for optimization APIs
├── network_topology                   # Python file to manage node layout/topology
├── README.md                          # Project documentation

Esp32 code

```

## 🧪 Sample ESP32 Integration

You can push live metrics using ESP32 code over WebSocket or REST (see your .ino sketch for implementation). Expected JSON format:

```json
{
  "node_id": "Node1",
  "protocol": "MQTT",
  "rssi": -60,
  "latency": 45,
  "throughput": 125,
  "packets_lost": 2,
  "packets_total": 100,
  "channel": 6,
  "timestamp": "2025-07-23T17:00:00Z"
}
```

## 📤 Export Features

- Export filtered data to `.csv`
- Print summary report of metrics


## 🧠 Future Enhancements

- AI-based QoS prediction
- Node location mapping
- Alert notification via email/SMS

## 📜 License

MIT License. Free for personal and academic use.

