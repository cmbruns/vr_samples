#!/bin/env python

import sys
import os
from textwrap import dedent

import numpy
import Image
from OpenGL.GL import * # @UnusedWildImport # this comment squelches IDE warnings
from OpenGL.GL.shaders import compileShader, compileProgram
import glfw

import openvr
from openvr.glframework.glfw_app import GlfwApp
from openvr.gl_renderer import OpenVrGlRenderer

class SphericalPanorama(object):
    def __init__(self, image):
        self.image = image
        print (self.image.shape)
        print (self.image.dtype)

    def init_gl(self):
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        # Set up photosphere image texture for OpenGL
        self.texture_handle = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_handle);
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_MIRRORED_REPEAT);
        glTexImage2D(GL_TEXTURE_2D, 
                     0, 
                     GL_RGB8, 
                     self.image.shape[1], # width 
                     self.image.shape[0], # height
                     0,
                     GL_RGB, 
                     GL_UNSIGNED_BYTE, 
                     self.image);
        glBindTexture(GL_TEXTURE_2D, 0);
        # Set up shaders for rendering
        vertex_shader = compileShader(dedent(
                """\
                #version 450 core
                #line 44
                
                out vec2 fragTexCoord;
                
                // projected screen quad
                const vec4 SCREEN_QUAD[4] = vec4[4](
                    vec4(-1, -1, 0.5, 1),
                    vec4( 1, -1, 0.5, 1),
                    vec4( 1,  1, 0.5, 1),
                    vec4(-1,  1, 0.5, 1));
                
                const vec2 TEX_COORD[4] = vec2[4](
                    vec2(0, 1),
                    vec2(1, 1),
                    vec2(1, 0),
                    vec2(0, 0));
                
                const int TRIANGLE_STRIP_INDICES[4] = int[4](
                    0, 1, 3, 2);
                
                void main() {
                    int vertexIndex = TRIANGLE_STRIP_INDICES[gl_VertexID];
                    gl_Position = vec4(SCREEN_QUAD[vertexIndex]);
                    fragTexCoord = vec2(TEX_COORD[vertexIndex]);
                }
                """),
                GL_VERTEX_SHADER)
        fragment_shader = compileShader(dedent(
                """\
                #version 450 core
                #line 74
        
                layout(binding = 0) uniform sampler2D image;
        
                in vec2 fragTexCoord;
        
                out vec4 pixelColor;
                
                void main() 
                {
                    pixelColor = 
                            texture(image, fragTexCoord);
                            // vec4(1, 0, 1, 1);
                }
                """),
                GL_FRAGMENT_SHADER)
        self.shader = compileProgram(vertex_shader, fragment_shader)

    def display_gl(self, modelview, projection):
        glClearColor(1, 0.9, 0.9, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        #
        glBindVertexArray(self.vao)
        glBindTexture(GL_TEXTURE_2D, self.texture_handle)
        glUseProgram(self.shader)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    def dispose_gl(self):
        glDeleteTextures([self.texture_handle,])
        glDeleteProgram(self.shader)
        glDeleteVertexArrays(1, [self.vao,])


if __name__ == "__main__":
    # Open equirectangular photosphere
    src_folder = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(src_folder, '../../../assets/images/_0010782_stitch2.jpg')
    img = Image.open(img_path)
    arr = numpy.array(img)
    actor = SphericalPanorama(arr)
    renderer = OpenVrGlRenderer(actor)
    with GlfwApp(renderer, "glfw OpenVR color cube") as glfwApp:
        glfwApp.run_loop()

