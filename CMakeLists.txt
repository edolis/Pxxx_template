cmake_minimum_required(VERSION 3.16)

set(SHARED_FOLDER "//raspi00/fware" CACHE STRING "Network share for OTA firmware")
set(EXTRA_COMPONENT_DIRS "${CMAKE_CURRENT_LIST_DIR}/components/toolbox")

# ----------------------------------------------------------------------
# Auto-detect project name from folder prefix (e.g., P029_kiln -> P029)
# ----------------------------------------------------------------------
get_filename_component(CURRENT_FOLDER_NAME ${CMAKE_CURRENT_SOURCE_DIR} NAME)
# Extract the part before the first underscore
string(REGEX REPLACE "^([^_]+).*" "\\1" PROJECT_PREFIX "${CURRENT_FOLDER_NAME}")
if(PROJECT_PREFIX MATCHES "^P[0-9x][0-9x][0-9x]")
    set(PROJECT_NAME "${PROJECT_PREFIX}")
    message(STATUS "Project name detected from folder prefix: ${PROJECT_NAME}")
else()
    set(PROJECT_NAME "my_esp_app")
    message(WARNING "Folder prefix '${PROJECT_PREFIX}' does not start with Pxxx. Using default: ${PROJECT_NAME}")
endif()

# ----------------------------------------------------------------------
# Certificate bundle handling
# ----------------------------------------------------------------------
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

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(${PROJECT_NAME})

# ----------------------------------------------------------------------
# Run Python script to inject version placeholders into main.cpp
# ----------------------------------------------------------------------
find_package(Python3 REQUIRED)

add_custom_target(
    inject_version_before_build
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tools/update_version_comment.py
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Injecting current git version into main.cpp"
    VERBATIM
)

# Make the final firmware target depend on the injection step
add_dependencies(${CMAKE_PROJECT_NAME}.elf inject_version_before_build)

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
        if(NOT PROJECT_VER_CACHE)
            set(PROJECT_VER_CACHE "v0.0.0-0")
        endif()
        string(REGEX REPLACE "[/\\\\]" "_" SAFE_VERSION "${PROJECT_VER_CACHE}")

        set(FW_BIN "${CMAKE_BINARY_DIR}/${PROJECT_NAME}.bin")
        set(COMPRESSED_FW "${CMAKE_BINARY_DIR}/${PROJECT_NAME}_${SAFE_VERSION}.bin.lz4")
        set(SHARED_FOLDER "${SHARED_FOLDER}")

        add_custom_command(
            TARGET gen_project_binary
            POST_BUILD
            COMMAND ${LZ4_EXECUTABLE} -9 --no-frame-crc -f ${FW_BIN} ${COMPRESSED_FW}
            COMMAND ${CMAKE_COMMAND} -E copy ${COMPRESSED_FW} ${SHARED_FOLDER}/
            COMMENT "LZ4 compressing OTA firmware as ${PROJECT_NAME}_${SAFE_VERSION}.bin.lz4"
            VERBATIM
        )
    endif()
endif()