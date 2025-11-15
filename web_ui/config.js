// AIChat Server - Unified Config & Logs UI
// Supports dual-panel layout with top navbar and real-time logs

let currentSection = 'api';
let configData = {};
let originalApiKey = '';
let ws;
let retryTimeout = 1000;

// === Initialize on page load ===
document.addEventListener('DOMContentLoaded', function() {
    setupTopNavigation();
    setupLogsPanel();
    loadConfiguration();
    setupFormBindings();
});

// === Top Navigation ===
function setupTopNavigation() {
    const navItems = document.querySelectorAll('.navbar-item');
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const section = this.dataset.section;
            if (section) switchSection(section);
        });
    });
}

function switchSection(section) {
    document.querySelectorAll('.navbar-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelectorAll('.config-section').forEach(sec => {
        sec.classList.remove('active');
    });
    
    const navEl = document.querySelector('[data-section="' + section + '"]');
    const secEl = document.getElementById(section + '-section');
    
    if (navEl) navEl.classList.add('active');
    if (secEl) {
        secEl.classList.add('active');
        try {
            secEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } catch (e) {
            secEl.scrollIntoView();
        }
    }
    currentSection = section;
}

// === Logs Panel ===
function setupLogsPanel() {
    const clearBtn = document.getElementById('clear-log-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            document.getElementById('log-output').textContent = '';
        });
    }
    connectLogs();
}

function connectLogs() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = wsProtocol + '//' + window.location.host + '/ws/logs';
    
    updateLogStatus('连接中...', 'connecting');
    
    try {
        ws = new WebSocket(wsUrl);
    } catch (e) {
        console.error('WebSocket connection failed:', e);
        updateLogStatus('连接失败', 'disconnected');
        return;
    }
    
    ws.onopen = function() {
        console.log('Log WebSocket connected');
        updateLogStatus('已连接', 'connected');
        retryTimeout = 1000;
    };
    
    ws.onmessage = function(event) {
        const logOutput = document.getElementById('log-output');
        logOutput.textContent += event.data;
        
        const autoscrollChk = document.getElementById('autoscroll-chk');
        if (autoscrollChk && autoscrollChk.checked) {
            const logsContainer = document.querySelector('.logs-container');
            logsContainer.scrollTop = logsContainer.scrollHeight;
        }
    };
    
    ws.onclose = function() {
        console.log('Log WebSocket disconnected');
        updateLogStatus('已断开', 'disconnected');
        
        setTimeout(function() {
            retryTimeout = Math.min(retryTimeout * 2, 10000);
            connectLogs();
        }, retryTimeout);
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
        updateLogStatus('连接错误', 'disconnected');
        ws.close();
    };
}

function updateLogStatus(text, status) {
    const statusEl = document.getElementById('log-status');
    if (statusEl) {
        statusEl.textContent = text;
        statusEl.classList.remove('connecting', 'connected', 'disconnected');
        statusEl.classList.add(status);
    }
}

