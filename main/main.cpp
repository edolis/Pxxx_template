/**
* @file main.cpp
* @brief ADS1115 test using ED_ADS1115 library
 *
 * @author Emanuele Dolis (emanuele.dolis@gmail.com)
 * @version GIT_VERSION: v1.1.3-2-g1ca6c6c-dirty
 * @date 2026-05-15
 * @submodules-start
 *   ED_COM_ADS1115 : d81ca85
 *   ED_EEPROM      : V1.0.0-0-g620932e-dirty
 *   ED_MQTT        : v1.1.0-3-gfbadb25-dirty
 *   ED_OTA         : v2.0.0-2-gcd9ff99-dirty
 *   ED_S_JSON      : v1.0.0-0-gf58ffa6
 *   ED_WIFI        : v1.0.0-0-g2f08383
 * @submodules-end
 */
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "ed_board.h"
#include "ED_i2c.h"
#include "ED_ads1115.h"

static const char *TAG = "ads1115_16sps";
static SemaphoreHandle_t sem = nullptr;

/**
 *  note. tested with 100kOhm/1kOhm voltage divider from 3.3v rail on A0
 *
 */


void measurement_task(void *arg) {
    ed::Ads1115 *ads = (ed::Ads1115*)arg;
    float voltage_mV;

    while (1) {
        // Start a conversion on channel 0
        if (ads->triggerConversion(0) != ESP_OK) {
            ESP_LOGE(TAG, "triggerConversion failed");
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        // Wait for the ALERT pin (timeout 200 ms – more than enough for 16 SPS)
        if (xSemaphoreTake(sem, pdMS_TO_TICKS(200))) {
            if (ads->getResult(voltage_mV) == ESP_OK) {
                ESP_LOGI(TAG, "AIN0: %.3f mV (%.6f V)", voltage_mV, voltage_mV / 1000.0f);
            } else {
                ESP_LOGE(TAG, "getResult failed");
            }
        } else {
            ESP_LOGW(TAG, "Conversion timeout");
        }

        // Wait half a second before the next reading
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

extern "C" void app_main() {
    ESP_LOGI(TAG, "Data rate = 16 SPS, reading every 500 ms");

    I2CBus i2cBus(I2C_NUM_0, ED_I2C_SDA, ED_I2C_SCL, 400000);
    ed::Ads1115 ads(i2cBus, 0x48);

    // Initialise with GAIN_ONE, but data rate = 16 SPS
    ESP_ERROR_CHECK(ads.init(ed::AdsGain::GAIN_ONE,
                             ed::AdsDataRate::SPS_16,    // 16 samples per second
                             ed::AdsMode::MODE_SINGLE_SHOT));
    // Override channel 0 gain to maximum for precision
    ads.setChannelGain(0, ed::AdsGain::GAIN_SIXTEEN);

    // Enable data-ready interrupt on GPIO6 (active low)
    ESP_ERROR_CHECK(ads.enableDataReadyPin(GPIO_NUM_6, true));
    sem = ads.getDataReadySemaphore();

    // Create task
    xTaskCreate(measurement_task, "meas", 4096, &ads, 5, NULL);

    // Main loop idle
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}