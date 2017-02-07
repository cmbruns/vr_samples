'''
Created on Feb 7, 2017

@author: Christopher M. Bruns
'''

import textwrap
import inspect

class SphereProgram(object):
    '''
    Possible future adjustable options include:
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
       '''
    def __init__(self, glsl_version='450 core'):
        self.glsl_version = glsl_version
        self._cached_vertex_shader = None
        
    def getVertexShader(self):
        '''
        Returns a string containing the GLSL shader source code.
        
        >>> v = SphereProgram().getVertexShader().splitlines()
        
        For testing, skip the second line, which contains a volatile line number
        >>> print(v[0])
        #version 450 core
        >>> print('\\n'.join(v[2:]))
        layout(location = 1) uniform mat4 view_matrix = mat4(1);
        layout(location = 1) in vec3 sphere_center;
        void main() 
        {
            // NOTE: projection is deferred to the geometry shader
            gl_Position = view_matrix * vec4(sphere_center, 1);
        }                
        '''
        if self._cached_vertex_shader is not None:
            return self._cached_vertex_shader
        framerecord = inspect.stack()[0] # cache this line number, to improve shader error messages
        self._cached_vertex_shader = textwrap.dedent(
                '''\
                #version %s
                #line %s
                layout(location = 1) uniform mat4 view_matrix = mat4(1);
                layout(location = 1) in vec3 sphere_center;
                void main() 
                {
                    // NOTE: projection is deferred to the geometry shader
                    gl_Position = view_matrix * vec4(sphere_center, 1);
                }\
                ''' % (self.glsl_version, 
                        framerecord.lineno+5))
        return self._cached_vertex_shader


class SphereActor(object):
    '''
    High-performance display actor for large numbers of spheres
    '''

    def __init__(self, params):
        '''
        Constructor
        '''


if __name__ == '__main__':
    import doctest
    doctest.testmod()
