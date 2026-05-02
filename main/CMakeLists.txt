# Git version detection
execute_process(COMMAND git describe --tags --long --dirty --always WORKING_DIRECTORY ${CMAKE_SOURCE_DIR} OUTPUT_VARIABLE GIT_DESCRIBE OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
execute_process(COMMAND git rev-parse HEAD WORKING_DIRECTORY ${CMAKE_SOURCE_DIR} OUTPUT_VARIABLE GIT_FULL_HASH OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)

if(NOT GIT_DESCRIBE)
    set(GIT_DESCRIBE "v0.0.0-0-g0000000-dirty")
    set(GIT_FULL_HASH "0000000000000000000000000000000000000000")
endif()

if(GIT_DESCRIBE MATCHES "^v([0-9.]+)-(.*)-(\\d+)-(g[0-9a-f]+)(-dirty)?$")
    string(REGEX REPLACE "^v([0-9.]+)-(.*)-(\\d+)-(g[0-9a-f]+)(-dirty)?$" "\\1" VERSION_BASE "${GIT_DESCRIBE}")
    string(REGEX REPLACE "^v([0-9.]+)-(.*)-(\\d+)-(g[0-9a-f]+)(-dirty)?$" "\\2" GIT_TAG "${GIT_DESCRIBE}")
    string(REGEX REPLACE "^v([0-9.]+)-(.*)-(\\d+)-(g[0-9a-f]+)(-dirty)?$" "\\3" COMMIT_COUNT "${GIT_DESCRIBE}")
    string(REGEX REPLACE "^v([0-9.]+)-(.*)-(\\d+)-(g[0-9a-f]+)(-dirty)?$" "\\4" GIT_SHORT_HASH "${GIT_DESCRIBE}")
    string(REGEX REPLACE "^v([0-9.]+)-(.*)-(\\d+)-(g[0-9a-f]+)(-dirty)?$" "\\5" DIRTY "${GIT_DESCRIBE}")
    if(DIRTY)
        set(VERSION_STRING "${VERSION_BASE}-${COMMIT_COUNT}-dirty")
    else()
        set(VERSION_STRING "${VERSION_BASE}-${COMMIT_COUNT}")
    endif()
else()
    set(VERSION_BASE "0.0.0")
    set(COMMIT_COUNT "0")
    set(GIT_TAG "untagged")
    string(REGEX REPLACE "^([a-f0-9]+)(-dirty)?$" "\\1" GIT_SHORT_HASH "${GIT_DESCRIBE}")
    string(REGEX REPLACE "^([a-f0-9]+)(-dirty)?$" "\\2" DIRTY "${GIT_DESCRIBE}")
    set(GIT_SHORT_HASH "g${GIT_SHORT_HASH}")
    if(DIRTY STREQUAL "-dirty")
        set(VERSION_STRING "v${VERSION_BASE}-${COMMIT_COUNT}-dirty")
    else()
        set(VERSION_STRING "v${VERSION_BASE}-${COMMIT_COUNT}")
    endif()
endif()

string(TIMESTAMP BUILD_TIMESTAMP "%Y%m%d-%H%M%S")
string(SUBSTRING "${GIT_SHORT_HASH}" 1 7 SHORT_HASH_NO_G)
set(BUILD_ID "P${BUILD_TIMESTAMP}-${SHORT_HASH_NO_G}")
set(PROJECT_VER_CACHE "${VERSION_STRING}" CACHE STRING "Firmware version string" FORCE)

# ----------------------------------------------------------------------
# OTA detection: enabled if the ED_OTA component is actually linked
# ----------------------------------------------------------------------
# The target __idf_ED_OTA is created only if ED_OTA is part of the build
# (directly or indirectly required)
if(TARGET __idf_ED_OTA)
    set(ENABLE_OTA 1)
    message(STATUS "OTA component is linked → LZ4 compression will run after build")
else()
    set(ENABLE_OTA 0)
    message(STATUS "OTA component not linked → skipping post‑build steps")
endif()

configure_file(${CMAKE_CURRENT_LIST_DIR}/version.h.in ${CMAKE_CURRENT_BINARY_DIR}/version.h @ONLY)

idf_component_register(SRCS "main.cpp" "$ENV{ESP_HEADERS}/x509_crt_bundle.S" INCLUDE_DIRS "." ${CMAKE_CURRENT_BINARY_DIR}
 REQUIRES ED_WIFI ED_MQTT diag ED_S_JSON)

target_compile_definitions(${COMPONENT_TARGET} PRIVATE ENABLE_OTA=${ENABLE_OTA})