# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: BSD-3-Clause

cmake_minimum_required(VERSION 3.16)
project(crupest-teapot LANGUAGES CXX)

set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Quick Quick3D)

qt_add_executable(crupest-teapot
    main.cpp
)

set_target_properties(crupest-teapot PROPERTIES
    WIN32_EXECUTABLE TRUE
    MACOSX_BUNDLE TRUE
)

target_link_libraries(crupest-teapot PUBLIC
    Qt::Core
    Qt::Gui
    Qt::Quick
    Qt::Quick3D
)

qt_add_qml_module(crupest-teapot
    URI Example
    VERSION 1.0
    QML_FILES main.qml
    RESOURCES teapot.mesh
    NO_RESOURCE_TARGET_PATH
)

install(TARGETS crupest-teapot)
