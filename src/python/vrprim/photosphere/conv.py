"""
Convert spherical panorama in equirectangular format into cubemap format
"""

import math

import numpy
from libtiff import TIFF
import png
import glfw
from OpenGL import GL
from OpenGL.GL import shaders
from OpenGL.GL.EXT.texture_filter_anisotropic import *

class Converter(object):
    def render_scene(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glUseProgram(self.shader)
        equirect_loc = GL.glGetUniformLocation(self.shader, "equirect")
        GL.glUniform1i(equirect_loc, 0)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)

    def cube_from_equirect(self, arr):
        """
        Use OpenGL to efficiently warp an equirectangular image into
        a single cubemap image
        """
        # Set up glfw
        eh = arr.shape[0]
        ew = arr.shape[1]
        print(ew, eh)
        # Cubemap has same width, and height *  1.5, right? todo:
        # scale = 4.0 / math.pi # so cube face center resolution matches equirectangular equator resolution
        scale = 1.0
        # scale *= 1.0 / 8.0 # smaller for faster testing
        cw = int(scale * ew)
        ch = int(scale * eh * 1.50)
        print(cw, ch)
        glfw.init()
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 5)
        # glfw.window_hint(glfw.VISIBLE, False)
        w = glfw.create_window(cw, ch, "Cubemap", None, None)
        # Create a framebuffer and render cube_color_texture
        glfw.make_context_current(w)
        vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(vao)
        fb = GL.glGenFramebuffers(1)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, fb)
        cube_color_tex = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, cube_color_tex)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA16, cw, ch, 0, GL.GL_RGBA, GL.GL_UNSIGNED_SHORT, None)
        GL.glFramebufferTexture(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, cube_color_tex, 0)
        GL.glDrawBuffers([GL.GL_COLOR_ATTACHMENT0,])
        if GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) != GL.GL_FRAMEBUFFER_COMPLETE:
            raise "Incomplete framebuffer"
        else:
            print("Framebuffer OK")
        # Create shader program
        vtx = shaders.compileShader("""#version 450
            #line 62

            out vec2 tex_coord;

            const vec4 SCREEN_QUAD[4] = vec4[4](
                vec4(-1, -1, 0.5, 1),
                vec4( 1, -1, 0.5, 1),
                vec4(-1,  1, 0.5, 1),
                vec4( 1,  1, 0.5, 1));

            void main() {
                vec4 c = SCREEN_QUAD[gl_VertexID]; // corner location
                gl_Position = c;
                tex_coord = 0.5 * (c.xy + vec2(1));
            }
            """, GL.GL_VERTEX_SHADER)
        frg = shaders.compileShader("""#version 450
            #line 79

            layout(binding=0) uniform sampler2D equirect;

            in vec2 tex_coord;
            out vec4 frag_color;

            const float PI = 3.14159265359;

            vec3 xyz_from_equirect(in vec2 eq) {
                vec2 c = 2*eq - vec2(1); // centered
                float lon = PI * c.x;
                float lat = -0.5 * PI * c.y;
                float s = cos(lat);
                return vec3(s*sin(lon), sin(lat), -s*cos(lon));
            }

            vec2 equirect_from_xyz(in vec3 xyz) {
                float r = length(xyz.xz);
                float lat = atan(xyz.y, r);
                float lon = atan(xyz.x, -xyz.z);
                return 0.5 * (vec2(lon / PI, -2.0 * lat / PI) + vec2(1));
            }

            vec3 xyz_from_cube(in vec2 cube) {
                if (cube.y > 2.0/3.0) { // lower strip
                    if (cube.x < 1.0/4.0) {
                        discard;
                    }
                    else if (cube.x > 2.0/4.0) {
                        discard;
                    }
                    else {
                        vec2 xy = (cube - vec2(3.0/8.0, 5.0/6.0)) * vec2(8, -6);
                        return normalize(vec3(xy.x, -1, -xy.y)); // bottom
                    }
                }
                else if (cube.y < 1.0/3.0) { // upper strip
                    if (cube.x < 1.0/4.0) {
                        discard;
                    }
                    else if (cube.x > 2.0/4.0) {
                        discard;
                    }
                    else { // top
                        vec2 xy = (cube - vec2(3.0/8.0, 1.0/6.0)) * vec2(8, -6);
                        return normalize(vec3(xy.x, 1, xy.y));
                    }
                }
                else { // central strip
                    if (cube.x < 0.25) {
                        vec2 xy = (cube - vec2(1.0/8.0, 0.5)) * vec2(8, -6);
                        return normalize(vec3(-1, xy.y, -xy.x)); // left
                    }
                    else if (cube.x < 0.50) { // front
                        vec2 xy = (cube - vec2(3.0/8.0, 0.5)) * vec2(8, -6);
                        return normalize(vec3(xy.x, xy.y, -1));
                    }
                    else if (cube.x < 0.75) { // right
                        vec2 xy = (cube - vec2(5.0/8.0, 0.5)) * vec2(8, -6);
                        return normalize(vec3(1, xy.y, xy.x));
                    }
                    else { // back
                        vec2 xy = (cube - vec2(7.0/8.0, 0.5)) * vec2(8, -6);
                        return normalize(vec3(-xy.x, xy.y, 1));
                    }
                }
            }

            void main() {
                vec3 xyz = xyz_from_cube(tex_coord);
                vec2 eq = equirect_from_xyz(xyz);

                // Use explicit level of detail to avoid seam at z==1, lon==PI
                // Use explicit gradients, to preseve anisotropic filtering during mipmap lookup
                vec2 dpdx = dFdx(eq);
                if (dpdx.x > 0.5) dpdx.x -= 1; // use "repeat" wrapping on gradient
                if (dpdx.x < -0.5) dpdx.x += 1;
                vec2 dpdy = dFdy(eq);
                frag_color = 50 * textureGrad(equirect, eq, dpdx, dpdy);

                // frag_color = vec4(eq, 0.5, 1);
                // frag_color = vec4(xyz, 1);
                // frag_color = vec4(tex_coord, 1, 1);
                // frag_color = vec4(xyz_from_equirect(tex_coord), 1);
            }
            """, GL.GL_FRAGMENT_SHADER)
        self.shader = shaders.compileProgram(vtx, frg)
        # Bind the input equirectangular image
        equi_tex = GL.glGenTextures(1)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, equi_tex)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB16, ew, eh, 0, GL.GL_RGB, GL.GL_UNSIGNED_SHORT, arr)
        aniso = GL.glGetFloatv(GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, aniso)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT);
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_MIRRORED_REPEAT);
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR);
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR_MIPMAP_LINEAR);
        GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
        # init
        GL.glDisable(GL.GL_BLEND)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glViewport(0, 0, cw, ch)
        GL.glClearColor(0.5, 0.5, 0.5, 0.0)
        # Render the image
        bToScreen = False
        if bToScreen:
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
            # while not glfw.window_should_close(w):
            for f in range(100):
                self.render_scene()
                glfw.swap_buffers(w)
        else:
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, fb)
            self.render_scene()
            GL.glFinish()
        # fetch the rendered image
        result = numpy.zeros(shape=(ch, cw, 4), dtype='uint16')
        GL.glReadPixels(0, 0, cw, ch, GL.GL_RGBA, GL.GL_UNSIGNED_SHORT, result)
        print(cw, ch)
        print(result.shape)
        # print(result.shape)
        # clean up
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        GL.glDeleteTextures([cube_color_tex,])
        GL.glDeleteFramebuffers([fb,])
        glfw.destroy_window(w)
        glfw.terminate()
        # raise NotImplementedError()
        return result

