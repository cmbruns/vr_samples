"""
Created on Feb 7, 2017

@author: Christopher M. Bruns
"""

import textwrap

from OpenGL import GL
from OpenGL.GL.shaders import compileShader, compileProgram
from OpenGL.arrays.vbo import VBO
import numpy

from openvr.glframework.glmatrix import pack, translate


class SphereProgram(object):
    """
    Possible future adjustable options include:
        correct_depth_buffer?
        radius:
            * constant global radius
            * uniform global radius
            * attribute per-sphere radius
            * uniform radius offset
            * uniform radius scale
        lighting:
            * constant global flat color
            * uniform global flat color
            * attribute per-sphere color
            * image-based lighting
            * directional light(s)
            * constant global material
            * uniform global material
            * per-sphere material
        silhouettes:
            * <none>
            * thickness:
                * pixel and/or scene unit thickness
                * perspective correct vs. constant pixel thickness
            * constant vs. uniform color
        per-sphere visibility
        ambient occlusion...
        solid core clipping
            padded clip slab plus final fragment clipping
       """

    def __init__(self, default_radius=0.2):
        self.default_radius = default_radius
        self.sphere_center_location = 1
        self.model_view_location = 2
        self.projection_location = 3
        self.program_handle = None

    def init_gl(self):
        vertex_shader = compileShader(self.get_vertex_shader(),
                                      GL.GL_VERTEX_SHADER)
        geometry_shader = compileShader(self.get_geometry_shader(),
                                        GL.GL_GEOMETRY_SHADER)
        fragment_shader = compileShader(self.get_fragment_shader(),
                                        GL.GL_FRAGMENT_SHADER)
        self.program_handle = compileProgram(vertex_shader, geometry_shader,
                                             fragment_shader)

    def load(self):
        GL.glUseProgram(self.program_handle)

    def dispose_gl(self):
        if self.program_handle is not None:
            GL.glDeleteProgram(self.program_handle)
            self.program_handle = None

    def get_vertex_shader(self):
        vertex_shader = textwrap.dedent(
            """\
            #version 450 core
            #line 78
            // Vertex shader for sphere imposters
            layout(location = %d) uniform mat4 view_matrix = mat4(1);
            layout(location = %d) in vec3 sphere_center;
            void main() 
            {
                // NOTE: projection is deferred to the geometry shader
                gl_Position = view_matrix * vec4(sphere_center, 1);
            }\
            """ % (self.model_view_location, self.sphere_center_location))
        return vertex_shader

    def get_geometry_shader(self):
        geometry_shader = textwrap.dedent(
            """\
            #version 450 core
            #line 94
            // Geometry shader for sphere imposters
            layout(points) in;
            layout(triangle_strip, max_vertices=10) out; // viewer-facing half-cube imposter geometry

            const float sz = 1;
            const float r = sz;
            const float l = -sz;
            const float t = sz;
            const float b = -sz;
            const float n = 1;
            const float f = 5;
            layout(location = %d) uniform mat4 projectionMatrix = 
                mat4( // mat4(1);
                    2/(r-l), 0, 0, -(r+l)/(r-l),
                    0, 2/(t-b), 0, -(t+b)/(t-b),
                    0, 0, -2/(f-n), -(f+n)/(f-n),
                    0, 0, 0, 1);
            
            const float radius = %s;
            // Spatially linear parameters can be computed per-vertex, and correctly interpolated per-fragment,
            // to help efficiently solve the quadratic ray-casting formula for this sphere.
            out LinearParameters
            {
                vec3 c; // sphere center - constant
                vec3 p; // imposter position - linear
                float c2; // cee squared - constant
                float pc; // pos dot center - linear
            } linpar;
            void emit_one_vertex(in vec3 offset) {
                // Because we always view the cube on-corner, we can afford to trim the bounding geometry a bit,
                // to reduce overdraw
                const float trim = 0.72; // 0.70 = aggressive trim, determined empirically
                vec3 center = linpar.c;
                linpar.p = linpar.c + trim * radius * offset;
                gl_Position = projectionMatrix * vec4(linpar.p, 1);
                linpar.pc = dot(linpar.p, linpar.c);
                EmitVertex();
            }
            // Create a bounding cube, with one corner oriented toward the viewer.
            // Rotate cube of size 2, so that corner 1,1,1 points toward +Z
            // First rotate -45 degrees about Y axis, to orient +XZ edge toward +Z
            // These values are all "const", so they are computed once at shader compile time, not during shader execution.
            // Y-axis is DOWN in mouse brain space, due to Fiji image convention
            // But I'm thinking of this cube in Y-axis UP orientation.
            // ...which is stupid, but I just flipped signs until it looked right.
            const float cos_45 = sqrt(2)/2;
            const float sin_45 = sqrt(2)/2;
            const mat3 rotY45 = mat3(
                cos_45, 0, sin_45,
                0,   1,   0,
                -sin_45, 0, cos_45);
            // Next rotate by arcsin(1/sqrt(3)) about X-axis, to orient corner +XYZ toward +Z
            const float sin_foo = -1.0/sqrt(3);
            const float cos_foo = sqrt(2)/sqrt(3);
            const mat3 rotXfoo = mat3(
                1,   0,   0,
                0, cos_foo, -sin_foo,
                0, sin_foo, cos_foo);
            const mat3 identity = mat3(
                1, 0, 0,
                0, 1, 0,
                0, 0, 1);
            const mat3 rotCorner = rotXfoo * rotY45; // identity; // rotXfoo * rotYm45;
            // Relative locations of all eight corners of the cube (see diagram below)
            const vec3 p1 = rotCorner * vec3(+1,+1,+1); // corner oriented toward viewer
            const vec3 p2 = rotCorner * vec3(-1,+1,-1); // upper rear corner
            const vec3 p3 = rotCorner * vec3(-1,+1,+1); // upper left corner
            const vec3 p4 = rotCorner * vec3(-1,-1,+1); // lower left corner
            const vec3 p5 = rotCorner * vec3(+1,-1,+1); // lower rear corner
            const vec3 p6 = rotCorner * vec3(+1,-1,-1); // lower right corner
            const vec3 p7 = rotCorner * vec3(+1,+1,-1); // upper right corner
            const vec3 p8 = rotCorner * vec3(-1, -1, -1); // rear back corner
            /*
                  2___________7                  
                  /|         /|
                 / |        / |                Y
               3/_________1/  |                ^
                | 8|_______|__|6               |
                |  /       |  /                |
                | /        | /                 /---->X
                |/_________|/                 /
                4          5                 /
                                            Z
            */
            void main() 
            {
                vec4 posIn = gl_in[0].gl_Position;
                linpar.c = posIn.xyz/posIn.w; // sphere center is constant for all vertices
                linpar.c2 = dot(linpar.c, linpar.c) - radius*radius; // 2*c coefficient is constant for all vertices
                // Use BACK faces for imposter geometry, just in case the viewpoint
                // is inside the sphere bounding box
                // imposter behind sphere (10 vertices)
                // Half cube can be constructed using 2 triangle strips,
                // each with 3 triangles
                // First strip: 2-3-8-4-5
                emit_one_vertex(p2);
                emit_one_vertex(p3);
                emit_one_vertex(p8);
                emit_one_vertex(p4);
                emit_one_vertex(p5);
                EndPrimitive();
                // Second strip: 5-6-8-7-2
                emit_one_vertex(p5);
                emit_one_vertex(p6);
                emit_one_vertex(p8);
                emit_one_vertex(p7);
                emit_one_vertex(p2);
                EndPrimitive();
             }\
            """ % (self.projection_location, self.default_radius))
        return geometry_shader

    def get_fragment_shader(self):
        fragment_shader = textwrap.dedent(
            """\
            #version 450 core
            #line 212
            // Fragment shader for sphere imposters
            in LinearParameters
            {
                vec3 c; // sphere center - constant
                vec3 p; // imposter position - linear
                float c2; // cee squared - constant
                float pc; // pos dot center - linear
            } linpar;
            const vec4 sphere_color = vec4(0, 1, 0, 1); // default to blue
            out vec4 frag_color;
            void main() 
            {
                // TODO: cull missed rays
                frag_color = sphere_color; // flat shading
            }\
            """ % ())
        return fragment_shader


