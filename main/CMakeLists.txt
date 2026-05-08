# ----------------------------------------------------------------------
# Git version detection – works for both tagged and untagged repos
# ----------------------------------------------------------------------
execute_process(COMMAND git describe --tags --long --dirty --always
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    OUTPUT_VARIABLE GIT_DESCRIBE
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
)
if(NOT GIT_DESCRIBE)
    set(GIT_DESCRIBE "v0.0.0-0-g0000000-dirty")
endif()
set(VERSION_STRING "${GIT_DESCRIBE}")

# Get short hash (7 chars) directly from git
execute_process(COMMAND git rev-parse --short=7 HEAD
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    OUTPUT_VARIABLE GIT_SHORT_HASH_RAW
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
)
if(NOT GIT_SHORT_HASH_RAW)
    set(GIT_SHORT_HASH_RAW "0000000")
endif()
set(GIT_SHORT_HASH "g${GIT_SHORT_HASH_RAW}")

# Get full hash
execute_process(COMMAND git rev-parse HEAD
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    OUTPUT_VARIABLE GIT_FULL_HASH
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
)
if(NOT GIT_FULL_HASH)
    set(GIT_FULL_HASH "0000000000000000000000000000000000000000")
endif()

# Extract tag name (first part of describe, e.g., "v0.0.1" from "v0.0.1-...")
set(GIT_TAG "untagged")
if(GIT_DESCRIBE MATCHES "^v[0-9.]+")
    string(REGEX MATCH "^v[0-9.]+" GIT_TAG "${GIT_DESCRIBE}")
endif()

# Build ID using the raw short hash (without 'g')
string(TIMESTAMP BUILD_TIMESTAMP "%Y%m%d-%H%M%S")
set(BUILD_ID "P${BUILD_TIMESTAMP}-${GIT_SHORT_HASH_RAW}")

# Export version string for top‑level OTA compression
set(PROJECT_VER_CACHE "${VERSION_STRING}" CACHE STRING "Firmware version string" FORCE)

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

# Generate version.h from template
configure_file(${CMAKE_CURRENT_LIST_DIR}/version.h.in ${CMAKE_CURRENT_BINARY_DIR}/version.h @ONLY)

# Component registration
idf_component_register(SRCS "main.cpp" "$ENV{ESP_HEADERS}/x509_crt_bundle.S"
    INCLUDE_DIRS "." ${CMAKE_CURRENT_BINARY_DIR}
    REQUIRES ED_WIFI ED_MQTT diag ED_S_JSON
)

target_compile_definitions(${COMPONENT_TARGET} PRIVATE ENABLE_OTA=${ENABLE_OTA})