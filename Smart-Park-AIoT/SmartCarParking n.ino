// =============================================================
// Smart Car Parking - Ultrasonic sensor board (Arduino UNO R4 WiFi)
// =============================================================
// เวอร์ชันนี้เปลี่ยนวิธีทำงานจากเดิม: เดิมบอร์ดรัน HTTP server ของตัวเอง
// (WiFiServer) แล้วรอให้เบราว์เซอร์ของคนดู "เข้ามาดึงข้อมูล" จากบอร์ด
// โดยตรง วิธีนี้ใช้ได้แค่ตอนเบราว์เซอร์อยู่ในวง WiFi เดียวกับบอร์ด
//
// พอย้ายเว็บ dashboard ไปรันบน Coolify (โดเมนสาธารณะผ่าน HTTPS) วิธีเดิมใช้
// ไม่ได้แล้ว เพราะ (1) เบราว์เซอร์ที่โหลดหน้า HTTPS จะถูกบล็อกไม่ให้ยิง
// request ไปหา IP วง local แบบ HTTP ตรง ๆ (Private Network Access) และ
// (2) คนที่เปิดเว็บจากที่อื่นก็ไม่มีทางเห็น IP วง local ของบอร์ดอยู่แล้ว
//
// เวอร์ชันนี้เลย "กลับด้าน" การเชื่อมต่อ: ให้ตัวบอร์ดเป็นฝ่ายยิงข้อมูลออกไป
// หาเซิร์ฟเวอร์กลาง (POST https://<โดเมน>/ultrasonic) แทน เหมือนกับที่
// camera_uploader.py ทำกับภาพจากกล้อง

#include <Arduino.h>
#include <WiFiS3.h>
#include <WiFiSSLClient.h>
#include <math.h>

// ---------------- ตั้งค่าก่อนอัปโหลด ----------------
const char* WIFI_SSID = "OPPO A15";
const char* WIFI_PASSWORD = "12345678no";

// โดเมนของเซิร์ฟเวอร์ที่ deploy ผ่าน Coolify (ไม่ต้องมี https:// นำหน้า
// และห้ามมี "/" ต่อท้าย) เช่น "bsoc0kg4c88sgws8csk08sgw.122.155.223.205.sslip.io"
const char* SERVER_HOST = "bsoc0kg4c88sgws8csk08sgw.122.155.223.205.sslip.io";
const int SERVER_PORT = 443;   // 443 = HTTPS (ค่าเริ่มต้นของ Coolify)
const bool USE_SSL = true;     // true ถ้าโดเมนเป็น https:// (ปกติ Coolify บังคับ HTTPS)
// -----------------------------------------------------

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
const unsigned long SEND_INTERVAL_MS = 700;   // ส่งข้อมูลเข้าเซิร์ฟเวอร์ทุกกี่ ms
const unsigned long HTTP_TIMEOUT_MS = 4000;

unsigned long lastSendTime = 0;

WiFiSSLClient sslClient;
WiFiClient plainClient;

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
  Serial.print("Wi-Fi connected. Board IP (สำหรับ debug เท่านั้น ไม่ได้ใช้รอรับ request แล้ว): ");
  Serial.println(ip);
  Serial.print("จะส่งข้อมูลไปที่: ");
  Serial.print(USE_SSL ? "https://" : "http://");
  Serial.print(SERVER_HOST);
  Serial.println("/ultrasonic");
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

const char* statusFromDistance(float d) {
  if (d >= 900.0f) {
    return "unknown";   // เซนเซอร์อ่านค่าไม่ได้ -> ส่งเป็น unknown แทนการเดา
  }
  return (d < OCCUPIED_THRESHOLD_CM) ? "occupied" : "empty";
}

void controlLeds(float d1, float d2, float d3, float d4) {
  digitalWrite(ledPin1, (d1 < OCCUPIED_THRESHOLD_CM) ? LOW : HIGH);
  digitalWrite(ledPin2, (d2 < OCCUPIED_THRESHOLD_CM) ? LOW : HIGH);
  digitalWrite(ledPin3, (d3 < OCCUPIED_THRESHOLD_CM) ? LOW : HIGH);
  digitalWrite(ledPin4, (d4 < OCCUPIED_THRESHOLD_CM) ? LOW : HIGH);
}

String buildUltrasonicJson(const char* s1, const char* s2, const char* s3, const char* s4) {
  String js = "{\"slots\":{";
  js += "\"P1\":\""; js += s1; js += "\",";
  js += "\"P2\":\""; js += s2; js += "\",";
  js += "\"P3\":\""; js += s3; js += "\",";
  js += "\"P4\":\""; js += s4; js += "\"";
  js += "}}";
  return js;
}

// ส่ง JSON payload ไปที่ POST /ultrasonic ของเซิร์ฟเวอร์กลาง
// คืนค่า true ถ้าส่งสำเร็จและเซิร์ฟเวอร์ตอบ 2xx
bool sendUltrasonicToServer(const String& jsonBody) {
  WiFiClient* clientPtr = USE_SSL ? (WiFiClient*)&sslClient : &plainClient;

  if (!clientPtr->connect(SERVER_HOST, SERVER_PORT)) {
    Serial.println("[HTTP] connect ไปเซิร์ฟเวอร์ไม่สำเร็จ");
    return false;
  }

  clientPtr->print("POST /ultrasonic HTTP/1.1\r\n");
  clientPtr->print("Host: "); clientPtr->print(SERVER_HOST); clientPtr->print("\r\n");
  clientPtr->print("Content-Type: application/json\r\n");
  clientPtr->print("Content-Length: "); clientPtr->print(jsonBody.length()); clientPtr->print("\r\n");
  clientPtr->print("Connection: close\r\n");
  clientPtr->print("\r\n");
  clientPtr->print(jsonBody);

  unsigned long start = millis();
  while (clientPtr->connected() && !clientPtr->available()) {
    if (millis() - start > HTTP_TIMEOUT_MS) {
      Serial.println("[HTTP] timeout รอ response");
      clientPtr->stop();
      return false;
    }
    delay(5);
  }

  String statusLine = clientPtr->readStringUntil('\n');
  clientPtr->stop();

  // ตัวอย่าง statusLine: "HTTP/1.1 200 OK"
  bool ok = statusLine.indexOf(" 200 ") != -1 || statusLine.indexOf(" 204 ") != -1;
  if (!ok) {
    Serial.print("[HTTP] เซิร์ฟเวอร์ตอบ: ");
    Serial.println(statusLine);
  }
  return ok;
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
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] หลุดการเชื่อมต่อ กำลังเชื่อมใหม่...");
    connectToWifi();
  }

  if (millis() - lastSendTime < SEND_INTERVAL_MS) {
    delay(LOOP_DELAY_MS);
    return;
  }
  lastSendTime = millis();

  float distance1 = measureDistanceAvg(trigPin1, echoPin1);
  float distance2 = measureDistanceAvg(trigPin2, echoPin2);
  float distance3 = measureDistanceAvg(trigPin3, echoPin3);
  float distance4 = measureDistanceAvg(trigPin4, echoPin4);

  controlLeds(distance1, distance2, distance3, distance4);

  const char* s1 = statusFromDistance(distance1);
  const char* s2 = statusFromDistance(distance2);
  const char* s3 = statusFromDistance(distance3);
  const char* s4 = statusFromDistance(distance4);

  String payload = buildUltrasonicJson(s1, s2, s3, s4);
  bool sent = sendUltrasonicToServer(payload);

  Serial.print(sent ? "[OK] " : "[FAIL] ");
  Serial.println(payload);
}
