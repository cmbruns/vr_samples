import os
import pkg_resources

import glfw
from PIL import Image
import numpy

from openvr.glframework.glfw_app import GlfwApp
from openvr.glframework.glmatrix import rotate_y, scale
from openvr.gl_renderer import OpenVrGlRenderer
from openvr.tracked_devices_actor import TrackedDevicesActor
from vrprim.photosphere import SphericalPanorama, CubeMapRaster, InfiniteBackground, InfinitePlane
from vrprim.mesh.teapot import TeapotActor

if __name__ == "__main__":

    # 1) Spherical panorama
    img_stream = pkg_resources.resource_stream('vrprim.photosphere', 'lauterbrunnen/cube.jpg')
    img = Image.open(img_stream)
    img_data = numpy.array(img)
    raster = CubeMapRaster(img_array=img_data)
    environment_actor = SphericalPanorama(raster=raster, proxy_geometry=InfiniteBackground())
    # 2) Infinite ground plane
    ground_actor = SphericalPanorama(raster=raster, proxy_geometry=InfinitePlane(plane_equation=[0, 1, 0, -0.05]))
    # 3) Teapot mesh
    teapot_actor = TeapotActor()
    s = 0.2  # size of teapot in meters
    # 4) Controllers
    # todo:

    actors = [
        environment_actor,  # infinite sky
        ground_actor,  # parallax corrected ground plane
        teapot_actor,
    ]
    renderer = OpenVrGlRenderer(actors, multisample=4)
    with GlfwApp(renderer, "photosphere test") as glfw_app:
        controllers = TrackedDevicesActor(glfw_app.renderer.poses)
        renderer.append(controllers)
        while not glfw.window_should_close(glfw_app.window):
            # scale teapot to original Melitta model aspect ratio
            teapot_actor.model_matrix = scale(s, s*4/3, s) * rotate_y(glfw.get_time())
            glfw_app.render_scene()
