#include <Arduino.h>
#include <WiFiS3.h>
#include <math.h>

WiFiServer server(80);

// Change these before uploading.
const char* WIFI_SSID = "OPPO A15";
const char* WIFI_PASSWORD = "12345678no";
const char* MDNS_NAME = "smartparking";

// Pin definitions for Sensor 1
const int trigPin1 = 0;
const int echoPin1 = 1;
const int ledPin1  = 7;

// Pin definitions for Sensor 2
const int trigPin2 = 2;
const int echoPin2 = 3;
const int ledPin2  = 8;

// Pin definitions for Sensor 3
const int trigPin3 = 4;
const int echoPin3 = 11;
const int ledPin3  = 9;

// Pin definitions for Sensor 4
const int trigPin4 = 5;
const int echoPin4 = 6;
const int ledPin4  = 10;

// Settings
const unsigned long PULSE_TIMEOUT = 30000UL;
const float SOUND_SPEED_CM_PER_US = 0.034;
const float OCCUPIED_THRESHOLD_CM = 10.0;
const int SAMPLES = 3;
const unsigned long SAMPLE_DELAY_MS = 20;
const unsigned long LOOP_DELAY_MS = 160;
const unsigned long WIFI_RETRY_DELAY_MS = 500;
const unsigned long DASHBOARD_UPDATE_MS = 500;

String latestPayload = "{\"available\":0,\"recommended\":\"-\",\"slots\":[]}";
unsigned long lastSensorUpdate = 0;

void sendHttpResponse(WiFiClient& client, int statusCode, const char* statusText, const char* contentType, const String& body) {
  client.print("HTTP/1.1 ");
  client.print(statusCode);
  client.print(" ");
  client.println(statusText);
  client.println("Access-Control-Allow-Origin: *");
  client.println("Access-Control-Allow-Methods: GET, OPTIONS");
  client.println("Access-Control-Allow-Headers: Content-Type");
  client.println("Cache-Control: no-store");
  client.print("Content-Type: ");
  client.println(contentType);
  client.print("Content-Length: ");
  client.println(body.length());
  client.println("Connection: close");
  client.println();
  client.print(body);
}

void sendOptionsResponse(WiFiClient& client) {
  client.println("HTTP/1.1 204 No Content");
  client.println("Access-Control-Allow-Origin: *");
  client.println("Access-Control-Allow-Methods: GET, OPTIONS");
  client.println("Access-Control-Allow-Headers: Content-Type");
  client.println("Cache-Control: no-store");
  client.println("Connection: close");
  client.println();
}

void handleHttpClient() {
  WiFiClient client = server.available();
  if (!client) {
    return;
  }

  unsigned long start = millis();
  while (client.connected() && !client.available() && millis() - start < 1000) {
    delay(1);
  }

  if (!client.available()) {
    client.stop();
    return;
  }

  String requestLine = client.readStringUntil('\n');
  requestLine.trim();

  while (client.available()) {
    String headerLine = client.readStringUntil('\n');
    if (headerLine == "\r" || headerLine.length() == 0) {
      break;
    }
  }

  if (requestLine.startsWith("OPTIONS ")) {
    sendOptionsResponse(client);
  } else if (requestLine.startsWith("GET /data ")) {
    sendHttpResponse(client, 200, "OK", "application/json", latestPayload);
  } else if (requestLine.startsWith("GET / ")) {
    sendHttpResponse(client, 200, "OK", "text/plain", "Smart Parking UNO R4 WiFi telemetry is running. Open /data for JSON.");
  } else {
    sendHttpResponse(client, 404, "Not Found", "text/plain", "Not found");
  }

  delay(1);
  client.stop();
}

void connectToWifi() {
  Serial.print("Connecting to Wi-Fi SSID: ");
  Serial.println(WIFI_SSID);

  WiFi.disconnect();
  delay(500);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting to Wi-Fi");

  const unsigned long CONNECT_TIMEOUT_MS = 30000UL;
  unsigned long start = millis();
  IPAddress ip(0, 0, 0, 0);

  // รอให้เชื่อม + ได้ IP จริง (ไม่ใช่ 0.0.0.0)
  while (true) {
    if (WiFi.status() == WL_CONNECTED) {
      ip = WiFi.localIP();
      if (ip != IPAddress(0, 0, 0, 0)) {
        break;
      }
    }

    delay(WIFI_RETRY_DELAY_MS);
    Serial.print(".");

    if (millis() - start > CONNECT_TIMEOUT_MS) {
      Serial.println();
      Serial.println("Wi-Fi connect timeout (30s) or localIP is 0.0.0.0. Reconnecting...");
      WiFi.disconnect();
      delay(500);
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
      start = millis();
    }
  }

  Serial.println();
  Serial.print("Wi-Fi connected. SSID: ");
  Serial.println(WiFi.SSID());
  Serial.print("RSSI: ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");
  Serial.print("Board IP: ");
  Serial.println(ip);

  // กันกรณี localIP กลับมาเป็น 0 อีกครั้งหลังจาก WiFi เชื่อม
  if (ip == IPAddress(0, 0, 0, 0)) {
    Serial.println("ERROR: localIP is 0.0.0.0; Wi-Fi seems unstable.");
  }
}

