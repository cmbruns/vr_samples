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

    def cube_from_equirect(self, arr0):
        """
        Use OpenGL to efficiently warp an equirectangular image into
        a single cubemap image
        """
        # Convert to 16-bit uint
        fmax = numpy.amax(arr0)
        fmin = numpy.amin(arr0)
        print(fmin, fmax)
        arr = arr0 * 65535.99/fmax
        arr = arr.astype('uint16')
        # Set up glfw
        eh = arr.shape[0]
        ew = arr.shape[1]
        print(ew, eh)
        # Cubemap has same width, and height *  1.5, right? todo:
        scale = 4.0 / math.pi # so cube face center resolution matches equirectangular equator resolution
        scale *= 1.0 / 8.0 # smaller for faster testing
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
            #line 54

            out vec2 tex_coord;

            const vec4 SCREEN_QUAD[4] = vec4[4](
                vec4(-1, -1, 0.5, 1),
                vec4( 1, -1, 0.5, 1),
                vec4(-1,  1, 0.5, 1),
                vec4( 1,  1, 0.5, 1));

            void main() {
                vec4 c = SCREEN_QUAD[gl_VertexID]; // corner location
                gl_Position = c;
                tex_coord = 0.5 * (c.xy + vec2(1, 1));
            }
            """, GL.GL_VERTEX_SHADER)
        frg = shaders.compileShader("""#version 450
            #line 70

            layout(binding=0) uniform sampler2D equirect;

            in vec2 tex_coord;
            out vec4 frag_color;

            void main() {
                // frag_color = vec4(0, 0, 1, 1);
                frag_color = texture(equirect, tex_coord);
                // frag_color = vec4(tex_coord, 1, 1);
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
        GL.glClearColor(0, 1, 0, 1)
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
    # Convert to 16-bit uint
    arr2 = arr * 65535.99/fmax
    arr2 = arr2.astype('uint16')
    # print(numpy.amax(arr2))
    # todo: Append an alpha channel

    # img = png.from_array(arr2, 'RGB')
    # img.save('test2.png')

main()
