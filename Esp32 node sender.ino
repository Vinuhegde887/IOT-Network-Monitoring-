#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <WiFiUdp.h>
#include <ESPping.h>
#include "esp_wifi.h"
#include "esp_wifi_types.h"

// WiFi credentials
const char* ssid = "Ayoo";
const char* password = "shri123er";

// Server details (Raspberry Pi)
const char* serverUrl = "http://192.168.126.85:5000/api/data";
const char* pingUrl = "192.168.126.85";  // For ICMP ping

// MQTT Settings
const char* mqtt_server = "192.168.126.85";
const int mqtt_port = 1883;
const char* mqtt_topic = "network/test";

// Node identifier (change for each ESP32)
String nodeId = "esp32_node1";  // Change this for each ESP32

// Protocol testing configuration
const String protocols[] = {"HTTP", "MQTT", "UDP", "TCP", "ICMP", "SMTP"};
const int numProtocols = 6;
int currentProtocolIndex = 0;
unsigned long protocolSwitchInterval = 30000; // Switch protocol every 30 seconds
unsigned long lastProtocolSwitch = 0;

// Wi-Fi channel to monitor
uint8_t channel = 1;

// Monitoring variables
struct ProtocolMetrics {
  String name;
  int packetsTotal;
  int packetsLost;
  float totalLatency;
  float totalThroughput;
  int measurementCount;
  unsigned long lastMeasurement;
};

ProtocolMetrics protocolMetrics[6];
int rssiSum = 0;
int packetCount = 0;
unsigned long startTime = 0;
unsigned long bytesReceived = 0;

// Network clients
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
WiFiUDP udpClient;
WiFiClient tcpClient;

// Protocol testing functions
void initializeProtocolMetrics() {
  for (int i = 0; i < numProtocols; i++) {
    protocolMetrics[i].name = protocols[i];
    protocolMetrics[i].packetsTotal = 0;
    protocolMetrics[i].packetsLost = 0;
    protocolMetrics[i].totalLatency = 0;
    protocolMetrics[i].totalThroughput = 0;
    protocolMetrics[i].measurementCount = 0;
    protocolMetrics[i].lastMeasurement = 0;
  }
}

// Updated callback function for ESP32 Arduino core 2.x and 3.x
void WiFiEvent(arduino_event_id_t event) {
  switch (event) {
    case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
      Serial.println("WiFi disconnected, reconnecting...");
      WiFi.begin(ssid, password);
      break;
    default:
      break;
  }
}

void promiscuousPacketHandler(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type != WIFI_PKT_MGMT && type != WIFI_PKT_DATA && type != WIFI_PKT_CTRL)
    return;

  const wifi_promiscuous_pkt_t *packet = (wifi_promiscuous_pkt_t*)buf;
  const wifi_pkt_rx_ctrl_t *rxctrl = &packet->rx_ctrl;
  
  // Count the packet for current protocol
  protocolMetrics[currentProtocolIndex].packetsTotal++;
  
  // Check if the packet has valid RSSI
  if (rxctrl->rssi != 0) {
    rssiSum += rxctrl->rssi;
    packetCount++;
  }
  
  // Calculate packet loss (simulated based on signal strength)
  if (rxctrl->rssi < -75) {  // -75 dBm threshold for packet loss
    protocolMetrics[currentProtocolIndex].packetsLost++;
  }
  
  // Track total bytes for throughput calculation
  bytesReceived += rxctrl->sig_len;
}

// HTTP Protocol Test
float testHTTPLatency() {
  HTTPClient http;
  unsigned long start = millis();
  
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");
  
  // Send a small test payload
  String testPayload = "{\"test\":\"ping\"}";
  int httpCode = http.POST(testPayload);
  
  unsigned long end = millis();
  http.end();
  
  if (httpCode > 0) {
    return (float)(end - start);
  } else {
    protocolMetrics[0].packetsLost++; // HTTP is index 0
    return 999.0;
  }
}

