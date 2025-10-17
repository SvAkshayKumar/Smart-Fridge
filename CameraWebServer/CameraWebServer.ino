

// /*
//  * ESP32-CAM Magnetic Door Sensor Test
//  * 
//  * This sketch reads the state of a magnetic reed switch and prints a message
//  * to the Serial Monitor whenever the state changes (e.g., a door opens or closes).
//  * 
//  * WIRING:
//  * - Connect one wire from the sensor to a GND pin on the ESP32-CAM.
//  * - Connect the other wire from the sensor to the GPIO pin defined below (sensorPin).
//  * 
//  * HOW IT WORKS:
//  * We use the internal pull-up resistor (`INPUT_PULLUP`).
//  * - When the door is OPEN (magnet is far), the switch is open. The pin is pulled HIGH (reads as 1).
//  * - When the door is CLOSED (magnet is near), the switch is closed, connecting the pin to GND. The pin is pulled LOW (reads as 0).
//  */

// // Define the GPIO pin you connected the sensor to.
// const int sensorPin = 13; 

// // Variable to store the last known state of the sensor.
// // We initialize it to the "HIGH" or "OPEN" state.
// int lastSensorState = HIGH; 

// void setup() {
//   // Start serial communication at a 115200 baud rate.
//   // This is a standard speed for ESP32.
//   Serial.begin(115200);
//   Serial.println("\n\n--- ESP32 Door Sensor Test Initializing ---");

//   // Set the sensor pin as an input with the internal pull-up resistor enabled.
//   pinMode(sensorPin, INPUT_PULLUP);

//   // Give a moment for things to stabilize and print the initial state.
//   delay(500);
//   Serial.print("The sensor is ready. Move the magnet to test.");
//   Serial.println("------------------------------------------");

//   // Read the initial state to avoid a false trigger at the start.
//   lastSensorState = digitalRead(sensorPin);
// }

// void loop() {
//   // Read the current state of the sensor pin.
//   int currentSensorState = digitalRead(sensorPin);

//   // Check if the current state is different from the last known state.
//   if (currentSensorState != lastSensorState) {
    
//     // The state has changed!
//     if (currentSensorState == HIGH) {
//       Serial.println("Door is now: OPEN");
//     } else {
//       Serial.println("Door is now: CLOSED");
//     }
    
//     // Update the last state with the new current state for the next loop.
//     lastSensorState = currentSensorState;

//     // A small delay to prevent "bouncing" where the switch rapidly opens/closes.
//     delay(50); 
//   }
  
//   // A small delay in the main loop to keep the ESP32 from running too hot.
//   delay(50);
// }


#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

// ===================
// Configuration
// ===================

// >>> ENTER YOUR WIFI CREDENTIALS HERE <<<
const char *ssid = "Rangapg16";
const char *password = "password@16";

// Server URL
const char *server_url = "http://192.168.0.101/newdata";

// GPIO Pin for the door sensor and Flash
const int SENSOR_GPIO = 13;
const int FLASH_GPIO = 4;

// Select camera model
#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// ===================
// Global Variables for Core Communication
// ===================

// This flag signals the main core to take a picture.
volatile bool take_picture_flag = false;

// Task handle for our sensor reading task
TaskHandle_t SensorTask;

// ====================================================================
// CORE 0 TASK: Dedicated Door Sensor Monitoring
// This function runs continuously on Core 0 to watch the door.
// ====================================================================
void doorSensorTask(void *pvParameters) {
  Serial.println("Sensor monitoring task started on Core 0.");
  
  // State machine variables to detect an "open then close" event
  bool doorWasOpen = false;

  for (;;) { // Infinite loop for the task
    int currentState = digitalRead(SENSOR_GPIO);

    // Using INPUT_PULLUP: HIGH = Open, LOW = Closed

    // State 1: Door is OPEN, and was previously closed
    if (currentState == HIGH && !doorWasOpen) {
      doorWasOpen = true;
      // Minor delay to debounce
      vTaskDelay(50 / portTICK_PERIOD_MS);
    }
    
    // State 2: Door is now CLOSED, and we know it was previously opened
    if (currentState == LOW && doorWasOpen) {
      Serial.println("EVENT: Door opened and closed. Triggering capture.");
      
      // Signal Core 1 to take a picture
      take_picture_flag = true;
      
      // Reset the state machine
      doorWasOpen = false;
      // Minor delay to debounce
      vTaskDelay(50 / portTICK_PERIOD_MS);
    }

    // Check every 100ms so we don't hog the CPU
    vTaskDelay(100 / portTICK_PERIOD_MS); 
  }
}

