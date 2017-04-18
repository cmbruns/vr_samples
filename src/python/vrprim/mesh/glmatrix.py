'''
Created on Apr 18, 2017

@author: brunsc
'''

import math

import numpy

class GlMatrix(numpy.matrix):
    '''
    Wrapper around numpy.matrix providing obsolete OpenGL-like API.
    '''

    @staticmethod
    def matrixbytes(matrix, do_transpose=False):
        if do_transpose:
            return numpy.ascontiguousarray(matrix.T)
        else:
            return numpy.ascontiguousarray(matrix)
    
    @staticmethod
    def frustum(left, right, bottom, top, zNear, zFar):
        A = (right + left) / (right - left)
        B = (top + bottom) / (top - bottom)
        C = -(zFar + zNear) / (zFar - zNear)
        D = -(2.0 * zFar * zNear) / (zFar - zNear)
        return numpy.matrix([
                [2.0 * zNear / (right - left), 0.0, A, 0.0],
                [0.0, 2.0 * zNear / (top - bottom), B, 0.0],
                [0.0, 0.0, C, D],
                [0.0, 0.0, -1.0, 0.0]], dtype=numpy.float32).T

    @staticmethod
    def identity():
        return numpy.matrix([
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]], dtype=numpy.float32)
    
    @staticmethod
    def ortho(l, r, b, t, n, f):
        return numpy.matrix([
                [2.0/(r-l), 0, 0, -(r+l)/(r-l)],
                [0, 2.0/(t-b), 0, -(t+b)/(t-b)],
                [0, 0, -2.0/(f-n), -(f+n)/(f-n)],
                [0, 0, 0, 1]], dtype=numpy.float32).T

    @staticmethod
    def perspective(fovY, aspect, zNear, zFar):
        fH = math.tan(fovY / 2.0 / 180.0 * math.pi) * zNear
        fW = fH * aspect
        return GlMatrix.frustum(-fW, fW, -fH, fH, zNear, zFar)

    @staticmethod
    def rotate_X(angle):
        s = math.sin(float(angle))
        c = math.cos(float(angle))
        return numpy.matrix([
                [1, 0, 0, 0],
                [0, c, -s, 0],
                [0, s, c, 0],
                [0, 0, 0, 1]], dtype=numpy.float32).T

    @staticmethod
    def rotate_Z(angle):
        s = math.sin(float(angle))
        c = math.cos(float(angle))
        return numpy.matrix([
                [c, -s, 0, 0],
                [s, c, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]], dtype=numpy.float32).T

    @staticmethod
    def translate(xyz):
        x, y, z = xyz
        array = [
                [1, 0, 0, x],
                [0, 1, 0, y],
                [0, 0, 1, z],
                [0, 0, 0, 1]]
        mat = numpy.matrix(array, dtype=numpy.float32)
        return mat.T
        