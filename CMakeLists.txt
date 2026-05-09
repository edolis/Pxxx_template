cmake_minimum_required(VERSION 3.16)

# ----------------------------------------------------------------------
# Detect project version from Git (runs at CMake configure time)
# ----------------------------------------------------------------------
execute_process(
    COMMAND git describe --tags --long --dirty --always
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    OUTPUT_VARIABLE GIT_DESCRIBE
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
)
if(NOT GIT_DESCRIBE)
    set(GIT_DESCRIBE "v0.0.0-0-g0000000-dirty")
endif()
set(PROJECT_VER ${GIT_DESCRIBE})
message(STATUS "Firmware version: ${PROJECT_VER}")

# ----------------------------------------------------------------------
# Project configuration
# ----------------------------------------------------------------------
set(SHARED_FOLDER "//raspi00/fware" CACHE STRING "Network share for OTA firmware")
set(EXTRA_COMPONENT_DIRS "${CMAKE_CURRENT_LIST_DIR}/components/toolbox")

# Auto-detect project name from folder prefix (e.g., P029_kiln -> P029)
get_filename_component(CURRENT_FOLDER_NAME ${CMAKE_CURRENT_SOURCE_DIR} NAME)
string(REGEX REPLACE "^([^_]+).*" "\\1" PROJECT_PREFIX "${CURRENT_FOLDER_NAME}")
if(PROJECT_PREFIX MATCHES "^P[0-9x][0-9x][0-9x]")
    set(PROJECT_NAME "${PROJECT_PREFIX}")
    message(STATUS "Project name detected from folder prefix: ${PROJECT_NAME}")
else()
    set(PROJECT_NAME "my_esp_app")
    message(WARNING "Folder prefix '${PROJECT_PREFIX}' does not start with Pxxx. Using default: ${PROJECT_NAME}")
endif()

# Certificate bundle handling
if(DEFINED ENV{ESP_HEADERS})
    file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}")
    file(WRITE "${CMAKE_BINARY_DIR}/sdkconfig.certs"
        "CONFIG_MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE_PATH=\"$ENV{ESP_HEADERS}/ca.pem\"\n"
    )
    set(SDKCONFIG_DEFAULTS
        "${CMAKE_SOURCE_DIR}/sdkconfig.defaults"
        "${CMAKE_BINARY_DIR}/sdkconfig.certs"
    )
else()
    message(FATAL_ERROR "ESP_HEADERS environment variable is not set!")
endif()

# Include ESP-IDF project tools
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(${PROJECT_NAME})

# ----------------------------------------------------------------------
# Force CMake to reconfigure when Git HEAD or tags change
# ----------------------------------------------------------------------
set_property(DIRECTORY . APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${CMAKE_SOURCE_DIR}/.git/HEAD;${CMAKE_SOURCE_DIR}/.git/refs/tags"
)

# ----------------------------------------------------------------------
# Extra version info passed directly to the compiler (no generated header needed)
# ----------------------------------------------------------------------
execute_process(
    COMMAND git rev-parse HEAD
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    OUTPUT_VARIABLE FW_FULL_HASH
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
)
if(NOT FW_FULL_HASH)
    set(FW_FULL_HASH "0000000000000000000000000000000000000000")
endif()

# Build ID – same format as the Python script (PYYYYMMDD-HHMMSS-ffffff)
string(TIMESTAMP BUILD_TIMESTAMP "P%Y%m%d-%H%M%S-%f")
string(SUBSTRING "${BUILD_TIMESTAMP}" 0 23 FW_BUILD_ID)

target_compile_definitions(${PROJECT_NAME}.elf PRIVATE
    FW_FULL_HASH="${FW_FULL_HASH}"
    FW_BUILD_ID="${FW_BUILD_ID}"
)

message(STATUS "Full hash: ${FW_FULL_HASH}")
message(STATUS "Build ID:  ${FW_BUILD_ID}")

# ----------------------------------------------------------------------
# Pre‑build step: update version.h and main.cpp Doxygen comment
# ----------------------------------------------------------------------
find_package(Python3 REQUIRED)

add_custom_target(
    update_version_info ALL
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tools/update_version_comment.py
        "--version" "${PROJECT_VER}"
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Updating Git version in main.cpp and version.h"
    VERBATIM
)

add_dependencies(${CMAKE_PROJECT_NAME}.elf update_version_info)

# ----------------------------------------------------------------------
# OTA post‑build: compress firmware with lz4 and copy to shared folder
# ----------------------------------------------------------------------
set(ENABLE_OTA OFF)
if(EXISTS "${CMAKE_SOURCE_DIR}/components/ED_OTA/ED_OTA.h")
    set(ENABLE_OTA ON)
endif()

if(ENABLE_OTA)
    find_program(LZ4_EXECUTABLE lz4)
    if(NOT LZ4_EXECUTABLE)
        message(WARNING "lz4 not found – OTA compression will be skipped")
    else()
        set(FW_BIN "${CMAKE_BINARY_DIR}/${PROJECT_NAME}.bin")

        add_custom_command(
            TARGET gen_project_binary
            POST_BUILD
            COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tools/compress_ota.py
                "${PROJECT_NAME}" "${FW_BIN}" "${SHARED_FOLDER}"
            COMMENT "Compressing firmware with lz4 and copying to shared folder"
            VERBATIM
        )
    endif()
endif()