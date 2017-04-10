
from textwrap import dedent

from OpenGL import GL
from OpenGL.GL.shaders import compileShader, compileProgram

class PanoramaRaster(object):
    def __init__(self, img_array, texture_unit=0):
        self.image = img_array
        self.texture_unit = texture_unit

    def init_gl(self):
        self.texture_handle = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture_handle);
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR);
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR);
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT);
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_MIRRORED_REPEAT);
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 
                     0, 
                     GL.GL_RGB8,
                     self.image.shape[1], # width 
                     self.image.shape[0], # height
                     0,
                     GL.GL_RGB, 
                     GL.GL_UNSIGNED_BYTE, 
                     self.image)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0);
        
    def display_gl(self):
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture_handle)
        
    def dispose_gl(self):
        GL.glDeleteTextures([self.texture_handle,])            

    def shader_fragment(self):
        "fragment of fragment-shader preamble needed to access pixels from this photosphere"
        return """
            #line 48
            layout(binding = %d) uniform sampler2D equirectangular_image;
            
            vec4 color_for_direction(in vec3 d) {
                const float PI = 3.1415926535897932384626433832795;
                float longitude = 0.5 * atan(d.z, d.x) / PI + 0.5; // range [0-1]
                float r = length(d.xz);
                float latitude = -atan(d.y, r) / PI + 0.5; // range [0-1]
                return texture(equirectangular_image, vec2(longitude, latitude));
            }
        """ % (self.texture_unit)


class EquirectangularRaster(PanoramaRaster):
    def __init__(self, img_array):
        super(EquirectangularRaster, self).__init__(img_array)
        # Verify 2:1 aspect ratio
        shp = img_array.shape
        print(shp)
        assert(shp[1] == 2 * shp[0])
    

class CubeMapRaster(PanoramaRaster):
    pass


class InfiniteBackground(object):
    def __init__(self, raster):
        self.raster = raster    
    
    def init_gl(self):
        # Set up shaders for rendering
        vertex_shader = compileShader(dedent(
                """#version 450 core
                #line 74
                
                layout(location = 1) uniform mat4 projection = mat4(1);
                layout(location = 2) uniform mat4 model_view = mat4(1);

                out vec3 viewDir;
                
                // projected screen quad
                const vec4 SCREEN_QUAD[4] = vec4[4](
                    vec4(-1, -1, 1, 1),
                    vec4( 1, -1, 1, 1),
                    vec4( 1,  1, 1, 1),
                    vec4(-1,  1, 1, 1));
                
                const int TRIANGLE_STRIP_INDICES[4] = int[4](
                    0, 1, 3, 2);
                
                void main() 
                {
                    int vertexIndex = TRIANGLE_STRIP_INDICES[gl_VertexID];
                    gl_Position = vec4(SCREEN_QUAD[vertexIndex]);
                    mat4 xyzFromNdc = inverse(projection * model_view);
                    vec4 campos = xyzFromNdc * vec4(0, 0, 0, 1);
                    vec4 vpos = xyzFromNdc * SCREEN_QUAD[vertexIndex];
                    viewDir = vpos.xyz/vpos.w - campos.xyz/campos.w;
                }
                """),
                GL.GL_VERTEX_SHADER)
        fragment_shader = compileShader(dedent(
                """\
                #version 450 core
                #line 105
        
                // prototype to be defined by raster implementation
                vec4 color_for_direction(in vec3 d);
                
                %s
                #line 111
                
                in vec3 viewDir;
        
                out vec4 pixelColor;
                
                void main() 
                {
                    pixelColor = color_for_direction(viewDir);
                }
                """ % (self.raster.shader_fragment())),
                GL.GL_FRAGMENT_SHADER)
        self.shader = compileProgram(vertex_shader, fragment_shader)

    def display_gl(self, modelview, projection):
        GL.glUseProgram(self.shader)
        GL.glUniformMatrix4fv(1, 1, False, projection)
        GL.glUniformMatrix4fv(2, 1, False, modelview)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)
        
    def dispose_gl(self):
        if self.shader is not None:
            GL.glDeleteProgram(self.shader)
    

class SphericalPanorama(object):
    def __init__(self, raster):
        self.raster = raster
        self.renderer = InfiniteBackground(raster)
        self.vao = None
        
    def init_gl(self):
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.raster.init_gl()
        self.renderer.init_gl()

    def display_gl(self, modelview, projection):
        GL.glBindVertexArray(self.vao)
        self.raster.display_gl()
        self.renderer.display_gl(modelview, projection)

    def dispose_gl(self):
        self.raster.dispose_gl()
        self.renderer.dispose_gl()
        GL.glDeleteVertexArrays(1, [self.vao,])


if __name__ == "__main__":
    # Open equirectangular photosphere
    import os
    
    import numpy
    from PIL import Image
    from openvr.glframework.glfw_app import GlfwApp
    from openvr.gl_renderer import OpenVrGlRenderer

    src_folder = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(src_folder, '../../../../assets/images/_0010782_stitch2.jpg')
    img = Image.open(img_path)
    arr = numpy.array(img)
    raster = EquirectangularRaster(arr)
    actor = SphericalPanorama(raster)
    renderer = OpenVrGlRenderer(actor)
    with GlfwApp(renderer, "photosphere test") as glfwApp:
        glfwApp.run_loop()
