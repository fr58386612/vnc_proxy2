#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VNC代理服务器打包脚本
使用PyInstaller将应用打包为exe文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description=""):
    """运行命令并检查结果"""
    print(f"\n{'='*50}")
    print(f"执行: {description}")
    print(f"命令: {cmd}")
    print(f"{'='*50}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ 执行成功")
        if result.stdout:
            print("输出:", result.stdout)
    else:
        print("❌ 执行失败")
        print("错误:", result.stderr)
        if result.stdout:
            print("输出:", result.stdout)
        return False
    return True

def check_dependencies():
    """检查和安装依赖"""
    print("检查Python环境和依赖...")
    
    # 检查Python版本
    print(f"Python版本: {sys.version}")
    
    # 检查是否在虚拟环境中
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ 检测到虚拟环境")
    else:
        print("⚠️  建议在虚拟环境中运行")
    
    return True

def install_dependencies():
    """安装依赖"""
    print("\n安装项目依赖...")
    
    # 使用uv安装依赖
    commands = [
        ("uv pip install pillow>=10.0.0", "安装Pillow"),
        ("uv pip install pystray>=0.19.4", "安装pystray"),
        ("uv pip install pyinstaller>=5.0", "安装PyInstaller"),
    ]
    
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            print(f"❌ 安装失败: {desc}")
            return False
    
    return True

def create_spec_file():
    """创建PyInstaller规格文件"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['vnc_proxy.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PIL._tkinter_finder',
        'pystray._base',
        'pystray._win32',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VNC代理服务器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为False隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
'''
    
    with open('vnc_proxy.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ 创建PyInstaller规格文件: vnc_proxy.spec")

def create_icon():
    """创建应用图标"""
    try:
        from PIL import Image, ImageDraw
        
        # 创建图标
        image = Image.new('RGB', (256, 256), color='#0066CC')
        draw = ImageDraw.Draw(image)
        
        # 绘制背景
        draw.rectangle([32, 32, 224, 224], fill='white', outline='#0066CC', width=8)
        
        # 绘制VNC文字
        # 由于PIL的文字渲染有限，我们画简单的图形来表示
        draw.rectangle([64, 80, 96, 176], fill='#0066CC')  # V的左边
        draw.rectangle([96, 144, 128, 176], fill='#0066CC')  # V的中间
        draw.rectangle([128, 80, 160, 176], fill='#0066CC')  # V的右边
        
        # N
        draw.rectangle([180, 80, 212, 176], fill='#0066CC')  # N的左边
        draw.rectangle([180, 80, 244, 112], fill='#0066CC')  # N的顶部
        draw.rectangle([212, 112, 244, 144], fill='#0066CC')  # N的中间
        draw.rectangle([212, 144, 244, 176], fill='#0066CC')  # N的右边
        
        # 保存为ICO格式
        image.save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        print("✅ 创建应用图标: icon.ico")
        return True
        
    except Exception as e:
        print(f"⚠️  创建图标失败: {e}")
        return False

def build_exe():
    """构建exe文件"""
    print("\n开始构建exe文件...")
    
    # 清理之前的构建
    if os.path.exists('dist'):
        shutil.rmtree('dist')
        print("清理dist目录")
    
    if os.path.exists('build'):
        shutil.rmtree('build')
        print("清理build目录")
    
    # 使用PyInstaller构建
    cmd = "pyinstaller --clean vnc_proxy.spec"
    if not run_command(cmd, "使用PyInstaller构建exe文件"):
        return False
    
    # 检查输出文件
    exe_path = Path("dist/VNC代理服务器.exe")
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✅ 构建成功！")
        print(f"   文件位置: {exe_path.absolute()}")
        print(f"   文件大小: {size_mb:.1f} MB")
        return True
    else:
        print("❌ 构建失败，未找到输出文件")
        return False

def main():
    """主函数"""
    print("VNC代理服务器 - 打包工具")
    print("=" * 50)
    
    try:
        # 检查环境
        if not check_dependencies():
            return False
        
        # 安装依赖
        if not install_dependencies():
            return False
        
        # 创建图标
        create_icon()
        
        # 创建规格文件
        create_spec_file()
        
        # 构建exe
        if not build_exe():
            return False
        
        print("\n" + "=" * 50)
        print("🎉 打包完成！")
        print("可执行文件位于: dist/VNC代理服务器.exe")
        print("双击运行即可启动VNC代理服务器")
        print("=" * 50)
        
        return True
        
    except KeyboardInterrupt:
        print("\n❌ 用户取消操作")
        return False
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)