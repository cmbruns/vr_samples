#!/bin/env python

import sys

from OpenGL.GL import * # @UnusedWildImport # this comment squelches IDE warnings

import openvr
from openvr.glframework.glfw_app import GlfwApp
from openvr.gl_renderer import OpenVrGlRenderer

class SphericalPanorama(object):
    def __init__(self):
        pass

    def init_gl(self):
        pass

    def display_gl(self, modelview, projection):
        glClearColor(1, 0.9, 0.9, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def dispose_gl(self):
        pass

print ("Hello")

actor = SphericalPanorama()
renderer = OpenVrGlRenderer(actor)
with GlfwApp(renderer, "glfw OpenVR color cube") as glfwApp:
    glfwApp.run_loop()

