add_library(horusbinaryv3)
include_directories(.)
target_compile_definitions(horusbinaryv3 PUBLIC ASN_DISABLE_OER_SUPPORT=1)
target_include_directories(horusbinaryv3 PUBLIC .)
AUX_SOURCE_DIRECTORY(. SUB_SOURCES)
target_sources(horusbinaryv3
  PRIVATE
    Telemetry.c
    ${SUB_SOURCES}
)