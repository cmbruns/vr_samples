#!/bin/env python

import unittest

import glfw
from OpenGL import GL
from PIL import Image
import numpy

from vrprim.imposter import sphere

def images_are_identical(img1, img2):
    ar1 = numpy.array(img1.convert('RGBA'))
    ar2 = numpy.array(img2.convert('RGBA'))
    return numpy.array_equiv(ar1, ar2)


class TestGLRendering(unittest.TestCase):
    def setUp(self):
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
        with open('../images/red16x16.png', 'rb') as fh:
            self.red_image = Image.open(fh)
            self.red_image.load()
        
    def tearDown(self):
        glfw.terminate()                
        
    def test_sphere_imposter(self):
        GL.glClearColor(1, 0, 0, 1) # red
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        s = sphere.SphereActor()
        s.init_gl()
        s.display_gl(None)
        s.dispose_gl()
        # Save render as image
        GL.glFlush()
        data = GL.glReadPixels(0, 0, 16, 16, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
        observed = Image.frombytes('RGBA', (16, 16), data)
        observed.save("test.png")
        self.assertFalse(images_are_identical(observed, self.red_image))

    def test_red_render(self):
        'Test minimal screen clear in OpenGL'
        # Color the entire display red
        GL.glClearColor(1, 0, 0, 1) # red
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        # Save render as image
        GL.glFlush()
        data = GL.glReadPixels(0, 0, 16, 16, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
        observed = Image.frombytes('RGBA', (16, 16), data)
        expected = self.red_image
        self.assertTrue(images_are_identical(observed, expected))
        print ("Red GL test completed")
        

if __name__ == '__main__':
    unittest.main()
