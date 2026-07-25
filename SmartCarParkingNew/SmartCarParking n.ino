#include <Arduino.h>
#include <WiFiS3.h>
#include <WiFiSSLClient.h>
#include <math.h>

// =========================================================
// การตั้งค่า Wi-Fi ของบ้าน/โรงเรียน (ใส่ให้ตรงก่อนอัปโหลด)
// =========================================================
const char* WIFI_SSID     = "OPPO A15";
const char* WIFI_PASSWORD = "12345678no";

// =========================================================
// เซิร์ฟเวอร์ปลายทาง (โดเมน Coolify ของคุณ)
// - ห้ามใส่ "http://" หรือ "https://" นำหน้า ใส่แค่ตัวโดเมนเฉยๆ
// - ห้ามมี "/" ต่อท้าย
// - ถ้าโดเมนของคุณเปลี่ยน ให้แก้ตรงนี้ที่เดียว
// =========================================================
const char* SERVER_HOST = "ucos408c04wkg8s0oo8wgwos.122.155.223.205.sslip.io";
const int   SERVER_PORT = 443;   // Coolify ออก HTTPS ให้อัตโนมัติ ปกติใช้ 443
const bool  SERVER_USE_SSL = true; // ถ้าโดเมนคุณไม่มี HTTPS จริงๆ ค่อยเปลี่ยนเป็น false และ SERVER_PORT เป็น 80
const char* SERVER_PATH = "/ultrasonic"; // endpoint ที่มีอยู่แล้วในฝั่งเซิร์ฟเวอร์ (cam_ai_server.py)

// ความถี่ในการยิงข้อมูลเข้าเซิร์ฟเวอร์ (มิลลิวินาที)
// อย่าถี่เกินไป เพราะทุกครั้งต้องทำ TLS handshake ใหม่ (ใช้เวลา+พลังงานพอสมควร)
const unsigned long SEND_INTERVAL_MS = 1500UL;

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
const unsigned long WIFI_RETRY_DELAY_MS = 500;
const unsigned long WIFI_CHECK_INTERVAL_MS = 5000UL;

WiFiClient    plainClient;
WiFiSSLClient sslClient;

unsigned long lastSendMs = 0;
unsigned long lastWifiCheckMs = 0;

// =========================================================
// Wi-Fi
// =========================================================
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
}

void ensureWifiConnected() {
  if (millis() - lastWifiCheckMs < WIFI_CHECK_INTERVAL_MS) {
    return;
  }
  lastWifiCheckMs = millis();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] หลุดการเชื่อมต่อ กำลังต่อใหม่...");
    connectToWifi();
  }
}

// =========================================================
// วัดระยะและแปลผล
// =========================================================
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

// คืนค่า "Occupied" / "Empty" / "Sensor Error" (ไว้ใช้คุมไฟ LED)
const char* statusFromDistance(float d) {
  if (d >= 900.0f) {
    return "Sensor Error";
  }
  return (d < OCCUPIED_THRESHOLD_CM) ? "Occupied" : "Empty";
}

// แปลงเป็นค่าที่ /ultrasonic ฝั่งเซิร์ฟเวอร์เข้าใจ: "occupied" / "empty" / "unknown"
// (ฝั่งเซิร์ฟเวอร์ถือว่าอะไรที่ไม่ใช่ occupied = ไม่กันโซนนั้นให้ AI กล้องเดา
//  ดังนั้น Sensor Error ไม่ควรส่งเป็น "empty" เพราะจะไปบังคับผลลัพธ์ผิดๆ)
String mapStatusForServer(const char* status) {
  if (strcmp(status, "Occupied") == 0) return "occupied";
  if (strcmp(status, "Empty") == 0) return "empty";
  return "unknown"; // Sensor Error
}

void controlLeds(float d1, float d2, float d3, float d4) {
  digitalWrite(ledPin1, (d1 < OCCUPIED_THRESHOLD_CM) ? LOW : HIGH);
  digitalWrite(ledPin2, (d2 < OCCUPIED_THRESHOLD_CM) ? LOW : HIGH);
  digitalWrite(ledPin3, (d3 < OCCUPIED_THRESHOLD_CM) ? LOW : HIGH);
  digitalWrite(ledPin4, (d4 < OCCUPIED_THRESHOLD_CM) ? LOW : HIGH);
}

// =========================================================
// ยิง POST /ultrasonic เข้าเซิร์ฟเวอร์ (แทนที่การให้ browser มาดึง /data)
// =========================================================
bool postSlotsToServer(const String& s1, const String& s2, const String& s3, const String& s4) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[POST] Wi-Fi ยังไม่เชื่อมต่อ ข้ามรอบนี้");
    return false;
  }

  String body = "{\"slots\":{\"P1\":\"" + s1 + "\",\"P2\":\"" + s2 +
                "\",\"P3\":\"" + s3 + "\",\"P4\":\"" + s4 + "\"}}";

  Client* client = SERVER_USE_SSL ? (Client*)&sslClient : (Client*)&plainClient;

  if (!client->connect(SERVER_HOST, SERVER_PORT)) {
    Serial.print("[POST] เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ: ");
    Serial.println(SERVER_HOST);
    client->stop();
    return false;
  }

  client->print("POST ");
  client->print(SERVER_PATH);
  client->println(" HTTP/1.1");
  client->print("Host: ");
  client->println(SERVER_HOST);
  client->println("Content-Type: application/json");
  client->print("Content-Length: ");
  client->println(body.length());
  client->println("Connection: close");
  client->println();
  client->print(body);

  // อ่านบรรทัดสถานะ (เช่น HTTP/1.1 200 OK) เพื่อ debug เฉยๆ ไม่ได้ใช้ต่อ
  unsigned long start = millis();
  while (client->connected() && !client->available() && millis() - start < 5000) {
    delay(5);
  }

  String statusLine = "(no response)";
  if (client->available()) {
    statusLine = client->readStringUntil('\n');
  }

  // เคลียร์ข้อมูลที่เหลือทิ้งแล้วปิดการเชื่อมต่อ
  unsigned long drainStart = millis();
  while (client->connected() && millis() - drainStart < 2000) {
    while (client->available()) {
      client->read();
    }
  }
  client->stop();

  Serial.print("[POST] body=");
  Serial.print(body);
  Serial.print(" -> ");
  Serial.println(statusLine);

  return statusLine.indexOf("200") > 0;
}

// =========================================================
// setup / loop
// =========================================================
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

  Serial.print("จะส่งข้อมูลไปที่ ");
  Serial.print(SERVER_USE_SSL ? "https://" : "http://");
  Serial.print(SERVER_HOST);
  Serial.println(SERVER_PATH);
}

void loop() {
  ensureWifiConnected();

  if (millis() - lastSendMs < SEND_INTERVAL_MS) {
    return;
  }
  lastSendMs = millis();

  float distance1 = measureDistanceAvg(trigPin1, echoPin1);
  float distance2 = measureDistanceAvg(trigPin2, echoPin2);
  float distance3 = measureDistanceAvg(trigPin3, echoPin3);
  float distance4 = measureDistanceAvg(trigPin4, echoPin4);

  controlLeds(distance1, distance2, distance3, distance4);

  String s1 = mapStatusForServer(statusFromDistance(distance1));
  String s2 = mapStatusForServer(statusFromDistance(distance2));
  String s3 = mapStatusForServer(statusFromDistance(distance3));
  String s4 = mapStatusForServer(statusFromDistance(distance4));

  postSlotsToServer(s1, s2, s3, s4);
}