class SphereActor(object):
    """
    High-performance display actor for large numbers of spheres
    """

    def __init__(self, vbos=None):
        self.shader = SphereProgram()
        self.vao = None
        if vbos is None:
            # Create on vertex buffer object
            self.vbos = [VBO(numpy.array([0, 1.5, 0], dtype='f')), ]

    def init_gl(self):
        self.shader.init_gl()
        self.vao = GL.glGenVertexArrays(1)
        for vbo in self.vbos:
            pass

    def display_gl(self, model_view, projection):
        GL.glBindVertexArray(self.vao)
        GL.glUseProgram(self.shader.program_handle)
        GL.glUniformMatrix4fv(self.shader.model_view_location, 1, False,
                              pack(model_view))
        GL.glUniformMatrix4fv(self.shader.projection_location, 1, False,
                              pack(projection))
        for vbo in self.vbos:
            vbo.bind()
            xyzloc = self.shader.sphere_center_location
            GL.glEnableVertexAttribArray(xyzloc)
            GL.glVertexAttribPointer(xyzloc, 3, GL.GL_FLOAT, False, 0, None)
            GL.glDrawArrays(GL.GL_POINTS, 0, 1)

    def dispose_gl(self):
        self.shader.dispose_gl()
        for vbo in self.vbos:
            vbo.delete()
        self.vbos = []


if __name__ == '__main__':
    import doctest

    doctest.testmod()
