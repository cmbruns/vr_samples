"""
Created on Apr 18, 2017

@author: Christopher Bruns
"""

import os

import numpy
from OpenGL import GL
from OpenGL.GL.shaders import compileShader, compileProgram
from OpenGL.arrays import vbo

from openvr.glframework.glmatrix import identity, pack, rotate_y, scale
from openvr.glframework import shader_string

class TriangleActor(object):
    def __init__(self):
        self.vao = None
        # hard-code shader parameter location index
        self.mvp_location = 0
        self.program = None
        # Create triangle geometry: corner 2D location and colors
        self.vertices = vbo.VBO(numpy.array([
            [-0.6, -0.4, 1.0, 0.0, 0.0],  # x, y, r, g, b
            [0.6, -0.4, 0.0, 1.0, 0.0],
            [0.0, 0.6, 0.0, 0.0, 1.0],
        ], dtype='float32'))

    def init_gl(self):
        # Create vertex array object, apparently required for modern OpenGL
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.vertices.bind()
        # hard-code shader parameter location indices
        vpos_location = 0
        vcol_location = 1
        GL.glEnableVertexAttribArray(vpos_location)
        float_size = self.vertices.dtype.itemsize  # 4 bytes per float32
        GL.glVertexAttribPointer(vpos_location, 2, GL.GL_FLOAT, False,
                                 float_size * 5, self.vertices + float_size * 0)
        GL.glEnableVertexAttribArray(vcol_location)
        GL.glVertexAttribPointer(vcol_location, 3, GL.GL_FLOAT, False,
                                 float_size * 5, self.vertices + float_size * 2)
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

    def display_gl(self, model_view, projection):
        GL.glBindVertexArray(self.vao)
        GL.glUseProgram(self.program)
        mvp = numpy.matrix(model_view) * projection
        GL.glUniformMatrix4fv(self.mvp_location, 1, False, pack(mvp))
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 3)

    def dispose_gl(self):
        if self.vao:
            GL.glDeleteVertexArrays(1, [self.vao, ])
        self.vertices.delete()
        GL.glDeleteProgram(self.program)


class ObjActor(object):
    def __init__(self, obj_stream):
        self.model_matrix = identity()
        self.vao = None
        self.shader = None
        self.vertexes = list()
        vertex_normals = list()
        self.normal_for_vertex = dict()
        self.faces = list()
        fh = obj_stream
        for line in fh:
            if line.startswith('#'):
                # e.g. "# Blender v2.65 (sub 0) OBJ File"
                continue  # ignore comments
            elif line.startswith('o '):
                # e.g. "o teapot.005"
                continue  # ignore object names
            elif line.startswith('v '):
                # e.g. "v -0.498530 0.712498 -0.039883"
                vec3 = [float(x) for x in line.split()[1:4]]
                self.vertexes.append(vec3)
            elif line.startswith('vn '):
                # e.g. "vn -0.901883 0.415418 0.118168"
                vec3 = [float(x) for x in line.split()[1:4]]
                vertex_normals.append(vec3)
            elif line.startswith('s '):
                continue  # ignore whatever "s" is
                # print(line)
            elif line.startswith('f '):
                face = list()
                for c in line.split()[1:]:
                    v, n = [int(x) for x in c.split('/')[0:3:2]]
                    face.append(v - 1)  # vertex index
                    self.normal_for_vertex[v - 1] = vertex_normals[n - 1]
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
        GL.glEnableVertexAttribArray(0)  # vertex location
        float_size = self.vbo.dtype.itemsize  # 4 bytes per float32
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, False,
                                 6 * float_size, self.vbo + 0 * float_size)
        GL.glEnableVertexAttribArray(1)  # vertex normal
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, False,
                                 6 * float_size, self.vbo + 3 * float_size)
        vertex_shader = compileShader(
            shader_string("""
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
            """),
            GL.GL_VERTEX_SHADER)
        fragment_shader = compileShader(
            shader_string("""            in vec3 normal;
            out vec4 fragColor;

            vec4 color_by_normal(in vec3 n) {
                return vec4(0.5 * (normalize(n) + vec3(1)), 1);
            }

            void main() 
            {
                fragColor = color_by_normal(normal);
            }
            """),
            GL.GL_FRAGMENT_SHADER)
        self.shader = compileProgram(vertex_shader, fragment_shader)
        GL.glEnable(GL.GL_DEPTH_TEST)

    def display_gl(self, model_view, projection):
        GL.glBindVertexArray(self.vao)
        GL.glUseProgram(self.shader)
        m = self.model_matrix * model_view
        GL.glUniformMatrix4fv(0, 1, False, pack(projection))
        GL.glUniformMatrix4fv(1, 1, False, pack(m))
        GL.glDrawElements(GL.GL_TRIANGLES, self.element_count, GL.GL_UNSIGNED_SHORT, None)

    def dispose_gl(self):
        if self.vao:
            GL.glDeleteVertexArrays(1, [self.vao, ])
            self.ibo.delete()
            self.vbo.delete()
            GL.glDeleteProgram(self.shader)
            self.vao = None


class TeapotActor(ObjActor):
    def __init__(self):
        src_folder = os.path.dirname(os.path.abspath(__file__))
        obj_path = os.path.join(src_folder, 'wt_teapot.obj')
        with open(obj_path) as fh:
            super(TeapotActor, self).__init__(obj_stream=fh)


if __name__ == "__main__":
    from openvr.glframework.glfw_app import GlfwVrApp
    import glfw
    teapot = TeapotActor()
    s = 0.2  # size of teapot in meters
    with GlfwVrApp(actors=[teapot, ]) as app:
        while not glfw.window_should_close(app.window):
            # scale teapot to original Melitta model aspect ratio
            teapot.model_matrix = scale(s, s*4/3, s) * rotate_y(glfw.get_time())
            app.render_scene()
