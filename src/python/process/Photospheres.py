'''
Created on Apr 14, 2017

@author: brunsc
'''

import sys

import numpy
from OpenGL import GL
from OpenGL.GL.shaders import compileShader, compileProgram
from PyQt5.QtWidgets import QApplication, QMainWindow, QGridLayout
from PyQt5.uic import loadUi
from PyQt5.QtGui import QImage
from PyQt5.QtNetwork import QNetworkRequest, QNetworkAccessManager
from PyQt5.QtOpenGL import QGLWidget, QGLFormat


class ImageWidget(QGLWidget):
    def __init__(self, *args, **kwargs):
        super(ImageWidget, self).__init__(*args, **kwargs)
        self.setStyleSheet('QWidget { background: blue; }');
        self.image = None
        self.image_needs_upload = False

    def setImage(self, image):
        if self.image is image:
            return # no change
        self.image = image.convertToFormat(QImage.Format_RGBA8888).mirrored()
        self.image_needs_upload = True
        self.repaint()

    def initializeGL(self):
        # print('initializeGL')
        GL.glClearColor(0.5, 0.5, 0.5, 1) # gray
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.texture_handle = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture_handle)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR_MIPMAP_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        vertex_shader = compileShader(
            """#version 450 core
            #line 49
            // projected screen quad
            const vec4 SCREEN_QUAD[4] = vec4[4](
                vec4(-1, -1, 0.5, 1),
                vec4( 1, -1, 0.5, 1),
                vec4( 1,  1, 0.5, 1),
                vec4(-1,  1, 0.5, 1));
            const int TRIANGLE_STRIP_INDICES[4] = int[4](
                0, 1, 3, 2);
            
            out vec2 texCoord;
            
            void main() 
            {
                int vertexIndex = TRIANGLE_STRIP_INDICES[gl_VertexID];
                gl_Position = SCREEN_QUAD[vertexIndex];
                texCoord = 0.5 * (SCREEN_QUAD[vertexIndex].xy + vec2(1));
            }
            """,
            GL.GL_VERTEX_SHADER)
        fragment_shader = compileShader(
            """#version 450 core
            #line 71

            layout(binding = 0) uniform sampler2D image;

            in vec2 texCoord;
            out vec4 pixelColor;
            
            void main() 
            {
                // pixelColor = vec4(1, 1, 0, 1);
                pixelColor = texture(image, texCoord);
            }
            """,
            GL.GL_FRAGMENT_SHADER)
        self.shader = compileProgram(vertex_shader, fragment_shader)
    
    def _uploadImageGL(self):
        # print('uploading')
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        # print('getting bytes')
        bits = self.image.bits()
        bits.setsize(self.image.byteCount())
        # print(bits)
        # print(len(bits))
        w = self.image.width()
        h = self.image.height()
        # print(w, h)
        arr = numpy.array(bits).reshape(h, w, 4)
        # print (arr.shape)
        GL.glTexImage2D(
                GL.GL_TEXTURE_2D,
                0, 
                GL.GL_RGBA,
                self.image.width(),
                self.image.height(),
                0,
                GL.GL_RGBA,
                GL.GL_UNSIGNED_BYTE, 
                arr)
        # print('glTexImage2D')
        GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
        self.image_needs_upload = False
    
    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        # print('paintGL')
        if not self.image:
            return
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture_handle)
        # print(self.texture_handle)
        if self.image_needs_upload:
            self._uploadImageGL()
        # todo:
        # print(self.shader)
        GL.glUseProgram(self.shader)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)

    def resizeGL(self, w, h):
        GL.glViewport(0, 0, w, h)


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        ui = loadUi('Photospheres.ui', self)
        self.setAcceptDrops(True)
        self.webCtrl = QNetworkAccessManager()
        self.webCtrl.finished.connect(self._fileLoaded)
        glFormat = QGLFormat()
        glFormat.setVersion(4, 5)
        glFormat.setProfile(QGLFormat.CoreProfile)
        self.glWidget = ImageWidget(glFormat, parent=ui.centralWidget())
        layout = QGridLayout() # Use a layout, so the GLWidget would resize
        layout.addWidget(self.glWidget)
        ui.centralWidget().setLayout(layout)
        ui.centralWidget().setStyleSheet('QWidget { background: green; }')

    def dragEnterEvent(self, event):
        if not event.mimeData().hasUrls():
            return
        event.accept()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            request = QNetworkRequest(url)
            self.webCtrl.get(request)        

    def _fileLoaded(self, networkReply):
        data = networkReply.readAll()
        # print(len(data))
        # todo: use libtiff or png libraries for 16-bit and 32-bit images
        image = QImage()
        image.loadFromData(data)
        # print(image.width(), image.height())
        # print(image.bitPlaneCount(), image.depth())
        # print(image.format(), image.pixelFormat())
        self.glWidget.setImage(image)


class PhotospheresApp(QApplication):
    def __init__(self, *args, **kwargs):
        super(PhotospheresApp, self).__init__(*args, **kwargs)
        mw = MainWindow()
        mw.show()
        sys.exit(self.exec_())


if __name__ == '__main__':
    PhotospheresApp(sys.argv)
