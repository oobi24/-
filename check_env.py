#!/usr/bin/env python3
"""
环境检查脚本 - 验证Tushare安装
"""
import sys
import os

print("="*70)
print("Python 环境检查")
print("="*70)
print(f"Python 路径: {sys.executable}")
print(f"Python 版本: {sys.version}")
print(f"\nPython 搜索路径:")
for i, path in enumerate(sys.path):
    print(f"  {i}: {path}")

print(f"\n用户site-packages: {os.path.expanduser('~\\AppData\\Roaming\\Python\\Python39\\site-packages')}")

print("\n" + "="*70)
print("检查 Tushare 安装")
print("="*70)

try:
    import tushare as ts
    print(f"✅ Tushare 已安装")
    print(f"   版本: {ts.__version__}")
    print(f"   路径: {ts.__file__}")

    # 测试API调用
    print("\n测试 API 连接...")
    # 这里只是检查模块能否导入，不实际调用API
    print("✅ Tushare 模块可正常导入")

except ImportError as e:
    print(f"❌ Tushare 未安装或未找到")
    print(f"   错误: {e}")
    print(f"\n请运行以下命令安装:")
    print(f"   {sys.executable} -m pip install tushare")

except Exception as e:
    print(f"⚠️ Tushare 导入出错: {e}")

print("\n" + "="*70)
print("检查其他依赖")
print("="*70)

deps = ['pandas', 'numpy', 'tkinter']
for dep in deps:
    try:
        if dep == 'tkinter':
            import tkinter as tk
            print(f"✅ {dep}: 已安装")
        else:
            mod = __import__(dep)
            ver = getattr(mod, '__version__', 'unknown')
            print(f"✅ {dep}: {ver}")
    except ImportError:
        print(f"❌ {dep}: 未安装")

print("\n" + "="*70)
input("按 Enter 键退出...")
