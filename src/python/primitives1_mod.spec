# -*- mode: python -*-

block_cipher = None


a = Analysis(['vrprim\\primitives1.py', 'primitives1.spec'],
             pathex=['E:\\brunsc\\git\\vr_samples\\src\\python'],
             binaries=[
                    ('C:/Users/brunsc/git/pyopenvr/src/openvr/libopenvr_api_32.dll', '.'),
                    ],
             datas=[
                    ('vrprim/photosphere/lauterbrunnen/cube.jpg', 'vrprim/photosphere/lauterbrunnen'),
                    ('vrprim/mesh/wt_teapot.obj', 'vrprim/mesh'),
                    ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='primitives1',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='primitives1')
