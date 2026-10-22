# SPDX-License-Identifier: GPL-2.0-or-later
file(MAKE_DIRECTORY "${WORK_DIR}/fixture/mods.d"
  "${WORK_DIR}/fixture/modules/texts/rawtext/buildfixture" "${WORK_DIR}/notes")
configure_file("${FIXTURE_DIR}/buildfixture.conf"
  "${WORK_DIR}/fixture/mods.d/buildfixture.conf" COPYONLY)
execute_process(COMMAND "${IMP2VS}" "${FIXTURE_DIR}/buildfixture.imp"
  -o "${WORK_DIR}/fixture/modules/texts/rawtext/buildfixture"
  RESULT_VARIABLE imported OUTPUT_VARIABLE import_output ERROR_VARIABLE import_error)
if(NOT imported EQUAL 0)
  message(FATAL_ERROR "Fixture import failed: ${import_output}${import_error}")
endif()
execute_process(COMMAND "${WORKFLOW_EXECUTABLE}" "${WORK_DIR}/fixture" "${WORK_DIR}/notes"
  RESULT_VARIABLE checked OUTPUT_VARIABLE check_output ERROR_VARIABLE check_error)
message("${check_output}")
if(NOT checked EQUAL 0)
  message(FATAL_ERROR "SWORD workflow check failed: ${check_error}")
endif()