// === Config Loading ===
async function loadConfiguration() {
    showLoading(true);
    
    try {
        const response = await fetch('/api/config');
        const result = await response.json();
        
        if (result.success) {
            configData = result.data;
            originalApiKey = result.data.ALIYUN_API_KEY || '';
            populateForm(result.data);
            showNotification('配置加载成功', 'success');
        } else {
            showNotification('加载配置失败：' + (result.error || '未知错误'), 'error');
        }
    } catch (error) {
        console.error('Error loading config:', error);
        showNotification('加载配置异常：' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function populateForm(data) {
    // API Config
    const el1 = document.getElementById('ACCESS_TOKEN');
    if (el1) el1.value = data.ACCESS_TOKEN || '123456';
    
    const el2 = document.getElementById('ALIYUN_API_KEY');
    if (el2) el2.value = data.ALIYUN_API_KEY || '';
    
    // Model Config
    const el3 = document.getElementById('CHAT_MODEL');
    if (el3) el3.value = data.CHAT_MODEL || 'qwen-turbo';
    
    const el4 = document.getElementById('INTENT_MODEL');
    if (el4) el4.value = data.INTENT_MODEL || 'qwen-turbo';
    
    const el5 = document.getElementById('SYSTEM_PROMPT');
    if (el5) el5.value = data.SYSTEM_PROMPT || '你是一个桌面机器人, 快速地回复我.';
    
    const el6 = document.getElementById('API_TIMEOUT');
    if (el6) el6.value = data.API_TIMEOUT || 10;
    
    // Hardware Config
    const el7 = document.getElementById('ASR_DEVICE');
    if (el7) el7.value = data.ASR_DEVICE || 'cpu';
    
    const el8 = document.getElementById('VAD_DEVICE');
    if (el8) el8.value = data.VAD_DEVICE || 'cpu';
    
    // AI Persona Config
    if (data.ai_persona) {
        const el9 = document.getElementById('botName');
        if (el9) el9.value = data.ai_persona.bot_name || '小凡';
        
        const el10 = document.getElementById('systemContent');
        if (el10) el10.value = data.ai_persona.system_content || '';
        
        const el11 = document.getElementById('backgroundFacts');
        if (el11) {
            if (data.ai_persona.background_facts && Array.isArray(data.ai_persona.background_facts)) {
                el11.value = data.ai_persona.background_facts.join('\n');
            } else if (data.ai_persona.backgroundFacts) {
                el11.value = data.ai_persona.backgroundFacts.join('\n');
            }
        }
    }
}

// === Config Save ===
async function saveConfig() {
    const saveBtn = document.getElementById('saveBtn');
    const originalText = saveBtn.textContent;
    
    try {
        const apiKeyInput = document.getElementById('ALIYUN_API_KEY');
        if (!apiKeyInput) {
            console.error('API Key input not found');
            return;
        }
        
        const apiKey = apiKeyInput.value;
        if (!apiKey || (apiKey.includes('*') && apiKey === originalApiKey)) {
            showNotification('请输入有效的阿里云 API Key', 'error');
            switchSection('api');
            apiKeyInput.focus();
            return;
        }
        
        saveBtn.disabled = true;
        saveBtn.textContent = '保存中...';
        
        const backgroundFactsEl = document.getElementById('backgroundFacts');
        const backgroundFacts = backgroundFactsEl.value
            .split('\n')
            .map(function(line) { return line.trim(); })
            .filter(function(line) { return line.length > 0; });
        
        const config = {
            ACCESS_TOKEN: document.getElementById('ACCESS_TOKEN').value,
            ALIYUN_API_KEY: apiKeyInput.value,
            CHAT_MODEL: document.getElementById('CHAT_MODEL').value,
            INTENT_MODEL: document.getElementById('INTENT_MODEL').value,
            SYSTEM_PROMPT: document.getElementById('SYSTEM_PROMPT').value,
            ASR_DEVICE: document.getElementById('ASR_DEVICE').value,
            VAD_DEVICE: document.getElementById('VAD_DEVICE').value,
            API_TIMEOUT: parseInt(document.getElementById('API_TIMEOUT').value) || 10,
            ai_persona: {
                bot_name: document.getElementById('botName').value,
                system_content: document.getElementById('systemContent').value,
                background_facts: backgroundFacts
            }
        };
        
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            showNotification('配置已保存成功！', 'success');
            originalApiKey = apiKeyInput.value;
            configData = config;
        } else {
            showNotification('保存失败：' + (result.error || result.detail || '未知错误'), 'error');
        }
    } catch (error) {
        console.error('Error saving config:', error);
        showNotification('保存异常：' + error.message, 'error');
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;
    }
}

// === Service Restart ===
async function restartService() {
    const restartBtn = document.getElementById('restartBtn');
    if (!restartBtn) return;
    
    const originalText = restartBtn.textContent;
    
    if (!confirm('确定要重启 AI 聊天服务吗？WebSocket 连接将保持。')) {
        return;
    }
    
    try {
        restartBtn.disabled = true;
        restartBtn.textContent = '重启中...';
        
        const response = await fetch('/api/service/restart', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            showNotification('✅ AI 聊天服务已重启！WebSocket 连接保持，日志将继续显示。', 'success');
            restartBtn.disabled = false;
            restartBtn.textContent = originalText;
        } else {
            showNotification('❌ 重启失败：' + (result.message || '未知错误'), 'error');
            restartBtn.disabled = false;
            restartBtn.textContent = originalText;
        }
    } catch (error) {
        console.error('Error restarting service:', error);
        showNotification('❌ 重启失败：' + error.message, 'error');
        restartBtn.disabled = false;
        restartBtn.textContent = originalText;
    }
}

// === Utilities ===
function togglePasswordVisibility() {
    const apiKeyInput = document.getElementById('ALIYUN_API_KEY');
    const showCheckbox = document.getElementById('showApiKey');
    
    if (apiKeyInput && showCheckbox) {
        apiKeyInput.type = showCheckbox.checked ? 'text' : 'password';
    }
}

function showLoading(show) {
    const loading = document.getElementById('loading');
    if (loading) {
        loading.style.display = show ? 'flex' : 'none';
    }
}

function showNotification(message, type) {
    type = type || 'info';
    const notification = document.getElementById('notification');
    const notificationMessage = document.getElementById('notificationMessage');
    if (!notification || !notificationMessage) return;
    
    notification.classList.remove('success', 'error', 'warning', 'show');
    notification.classList.add(type);
    notificationMessage.textContent = message;
    
    void notification.offsetWidth;
    notification.classList.add('show');
    
    setTimeout(function() {
        closeNotification();
    }, 5000);
}

function closeNotification() {
    const notification = document.getElementById('notification');
    if (notification) {
        notification.classList.remove('show');
    }
}

// === Form Bindings ===
function setupFormBindings() {
    const form = document.getElementById('configForm');
    if (form) {
        form.addEventListener('input', function() {
            validateForm();
        });
    }
    
    const showApiKey = document.getElementById('showApiKey');
    if (showApiKey) {
        showApiKey.addEventListener('change', togglePasswordVisibility);
    }
    
    const saveBtn = document.getElementById('saveBtn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveConfig);
    }
    
    const restartBtn = document.getElementById('restartBtn');
    if (restartBtn) {
        restartBtn.addEventListener('click', restartService);
    }
}

function validateForm() {
    const apiKeyEl = document.getElementById('ALIYUN_API_KEY');
    const apiKey = apiKeyEl ? apiKeyEl.value : '';
    // Additional validation can be added here
}

// === Keyboard Shortcuts ===
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        if (document.getElementById('configForm')) {
            e.preventDefault();
            saveConfig();
        }
    }
});
