#!/bin/env python

# Example program for viewing a 360 photosphere in a virtual reality headset
# using parallax shifting to place the ground plane on the floor

import os
from textwrap import dedent

import numpy
from OpenGL import GL
from OpenGL.GL.shaders import compileShader, compileProgram
try:
    from PIL import Image
except ImportError:
    import Image

from openvr.glframework.glfw_app import GlfwApp
from openvr.gl_renderer import OpenVrGlRenderer


class SphericalPanorama(object):
    def __init__(self, image):
        self.image = image
        self.shader = None
        self.vao = None
        self.texture_handle = None

    def init_gl(self):
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        # Set up photosphere image texture for OpenGL
        self.texture_handle = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture_handle);
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR);
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR);
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT);
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_MIRRORED_REPEAT);
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 
                     0, 
                     GL.GL_RGB8, 
                     self.image.shape[1], # width 
                     self.image.shape[0], # height
                     0,
                     GL.GL_RGB, 
                     GL.GL_UNSIGNED_BYTE, 
                     self.image);
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0);
        # Set up shaders for rendering
        vertex_shader = compileShader(dedent(
                """#version 450 core
                #line 52
                
                layout(location = 1) uniform mat4 projection = mat4(1);
                layout(location = 2) uniform mat4 model_view = mat4(1);

                out vec3 viewDir;
                out vec3 camPos;
                
                // projected screen quad
                const vec4 SCREEN_QUAD[4] = vec4[4](
                    vec4(-1, -1, 1, 1),
                    vec4( 1, -1, 1, 1),
                    vec4( 1,  1, 1, 1),
                    vec4(-1,  1, 1, 1));
                
                const int TRIANGLE_STRIP_INDICES[4] = int[4](
                    0, 1, 3, 2);
                
                void main() 
                {
                    int vertexIndex = TRIANGLE_STRIP_INDICES[gl_VertexID];
                    gl_Position = vec4(SCREEN_QUAD[vertexIndex]);
                    mat4 xyzFromNdc = inverse(projection * model_view);
                    vec4 campos4 = xyzFromNdc * vec4(0, 0, 0, 1);
                    vec4 vpos = xyzFromNdc * SCREEN_QUAD[vertexIndex];
                    camPos = campos4.xyz /campos4.w;
                    viewDir = vpos.xyz/vpos.w - camPos;
                }
                """),
                GL.GL_VERTEX_SHADER)
        fragment_shader = compileShader(dedent(
                """#version 450 core
                #line 84
                
                const vec3 original_cam_pos = vec3(0, 2.0, 0);
                const float floor_level = -0.40;
                const vec4 ground_plane = vec4(0, 1, 0, -floor_level);
        
                layout(binding = 0) uniform sampler2D image;
                
                in vec3 viewDir;
                in vec3 camPos;
        
                out vec4 pixelColor;
                
                const float PI = 3.1415926535897932384626433832795;
                
                // this function abstracts away equirectangular vs cubemap fetch
                vec4 color_for_original_direction(in vec3 d) {
                    float longitude = 0.5 * atan(d.z, d.x) / PI + 0.5; // range [0-1]
                    float r = length(d.xz);
                    float latitude = -atan(d.y, r) / PI + 0.5; // range [0-1]
                    return texture(image, vec2(longitude, latitude));
                }

                vec3 intersect_plane(vec3 ray_point, vec3 ray_direction, vec4 plane) {
                    // intersection of view direction and plane
                    // http://math.stackexchange.com/questions/400268/equation-for-a-line-through-a-plane-in-homogeneous-coordinates
                    const vec3 w = plane.xyz;
                    const float e = plane.w;
                    vec3 l = ray_direction;
                    vec3 m = cross(ray_point, l);
                    // r is the point on the floor we are looking at
                    vec3 r = (cross(w, m) - e*l) / dot(w,l);
                    return r;
                }
                
                // intersect_proxy_geometry() will change depending on nature of proxy geometry
                vec3 intersect_proxy_geometry(vec3 ray_point, vec3 ray_direction) 
                {
                    return intersect_plane(ray_point, ray_direction, ground_plane);
                }
                
                vec4 color_for_direction(in vec3 d) {
                    if (d.y < 0) {
                        // below the horizon, shift parallax to infinite plane at finite distance
                        vec3 r = intersect_proxy_geometry(camPos, viewDir);
                        vec3 dir2 = r - original_cam_pos;
                        return color_for_original_direction(dir2);
                    }
                    else {
                        // above the horizon, view to infinity in all directions
                        return color_for_original_direction(d);
                    }
                }
                
                void main() 
                {
                    pixelColor = color_for_direction(viewDir);
                }
                """),
                GL.GL_FRAGMENT_SHADER)
        self.shader = compileProgram(vertex_shader, fragment_shader)

    def display_gl(self, modelview, projection):
        GL.glBindVertexArray(self.vao)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture_handle)
        GL.glUseProgram(self.shader)
        GL.glUniformMatrix4fv(1, 1, False, projection)
        GL.glUniformMatrix4fv(2, 1, False, modelview)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)

    def dispose_gl(self):
        GL.glDeleteTextures([self.texture_handle,])
        if self.shader is not None:
            GL.glDeleteProgram(self.shader)
        GL.glDeleteVertexArrays(1, [self.vao,])


if __name__ == "__main__":
    # Open equirectangular photosphere
    src_folder = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(src_folder, '../../assets/images/_0010782_stitch2.jpg')
    img = Image.open(img_path)
    arr = numpy.array(img)
    actor = SphericalPanorama(arr)
    renderer = OpenVrGlRenderer(actor)
    with GlfwApp(renderer, "parallax shifted photosphere test") as glfwApp:
        glfwApp.run_loop()