// ====================================================================
// CORE 1 FUNCTION: Capture, Convert, and Send Photo
// This runs on Core 1 when triggered by Core 0.
// ====================================================================
void captureAndSendPhoto() {
  Serial.println("Turning on flash and capturing...");
  digitalWrite(FLASH_GPIO, HIGH); // Turn on flash
  delay(100); // Give LED time to fully light up

  camera_fb_t *fb = NULL;
  
  // 1. Capture the raw frame (RGB565 based on your settings)
  fb = esp_camera_fb_get();
  digitalWrite(FLASH_GPIO, LOW); // Turn off flash immediately after capture
  
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  // 2. Convert RGB565 to JPEG for uploading
  uint8_t *jpg_buf = NULL;
  size_t jpg_buf_len = 0;
  // Convert frame to jpeg with 80% quality
  bool converted = frame2jpg(fb, 80, &jpg_buf, &jpg_buf_len);
  
  // Return the raw frame buffer to the camera driver to be reused
  esp_camera_fb_return(fb);

  if(!converted){
    Serial.println("JPEG compression failed");
    return;
  }

  Serial.println("Sending image to server...");
  HTTPClient http;
  http.begin(server_url);
  http.setTimeout(10000); // 10 seconds timeout

  // --- Construct the multipart/form-data request ---
  String boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW";
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  
  // Add metadata part
  String body_start = "--" + boundary + "\r\n";
  body_start += "Content-Disposition: form-data; name=\"metadata\"\r\n\r\n";
  body_start += "{\"status\": \"Door Opened and Closed\"}\r\n";

  // Add image file part header
  body_start += "--" + boundary + "\r\n";
  body_start += "Content-Disposition: form-data; name=\"imageFile\"; filename=\"capture.jpg\"\r\n";
  body_start += "Content-Type: image/jpeg\r\n\r\n";

  // The footer
  String body_end = "\r\n--" + boundary + "--\r\n";
  
  // Calculate total length
  size_t total_len = body_start.length() + jpg_buf_len + body_end.length();
  
  // Allocate memory for the whole body
  uint8_t *full_body = (uint8_t*) malloc(total_len);
  if(full_body == NULL) {
      Serial.println("Malloc failed, out of memory");
      free(jpg_buf);
      http.end();
      return;
  }
  
  // Copy parts into the full body buffer
  size_t offset = 0;
  memcpy(full_body + offset, body_start.c_str(), body_start.length());
  offset += body_start.length();
  memcpy(full_body + offset, jpg_buf, jpg_buf_len);
  offset += jpg_buf_len;
  memcpy(full_body + offset, body_end.c_str(), body_end.length());

  // Free the JPEG buffer now that it's copied
  free(jpg_buf);

  // --- Send the POST request ---
  int httpResponseCode = http.POST(full_body, total_len);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.printf("Success! Server response code: %d\n", httpResponseCode);
  } else {
    Serial.printf("Error sending POST: %s\n", http.errorToString(httpResponseCode).c_str());
  }
  
  // --- Clean up ---
  free(full_body);
  http.end();
  Serial.println("Upload process finished. Waiting for next event.");
}

// ====================================================================
// SETUP: Runs once on Core 1
// ====================================================================
void setup() {
  // Disable brownout detector
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  
  Serial.begin(115200);
  Serial.println("\n\n--- System Initializing ---");

  // Initialize pins
  pinMode(SENSOR_GPIO, INPUT_PULLUP);
  pinMode(FLASH_GPIO, OUTPUT);
  digitalWrite(FLASH_GPIO, LOW); // Ensure flash is off

  // ==================================================================
  // CAMERA CONFIGURATION - EXACTLY FROM YOUR WORKING CODE
  // ==================================================================
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
  // --- YOUR ORIGINAL SETTINGS ---
  config.pixel_format = PIXFORMAT_RGB565;
  config.frame_size = FRAMESIZE_240X240;
  config.jpeg_quality = 12;
  config.fb_count = 2;
  config.grab_mode = CAMERA_GRAB_LATEST;
  // ------------------------------

  Serial.println("Initializing camera...");
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return;
  }
  Serial.println("Camera initialized successfully.");

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");

  // Flash LED briefly to show readiness
  digitalWrite(FLASH_GPIO, HIGH);
  delay(200);
  digitalWrite(FLASH_GPIO, LOW);

  // Create the sensor task and pin it to Core 0
  xTaskCreatePinnedToCore(
      doorSensorTask,   /* Task function. */
      "SensorTask",     /* name of task. */
      4096,             /* Stack size of task */
      NULL,             /* parameter of the task */
      1,                /* priority of the task */
      &SensorTask,      /* Task handle */
      0);               /* Pin task to CORE 0 */

  Serial.println("System Ready. Open and close the door to test.");
}


// ====================================================================
// LOOP: Runs continuously on Core 1
// ====================================================================
void loop() {
  // Check if Core 0 has set the flag
  if (take_picture_flag) {
    
    // Only proceed if WiFi is connected
    if(WiFi.status() == WL_CONNECTED) {
      captureAndSendPhoto();
    } else {
      Serial.println("Error: WiFi Disconnected. Cannot send photo.");
    }
    
    // Reset the flag
    take_picture_flag = false;
  }

  delay(100);
}