#!/usr/bin/env python3
"""
AIChat 实时日志系统 - 验证脚本
用于检查配置是否正确且所有组件就绪
"""

import os
import sys
import importlib.util
from pathlib import Path

def check_file_exists(path, description):
    """检查文件是否存在"""
    if os.path.exists(path):
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description} 未找到: {path}")
        return False

def check_import(module_name, description):
    """检查模块是否可导入"""
    try:
        importlib.import_module(module_name)
        print(f"✅ {description} 模块已安装")
        return True
    except ImportError as e:
        print(f"❌ {description} 模块未安装: {e}")
        return False

def check_python_code_syntax(filepath, description):
    """检查Python文件语法"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, filepath, 'exec')
        print(f"✅ {description} 语法正确")
        return True
    except SyntaxError as e:
        print(f"❌ {description} 语法错误: {e}")
        return False

def main():
    print("=" * 70)
    print("AIChat 实时日志系统 - 部署验证")
    print("=" * 70)
    print()

    server_dir = os.path.dirname(os.path.abspath(__file__))
    web_ui_dir = os.path.join(server_dir, "web_ui")
    
    all_passed = True

    # 检查关键文件
    print("📁 文件完整性检查:")
    print("-" * 70)
    
    files_to_check = [
        (os.path.join(server_dir, "config_ui.py"), "配置UI主文件"),
        (os.path.join(server_dir, "main.py"), "主服务入口"),
        (os.path.join(server_dir, "requirements.txt"), "依赖文件"),
        (os.path.join(web_ui_dir, "config.html"), "配置页面"),
        (os.path.join(web_ui_dir, "config.js"), "配置页面脚本"),
        (os.path.join(web_ui_dir, "config.css"), "配置页面样式"),
        (os.path.join(web_ui_dir, "logs.html"), "日志页面"),
        (os.path.join(web_ui_dir, "logs.js"), "日志页面脚本"),
    ]
    
    for file_path, description in files_to_check:
        if not check_file_exists(file_path, description):
            all_passed = False
    
    print()

    # 检查Python依赖
    print("📦 Python 依赖检查:")
    print("-" * 70)
    print("⚠️  注意：在虚拟环境中应已安装这些包")
    print("   请确保运行了: pip install -r requirements.txt")
    print()
    
    required_packages = [
        ("fastapi", "FastAPI Web框架"),
        ("uvicorn", "ASGI服务器"),
        ("pydantic", "数据验证"),
        ("websockets", "WebSocket支持"),
    ]
    
    missing_packages = False
    for package, description in required_packages:
        if not check_import(package, description):
            missing_packages = True
    
    if missing_packages:
        print()
        print("💡 提示：如果运行在虚拟环境中，请执行:")
        print("   pip install -r requirements.txt")
        print()
    
    print()

    # 检查Python代码语法
    print("🔍 Python 代码语法检查:")
    print("-" * 70)
    
    python_files = [
        (os.path.join(server_dir, "config_ui.py"), "配置UI主文件"),
    ]
    
    for file_path, description in python_files:
        if os.path.exists(file_path):
            if not check_python_code_syntax(file_path, description):
                all_passed = False
        else:
            print(f"⚠️  {description} 未找到，跳过语法检查")
    
    print()

    # 检查关键代码片段
    print("🔎 关键功能检查:")
    print("-" * 70)
    
    config_ui_path = os.path.join(server_dir, "config_ui.py")
    if os.path.exists(config_ui_path):
        with open(config_ui_path, 'r', encoding='utf-8') as f:
            config_ui_content = f.read()
        
        checks = [
            ("log_queue: queue.Queue", "日志队列定义"),
            ("async def websocket_broadcaster", "WebSocket广播函数"),
            ("def log_reader_thread", "日志读取线程"),
            ("@app.websocket(\"/ws/logs\")", "WebSocket端点"),
            ("PYTHONUNBUFFERED", "无缓冲输出环境变量"),
        ]
        
        for code_snippet, description in checks:
            if code_snippet in config_ui_content:
                print(f"✅ {description} 已实现")
            else:
                print(f"❌ {description} 未找到")
                all_passed = False
    
    # 检查logs.html
    logs_html_path = os.path.join(web_ui_dir, "logs.html")
    if os.path.exists(logs_html_path):
        with open(logs_html_path, 'r', encoding='utf-8') as f:
            logs_html_content = f.read()
        
        html_checks = [
            ('<pre id="log-output">', "日志输出区域"),
            ('id="log-status"', "连接状态指示器"),
            ('id="autoscroll-chk"', "自动滚动选项"),
            ('id="clear-log-btn"', "清空日志按钮"),
        ]
        
        for html_snippet, description in html_checks:
            if html_snippet in logs_html_content:
                print(f"✅ {description} 已实现")
            else:
                print(f"❌ {description} 未找到")
                all_passed = False
    
    # 检查logs.js
    logs_js_path = os.path.join(web_ui_dir, "logs.js")
    if os.path.exists(logs_js_path):
        with open(logs_js_path, 'r', encoding='utf-8') as f:
            logs_js_content = f.read()
        
        js_checks = [
            ("new WebSocket", "WebSocket连接"),
            ("ws.onmessage", "消息接收处理"),
            ("ws.onclose", "连接关闭处理"),
            ("function connect()", "连接函数"),
            ("retryTimeout", "重连延迟机制"),
        ]
        
        for js_snippet, description in js_checks:
            if js_snippet in logs_js_content:
                print(f"✅ {description} 已实现")
            else:
                print(f"❌ {description} 未找到")
                all_passed = False
    
    # 检查config.html导航
    config_html_path = os.path.join(web_ui_dir, "config.html")
    if os.path.exists(config_html_path):
        with open(config_html_path, 'r', encoding='utf-8') as f:
            config_html_content = f.read()
        
        if '/logs.html' in config_html_content and '📜' in config_html_content:
            print(f"✅ 导航菜单已添加日志链接")
        else:
            print(f"❌ 导航菜单中的日志链接未找到")
            all_passed = False
    
    print()
    print("=" * 70)
    
    if all_passed:
        print("🎉 验证完成！所有检查都已通过！")
        print()
        print("后续步骤:")
        print("1. 激活虚拟环境: conda activate ./AIChatServerEnv")
        print("2. 启动服务: ./entrypoint.sh")
        print("3. 访问配置页: http://localhost:8080/config.html")
        print("4. 查看日志: http://localhost:8080/logs.html")
        print()
        return 0
    else:
        print("⚠️  验证发现问题，请检查上述错误信息")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
