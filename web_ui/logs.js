/**
 * AIChat Server 实时日志查看器脚本
 */
document.addEventListener('DOMContentLoaded', () => {
    const logOutput = document.getElementById('log-output');
    const logContainer = document.getElementById('log-container');
    const logStatus = document.getElementById('log-status');
    const clearLogBtn = document.getElementById('clear-log-btn');
    const autoscrollChk = document.getElementById('autoscroll-chk');

    let ws;
    let retryTimeout = 1000; // 初始重连延迟

    function connect() {
        // 构造 WebSocket URL
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/logs`;

        logStatus.textContent = '连接中...';
        logStatus.className = 'connecting';

        try {
            ws = new WebSocket(wsUrl);
        } catch (e) {
            console.error('WebSocket connection failed:', e);
            logStatus.textContent = '连接失败';
            logStatus.className = 'disconnected';
            return;
        }

        ws.onopen = () => {
            console.log('Log WebSocket connected.');
            logStatus.textContent = '已连接';
            logStatus.className = 'connected';
            retryTimeout = 1000; // 重置重连计时器
        };

        ws.onmessage = (event) => {
            const line = event.data;
            logOutput.textContent += line;

            // 检查是否需要自动滚动
            if (autoscrollChk.checked) {
                // 滚动到底部
                logContainer.scrollTop = logContainer.scrollHeight;
            }
        };

        ws.onclose = () => {
            console.log('Log WebSocket disconnected.');
            logStatus.textContent = '已断开';
            logStatus.className = 'disconnected';

            // 尝试重连，使用指数退避
            setTimeout(() => {
                console.log('Reconnecting...');
                retryTimeout = Math.min(retryTimeout * 2, 10000); // 最多10秒
                connect();
            }, retryTimeout);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            logStatus.textContent = '连接错误';
            logStatus.className = 'disconnected';
            ws.close(); // 确保触发 onclose 以便重连
        };
    }

    // 清空日志按钮
    clearLogBtn.addEventListener('click', () => {
        logOutput.textContent = '';
    });

    // 初始连接
    connect();
});
