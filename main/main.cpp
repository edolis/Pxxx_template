/**
* @file main.cpp
* @brief RCWL1670 ultrasonic sensor library test
 *
 * @author Emanuele Dolis (emanuele.dolis@gmail.com)
 * @version GIT_VERSION: v1.1.3-5-g511346d-dirty
 * @date 2026-06-24
 * @submodules-start
 *   ED_WIFI : v1.1.0-1-g3b68ca4
 * @submodules-end
 */

// -----------------------------------------------------------------------------
// 1. Target and board definitions
// -----------------------------------------------------------------------------
#define CONFIG_IDF_TARGET_ESP32C6
#include "ed_board.h"

// -----------------------------------------------------------------------------
// 2. ESP-IDF headers
// -----------------------------------------------------------------------------
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

// -----------------------------------------------------------------------------
// 3. RCWL1670 driver
// -----------------------------------------------------------------------------
#include "ED_SNS_RCWL1670.h"

// -----------------------------------------------------------------------------
// 4. Application constants
// -----------------------------------------------------------------------------
static const char *TAG = "MAIN";

// Tank geometry – distance from sensor to bottom (cm)
#define TANK_HEIGHT  200.0f

// Sensor pins (direct 3.3V connection – no voltage divider)
#define TRIG_PIN     GPIO_NUM_6
#define ECHO_PIN     GPIO_NUM_7

// Sensor parameters (tunable)
#define MIN_DIST     5       // minimum measurable distance (cm)
#define MAX_DIST     400     // maximum measurable distance (cm)
#define MAX_RETRY    2       // retries on failed reading
#define FINE_TUNE    200     // echo timeout adjustment (50‑300)
#define DEBUG_EN     false    // enable debug logging initially

// -----------------------------------------------------------------------------
// 5. Main application
// -----------------------------------------------------------------------------
extern "C" void app_main(void)
{
    ESP_LOGI(TAG, "=== RCWL1670 Full Feature Test ===");

    // -------------------------------------------------------------
    // 5.1 Create sensor instance with all parameters
    // -------------------------------------------------------------
    ed_sns::RCWL1670 sensor(TRIG_PIN, ECHO_PIN,
                            MIN_DIST, MAX_DIST,
                            MAX_RETRY, FINE_TUNE,
                            DEBUG_EN);

    // -------------------------------------------------------------
    // 5.2 Initialise GPIOs
    // -------------------------------------------------------------
    esp_err_t ret = sensor.init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Sensor init failed (err=0x%x)", ret);
        return;
    }
    ESP_LOGI(TAG, "Sensor initialised successfully");

    // -------------------------------------------------------------
    // 5.3 Display current configuration
    // -------------------------------------------------------------
    auto cfg = sensor.get_config();
    ESP_LOGI(TAG, "Configuration:");
    ESP_LOGI(TAG, "  TRIG pin : %d", cfg.trig_pin);
    ESP_LOGI(TAG, "  ECHO pin : %d", cfg.echo_pin);
    ESP_LOGI(TAG, "  Min dist : %u cm", cfg.min_dist);
    ESP_LOGI(TAG, "  Max dist : %u cm", cfg.max_dist);
    ESP_LOGI(TAG, "  Max retry: %u", cfg.max_retry);
    ESP_LOGI(TAG, "  Fine tune: %u", cfg.fine_tune);
    ESP_LOGI(TAG, "  Debug    : %s", cfg.debug ? "ON" : "OFF");

    // -------------------------------------------------------------
    // 5.4 Reset Kalman filter (clean start)
    // -------------------------------------------------------------
    sensor.reset_filter();
    ESP_LOGI(TAG, "Kalman filter reset");

    // -------------------------------------------------------------
    // 5.5 Main measurement loop – demonstrates all features
    // -------------------------------------------------------------
    uint16_t raw_dist = 0;
    float    filtered_dist = 0.0f;
    float    water_level = 0.0f;
    int      percentage = 0;
    int      cycle = 0;

    while (1) {
        cycle++;
        ESP_LOGI(TAG, "--- Cycle %d ---", cycle);

        // ---------------------------------------------------------
        // a) Raw measurement (without filter)
        // ---------------------------------------------------------
        ret = sensor.measure(raw_dist);
        if (ret == ESP_OK) {
            ESP_LOGI(TAG, "Raw distance : %3u cm", raw_dist);
        } else {
            ESP_LOGW(TAG, "Raw measurement failed");
        }

        // ---------------------------------------------------------
        // b) Filtered measurement (with Kalman)
        // ---------------------------------------------------------
        ret = sensor.measure_filtered(filtered_dist);
        if (ret == ESP_OK) {
            ESP_LOGI(TAG, "Filtered dist: %5.1f cm", filtered_dist);

            // Calculate water level and percentage
            water_level = TANK_HEIGHT - filtered_dist;
            if (water_level < 0.0f)   water_level = 0.0f;
            if (water_level > TANK_HEIGHT) water_level = TANK_HEIGHT;
            percentage = (int)((water_level / TANK_HEIGHT) * 100.0f);

            ESP_LOGI(TAG, "Water level : %5.1f cm from bottom", water_level);
            ESP_LOGI(TAG, "Fill        : %3d %%", percentage);

            // Alerts
            if (percentage <= 20) {
                ESP_LOGW(TAG, "⚠️  LOW WATER LEVEL (<= 20%%)");
            } else if (percentage >= 95) {
                ESP_LOGW(TAG, "⚠️  TANK NEARLY FULL (>= 95%%)");
            }
        } else {
            ESP_LOGW(TAG, "Filtered measurement failed");
        }

        // ---------------------------------------------------------
        // c) Demonstrate debug toggle (toggle every 10 cycles)
        // ---------------------------------------------------------
        if (cycle % 10 == 0) {
            bool new_debug = !sensor.get_config().debug;
            sensor.set_debug(new_debug);
            ESP_LOGI(TAG, "Debug toggled to %s", new_debug ? "ON" : "OFF");
        }

        // ---------------------------------------------------------
        // d) Demonstrate reset_filter (reset every 30 cycles)
        // ---------------------------------------------------------
        if (cycle % 30 == 0) {
            sensor.reset_filter();
            ESP_LOGI(TAG, "Kalman filter reset (periodic)");
        }

        // ---------------------------------------------------------
        // e) Wait before next reading
        // ---------------------------------------------------------
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}