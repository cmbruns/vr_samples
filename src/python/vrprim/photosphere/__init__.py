import numpy
from OpenGL import GL
from OpenGL.GL.shaders import compileShader, compileProgram
from OpenGL.GL.EXT.texture_filter_anisotropic import GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT, GL_TEXTURE_MAX_ANISOTROPY_EXT
from PIL import Image

from openvr.glframework import shader_string, shader_substring

class BasicShaderComponent(object):
    def frag_shader_decl_substring(self):
        return ""

    def frag_shader_main_substring(self):
        return ""

    def vrtx_shader_decl_substring(self):
        return ""

    def vrtx_shader_main_substring(self):
        return ""


class PanoramaRaster(BasicShaderComponent):
    def __init__(self, img_path=None, texture_unit=0, img_array=None):
        if img_path and not img_array:
            img = Image.open(img_path)
            self.image = numpy.array(img)
        else:
            self.image = img_array
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
        GL.glTexParameteri(self.target, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(self.target, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR_MIPMAP_LINEAR)
        self._upload_texture()
        GL.glGenerateMipmap(self.target)
        GL.glBindTexture(self.target, 0)
        
    def display_gl(self):
        GL.glBindTexture(self.target, self.texture_handle)
        
    def dispose_gl(self):
        GL.glDeleteTextures([self.texture_handle,])            

    def frag_shader_decl_substring(self):
        "fragment of fragment-shader preamble needed to access pixels from this photosphere"
        return """
            #line 49
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
    def __init__(self, *args, **kwargs):
        super(EquirectangularRaster, self).__init__(*args, **kwargs)
        # Verify 2:1 aspect ratio
        shp = self.image.shape
        assert(shp[1] == 2 * shp[0])
    

class CubeMapRaster(PanoramaRaster):
    def __init__(self, *args, **kwargs):
        super(CubeMapRaster, self).__init__(*args, **kwargs)
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
     
    def frag_shader_decl_substring(self):
        "fragment of fragment-shader preamble needed to access pixels from this photosphere"
        return """
            #line 136
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
        self.shader = None
    
    def init_gl(self):
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.raster.init_gl()
        # Set up shaders for rendering
        shader_components = [self.raster, self.proxy_geometry]
        decls = ''.join([a.vrtx_shader_decl_substring() for a in shader_components])
        mains = ''.join([a.vrtx_shader_main_substring() for a in shader_components])
        vertex_shader = compileShader(shader_string("""
            layout(location = 1) uniform mat4 projection = mat4(1);
            layout(location = 2) uniform mat4 model_view = mat4(1);

            out vec3 viewDir;
            flat out vec3 camPos;
            
            // projected screen quad
            const vec4 SCREEN_QUAD[4] = vec4[4](
                vec4(-1, -1, 0.5, 1),
                vec4( 1, -1, 0.5, 1),
                vec4( 1,  1, 0.5, 1),
                vec4(-1,  1, 0.5, 1));

            const int TRIANGLE_STRIP_INDICES[4] = int[4](
                0, 1, 3, 2);
            
            vec3 camPosFromModelView(in mat4 modelView) {
                // assuming no scaling
                mat3 rot = mat3(modelView);
                vec3 d = vec3(modelView[3]);
                return -d * rot;
            }

            // declarations from subshaders           
            %s
            #line 205
            
            void main() 
            {
                int vertexIndex = TRIANGLE_STRIP_INDICES[gl_VertexID];
                gl_Position = vec4(SCREEN_QUAD[vertexIndex]);
                mat4 xyzFromNdc = inverse(projection * model_view);
                camPos = camPosFromModelView(model_view);
                vec4 vpos = xyzFromNdc * SCREEN_QUAD[vertexIndex];
                viewDir = vpos.xyz/vpos.w - camPos;
                
                // code from subshaders
                %s
            }
            """ % (decls, mains)),
            GL.GL_VERTEX_SHADER)
        decls = ''.join([a.frag_shader_decl_substring() for a in shader_components])
        mains = ''.join([a.frag_shader_main_substring() for a in shader_components])
        fragment_shader = compileShader(shader_string("""
            // declarations from shader components below
            %s
            #line 219
            
            in vec3 viewDir;
            in vec3 camPos;
            out vec4 pixelColor;
            
            void main() 
            {
                // code from shader components below
                %s
                #line 229
                
                vec3 dir = adjusted_view_direction(viewDir, camPos);
                pixelColor = color_for_direction(dir);
            }
            """ % (decls, mains)),
            GL.GL_FRAGMENT_SHADER)
        self.shader = compileProgram(vertex_shader, fragment_shader)

    def display_gl(self, modelview, projection):
        GL.glBindVertexArray(self.vao)
        GL.glDepthRange(1, 1)  # Draw skybox at infinity...
        GL.glDepthFunc(GL.GL_LEQUAL)  # ...but paint over other infinitely distant things, such as the result of glClear
        self.raster.display_gl()
        # print(modelview)
        # print(projection)
        GL.glUseProgram(self.shader)
        GL.glUniformMatrix4fv(1, 1, False, projection)
        GL.glUniformMatrix4fv(2, 1, False, modelview)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)
        # Restore earth depth behavior
        GL.glDepthRange(0, 1)
        GL.glDepthFunc(GL.GL_LESS)

    def dispose_gl(self):
        self.raster.dispose_gl()
        if self.vao:
            GL.glDeleteVertexArrays(1, [self.vao,])
        if self.shader:
            GL.glDeleteProgram(self.shader)


