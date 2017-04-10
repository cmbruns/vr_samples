from OpenGL import GL
from OpenGL.GL.shaders import compileShader, compileProgram
from OpenGL.GL.EXT.texture_filter_anisotropic import GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT, GL_TEXTURE_MAX_ANISOTROPY_EXT
from PIL import Image


class PanoramaRaster(object):
    def __init__(self, img_path, texture_unit=0):
        img = Image.open(img_path)
        self.image = numpy.array(img)
        self.texture_unit = texture_unit
        self.target = GL.GL_TEXTURE_2D

    def _upload_texture(self):
        GL.glTexParameteri(self.target, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
        GL.glTexParameteri(self.target, GL.GL_TEXTURE_WRAP_T, GL.GL_MIRRORED_REPEAT)
        aniso = GL.glGetFloatv(GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, aniso)
        GL.glTexImage2D(self.target, 
                     0, 
                     GL.GL_RGB8,
                     self.image.shape[1], # width 
                     self.image.shape[0], # height
                     0,
                     GL.GL_RGB, 
                     GL.GL_UNSIGNED_BYTE, 
                     self.image)        

    def init_gl(self):
        self.texture_handle = GL.glGenTextures(1)
        GL.glBindTexture(self.target, self.texture_handle)
        GL.glTexParameteri(self.target, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(self.target, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR_MIPMAP_LINEAR)
        self._upload_texture()
        GL.glGenerateMipmap(self.target)
        GL.glBindTexture(self.target, 0)
        
    def display_gl(self):
        GL.glBindTexture(self.target, self.texture_handle)
        
    def dispose_gl(self):
        GL.glDeleteTextures([self.texture_handle,])            

    def shader_fragment(self):
        "fragment of fragment-shader preamble needed to access pixels from this photosphere"
        return """
            #line 48
            layout(binding = %d) uniform sampler2D equirectangular_image;
            
            vec4 color_for_direction(in vec3 d) {
                const float PI = 3.1415926535897932384626433832795;
                float longitude = 0.5 * atan(d.x, -d.z) / PI + 0.5; // range [0-1]
                float r = length(d.xz);
                float latitude = -atan(d.y, r) / PI + 0.5; // range [0-1]
                vec2 tex_coord = vec2(longitude, latitude);
                
                // Use explicit gradients, to preserve anisotropic filtering during mipmap lookup
                vec2 dpdx = dFdx(tex_coord);
                if (dpdx.x > 0.5) dpdx.x -= 1; // use "repeat" wrapping on gradient
                if (dpdx.x < -0.5) dpdx.x += 1;
                vec2 dpdy = dFdy(tex_coord);
                if (dpdy.x > 0.5) dpdy.x -= 1; // use "repeat" wrapping on gradient
                if (dpdy.x < -0.5) dpdy.x += 1;
                
                return textureGrad(equirectangular_image, tex_coord, dpdx, dpdy);
            }
        """ % (self.texture_unit)


class EquirectangularRaster(PanoramaRaster):
    def __init__(self, img_array, texture_unit=0):
        super(EquirectangularRaster, self).__init__(img_array, texture_unit)
        # Verify 2:1 aspect ratio
        shp = self.image.shape
        assert(shp[1] == 2 * shp[0])
    

class CubeMapRaster(PanoramaRaster):
    def __init__(self, img_array, texture_unit=0):
        super(CubeMapRaster, self).__init__(img_array, texture_unit)
        # Verify 4:3 aspect ratio
        shp = self.image.shape
        tile = shp[0] / 3
        assert(shp[0] == 3 * tile)
        assert(shp[1] == 4 * tile)
        self.target = GL.GL_TEXTURE_CUBE_MAP
        
    def init_gl(self):
        super(CubeMapRaster, self).init_gl()
        GL.glEnable(GL.GL_TEXTURE_CUBE_MAP_SEAMLESS)

    def _upload_texture(self):
        # Always use GL_CLAMP_TO_EDGE with cubemaps
        GL.glTexParameteri(self.target, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(self.target, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(self.target, GL.GL_TEXTURE_WRAP_R, GL.GL_CLAMP_TO_EDGE)
        sz = int(self.image.shape[0] / 3)
        # Extract faces from combined cubemap image
        # a[::, ::-1] flips image array "a" left-right
        face_left = numpy.array(self.image[sz:sz*2, sz*0:sz*1][::, ::-1])
        face_front = numpy.array(self.image[sz:sz*2, sz*1:sz*2][::, ::-1])
        face_right = numpy.array(self.image[sz:sz*2, sz*2:sz*3][::, ::-1])
        face_rear = numpy.array(self.image[sz:sz*2, sz*3:sz*4][::, ::-1])
        face_top = numpy.array(self.image[sz*0:sz*1, sz*1:sz*2][::-1, ::])
        face_nadir = numpy.array(self.image[sz*2:sz*3, sz*1:sz*2][::-1, ::])
        GL.glTexImage2D(
                GL.GL_TEXTURE_CUBE_MAP_POSITIVE_X, 
                0, GL.GL_RGB8, sz, sz, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE,
                face_right)
        GL.glTexImage2D(
                GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Y, 
                0, GL.GL_RGB8, sz, sz, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE,
                face_top)
        GL.glTexImage2D(
                GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Z, 
                0, GL.GL_RGB8, sz, sz, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE,
                face_rear)
        GL.glTexImage2D(
                GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_X, 
                0, GL.GL_RGB8, sz, sz, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE,
                face_left)
        GL.glTexImage2D(
                GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Y, 
                0, GL.GL_RGB8, sz, sz, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE,
                face_nadir)
        GL.glTexImage2D(
                GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Z, 
                0, GL.GL_RGB8, sz, sz, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE,
                face_front)
     
    def shader_fragment(self):
        "fragment of fragment-shader preamble needed to access pixels from this photosphere"
        return """
            #line 135
            layout(binding = %d) uniform samplerCube cubemap_image;
            
            vec4 color_for_direction(in vec3 d) {
                return texture(cubemap_image, d);
            }
        """ % (self.texture_unit)


class SphericalPanorama(object):
    def __init__(self, raster, proxy_geometry):
        self.raster = raster
        self.proxy_geometry = proxy_geometry
        self.vao = None
    
    def init_gl(self):
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.raster.init_gl()
        # Set up shaders for rendering
        vertex_shader = compileShader(
            """#version 450 core
            #line 157
            
            layout(location = 1) uniform mat4 projection = mat4(1);
            layout(location = 2) uniform mat4 model_view = mat4(1);

            out vec3 viewDir;
            flat out vec3 camPos;
            
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
                vec4 camPos4 = xyzFromNdc * vec4(0, 0, 0, 1);
                camPos = camPos4.xyz / camPos4.w;
                vec4 vpos = xyzFromNdc * SCREEN_QUAD[vertexIndex];
                viewDir = vpos.xyz/vpos.w - camPos;
            }
            """,
            GL.GL_VERTEX_SHADER)
        fragment_shader = compileShader(
            """#version 450 core
            #line 189
    
            // prototype to be defined by raster implementation
            vec4 color_for_direction(in vec3 d);
            %s // raster implementation gets inserted here...
            #line 194
            
            // prototype to be defined by proxy geometry implementation
            vec3 adjusted_view_direction(in vec3 true_direction, in vec3 eye_location);
            %s // proxy geometry implementation gets inserted here...
            #line 199
            
            in vec3 viewDir;
            in vec3 camPos;
            out vec4 pixelColor;
            
            void main() 
            {
                vec3 dir = adjusted_view_direction(viewDir, camPos);
                pixelColor = color_for_direction(dir);
            }
            """ % (self.raster.shader_fragment(), self.proxy_geometry.shader_fragment()),
            GL.GL_FRAGMENT_SHADER)
        self.shader = compileProgram(vertex_shader, fragment_shader)

    def display_gl(self, modelview, projection):
        GL.glBindVertexArray(self.vao)
        self.raster.display_gl()
        # print(modelview)
        GL.glUseProgram(self.shader)
        GL.glUniformMatrix4fv(1, 1, False, projection)
        GL.glUniformMatrix4fv(2, 1, False, modelview)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)
        
    def dispose_gl(self):
        self.raster.dispose_gl()
        GL.glDeleteVertexArrays(1, [self.vao,])
        if self.shader is not None:
            GL.glDeleteProgram(self.shader)


class InfiniteBackground(object):
    """
    Proxy geometry representing a spherical panorama at infinite distance.
    For example the celestial sphere of stars and planets and other distant objects.
    """
    def shader_fragment(self):
        return """
            #line 237
            vec3 adjusted_view_direction(in vec3 true_direction, in vec3 eye_location)
            {
                return true_direction; // there is no parallax at infinite distance
            }
            """


class InfinitePlane(object):
    def __init__(self, plane_equation=[0, 1, 0, 0]):
        self.plane_equation = plane_equation
    
    """
    Proxy geometry representing a spherical panorama at infinite distance.
    For example the celestial sphere of stars and planets and other distant objects.
    """
    def shader_fragment(self):
        p = self.plane_equation
        return """
            #line 256
            vec3 adjusted_view_direction(in vec3 true_direction, in vec3 eye_location)
            {
                const vec4 plane_equation = vec4(%f, %f, %f, %f);
                const vec3 original_camera_position = vec3(0, 2, 0);

                // intersection of view direction and plane
                // http://math.stackexchange.com/questions/400268/equation-for-a-line-through-a-plane-in-homogeneous-coordinates
                const vec3 w = plane_equation.xyz;
                const float e = plane_equation.w;
                vec3 l = true_direction;

                // Some directions don't intersect the plane
                float determinant = dot(w, l);
                if (determinant > 0.0) discard; // plane is not visible
                
                vec3 m = cross(eye_location, l);
                // r is the point on the floor we are looking at
                vec3 r = (cross(w, m) - e*l) / dot(w,l);
                
                return r - original_camera_position;
            }
            """ % (p[0], p[1], p[2], p[3])


if __name__ == "__main__":
    # Open equirectangular photosphere
    import os
    
    import numpy
    from openvr.glframework.glfw_app import GlfwApp
    from openvr.gl_renderer import OpenVrGlRenderer

    src_folder = os.path.dirname(os.path.abspath(__file__))
    if False:
        img_path = os.path.join(src_folder, '../../../../assets/images/_0010782_stitch2.jpg')
        raster = EquirectangularRaster(img_path)
    else:
        img_path = os.path.join(src_folder, '../../../../assets/images/lauterbrunnen_cube.jpg')
        raster = CubeMapRaster(img_path)
    actor1 = SphericalPanorama(raster=raster, proxy_geometry=InfiniteBackground())
    actor2 = SphericalPanorama(raster=raster, proxy_geometry=InfinitePlane())
    renderer = OpenVrGlRenderer([actor1, actor2])
    with GlfwApp(renderer, "photosphere test") as glfwApp:
        glfwApp.run_loop()
