
import math
import ctypes

import numpy
import glfw
import OpenGL.arrays
from OpenGL import GL
from OpenGL.GL.shaders import compileShader, compileProgram



def translate(xyz):
    x, y, z = xyz
    return numpy.matrix(
            [[1,0,0,x],
             [0,1,0,y],
             [0,0,1,z],
             [0,0,0,1]], 'float32')
 
def identity():
    return numpy.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
            ], 'float32')

def frustum(left, right, bottom, top, zNear, zFar):
    A = (right + left) / (right - left)
    B = (top + bottom) / (top - bottom)
    C = -(zFar + zNear) / (zFar - zNear)
    D = -(2.0 * zFar * zNear) / (zFar - zNear)
    result = numpy.matrix([
            [2.0 * zNear / (right - left), 0.0, A, 0.0],
            [0.0, 2.0 * zNear / (top - bottom), B, 0.0],
            [0.0, 0.0, C, D],
            [0.0, 0.0, -1.0, 0.0],
            ], 'float32')
    return result
    # return numpy.array(result.T, 'float32') # todo: transpose or not?

def perspective(fovY, aspect, zNear, zFar):
    fH = math.tan(fovY / 2.0 / 180.0 * math.pi) * zNear
    fW = fH * aspect
    return frustum(-fW, fW, -fH, fH, zNear, zFar)


class GlfwViewer(object):
    def __init__(self):
        self.vao = None
        self.window = None
    
    def __enter__(self):
        if not glfw.init():
            raise Exception("GLFW Initialization error")
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 5)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        self.width = 640
        self.height = 480
        self.window = glfw.create_window(self.width, self.height, "OBJ Viewer", None, None)
        if not self.window:
            raise RuntimeError("Failed to create glfw window")
        glfw.set_error_callback(self.error_callback)
        self.init_gl()
        return self
        
    def __exit__(self, type_, value, traceback):
        self.dispose_gl()
        glfw.destroy_window(self.window)
        glfw.terminate()

    def init_gl(self):
        glfw.make_context_current(self.window)
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        GL.glClearColor(0, 0, 1, 1)
        GL.glViewport(0, 0, self.width, self.height)
        self.modelview = translate([0, 0, -5.0])
        self.projection = perspective(45.0, self.width / float(self.height), 0.1, 10.0)

    def display_gl(self):
        glfw.make_context_current(self.window)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        self.render_scene(self.modelview, self.projection)
        glfw.swap_buffers(self.window)
        glfw.poll_events()
        
    def render_scene(self, modelview, projection):
        "Override this method in derived class"
        pass

    def dispose_gl(self):
        if not self.window:
            return
        glfw.make_context_current(self.window)
        if not self.vao:
            return
        GL.glDeleteVertexArrays(1, [self.vao,])
        self.vao = None
        
    def error_callback(self, description):
        raise RuntimeError(description)
    
    def run_loop(self):
        while not glfw.window_should_close(self.window):
            self.display_gl()


class ObjViewer(GlfwViewer):
    def __init__(self):
        import os
        super(ObjViewer, self).__init__()
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
        vbo = list()
        ibo = list()
        for i in range(len(self.vertexes)):
            v = self.vertexes[i]
            n = self.normal_for_vertex[i]
            vbo.append(v)
            vbo.append(n)
        for f in self.faces:
            for v in f:
                ibo.append(v)
                # todo: only works for single triangle faces at the moment...
        self.element_count = len(ibo)
        vbo = numpy.array(vbo, 'float32')
        ibo = numpy.array(ibo, 'int16')
        self.vbo = OpenGL.arrays.vbo.VBO(vbo)
        self.ibo = OpenGL.arrays.vbo.VBO(ibo, target=GL.GL_ELEMENT_ARRAY_BUFFER)
    
    def init_gl(self):
        super(ObjViewer, self).init_gl()
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glClearColor(0.5, 0.5, 0.5, 1)
        self.ibo.bind()
        self.vbo.bind()
        GL.glEnableVertexAttribArray(0) # vertex location
        fsize = ctypes.sizeof(ctypes.c_float)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, False, 
                6 * fsize, ctypes.cast(0 * fsize, ctypes.c_void_p))
        GL.glEnableVertexAttribArray(1) # vertex normal
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, False, 
                6 * fsize, ctypes.cast(3 * fsize, ctypes.c_void_p))
        vertex_shader = compileShader(
            """#version 450 core
            #line 180
            
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
            #line 204
    
            in vec3 normal;
            out vec4 fragColor;

            vec4 color_by_normal(in vec3 n) {
                return vec4(0.5 * (normalize(n) + vec3(1)), 1);
            }

            void main() 
            {
                // fragColor = vec4(0, 1, 0, 1);
                fragColor = color_by_normal(normal);
            }
            """,
            GL.GL_FRAGMENT_SHADER)
        self.shader = compileProgram(vertex_shader, fragment_shader)

    def render_scene(self, modelview, projection):
        super(ObjViewer, self).render_scene(modelview, projection)
        self.ibo.bind()
        self.vbo.bind()
        GL.glUseProgram(self.shader)
        # print(projection)
        GL.glUniformMatrix4fv(0, 1, True, numpy.ascontiguousarray(projection, dtype=numpy.float32))
        GL.glUniformMatrix4fv(1, 1, True, numpy.ascontiguousarray(modelview, dtype=numpy.float32))
        GL.glDrawElements(GL.GL_TRIANGLES, self.element_count, GL.GL_UNSIGNED_SHORT, None)


def main():
    with ObjViewer() as v:
        v.run_loop()

if __name__ == "__main__":
    main()
