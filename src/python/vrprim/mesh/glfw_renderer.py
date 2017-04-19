'''
Created on Apr 18, 2017

@author: brunsc
'''

import sys
import os

import numpy
from OpenGL import GL
from OpenGL.GL.shaders import compileShader, compileProgram
from OpenGL.arrays import vbo
import glfw

import glmatrix
from glmatrix import mbytes
from openvr.gl_renderer import OpenVrGlRenderer
from openvr.glframework.glfw_app import GlfwApp


class TriangleActor(object):
    def init_gl(self):
        # Create vertex array object, apparently required for modern OpenGL
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        # Create triangle geometry: corner 2D location and colors
        self.vertices = vbo.VBO(numpy.array([
                [ -0.6, -0.4, 1.0, 0.0, 0.0 ], # x, y, r, g, b
                [  0.6, -0.4, 0.0, 1.0, 0.0 ],
                [  0.0,  0.6, 0.0, 0.0, 1.0 ],
                ], dtype='float32'))
        self.vertices.bind()
        # hard-code shader parameter location indices
        self.mvp_location = 0
        vpos_location = 0
        vcol_location = 1
        GL.glEnableVertexAttribArray(vpos_location)
        fsize = self.vertices.dtype.itemsize # 4 bytes per float32
        GL.glVertexAttribPointer(vpos_location, 2, GL.GL_FLOAT, False,
                              fsize * 5, self.vertices + fsize * 0)
        GL.glEnableVertexAttribArray(vcol_location)
        GL.glVertexAttribPointer(vcol_location, 3, GL.GL_FLOAT, False,
                              fsize * 5, self.vertices + fsize * 2)
        # Create GLSL shader program
        vertex_shader = compileShader(
            """#version 450 core
            #line 45
            
            layout(location = %d) uniform mat4 MVP = mat4(1);
            
            layout(location = %d) in vec2 vPos;
            layout(location = %d) in vec3 vCol;
            
            out vec3 color;
    
            void main() 
            {
                gl_Position = MVP * vec4(vPos, 0.0, 1.0);
                color = vCol;
            }
            """ % (self.mvp_location, vpos_location, vcol_location),
            GL.GL_VERTEX_SHADER)
        fragment_shader = compileShader(
            """#version 450 core
            #line 63
    
            in vec3 color;
            out vec4 fragColor;
    
            void main() 
            {
                fragColor = vec4(color, 1);
            }
            """,
            GL.GL_FRAGMENT_SHADER)
        self.program = compileProgram(vertex_shader, fragment_shader)
        
    def display_gl(self, modelview, projection):
        GL.glBindVertexArray(self.vao)
        GL.glUseProgram(self.program)
        # mvp = modelview * glmatrix.rotate_Z(glfw.get_time()) * projection
        mvp = modelview * projection
        GL.glUniformMatrix4fv(self.mvp_location, 1, False, mbytes(mvp))
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 3)
        
    def dispose_gl(self):
        if self.vao:
            GL.glDeleteVertexArrays(1, [self.vao,])
        self.vertices.delete()
        GL.glDeleteProgram(self.program)
        

class TeapotActor(object):
    def __init__(self):
        src_folder = os.path.dirname(os.path.abspath(__file__))
        obj_path = os.path.join(src_folder, 'wt_teapot.obj')
        self.vertexes = list()
        vertex_normals = list()
        self.normal_for_vertex = dict()
        self.faces = list()
        with open(obj_path) as fh:
            for line in fh:
                if line.startswith('#'):
                    # e.g. "# Blender v2.65 (sub 0) OBJ File"
                    continue # ignore comments
                elif line.startswith('o '):
                    # e.g. "o teapot.005"
                    continue # ignore object names
                elif line.startswith('v '):
                    # e.g. "v -0.498530 0.712498 -0.039883"
                    vec3 = [float(x) for x in line.split()[1:4]]
                    self.vertexes.append(vec3)
                elif line.startswith('vn '):
                    # e.g. "vn -0.901883 0.415418 0.118168"
                    vec3 = [float(x) for x in line.split()[1:4]]
                    vertex_normals.append(vec3)
                elif line.startswith('s '):
                    continue # ignore whatever "s" is
                    # print(line)
                elif line.startswith('f '):
                    face = list()
                    for c in line.split()[1:]:
                        v, n = [int(x) for x in c.split('/')[0:3:2]]
                        face.append(v-1) # vertex index
                        self.normal_for_vertex[v-1] = vertex_normals[n-1]
                        self.faces.append(face)
                    # print(line)
                    # print(face)                  
                else:
                    print(line)
                    break
        self.vbo = list()
        ibo = list()
        for i in range(len(self.vertexes)):
            v = self.vertexes[i]
            n = self.normal_for_vertex[i]
            self.vbo.append(v)
            self.vbo.append(n)
        for f in self.faces:
            for v in f:
                ibo.append(v)
                # todo: only works for single triangle faces at the moment...
        self.element_count = len(ibo)
        self.vbo = numpy.array(self.vbo, 'float32')
        ibo = numpy.array(ibo, 'int16')
        self.vbo = vbo.VBO(self.vbo)
        self.ibo = vbo.VBO(ibo, target=GL.GL_ELEMENT_ARRAY_BUFFER)
    
    def init_gl(self):
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.ibo.bind()
        self.vbo.bind()
        GL.glEnableVertexAttribArray(0) # vertex location
        fsize = self.vbo.dtype.itemsize # 4 bytes per float32
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, False, 
                6 * fsize, self.vbo + 0 * fsize)
        GL.glEnableVertexAttribArray(1) # vertex normal
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, False, 
                6 * fsize, self.vbo + 3 * fsize)
        vertex_shader = compileShader(
            """#version 450 core
            #line 161
            
            layout(location = 0) in vec3 in_Position;
            layout(location = 1) in vec3 in_Normal;
            
            layout(location = 0) uniform mat4 projection = mat4(1);
            layout(location = 1) uniform mat4 model_view = mat4(1);
            
            out vec3 normal;

            void main() 
            {
                gl_Position = projection * model_view * vec4(in_Position, 1.0);
                mat4 normal_matrix = transpose(inverse(model_view));
                normal = normalize((normal_matrix * vec4(in_Normal, 0)).xyz);
            }
            """,
            GL.GL_VERTEX_SHADER)
        fragment_shader = compileShader(
            """#version 450 core
            #line 181
    
            in vec3 normal;
            out vec4 fragColor;

            vec4 color_by_normal(in vec3 n) {
                return vec4(0.5 * (normalize(n) + vec3(1)), 1);
            }

            void main() 
            {
                fragColor = color_by_normal(normal);
            }
            """,
            GL.GL_FRAGMENT_SHADER)
        self.shader = compileProgram(vertex_shader, fragment_shader)
    
    def display_gl(self, modelview, projection):
        GL.glBindVertexArray(self.vao)
        GL.glUseProgram(self.shader)
        m = glmatrix.rotate_X(glfw.get_time()) * modelview
        GL.glUniformMatrix4fv(0, 1, False, mbytes(projection))
        GL.glUniformMatrix4fv(1, 1, False, mbytes(m))
        GL.glDrawElements(GL.GL_TRIANGLES, self.element_count, GL.GL_UNSIGNED_SHORT, None)
    
    def dispose_gl(self):
        if self.vao:
            GL.glDeleteVertexArrays(1, [self.vao,])
            self.ibo.delete()
            self.vbo.delete()
            GL.glDeleteProgram(self.shader)
            self.vao = None


