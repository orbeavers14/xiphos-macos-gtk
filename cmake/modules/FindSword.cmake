# SPDX-License-Identifier: GPL-2.0-or-later
# Homebrew's SWORD package has headers/dylib but no sword.pc.
find_path(Sword_INCLUDE_DIR swversion.h PATH_SUFFIXES sword)
find_library(Sword_LIBRARY NAMES sword)
if(Sword_INCLUDE_DIR)
  file(STRINGS "${Sword_INCLUDE_DIR}/swversion.h" _sword_version_line
    REGEX "^#define SWORD_VERSION_STR ")
  string(REGEX MATCH "[0-9]+\\.[0-9]+\\.[0-9]+" Sword_VERSION "${_sword_version_line}")
endif()
include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(Sword
  REQUIRED_VARS Sword_INCLUDE_DIR Sword_LIBRARY VERSION_VAR Sword_VERSION)
if(Sword_FOUND AND NOT TARGET PkgConfig::Sword)
  add_library(PkgConfig::Sword INTERFACE IMPORTED)
  set_target_properties(PkgConfig::Sword PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${Sword_INCLUDE_DIR}"
    INTERFACE_LINK_LIBRARIES "${Sword_LIBRARY}")
endif()
mark_as_advanced(Sword_INCLUDE_DIR Sword_LIBRARY)
