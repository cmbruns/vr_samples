#!/bin/env python

import unittest

import glfw
from OpenGL import GL
from PIL import Image
import numpy

def images_are_identical(img1, img2):
    ar1 = numpy.array(img1.convert('RGBA'))
    ar2 = numpy.array(img2.convert('RGBA'))
    return numpy.array_equiv(ar1, ar2)


class TestGLRendering(unittest.TestCase):
    def test_red_render(self):
        'Test minimal screen clear in OpenGL'
        if not glfw.init():
            raise Exception("GLFW Initialization error")
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.VISIBLE, False) # Hidden window is next best thing to offscreen
        window = glfw.create_window(16, 16, "Little test window", None, None)
        if window is None:
            glfw.terminate()
            raise Exception("GLFW window creation error")
        glfw.make_context_current(window)
        # TODO: draw scene
        GL.glClearColor(1, 0, 0, 1) # red
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        # Save render as image
        GL.glFlush()
        data = GL.glReadPixels(0, 0, 16, 16, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
        glfw.terminate()
        # Compare to expected image
        observed = Image.frombytes('RGBA', (16, 16), data)
        with open('../images/red16x16.png', 'rb') as fh:
            expected = Image.open(fh)
            expected.load()
        self.assertTrue(images_are_identical(observed, expected))
        print ("Red GL test completed")


if __name__ == '__main__':
    unittest.main()
