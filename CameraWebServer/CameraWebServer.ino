#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

// ===================
// Configuration
// ===================
const char *ssid = "Akshay";
const char *password = "abcdefgh";
const char *server_url = "http://10.83.12.170:5000/newdata";

// GPIO Pins
const int SENSOR_GPIO = 13;
const int FLASH_GPIO = 4;
const int DOOR_STATUS_PIN = 12;

#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// State flags for handling latest request
volatile bool take_picture_flag = false;
volatile bool is_uploading = false;
volatile bool process_is_stale = false;

TaskHandle_t SensorTask;

// ====================================================================
// CORE 0 TASK: Door Sensor Monitoring
// ====================================================================
void doorSensorTask(void *pvParameters) {
  Serial.println("Sensor monitoring task started on Core 0.");
  bool doorWasOpen = false;

  for (;;) {
    int currentState = digitalRead(SENSOR_GPIO);

    digitalWrite(DOOR_STATUS_PIN, currentState ? HIGH : LOW);

    if (currentState == HIGH && !doorWasOpen) {
      doorWasOpen = true;
      vTaskDelay(50 / portTICK_PERIOD_MS);
    }

    if (currentState == LOW && doorWasOpen) {
      Serial.println("EVENT: Door opened and closed. Triggering capture.");

      if (is_uploading) {
        Serial.println("CANCELLATION: New request arrived during upload. Setting stale flag.");
        process_is_stale = true;
      }

      take_picture_flag = true;
      doorWasOpen = false;
    }

    vTaskDelay(100 / portTICK_PERIOD_MS);
  }
}

// ====================================================================
// CORE 1 FUNCTION: Capture and Send Photo (JPEG directly)
// ====================================================================
void captureAndSendPhoto() {
  Serial.println("Turning on flash and preparing to capture...");

  // 1️⃣ Turn on LED flash and wait to reach full brightness
  digitalWrite(FLASH_GPIO, HIGH);
  delay(600);  // Increase delay to allow LED to fully turn ON

  // 2️⃣ Start the camera sensor warm-up (avoids first dark frame)
  esp_camera_fb_return(esp_camera_fb_get()); // Throw away first frame
  delay(100); // Give the sensor some time to adjust

  // 3️⃣ Capture the image
  Serial.println("Capturing image...");
  camera_fb_t *fb = esp_camera_fb_get();

  // 4️⃣ Hold light briefly after capture
  delay(200);  
  digitalWrite(FLASH_GPIO, LOW);

  // 5️⃣ Check for errors
  if (!fb) {
    Serial.println("Camera capture failed!");
    return;
  }

  if (process_is_stale) {
    Serial.println("ABORTING: Process is stale. Discarding captured image.");
    esp_camera_fb_return(fb);
    return;
  }

  Serial.printf("Captured image: %d bytes\n", fb->len);

  // 6️⃣ Send the JPEG to the server
  HTTPClient http;
  http.begin(server_url);
  http.setTimeout(20000);
  http.addHeader("Content-Type", "image/jpeg");

  Serial.println("Sending image and inventory data to server...");
  int httpResponseCode = http.POST(fb->buf, fb->len);
  esp_camera_fb_return(fb);

  if (httpResponseCode > 0) {
    Serial.printf("Server responded with code: %d\n", httpResponseCode);
    String response = http.getString();
    Serial.println(response);
  } else {
    Serial.printf("Error sending POST: %s\n", http.errorToString(httpResponseCode).c_str());
  }

  http.end();
  Serial.println("Upload process finished.");
}

// ====================================================================
// SETUP
// ====================================================================
void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  Serial.begin(115200);
  Serial.println("\n--- Smart Fridge System Initializing ---");

  pinMode(SENSOR_GPIO, INPUT_PULLUP);
  pinMode(FLASH_GPIO, OUTPUT);
  pinMode(DOOR_STATUS_PIN, OUTPUT);
  digitalWrite(FLASH_GPIO, LOW);
  digitalWrite(DOOR_STATUS_PIN, LOW);

  // Camera Configuration for JPEG
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;  // << Now using JPEG format directly
  config.frame_size = FRAMESIZE_QVGA;    // 320x240
  config.jpeg_quality = 4;              // 0 = highest, 63 = lowest
  config.fb_count = 1;                   // Reduce memory use
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;

  Serial.println("Initializing camera...");
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return;
  }
  Serial.println("Camera initialized successfully.");

  // Connect WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  Serial.println(WiFi.localIP());

  // Start door sensor monitoring task
  xTaskCreatePinnedToCore(doorSensorTask, "SensorTask", 4096, NULL, 1, &SensorTask, 0);
  Serial.println("System Ready.");
}

// ====================================================================
// LOOP
// ====================================================================
void loop() {
  if (take_picture_flag) {
    take_picture_flag = false;
    process_is_stale = false;
    is_uploading = true;

    Serial.println("=== Starting New Capture and Upload Process ===");

    if (WiFi.status() == WL_CONNECTED) {
      captureAndSendPhoto();
    } else {
      Serial.println("Error: WiFi Disconnected.");
    }

    is_uploading = false;

    if (process_is_stale) {
      Serial.println("NOTICE: Process was cancelled, but finished before new one started.");
    }
    Serial.println("=== Capture and Upload Process Ended ===");
  }

  delay(100);
}