def to_cube(arr):
    w = arr.shape[0]
    h = arr.shape[1]
    aspect = w / h
    if aspect == 2:
        return Converter().cube_from_equirect(arr)
    raise NotImplementedError()

def main():
    tif = TIFF.open('1w180.9.tiff', 'r')
    arr = tif.read_image()
    tif.close()
    fmin = numpy.amin(arr[numpy.nonzero(arr)])
    # Clip data to percentile range with dynamic range below 65535
    pct_low = 0
    pct_high = 100
    val_low, val_high = numpy.percentile(arr[numpy.nonzero(arr)], [pct_low, pct_high])
    dynamic_range = val_high / val_low
    eps = 0.07
    while dynamic_range > 65535:
        pct_low = eps
        pct_high = 100.0 - eps
        val_low, val_high = numpy.percentile(arr[numpy.nonzero(arr)], [pct_low, pct_high])
        dynamic_range = val_high / val_low
        print(pct_low, pct_high, val_low, val_high, dynamic_range)
        eps *= 1.2
    arr *= 65535.0 / val_high
    arr[arr>65535] = 65535
    arr[arr<0] = 0
    print(numpy.histogram(arr))
    arr = arr.astype('uint16')
    #
    cube = Converter().cube_from_equirect(arr)
    print(cube.shape)
    # This is the slow part
    save_png = True
    if save_png:
        img = png.from_array(cube, 'RGBA')
        img.save('cube.png')

    print(arr.shape, arr.dtype)
    # print(arr)
    print(numpy.amin(arr))
    fmax = numpy.amax(arr)
    print(fmax)
    # Convert to 16-bit uint
    arr2 = arr * 65535.99/fmax
    arr2 = arr2.astype('uint16')
    # print(numpy.amax(arr2))
    # todo: Append an alpha channel

    # img = png.from_array(arr2, 'RGB')
    # img.save('test2.png')

main()