// MQTT Protocol Test
float testMQTTLatency() {
  if (!mqttClient.connected()) {
    if (mqttClient.connect(nodeId.c_str())) {
      Serial.println("MQTT Connected");
    } else {
      protocolMetrics[1].packetsLost++; // MQTT is index 1
      return 999.0;
    }
  }
  
  unsigned long start = millis();
  String testMessage = "ping_" + String(millis());
  
  if (mqttClient.publish(mqtt_topic, testMessage.c_str())) {
    mqttClient.loop(); // Process any incoming messages
    unsigned long end = millis();
    return (float)(end - start);
  } else {
    protocolMetrics[1].packetsLost++;
    return 999.0;
  }
}

// UDP Protocol Test
float testUDPLatency() {
  unsigned long start = millis();
  
  udpClient.begin(8888);
  
  if (udpClient.beginPacket(serverUrl + 7, 8888)) { // Adjust IP extraction
    String testMessage = "UDP_TEST_" + nodeId;
    udpClient.print(testMessage);
    
    if (udpClient.endPacket()) {
      // Wait for response (simplified)
      delay(10);
      unsigned long end = millis();
      udpClient.stop();
      return (float)(end - start);
    }
  }
  
  protocolMetrics[2].packetsLost++; // UDP is index 2
  udpClient.stop();
  return 999.0;
}

// TCP Protocol Test
float testTCPLatency() {
  unsigned long start = millis();
  
  // Extract IP from serverUrl (simplified - you may need to adjust)
  String serverIP = "192.168.133.38";
  
  if (tcpClient.connect(serverIP.c_str(), 5000)) {
    String testMessage = "GET / HTTP/1.1\r\nHost: " + serverIP + "\r\n\r\n";
    tcpClient.print(testMessage);
    
    // Wait for response
    unsigned long timeout = millis() + 1000;
    while (tcpClient.available() == 0 && millis() < timeout) {
      delay(1);
    }
    
    if (tcpClient.available()) {
      tcpClient.readString(); // Read response
    }
    
    tcpClient.stop();
    unsigned long end = millis();
    return (float)(end - start);
  } else {
    protocolMetrics[3].packetsLost++; // TCP is index 3
    return 999.0;
  }
}

// ICMP Protocol Test (Ping)
float testICMPLatency() {
  bool success = Ping.ping(pingUrl, 1);
  
  if (success) {
    return Ping.averageTime();
  } else {
    protocolMetrics[4].packetsLost++; // ICMP is index 4
    return 999.0;
  }
}

// SMTP Protocol Test (Simplified)
float testSMTPLatency() {
  unsigned long start = millis();
  
  WiFiClient smtpClient;
  String serverIP = "192.168.133.38";
  
  if (smtpClient.connect(serverIP.c_str(), 25)) {
    // Simple SMTP handshake
    smtpClient.println("HELO " + nodeId);
    
    // Wait for response
    unsigned long timeout = millis() + 2000;
    while (smtpClient.available() == 0 && millis() < timeout) {
      delay(1);
    }
    
    if (smtpClient.available()) {
      String response = smtpClient.readString();
      smtpClient.println("QUIT");
    }
    
    smtpClient.stop();
    unsigned long end = millis();
    return (float)(end - start);
  } else {
    protocolMetrics[5].packetsLost++; // SMTP is index 5
    return 999.0;
  }
}

// Measure latency for current protocol
float measureProtocolLatency() {
  switch (currentProtocolIndex) {
    case 0: return testHTTPLatency();
    case 1: return testMQTTLatency();
    case 2: return testUDPLatency();
    case 3: return testTCPLatency();
    case 4: return testICMPLatency();
    case 5: return testSMTPLatency();
    default: return 999.0;
  }
}

