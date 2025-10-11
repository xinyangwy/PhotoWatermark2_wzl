# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 定义数据文件和目录
datas = [
    ('resources', 'resources'),
    ('images', 'images'),
    ('config', 'config'),
]

# 定义隐藏的导入
hiddenimports = [
    'PyQt6.sip'
]

# 设置打包选项
a = Analysis(['main.py'],
             pathex=[],
             binaries=[],
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 创建单文件EXE
# 单文件模式下，所有依赖库和资源都将被打包到一个EXE文件中
exe = EXE(pyz,
          a.scripts,
          a.binaries,  # 包含所有二进制文件
          a.zipfiles,
          a.datas,     # 包含所有数据文件
          [],
          name='PhotoMark',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,  # 不显示控制台窗口
          icon='resources/icon.ico',
          onefile=True)  # 启用单文件模式

# 单文件模式不需要COLLECT步骤