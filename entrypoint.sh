#!/bin/sh
# 启动脚本：首先启动 Web 配置 UI
# Python 主服务由 Web UI 管理其生命周期

# 严格模式
set -e

echo "======================================"
echo "AIChat Server Entrypoint"
echo "======================================"
echo ""

# 默认的配置文件路径，与 Python 中保持一致
CONFIG_FILE=${CONFIG_PATH:-/config/config.json}

echo "🌐 Starting Configuration UI server on port 8080..."
echo ""
echo "======================================"
echo "📋 Configuration Instructions:"
echo "======================================"
echo ""
echo "1. Open your web browser"
echo "2. Navigate to: http://<YOUR_SERVER_IP>:8080"
echo "3. Fill in the configuration form"
echo "4. Click '▶️ 启动服务' to start the AIChat service"
echo ""
echo "Service lifecycle is managed through the Web UI:"
echo "  - ▶️  Start Service   (启动服务)"
echo "  - ⏹️  Stop Service    (停止服务)"
echo "  - 🔄 Restart Service (重启服务)"
echo ""
echo "======================================"
echo ""

# 运行 config_ui.py
exec python ./config_ui.py