void startWebServer() {

  server.begin();

  Serial.print("Board name: ");
  Serial.println(MDNS_NAME);
  Serial.println("HTTP server started. Dashboard should fetch http://BOARD_IP/data");
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(trigPin1, OUTPUT); pinMode(echoPin1, INPUT); pinMode(ledPin1, OUTPUT);
  pinMode(trigPin2, OUTPUT); pinMode(echoPin2, INPUT); pinMode(ledPin2, OUTPUT);
  pinMode(trigPin3, OUTPUT); pinMode(echoPin3, INPUT); pinMode(ledPin3, OUTPUT);
  pinMode(trigPin4, OUTPUT); pinMode(echoPin4, INPUT); pinMode(ledPin4, OUTPUT);

  digitalWrite(trigPin1, LOW);
  digitalWrite(trigPin2, LOW);
  digitalWrite(trigPin3, LOW);
  digitalWrite(trigPin4, LOW);

  connectToWifi();
  startWebServer();
}

float measureDistanceSingle(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  unsigned long duration = pulseIn(echoPin, HIGH, PULSE_TIMEOUT);

  if (duration == 0) {
    return 999.0f;
  }

  return (duration * SOUND_SPEED_CM_PER_US) / 2.0f;
}

float measureDistanceAvg(int trigPin, int echoPin) {
  float sum = 0.0f;
  int valid = 0;

  for (int i = 0; i < SAMPLES; i++) {
    float d = measureDistanceSingle(trigPin, echoPin);

    if (d < 900.0f) {
      sum += d;
      valid++;
    }

    delay(SAMPLE_DELAY_MS);
  }

  if (valid == 0) {
    return 999.0f;
  }

  return sum / valid;
}

int computeConfidence(float d) {
  if (d >= 900.0f) {
    return 40;
  }

  float diff = fabs(d - OCCUPIED_THRESHOLD_CM);
  int conf = (int)constrain(55 + diff * 6.0f, 50.0f, 100.0f);

  return conf;
}

const char* statusFromDistance(float d) {
  if (d >= 900.0f) {
    return "Sensor Error";
  }

  return (d < OCCUPIED_THRESHOLD_CM) ? "Occupied" : "Empty";
}

String buildJsonPayload(float d1, float d2, float d3, float d4) {
  const char* s1 = statusFromDistance(d1);
  const char* s2 = statusFromDistance(d2);
  const char* s3 = statusFromDistance(d3);
  const char* s4 = statusFromDistance(d4);

  int c1 = computeConfidence(d1);
  int c2 = computeConfidence(d2);
  int c3 = computeConfidence(d3);
  int c4 = computeConfidence(d4);

  int available = 0;
  if (strcmp(s1, "Empty") == 0) available++;
  if (strcmp(s2, "Empty") == 0) available++;
  if (strcmp(s3, "Empty") == 0) available++;
  if (strcmp(s4, "Empty") == 0) available++;

  String recommended = "-";
  int maxConf = -1;

  if (strcmp(s1, "Empty") == 0 && c1 > maxConf) { recommended = "P1"; maxConf = c1; }
  if (strcmp(s2, "Empty") == 0 && c2 > maxConf) { recommended = "P2"; maxConf = c2; }
  if (strcmp(s3, "Empty") == 0 && c3 > maxConf) { recommended = "P3"; maxConf = c3; }
  if (strcmp(s4, "Empty") == 0 && c4 > maxConf) { recommended = "P4"; maxConf = c4; }

  if (recommended == "-") {
    if (c1 > maxConf) { recommended = "P1"; maxConf = c1; }
    if (c2 > maxConf) { recommended = "P2"; maxConf = c2; }
    if (c3 > maxConf) { recommended = "P3"; maxConf = c3; }
    if (c4 > maxConf) { recommended = "P4"; maxConf = c4; }
  }

  String js;
  js += "{\"available\":";
  js += available;
  js += ",\"recommended\":\"";
  js += recommended;
  js += "\",\"slots\":[";

  js += "{\"id\":\"P1\",\"status\":\"" + String(s1) + "\",\"confidence\":" + c1 + "},";
  js += "{\"id\":\"P2\",\"status\":\"" + String(s2) + "\",\"confidence\":" + c2 + "},";
  js += "{\"id\":\"P3\",\"status\":\"" + String(s3) + "\",\"confidence\":" + c3 + "},";
  js += "{\"id\":\"P4\",\"status\":\"" + String(s4) + "\",\"confidence\":" + c4 + "}";

  js += "]}";

  return js;
}

void controlLeds(float d1, float d2, float d3, float d4) {
  digitalWrite(ledPin1, (d1 < OCCUPIED_THRESHOLD_CM) ? LOW : HIGH);
  digitalWrite(ledPin2, (d2 < OCCUPIED_THRESHOLD_CM) ? LOW : HIGH);
  digitalWrite(ledPin3, (d3 < OCCUPIED_THRESHOLD_CM) ? LOW : HIGH);
  digitalWrite(ledPin4, (d4 < OCCUPIED_THRESHOLD_CM) ? LOW : HIGH);
}

void loop() {
  handleHttpClient();

  if (millis() - lastSensorUpdate < DASHBOARD_UPDATE_MS) {
    delay(LOOP_DELAY_MS);
    return;
  }

  lastSensorUpdate = millis();

  float distance1 = measureDistanceAvg(trigPin1, echoPin1);
  float distance2 = measureDistanceAvg(trigPin2, echoPin2);
  float distance3 = measureDistanceAvg(trigPin3, echoPin3);
  float distance4 = measureDistanceAvg(trigPin4, echoPin4);

  controlLeds(distance1, distance2, distance3, distance4);

  latestPayload = buildJsonPayload(distance1, distance2, distance3, distance4);
 // Serial.println(latestPayload);
}