class InfiniteBackground(BasicShaderComponent):
    """
    Proxy geometry representing a spherical panorama at infinite distance.
    For example the celestial sphere of stars and planets and other distant objects.
    """
    def frag_shader_decl_substring(self):
        return shader_substring("""
            vec3 adjusted_view_direction(in vec3 local_view_direction, in vec3 eye_location)
            {
                return local_view_direction; // there is no parallax at infinite distance
            }
            """)


class InfinitePlane(BasicShaderComponent):
    def __init__(self, plane_equation=[0, 1, 0, 0]):
        self.plane_equation = plane_equation

    def vrtx_shader_decl_substring(self):
        p = self.plane_equation
        return shader_substring("""
            const vec4 plane_in_world = vec4(%f, %f, %f, %f);

            flat out vec4 plane_intersection;
        """ % (p[0], p[1], p[2], p[3]))

    def vrtx_shader_main_substring(self):
        return shader_substring("""
            mat4 eye_from_world = inverse(transpose(model_view));
            vec4 plane_in_eye = eye_from_world * plane_in_world;
            vec4 view_in_eye4 = model_view * vec4(viewDir, 0);
            vec3 view_in_eye = view_in_eye4.xyz / view_in_eye4.w;
            float w = -dot(plane_in_eye.xyz, view_in_eye) / plane_in_eye.w;
            vec4 intersection_in_eye = vec4(view_in_eye, w);
            plane_intersection = intersection_in_eye; // in ndc
        """)
    
    """
    Proxy geometry representing a spherical panorama at infinite distance.
    For example the celestial sphere of stars and planets and other distant objects.
    """
    def frag_shader_decl_substring(self):
        p = self.plane_equation
        return shader_substring("""
            layout(location = 1) uniform mat4 projection = mat4(1);
            const vec3 original_camera_position = vec3(0, 2, 0); // todo: pass in as uniform
            const vec4 plane_equation = vec4(%f, %f, %f, %f);
            flat in vec4 plane_intersection;

            vec3 adjusted_view_direction(in vec3 local_view_direction, in vec3 eye_location)
            {

                // This approach gains numerical stability by never
                // explicitly generating plane intersection points; especially
                // near the horizon.
                // Compute perpendicular distance between plane and local viewpoint
                float h1 = dot(vec4(eye_location, 1), plane_equation);
                if (h1 < 0) 
                    discard; // current viewpoint is under the plane
                float discrim = dot(plane_equation.xyz, local_view_direction);
                if (discrim > 0)
                    discard; // view direction does not intersect the plane
                // component of view direction orthogonal to plane
                vec3 d_orth = discrim * plane_equation.xyz;
                // component of view direction parallel to plane
                vec3 d_par = local_view_direction - d_orth;
                // 1) First scale view vector by relative distance from plane.
                // Because original camera height (h0) is more stable than current
                // viewpoint height (h1), use h0 as the denominator and scale
                // the parallel component (as opposed to h1 denominator and
                // orthogonal component) of the view direction.
                float h0 = dot(vec4(original_camera_position, 1), plane_equation);
                d_par = d_par * (h1 / h0); // OK
                // 2) Shift viewpoint by parallel offset
                vec3 dv = eye_location - original_camera_position;
                vec3 dv_orth = dot(plane_equation.xyz, dv) * plane_equation.xyz;
                vec3 dv_par = dv - dv_orth;
                d_par += dv_par * (length(d_orth) / h0); // converts from meters to whatever units view direction has

                // todo: set gl_FragDepth...
                // gl_FragDepth = 1.0;
                // z-component of local view direction
                float z_depth_in_eye = plane_intersection.z / plane_intersection.w;
                vec4 z_depth_in_ndc = projection * vec4(0, 0, z_depth_in_eye, 1);
                float depth = z_depth_in_ndc.z / z_depth_in_ndc.w;
                
                if (depth < 0) discard;
                if (depth > 1) depth = 1;
                // gl_FragDepth = depth; // todo: not working yet

                return d_par + d_orth; // reconstruct full view direction from two components
            }
            """ % (p[0], p[1], p[2], p[3]))


if __name__ == "__main__":
    # Open equirectangular photosphere
    import os

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
    renderer = OpenVrGlRenderer([actor1, actor2,])
    with GlfwApp(renderer, "photosphere test") as glfwApp:
        glfwApp.run_loop()
