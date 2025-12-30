add_library(horusbinaryv3)
include_directories(.)
target_include_directories(horusbinaryv3 PUBLIC .)
AUX_SOURCE_DIRECTORY(. SUB_SOURCES)
target_sources(horusbinaryv3
  PRIVATE
    Telemetry.c
    ${SUB_SOURCES}

  # PUBLIC
  #   FILE_SET v3headers
  #   TYPE HEADERS
  #   BASE_DIRS
  #     ./
  #   FILES
  #     ./Telemetry.h
  #     ./AdditionalSensors.h
  #     ./AdditionalSensorType.h
  #     ./CustomFieldValues.h
)