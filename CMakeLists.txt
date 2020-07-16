cmake_minimum_required(VERSION 3.0)
project(horus C)

include(GNUInstallDirs)
mark_as_advanced(CLEAR
    CMAKE_INSTALL_BINDIR
    CMAKE_INSTALL_INCLUDEDIR
    CMAKE_INSTALL_LIBDIR
)

#
# Prevent in-source builds
# If an in-source build is attempted, you will still need to clean up a few
# files manually.
#
set(CMAKE_DISABLE_SOURCE_CHANGES ON)
set(CMAKE_DISABLE_IN_SOURCE_BUILD ON)
if("${CMAKE_SOURCE_DIR}" STREQUAL "${CMAKE_BINARY_DIR}")
  message(FATAL_ERROR "In-source builds in ${CMAKE_BINARY_DIR} are not "
   "allowed, please remove ./CMakeCache.txt and ./CMakeFiles/, create a "
   "separate build directory and run cmake from there.")
endif("${CMAKE_SOURCE_DIR}" STREQUAL "${CMAKE_BINARY_DIR}")


# Set project version information. This should probably be done via external
# file at some point.
#
set(HORUS_VERSION_MAJOR 0)
set(HORUS_VERSION_MINOR 2)
# Set to patch level if needed, otherwise leave FALSE.
# Must be positive (non-zero) if set, since 0 == FALSE in CMake.
set(HORUS_VERSION_PATCH FALSE)
set(HORUS_VERSION "${HORUS_VERSION_MAJOR}.${HORUS_VERSION_MINOR}")
# Patch level version bumps should not change API/ABI.
set(SOVERSION "${HORUS_VERSION_MAJOR}.${HORUS_VERSION_MINOR}")
if(HORUS_VERSION_PATCH)
    set(HORUS_VERSION "${HORUS_VERSION}.${HORUS_VERSION_PATCH}")
endif()
message(STATUS "Horuslib version: ${HORUS_VERSION}")

# Set default flags
set(CMAKE_C_FLAGS "-Wall -Wextra -Wno-unused-function -Wno-strict-overflow -O3 -g -I. -MD ${CMAKE_C_FLAGS} -DENABLE_ASSERTIONS")

# Arch specific stuff here
message(STATUS "Host system arch is: ${CMAKE_SYSTEM_PROCESSOR}")


add_subdirectory(src)

# Ctests ----------------------------------------------------------------------

include(CTest)
enable_testing()

     add_test(NAME test_horus_binary
             COMMAND sh -c "cd ${CMAKE_CURRENT_BINARY_DIR}/src;
                            sox ${CMAKE_CURRENT_SOURCE_DIR}/samples/horus_binary_ebno_4.5db.wav -r 48000 -t raw - |
                            ./horus_demod -m binary - -"
              )
             set_tests_properties(test_horus_binary PROPERTIES PASS_REGULAR_EXPRESSION "1C9A9545")

     add_test(NAME test_horus_rtty_7n1
             COMMAND sh -c "cd ${CMAKE_CURRENT_BINARY_DIR}/src;
                            sox ${CMAKE_CURRENT_SOURCE_DIR}/samples/rtty_7n1.wav -r 48000 -t raw - |
                            ./horus_demod -c -m rtty7n1 - - | grep OK | wc -l"
              )
             set_tests_properties(test_horus_rtty_7n1 PROPERTIES PASS_REGULAR_EXPRESSION "3")

     add_test(NAME test_horus_rtty_7n2
             COMMAND sh -c "cd ${CMAKE_CURRENT_BINARY_DIR}/src;
                            sox ${CMAKE_CURRENT_SOURCE_DIR}/samples/rtty_7n2.wav -r 48000 -t raw - |
                            ./horus_demod -c -m rtty - - | grep OK | wc -l"
              )
             set_tests_properties(test_horus_rtty_7n2 PROPERTIES PASS_REGULAR_EXPRESSION "6")

     add_test(NAME test_horus_rtty_8n2
             COMMAND sh -c "cd ${CMAKE_CURRENT_BINARY_DIR}/src;
                            sox ${CMAKE_CURRENT_SOURCE_DIR}/samples/rtty_8n2.wav -r 48000 -t raw - |
                            ./horus_demod -c --rate=300 -m rtty8n2 - - | grep OK | wc -l"
              )
             set_tests_properties(test_horus_rtty_8n2 PROPERTIES PASS_REGULAR_EXPRESSION "4")

     add_test(NAME test_horus_binary_iq
             COMMAND sh -c "cd ${CMAKE_CURRENT_BINARY_DIR}/src;
                            cat ${CMAKE_CURRENT_SOURCE_DIR}/samples/horusb_iq_s16.raw | 
                            ./horus_demod -q -m binary --fsk_lower=1000 --fsk_upper=20000 - -"
             )
             set_tests_properties(test_horus_binary_iq PROPERTIES
             PASS_REGULAR_EXPRESSION "000900071E2A000000000000000000000000259A6B14")
    
     # Wenet - Using Mask estimator (Assuming ~120 kHz tone spacing)
     add_test(NAME test_wenet_mask
        COMMAND sh -c "cd ${CMAKE_CURRENT_BINARY_DIR}/src;
                       cat ${CMAKE_CURRENT_SOURCE_DIR}/samples/wenet_sample.c8 | 
                       ./fsk_demod --cu8 -s --mask=120000 2 921416 115177 - - |
                       ./drs232_ldpc - - 2>&1 | strings"
        )
        set_tests_properties(test_wenet_mask PROPERTIES
        PASS_REGULAR_EXPRESSION "packet_errors: 0 PER: 0.000")

     # Using regular frequency estimator, tell freq est to avoid first 100 kHz due to a DC line 
     add_test(NAME test_wenet_nomask
        COMMAND sh -c "cd ${CMAKE_CURRENT_BINARY_DIR}/src; 
                       cat ${CMAKE_CURRENT_SOURCE_DIR}/samples/wenet_sample.c8 | 
                       ./fsk_demod --cu8 -s --fsk_lower 100000 2 921416 115177 - - |
                       ./drs232_ldpc - - 2>&1 | strings"
        )
        set_tests_properties(test_wenet_nomask PROPERTIES
        PASS_REGULAR_EXPRESSION "packet_errors: 0 PER: 0.000")


