# SPDX-License-Identifier: GPL-2.0-or-later
cmake_minimum_required(VERSION 3.18)
project(xiphos_macos_smoke C CXX OBJC)
if(NOT APPLE)
  message(FATAL_ERROR "Run these checks on macOS")
endif()
get_filename_component(XIPHOS_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../.." ABSOLUTE)
list(APPEND CMAKE_MODULE_PATH "${XIPHOS_SOURCE_DIR}/cmake/modules")
include("${XIPHOS_SOURCE_DIR}/cmake/XiphosFlags.cmake")
find_package(PkgConfig REQUIRED)
pkg_check_modules(GTK REQUIRED IMPORTED_TARGET gtk+-3.0)
find_package(Sword 1.8.1 REQUIRED)
find_package(Biblesync REQUIRED)
find_package(Intl REQUIRED)
find_library(AVFOUNDATION_FRAMEWORK AVFoundation REQUIRED)
  find_library(FOUNDATION_FRAMEWORK Foundation REQUIRED)
enable_testing()
add_executable(dependencies dependencies.cc)
target_include_directories(dependencies PRIVATE ${Intl_INCLUDE_DIRS})
target_link_libraries(dependencies PRIVATE PkgConfig::GTK PkgConfig::Sword PkgConfig::Biblesync ${Intl_LIBRARIES})
add_test(NAME dependencies COMMAND dependencies)
add_executable(speech speech.c "${XIPHOS_SOURCE_DIR}/src/gtk/macos_tts.m")
target_include_directories(speech PRIVATE "${XIPHOS_SOURCE_DIR}/src/gtk")
set_source_files_properties("${XIPHOS_SOURCE_DIR}/src/gtk/macos_tts.m" PROPERTIES COMPILE_OPTIONS "-fno-objc-arc")
target_link_libraries(speech PRIVATE ${AVFOUNDATION_FRAMEWORK} ${FOUNDATION_FRAMEWORK})
add_test(NAME speech-invalid-input COMMAND speech)

find_program(IMP2VS NAMES imp2vs REQUIRED)
add_executable(sword_workflows sword_workflows.cc)
target_link_libraries(sword_workflows PRIVATE PkgConfig::Sword)
add_test(NAME sword-workflows COMMAND ${CMAKE_COMMAND}
  -DIMP2VS=${IMP2VS}
  -DFIXTURE_DIR=${CMAKE_CURRENT_SOURCE_DIR}/fixtures
  -DWORKFLOW_EXECUTABLE=$<TARGET_FILE:sword_workflows>
  -DWORK_DIR=${CMAKE_CURRENT_BINARY_DIR}/workflow-test
  -P ${CMAKE_CURRENT_SOURCE_DIR}/run-workflows.cmake)

set(XIPHOS_TEST_APP "" CACHE FILEPATH "Optional full Xiphos executable for D-Bus integration test")
set(XIPHOS_TEST_DISPLAY ":99" CACHE STRING "Already-running isolated X display for integration test")
if(XIPHOS_TEST_APP)
  find_package(Python3 COMPONENTS Interpreter REQUIRED)
  add_test(NAME xiphos-dbus-navigation COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/navigation.py
    --app ${XIPHOS_TEST_APP}
    --profile ${CMAKE_CURRENT_BINARY_DIR}/navigation-profile
    --display ${XIPHOS_TEST_DISPLAY})
  set_tests_properties(xiphos-dbus-navigation PROPERTIES TIMEOUT 120)
endif()
