#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

// ===================
// Configuration
// ===================
const char *ssid = "Rangapg16";
const char *password = "password@16";
const char *server_url = "http://192.168.0.103:5000/newdata"; 

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
    
    if (currentState == HIGH) {
      digitalWrite(DOOR_STATUS_PIN, HIGH);
    } else {
      digitalWrite(DOOR_STATUS_PIN, LOW);
    }

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
// CORE 1 FUNCTION: Capture and Send Photo (Modified with Timeout)
// ====================================================================
void captureAndSendPhoto() {
  Serial.println("Turning on flash and capturing...");
  digitalWrite(FLASH_GPIO, HIGH);
  delay(150);
  camera_fb_t *fb = esp_camera_fb_get();
  digitalWrite(FLASH_GPIO, LOW);
  
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  if (process_is_stale) {
    Serial.println("ABORTING: Process is stale. Discarding captured image.");
    esp_camera_fb_return(fb);
    return;
  }

  uint8_t *jpg_buf = NULL;
  size_t jpg_buf_len = 0;
  bool converted = frame2jpg(fb, 80, &jpg_buf, &jpg_buf_len);
  esp_camera_fb_return(fb);

  if (!converted) {
    Serial.println("JPEG conversion failed");
    return;
  }

  if (process_is_stale) {
    Serial.println("ABORTING: Process is stale. Discarding converted JPEG.");
    free(jpg_buf);
    return;
  }

  const char* model_output_json = "{\"items\":[{\"type\":\"Tomato\",\"quantity\":2},{\"type\":\"Apple\",\"quantity\":5},{\"type\":\"Cheese\",\"quantity\":1},{\"type\":\"Eggs\",\"quantity\":12},{\"type\":\"Milk\",\"quantity\":1}]}";

  Serial.println("Sending image and inventory data to server...");
  HTTPClient http;
  http.begin(server_url);
  
  // --- START OF FIX ---
  // Set timeout to 20 seconds (20000 ms) to wait for Gemini API
  http.setTimeout(20000); 
  // --- END OF FIX ---
  
  http.addHeader("X-Metadata", model_output_json);
  http.addHeader("Content-Type", "image/jpeg");

  int httpResponseCode = http.POST(jpg_buf, jpg_buf_len);
  
  free(jpg_buf);

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
// SETUP: Runs once on Core 1
// ====================================================================
void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  Serial.begin(115200);
  Serial.println("\n--- Smart Fridge System Initializing ---");

  pinMode(SENSOR_GPIO, INPUT_PULLUP);
  pinMode(FLASH_GPIO, OUTPUT);
  digitalWrite(FLASH_GPIO, LOW);
  pinMode(DOOR_STATUS_PIN, OUTPUT);
  digitalWrite(DOOR_STATUS_PIN, LOW);

  camera_config_t config;
  config.pixel_format = PIXFORMAT_RGB565;
  config.frame_size = FRAMESIZE_240X240;
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
  config.jpeg_quality = 12;
  config.fb_count = 2;
  config.grab_mode = CAMERA_GRAB_LATEST;

  Serial.println("Initializing camera...");
  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera init failed!"); return;
  }
  Serial.println("Camera initialized.");

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nWiFi connected");

  xTaskCreatePinnedToCore(doorSensorTask, "SensorTask", 4096, NULL, 1, &SensorTask, 0);
  Serial.println("System Ready.");
}

// ====================================================================
// LOOP: Runs continuously on Core 1
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
    
    if(process_is_stale) {
      Serial.println("NOTICE: Process was cancelled, but finished before new one started.");
    }
     Serial.println("=== Capture and Upload Process Ended ===");
  }
  delay(100);
}