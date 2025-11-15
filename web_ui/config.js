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
    
    // [修改] 确定唯一的"主"提示词
    // 优先使用 SYSTEM_PROMPT，因为它目前被 chat_service.py 实际使用
    const masterPrompt = data.SYSTEM_PROMPT || '你是一个桌面机器人, 快速地回复我.';
    
    // 填充隐藏的 SYSTEM_PROMPT 字段
    const el5 = document.getElementById('SYSTEM_PROMPT');
    if (el5) el5.value = masterPrompt;
    
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
        if (el9) el9.value = data.ai_persona.bot_name || 'Echo';
        
        // [修改] 填充可见的 systemContent 字段（也使用 masterPrompt）
        const el10 = document.getElementById('systemContent');
        if (el10) el10.value = masterPrompt; // 使用 masterPrompt 保持同步
        
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
        // 1. 验证所有必填项
        const validationResult = validateRequiredFields();
        if (!validationResult.valid) {
            // 如果有错误，跳转到第一个有问题的字段
            if (validationResult.firstErrorSection) {
                switchSection(validationResult.firstErrorSection);
            }
            // 显示详细的错误消息
            showValidationErrorModal(validationResult.errors);
            return;
        }
        
        saveBtn.disabled = true;
        saveBtn.textContent = '保存中...';
        
        const apiKeyInput = document.getElementById('ALIYUN_API_KEY');
        const backgroundFactsEl = document.getElementById('backgroundFacts');
        const backgroundFacts = backgroundFactsEl.value
            .split('\n')
            .map(function(line) { return line.trim(); })
            .filter(function(line) { return line.length > 0; });
        
        // [修改] 从 *唯一可见* 的 "人设描述" 字段获取值
        const masterSystemPrompt = document.getElementById('systemContent').value;
        
        // [可选但推荐] 同步更新隐藏字段的值
        document.getElementById('SYSTEM_PROMPT').value = masterSystemPrompt;

        // [修改] 构建配置对象，将 masterSystemPrompt 同时赋值给两个字段
        const config = {
            ACCESS_TOKEN: document.getElementById('ACCESS_TOKEN').value,
            ALIYUN_API_KEY: apiKeyInput.value,
            CHAT_MODEL: document.getElementById('CHAT_MODEL').value,
            INTENT_MODEL: document.getElementById('INTENT_MODEL').value,
            SYSTEM_PROMPT: masterSystemPrompt, // <-- 从可见的字段获取
            ASR_DEVICE: document.getElementById('ASR_DEVICE').value,
            VAD_DEVICE: document.getElementById('VAD_DEVICE').value,
            API_TIMEOUT: parseInt(document.getElementById('API_TIMEOUT').value) || 10,
            ai_persona: {
                bot_name: document.getElementById('botName').value,
                system_content: masterSystemPrompt, // <-- 从可见的字段获取
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
            // 显示成功的模态框
            showSuccessModal('✅ 配置已保存成功！\n\n所有设置已更新并保存到系统。');
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

// === Validation Functions ===
function validateRequiredFields() {
    const errors = [];
    let firstErrorSection = null;
    
    // 验证 API 配置部分
    const apiKey = document.getElementById('ALIYUN_API_KEY').value.trim();
    if (!apiKey || apiKey.includes('*')) {
        errors.push({ section: 'api', message: '阿里云 API Key（必填）' });
        if (!firstErrorSection) firstErrorSection = 'api';
    }
    
    const accessToken = document.getElementById('ACCESS_TOKEN').value.trim();
    if (!accessToken) {
        errors.push({ section: 'api', message: '访问令牌（必填）' });
        if (!firstErrorSection) firstErrorSection = 'api';
    }
    
    // 验证模型配置部分
    const chatModel = document.getElementById('CHAT_MODEL').value.trim();
    if (!chatModel) {
        errors.push({ section: 'model', message: '聊天模型（必填）' });
        if (!firstErrorSection) firstErrorSection = 'model';
    }
    
    const intentModel = document.getElementById('INTENT_MODEL').value.trim();
    if (!intentModel) {
        errors.push({ section: 'model', message: '意图识别模型（必填）' });
        if (!firstErrorSection) firstErrorSection = 'model';
    }
    
    const systemPrompt = document.getElementById('SYSTEM_PROMPT').value.trim();
    if (!systemPrompt) {
        errors.push({ section: 'model', message: '系统提示词（必填）' });
        if (!firstErrorSection) firstErrorSection = 'model';
    }
    
    const apiTimeout = document.getElementById('API_TIMEOUT').value.trim();
    if (!apiTimeout || isNaN(parseInt(apiTimeout)) || parseInt(apiTimeout) <= 0) {
        errors.push({ section: 'model', message: 'API 超时时间（必填，需为正整数）' });
        if (!firstErrorSection) firstErrorSection = 'model';
    }
    
    // 验证硬件配置部分
    const asrDevice = document.getElementById('ASR_DEVICE').value.trim();
    if (!asrDevice) {
        errors.push({ section: 'hardware', message: '语音识别设备（必填）' });
        if (!firstErrorSection) firstErrorSection = 'hardware';
    }
    
    const vadDevice = document.getElementById('VAD_DEVICE').value.trim();
    if (!vadDevice) {
        errors.push({ section: 'hardware', message: '语音活动检测设备（必填）' });
        if (!firstErrorSection) firstErrorSection = 'hardware';
    }
    
    // 验证 AI Persona 配置部分
    const botName = document.getElementById('botName').value.trim();
    if (!botName) {
        errors.push({ section: 'persona', message: '机器人名称（必填）' });
        if (!firstErrorSection) firstErrorSection = 'persona';
    }
    
    const systemContent = document.getElementById('systemContent').value.trim();
    if (!systemContent) {
        errors.push({ section: 'persona', message: '系统内容/角色定义（必填）' });
        if (!firstErrorSection) firstErrorSection = 'persona';
    }
    
    return {
        valid: errors.length === 0,
        errors: errors,
        firstErrorSection: firstErrorSection
    };
}

// === Modal Functions ===
function showValidationErrorModal(errors) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
    `;
    
    const content = document.createElement('div');
    content.className = 'modal-content';
    content.style.cssText = `
        background: white;
        border-radius: 8px;
        padding: 30px;
        max-width: 500px;
        width: 90%;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        animation: slideIn 0.3s ease-out;
    `;
    
    const header = document.createElement('h2');
    header.textContent = '⚠️ 保存失败';
    header.style.cssText = `
        color: #d32f2f;
        margin: 0 0 20px 0;
        font-size: 20px;
    `;
    
    const message = document.createElement('p');
    message.textContent = '以下必填项未完成，请补充：';
    message.style.cssText = `
        color: #666;
        margin: 0 0 15px 0;
        font-size: 14px;
    `;
    
    const errorList = document.createElement('ul');
    errorList.style.cssText = `
        margin: 0 0 25px 0;
        padding-left: 20px;
        list-style: none;
    `;
    
    errors.forEach(function(error) {
        const li = document.createElement('li');
        li.style.cssText = `
            color: #d32f2f;
            margin-bottom: 8px;
            font-size: 14px;
            padding-left: 25px;
            position: relative;
        `;
        li.textContent = '• ' + error.message;
        errorList.appendChild(li);
    });
    
    const buttonContainer = document.createElement('div');
    buttonContainer.style.cssText = `
        display: flex;
        gap: 10px;
        justify-content: flex-end;
    `;
    
    const confirmBtn = document.createElement('button');
    confirmBtn.textContent = '我已了解，去修改';
    confirmBtn.style.cssText = `
        background: #1976d2;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: background 0.2s;
    `;
    confirmBtn.onmouseover = function() { this.style.background = '#1565c0'; };
    confirmBtn.onmouseout = function() { this.style.background = '#1976d2'; };
    confirmBtn.addEventListener('click', function() {
        document.body.removeChild(modal);
    });
    
    buttonContainer.appendChild(confirmBtn);
    
    content.appendChild(header);
    content.appendChild(message);
    content.appendChild(errorList);
    content.appendChild(buttonContainer);
    
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    // 添加动画样式
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateY(-50px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);
}

function showSuccessModal(message) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
    `;
    
    const content = document.createElement('div');
    content.className = 'modal-content';
    content.style.cssText = `
        background: white;
        border-radius: 8px;
        padding: 30px;
        max-width: 500px;
        width: 90%;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        animation: slideIn 0.3s ease-out;
        text-align: center;
    `;
    
    const successIcon = document.createElement('div');
    successIcon.style.cssText = `
        font-size: 48px;
        margin-bottom: 15px;
    `;
    successIcon.textContent = '✅';
    
    const header = document.createElement('h2');
    header.textContent = '保存成功';
    header.style.cssText = `
        color: #4caf50;
        margin: 0 0 15px 0;
        font-size: 20px;
    `;
    
    const messageEl = document.createElement('p');
    messageEl.textContent = message;
    messageEl.style.cssText = `
        color: #666;
        margin: 0 0 25px 0;
        font-size: 14px;
        line-height: 1.6;
        white-space: pre-line;
    `;
    
    const buttonContainer = document.createElement('div');
    buttonContainer.style.cssText = `
        display: flex;
        gap: 10px;
        justify-content: center;
    `;
    
    const confirmBtn = document.createElement('button');
    confirmBtn.textContent = '好的，关闭';
    confirmBtn.style.cssText = `
        background: #4caf50;
        color: white;
        border: none;
        padding: 10px 30px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: background 0.2s;
    `;
    confirmBtn.onmouseover = function() { this.style.background = '#45a049'; };
    confirmBtn.onmouseout = function() { this.style.background = '#4caf50'; };
    confirmBtn.addEventListener('click', function() {
        document.body.removeChild(modal);
    });
    
    buttonContainer.appendChild(confirmBtn);
    
    content.appendChild(successIcon);
    content.appendChild(header);
    content.appendChild(messageEl);
    content.appendChild(buttonContainer);
    
    modal.appendChild(content);
    document.body.appendChild(modal);
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
