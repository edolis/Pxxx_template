# ----------------------------------------------------------------------
# OTA detection: enabled if ED_OTA component is linked
# ----------------------------------------------------------------------
if(TARGET __idf_ED_OTA)
    set(ENABLE_OTA 1)
    message(STATUS "OTA component is linked → LZ4 compression will run after build")
else()
    set(ENABLE_OTA 0)
    message(STATUS "OTA component not linked → skipping post‑build steps")
endif()

idf_component_register(SRCS
  "main.cpp"
"$ENV{ESP_HEADERS}/x509_crt_bundle.S"
    INCLUDE_DIRS "." ${CMAKE_CURRENT_BINARY_DIR}
    REQUIRES
    ED_WIFI
    ED_MQTT
    diag
   # ED_S_JSON
    ED_OTA
   # ED_EEPROM
   # ED_COM_ADS1115
   # ED_SNS_OPT3001
   # ED_SNS_MT6701
   # ED_SNS_LD2450
   ED_SNS_RCWL1670
   # ED_COM_MCP4725
   # ED_SNS_AS7343
     esp_timer esp_hw_support led_strip driver
)

target_compile_definitions(${COMPONENT_TARGET} PRIVATE ENABLE_OTA=${ENABLE_OTA})