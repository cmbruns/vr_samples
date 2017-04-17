
import sys
import math
import ctypes

import numpy
import glfw
from OpenGL import GL
from OpenGL.GL.shaders import compileShader, compileProgram

def mat4x4_identity():
    return numpy.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
            ], dtype=numpy.float32)
    
def mat4x4_rotate_Z(matrix, angle):
    s = math.sin(angle)
    c = math.cos(angle)
    R = numpy.matrix([
            [c, s, 0, 0],
            [-s, c, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
            ], dtype=numpy.float32)
    return matrix * R

def mat4x4_ortho(l, r, b, t, n, f):
    M = mat4x4_identity()
    M[0,0] = 2.0/(r-l)
    M[0,1] = M[0,2] = M[0,3] = 0.0
    M[1,1] = 2.0/(t-b)
    M[1,0] = M[1,2] = M[1,3] = 0.0
    M[2,2] = -2.0/(f-n)
    M[2,0] = M[2,1] = M[2,3] = 0.0
    M[3,0] = -(r+l)/(r-l)
    M[3,1] = -(t+b)/(t-b)
    M[3,2] = -(f+n)/(f-n)
    M[3,3] = 1.0
    return M
    
def main():
    glfw.set_error_callback(error_callback)
    if not glfw.init():
        raise Exception("GLFW Initialization error")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 5)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    window = glfw.create_window(640, 480, "Triangle Viewer", None, None)
    if not window:
        glfw.terminate()
        raise RuntimeError("Failed to create glfw window")
    glfw.make_context_current(window)
    vao = GL.glGenVertexArrays(1)
    GL.glBindVertexArray(vao)
    glfw.swap_interval(1)
    vertex_buffer = GL.glGenBuffers(1)
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vertex_buffer)
    vertices = numpy.array([
            [ -0.6, -0.4, 1.0, 0.0, 0.0 ], # x, y, r, g, b
            [  0.6, -0.4, 0.0, 1.0, 0.0 ],
            [  0.0,  0.6, 0.0, 0.0, 1.0 ],
            ], dtype=numpy.float32)
    GL.glBufferData(GL.GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL.GL_STATIC_DRAW)
    vertex_shader = compileShader(
        """#version 450 core
        #line 50
        
        layout(location = 0) uniform mat4 MVP = mat4(1);
        
        layout(location = 0) in vec2 vPos;
        layout(location = 1) in vec3 vCol;
        
        out vec3 color;

        void main() 
        {
            gl_Position = MVP * vec4(vPos, 0.0, 1.0);
            color = vCol;
        }
        """,
        GL.GL_VERTEX_SHADER)
    fragment_shader = compileShader(
        """#version 450 core
        #line 68

        in vec3 color;
        out vec4 fragColor;

        void main() 
        {
            fragColor = vec4(color, 1);
        }
        """,
        GL.GL_FRAGMENT_SHADER)
    program = compileProgram(vertex_shader, fragment_shader)
    mvp_location = 0
    vpos_location = 0
    vcol_location = 1
    GL.glEnableVertexAttribArray(vpos_location);
    fsize = ctypes.sizeof(ctypes.c_float)
    GL.glVertexAttribPointer(vpos_location, 2, GL.GL_FLOAT, False,
                          fsize * 5, ctypes.cast(fsize*0, ctypes.c_void_p));
    GL.glEnableVertexAttribArray(vcol_location);
    GL.glVertexAttribPointer(vcol_location, 3, GL.GL_FLOAT, False,
                          fsize * 5, ctypes.cast(fsize*2, ctypes.c_void_p));
    while not glfw.window_should_close(window):
        width, height = glfw.get_framebuffer_size(window)
        ratio = width / float(height)
        glfw.make_context_current(window)
        GL.glViewport(0, 0, width, height)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        m = mat4x4_identity()
        m = mat4x4_rotate_Z(m, float(glfw.get_time()))
        p = mat4x4_ortho(-ratio, ratio, -1.0, 1.0, 1.0, -1.0)
        mvp = p * m
        GL.glUseProgram(program)
        GL.glUniformMatrix4fv(mvp_location, 1, True, numpy.ascontiguousarray(
                mvp, dtype=numpy.float32))
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 3)
        glfw.swap_buffers(window)
        glfw.poll_events()
    glfw.make_context_current(window)
    glfw.destroy_window(window)
    glfw.terminate()
    sys.exit(0)
    
def error_callback(self, description):
    raise RuntimeError(description)

if __name__ == "__main__":
    main()
