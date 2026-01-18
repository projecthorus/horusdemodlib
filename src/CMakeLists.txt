include_directories(${CMAKE_CURRENT_SOURCE_DIR})

set(horus_srcs
  fsk.c
  kiss_fft.c
  kiss_fftr.c
  mpdecode_core.c
  H_256_768_22.c
  H_128_384_23.c
  golay23.c
  phi0.c
  horus_api.c
  horus_l2.c
)

add_library(horus SHARED ${horus_srcs})
target_link_libraries(horus m)
set_target_properties(horus PROPERTIES
    PUBLIC_HEADER horus_api.h
)
target_include_directories(horus INTERFACE
    $<INSTALL_INTERFACE:include/horus>
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
)
install(TARGETS horus EXPORT horus-config
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/horus
)


install(EXPORT horus-config
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/horus
)
# Export libhab target for import into build trees of other projects.
export(TARGETS horus
    FILE ${CMAKE_BINARY_DIR}/horus.cmake
)

add_executable(fsk_mod fsk_mod.c)
target_link_libraries(fsk_mod m horus ${CMAKE_REQUIRED_LIBRARIES})

add_executable(fsk_demod fsk_demod.c modem_probe.c octave.c)
target_link_libraries(fsk_demod m horus ${CMAKE_REQUIRED_LIBRARIES})

add_executable(fsk_get_test_bits fsk_get_test_bits.c)
target_link_libraries(fsk_get_test_bits)

add_executable(fsk_put_test_bits fsk_put_test_bits.c)
target_link_libraries(fsk_put_test_bits ${CMAKE_REQUIRED_LIBRARIES})


add_definitions(-DINTERLEAVER -DSCRAMBLER -DRUN_TIME_TABLES)
add_executable(horus_gen_test_bits horus_gen_test_bits.c horus_l2.c)
target_link_libraries(horus_gen_test_bits m horus horusbinaryv3)

add_definitions(-DHORUS_L2_RX -DINTERLEAVER -DSCRAMBLER -DRUN_TIME_TABLES)
add_executable(horus_demod horus_demod.c horus_api.c horus_l2.c golay23.c fsk.c kiss_fft.c)
target_link_libraries(horus_demod m horus ${CMAKE_REQUIRED_LIBRARIES})

install(TARGETS fsk_mod fsk_demod fsk_get_test_bits fsk_put_test_bits horus_gen_test_bits horus_demod DESTINATION bin)