void sendDataToServer() {
  // Only proceed if connected to WiFi
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected. Skipping data transmission.");
    return;
  }
  
  // Get current protocol metrics
  ProtocolMetrics& currentMetrics = protocolMetrics[currentProtocolIndex];
  
  // Measure latency for current protocol
  float latency = measureProtocolLatency();
  
  // Update protocol metrics
  currentMetrics.totalLatency += latency;
  currentMetrics.measurementCount++;
  
  // Calculate throughput in KB/s
  float elapsedSec = (millis() - startTime) / 1000.0;
  float throughput = bytesReceived / 1024.0 / elapsedSec;
  currentMetrics.totalThroughput += throughput;
  
  // Prepare the JSON data
  DynamicJsonDocument doc(1024);
  doc["node_id"] = nodeId;
  doc["protocol"] = currentMetrics.name;
  doc["channel"] = channel;
  doc["packets_total"] = currentMetrics.packetsTotal;
  doc["packets_lost"] = currentMetrics.packetsLost;
  
  // Calculate average RSSI
  int avgRssi = 0;
  if (packetCount > 0) {
    avgRssi = rssiSum / packetCount;
  }
  doc["rssi"] = avgRssi;
  
  doc["latency"] = latency;
  doc["throughput"] = throughput;
  doc["timestamp"] = ""; // Server will add timestamp
  
  // Add protocol-specific metrics
  doc["avg_latency"] = currentMetrics.measurementCount > 0 ? 
                       currentMetrics.totalLatency / currentMetrics.measurementCount : 0;
  doc["avg_throughput"] = currentMetrics.measurementCount > 0 ? 
                          currentMetrics.totalThroughput / currentMetrics.measurementCount : 0;
  
  // Convert to JSON string
  String jsonString;
  serializeJson(doc, jsonString);
  
  // Send data to the Raspberry Pi server
  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");
  
  int httpResponseCode = http.POST(jsonString);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("Protocol: " + currentMetrics.name + 
                  " | HTTP Response: " + String(httpResponseCode) + 
                  " | Latency: " + String(latency) + "ms" +
                  " | Throughput: " + String(throughput) + "KB/s");
  } else {
    Serial.println("Error sending data for protocol " + currentMetrics.name + 
                  ": " + String(httpResponseCode));
  }
  
  http.end();
}

void switchProtocol() {
  if (millis() - lastProtocolSwitch >= protocolSwitchInterval) {
    currentProtocolIndex = (currentProtocolIndex + 1) % numProtocols;
    lastProtocolSwitch = millis();
    
    Serial.println("Switched to protocol: " + protocols[currentProtocolIndex]);
    
    // Reset counters for new protocol measurement period
    startTime = millis();
    bytesReceived = 0;
    rssiSum = 0;
    packetCount = 0;
  }
}

void setup() {
  Serial.begin(115200);
  delay(10);
  
  // Initialize protocol metrics
  initializeProtocolMetrics();
  
  // Initialize WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  // Register event handler
  WiFi.onEvent(WiFiEvent);
  
  Serial.println("Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  
  // Initialize MQTT
  mqttClient.setServer(mqtt_server, mqtt_port);
  
  // Initialize promiscuous mode for network monitoring
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(&promiscuousPacketHandler);
  
  // Set channel to monitor
  esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
  
  // Start monitoring
  startTime = millis();
  lastProtocolSwitch = millis();
  
  Serial.println("Starting multi-protocol network monitoring...");
  Serial.println("Current protocol: " + protocols[currentProtocolIndex]);
}

void loop() {
  // Switch protocol periodically
  switchProtocol();
  
  // Every 10 seconds, send data to server
  if (millis() - startTime >= 10000) {
    sendDataToServer();
    
    // Reset measurement counters (but keep protocol metrics)
    startTime = millis();
    rssiSum = 0;
    packetCount = 0;
    bytesReceived = 0;
  }
  
  // Handle MQTT loop if connected
  if (currentProtocolIndex == 1 && mqttClient.connected()) {
    mqttClient.loop();
  }
  
  // Small delay to avoid watchdog trigger
  delay(10);
}