import textwrap

import numpy
from OpenGL import GL
from OpenGL.GL.shaders import compileShader, compileProgram
from OpenGL.arrays.vbo import VBO
import glfw

class TriangleViewer(object):
    def __init__(self):
        self.size = (640, 480)
        self.is_dragging = False
    
    def __enter__(self):
        if not glfw.init():
            raise Exception("GLFW Initialization error")
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 5)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        self.window = glfw.create_window(self.size[0], self.size[1], "Little test window", None, None)
        if self.window is None:
            glfw.terminate()
            raise Exception("GLFW window creation error")
        glfw.set_key_callback(self.window, self.key_callback)
        glfw.set_cursor_pos_callback(self.window, self.mouse_pos_callback)
        glfw.set_mouse_button_callback(self.window, self.mouse_button_callback)
        glfw.make_context_current(self.window)
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        GL.glClearColor(0, 0, 1, 1)
        self.program = compileProgram(
                compileShader(textwrap.dedent('''\
                    #version 450 core
                    layout(location = 1) in vec3 pos;
                    layout(location = 1) uniform mat4 view_matrix = mat4(1);
                    void main() {
                        gl_Position = view_matrix * vec4(pos, 1);
                    }
                    '''), GL.GL_VERTEX_SHADER),
                compileShader(textwrap.dedent('''\
                    #version 450 core
                    out vec4 frag_color;
                    void main() {
                        frag_color = vec4(0.4, 0.4, 0.4, 1.0);
                    }
                    '''), GL.GL_FRAGMENT_SHADER))
        GL.glUseProgram(self.program)
        self.vbo = VBO(numpy.array([
                [0.0, 0.0, 0],
                [0.2, 0.0, 0],
                [0.0, 0.5, 0]], 'f'))
        self.vbo.bind()
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, False, 0, None)
        while not glfw.window_should_close(self.window):
            self.render_scene()
        
    def __exit__(self, a, b, c):
        GL.glDeleteProgram(self.program)
        self.vbo.delete()
        GL.glDeleteVertexArrays(1, [self.vao,])
        glfw.terminate()

    def key_callback(self, window, key, scancode, action, mods):
        "press ESCAPE to quit the application"
        if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            glfw.set_window_should_close(window, True)
    
    def mouse_pos_callback(self, window, xpos, ypos):
        if not self.is_dragging:
            return
        dx = xpos - self.mouse_pos[0]
        dy = ypos - self.mouse_pos[1]
        self.mouse_pos = (xpos, ypos)
        # print(dx, dy)
    
    def mouse_button_callback(self, window, button, action, mods):
        if button != glfw.MOUSE_BUTTON_LEFT:
            return
        if action == glfw.PRESS:
            self.is_dragging = True
            self.mouse_pos = glfw.get_cursor_pos(self.window)
        elif action == glfw.RELEASE:
            self.is_dragging = False
        
    def render_scene(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 3);
        glfw.swap_buffers(self.window)
        glfw.poll_events()


if __name__ == '__main__':
    with TriangleViewer() as t:
        pass