class GlfwRenderer(object):
    "Regular desktop version of GLFW renderer"
    def __init__(self, actors=[], size=[640, 480]):
        self.actor_list = actors
        self.initial_size = size
        # Initialize GLFW opengl API
        glfw.set_error_callback(self.error_callback)
        if not glfw.init():
            raise Exception("GLFW Initialization error")
        self._configure_context()
        # Create OpenGL window and context
        self.window = glfw.create_window(self.initial_size[0], 
                self.initial_size[1], "Triangle Viewer", None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError("Failed to create glfw window")
        self.init_gl()
        glfw.swap_interval(1)
    
    def _configure_context(self):
        # Use modern OpenGL version 4.5 core
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 5)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)        
        
    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        # Clean up and exit
        if self.window:
            glfw.make_context_current(self.window)
            for actor in self.actor_list:
                actor.dispose_gl()
            glfw.destroy_window(self.window)
        glfw.terminate()
        sys.exit(0)
        
    def init_gl(self):
        glfw.make_context_current(self.window)
        GL.glClearColor(0.5, 0.5, 0.5, 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)
        for actor in self.actor_list:
            actor.init_gl()
        
    def render(self, actors=[]):
        glfw.make_context_current(self.window)
        width, height = glfw.get_framebuffer_size(self.window)
        GL.glViewport(0, 0, width, height)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        modelview = glmatrix.translate([0, 0, -5.0])
        projection = glmatrix.perspective(45.0, width / float(height), 0.1, 10.0)
        for actor in self.actor_list:
            actor.display_gl(modelview, projection)
        glfw.swap_buffers(self.window)
        glfw.poll_events()
        
    def error_callback(self, error_code, description):
        raise RuntimeError(description)


class GlfwOpenVrRenderer(GlfwRenderer):
    def __init__(self, actors=[], size=[640, 480]):
        self.vr_renderer = OpenVrGlRenderer(actors)
        super(GlfwOpenVrRenderer, self).__init__(actors, size)
        glfw.swap_interval(0)
        
    def _configure_context(self):
        # Use modern OpenGL version 4.5 core
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 5)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)        
        glfw.window_hint(glfw.DOUBLEBUFFER, False)
        
    def init_gl(self):
        glfw.make_context_current(self.window)
        GL.glClearColor(0.5, 0.5, 0.5, 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)
        self.vr_renderer.init_gl()
 
    def render(self, actors=[]):
        glfw.make_context_current(self.window)
        self.vr_renderer.render_scene()
        GL.glFlush() # single buffering        
        glfw.poll_events()

    def __exit__(self, type_, value, traceback):
        # Clean up and exit
        if self.window:
            glfw.make_context_current(self.window)
            glfw.destroy_window(self.window)
            if self.vr_renderer is not None:
                self.vr_renderer.dispose_gl()
        glfw.terminate()
        sys.exit(0)


def main():
    if False:
        with GlfwApp(OpenVrGlRenderer(TriangleActor())) as app:
            app.run_loop()
    else:
        with GlfwOpenVrRenderer([TeapotActor(), TriangleActor(),]) as rend:
            while not glfw.window_should_close(rend.window):
                rend.render()

if __name__ == "__main__":
    main()

