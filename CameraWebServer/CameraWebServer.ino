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
const char *server_url = "http://192.1e-168.0.103:5000/newdata"; 

// GPIO Pins
const int SENSOR_GPIO = 13;
const int FLASH_GPIO = 4;
const int DOOR_STATUS_PIN = 12;

#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// --- MODIFICATION: New state flags for handling latest request ---
volatile bool take_picture_flag = false;
volatile bool is_uploading = false;      // Is an upload currently in progress?
volatile bool process_is_stale = false;  // Has a newer request arrived, making the current one obsolete?
// --- END OF MODIFICATION ---

TaskHandle_t SensorTask;

// ====================================================================
// CORE 0 TASK: Door Sensor Monitoring (Modified for responsiveness and new requests)
// ====================================================================
void doorSensorTask(void *pvParameters) {
  Serial.println("Sensor monitoring task started on Core 0.");
  bool doorWasOpen = false;
  for (;;) {
    int currentState = digitalRead(SENSOR_GPIO);
    
    // Control DOOR_STATUS_PIN based on the sensor's current state
    // This will now be very responsive.
    if (currentState == HIGH) {
      digitalWrite(DOOR_STATUS_PIN, HIGH); // Door is OPEN, turn pin ON
    } else {
      digitalWrite(DOOR_STATUS_PIN, LOW);  // Door is CLOSED, turn pin OFF
    }

    if (currentState == HIGH && !doorWasOpen) {
      doorWasOpen = true;
      vTaskDelay(50 / portTICK_PERIOD_MS);
    }
    
    // --- MODIFICATION: New trigger logic ---
    if (currentState == LOW && doorWasOpen) {
      Serial.println("EVENT: Door opened and closed. Triggering capture.");
      
      // If a process is already running, flag it as stale/to be cancelled.
      if (is_uploading) {
        Serial.println("CANCELLATION: New request arrived during upload. Setting stale flag.");
        process_is_stale = true;
      }
      
      take_picture_flag = true; // Signal Core 1 to start a (new) capture.
      doorWasOpen = false;

      // REMOVED the long delay here to make the task responsive.
    }
    // --- END OF MODIFICATION ---

    vTaskDelay(100 / portTICK_PERIOD_MS);
  }
}

// ====================================================================
// CORE 1 FUNCTION: Capture and Send Photo (Modified to be cancellable)
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

  // --- MODIFICATION: Check if a new request has made this one stale ---
  if (process_is_stale) {
    Serial.println("ABORTING: Process is stale. Discarding captured image.");
    esp_camera_fb_return(fb); // Clean up the frame buffer
    return; // Exit the function early
  }
  // --- END OF MODIFICATION ---

  uint8_t *jpg_buf = NULL;
  size_t jpg_buf_len = 0;
  bool converted = frame2jpg(fb, 80, &jpg_buf, &jpg_buf_len);
  esp_camera_fb_return(fb);

  if (!converted) {
    Serial.println("JPEG conversion failed");
    return;
  }

  // --- MODIFICATION: Check if a new request has made this one stale ---
  if (process_is_stale) {
    Serial.println("ABORTING: Process is stale. Discarding converted JPEG.");
    free(jpg_buf); // Clean up the jpeg buffer
    return; // Exit the function early
  }
  // --- END OF MODIFICATION ---

  const char* model_output_json = "{\"items\":[{\"type\":\"Tomato\",\"quantity\":2},{\"type\":\"Apple\",\"quantity\":5},{\"type\":\"Cheese\",\"quantity\":1},{\"type\":\"Eggs\",\"quantity\":12},{\"type\":\"Milk\",\"quantity\":1}]}";

  Serial.println("Sending image and inventory data to server...");
  HTTPClient http;
  http.begin(server_url);
  
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
// LOOP: Runs continuously on Core 1 (Modified to manage upload states)
// ====================================================================
void loop() {
  if (take_picture_flag) {
    take_picture_flag = false; // Consume the flag immediately
    process_is_stale = false;  // Reset stale flag for the new run
    is_uploading = true;       // Set status to busy
    
    Serial.println("=== Starting New Capture and Upload Process ===");
    if (WiFi.status() == WL_CONNECTED) {
      captureAndSendPhoto();
    } else {
      Serial.println("Error: WiFi Disconnected.");
    }
    
    is_uploading = false; // Set status to free
    
    if(process_is_stale) {
      Serial.println("NOTICE: Process was cancelled, but finished before new one started.");
    }
     Serial.println("=== Capture and Upload Process Ended ===");
  }
  delay(100);
}