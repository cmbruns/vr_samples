'''
Created on Apr 18, 2017

@author: brunsc
'''

import math

import numpy

class GlMatrix(object):
    '''
    Wrapper around numpy.matrix providing obsolete OpenGL-like API.
    Except these matrices are column major, so the method definitions
    can better resemble the OpenGL docs.
    So remember to use pre-multiplication to compose these matrices.
    And use the bytes() method to get a transposed flattened version for 
    use in calls to, say,
        glUniformMatrix4fv(...,..., False, foo.bytes())
        or
        glUniformMatrix4fv(...,..., True, foo.bytes(False))
    '''

    _dtype = numpy.float32
    
    def __init__(self, data):
        self._matrix = numpy.matrix(data, dtype=self._dtype)
        
    def __getitem__(self, key):
        return self._matrix[key]
    
    def __setitem__(self, key, value):
        self._matrix[key] = value
        
    def __mul__(self, rhs):
        return GlMatrix(self._matrix * rhs._matrix)
    
    def bytes(self, do_transpose=True):
        if do_transpose:
            return numpy.ascontiguousarray(self._matrix.T, dtype=self._dtype)
        else:
            return numpy.ascontiguousarray(self._matrix, dtype=self._dtype)
    
    @staticmethod
    def frustum(left, right, bottom, top, zNear, zFar):
        A = (right + left) / (right - left)
        B = (top + bottom) / (top - bottom)
        C = -(zFar + zNear) / (zFar - zNear)
        D = -(2.0 * zFar * zNear) / (zFar - zNear)
        return GlMatrix([
                [2.0 * zNear / (right - left), 0.0, A, 0.0],
                [0.0, 2.0 * zNear / (top - bottom), B, 0.0],
                [0.0, 0.0, C, D],
                [0.0, 0.0, -1.0, 0.0]])

    @staticmethod
    def identity():
        return GlMatrix([
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]])
    
    @staticmethod
    def ortho(l, r, b, t, n, f):
        return GlMatrix([
                [2.0/(r-l), 0, 0, -(r+l)/(r-l)],
                [0, 2.0/(t-b), 0, -(t+b)/(t-b)],
                [0, 0, -2.0/(f-n), -(f+n)/(f-n)],
                [0, 0, 0, 1]])

    @staticmethod
    def perspective(fovY, aspect, zNear, zFar):
        fH = math.tan(fovY / 2.0 / 180.0 * math.pi) * zNear
        fW = fH * aspect
        return GlMatrix.frustum(-fW, fW, -fH, fH, zNear, zFar)

    @staticmethod
    def rotate_Z(angle):
        s = math.sin(float(angle))
        c = math.cos(float(angle))
        return GlMatrix([
                [c, -s, 0, 0],
                [s, c, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]])

    @staticmethod
    def translate(xyz):
        x, y, z = xyz
        return GlMatrix([
                [1, 0, 0, x],
                [0, 1, 0, y],
                [0, 0, 1, z],
                [0, 0, 0, 1]])
        