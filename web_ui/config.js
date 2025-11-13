/**
 * AIChat Server 配置管理前端脚本
 */

// ============ 全局变量 ============
let currentSection = 'api';
let configData = {};
let originalApiKey = '';

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', function() {
    setupNavigation();
    loadConfiguration();
});

// ============ 导航栏处理 ============
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            const section = this.dataset.section;
            switchSection(section);
        });
    });
}

function switchSection(section) {
    // 移除所有活跃状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelectorAll('.config-section').forEach(sec => {
        sec.classList.remove('active');
    });
    
    // 激活选中的导航和部分
    document.querySelector(`[data-section="${section}"]`).classList.add('active');
    document.getElementById(`${section}-section`).classList.add('active');
    
    currentSection = section;
}

// ============ 配置加载 ============
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
    // 填充 API 配置
    document.getElementById('ACCESS_TOKEN').value = data.ACCESS_TOKEN || '123456';
    document.getElementById('ALIYUN_API_KEY').value = data.ALIYUN_API_KEY || '';
    
    // 填充模型配置
    document.getElementById('CHAT_MODEL').value = data.CHAT_MODEL || 'qwen-turbo';
    document.getElementById('INTENT_MODEL').value = data.INTENT_MODEL || 'qwen-turbo';
    document.getElementById('SYSTEM_PROMPT').value = data.SYSTEM_PROMPT || '你是一个桌面机器人, 快速地回复我.';
    document.getElementById('API_TIMEOUT').value = data.API_TIMEOUT || 10;
    
    // 填充硬件配置
    document.getElementById('ASR_DEVICE').value = data.ASR_DEVICE || 'cpu';
    document.getElementById('VAD_DEVICE').value = data.VAD_DEVICE || 'cpu';
    
    // 填充 AI Persona 配置
    if (data.ai_persona) {
        document.getElementById('botName').value = data.ai_persona.bot_name || '小凡';
        document.getElementById('systemContent').value = data.ai_persona.system_content || '';
        if (data.ai_persona.background_facts && Array.isArray(data.ai_persona.background_facts)) {
            document.getElementById('backgroundFacts').value = data.ai_persona.background_facts.join('\n');
        }
    }
}

// ============ 表单保存 ============
async function saveConfig() {
    const saveBtn = document.getElementById('saveBtn');
    const originalText = saveBtn.textContent;
    
    try {
        // 验证必填字段
        const apiKey = document.getElementById('ALIYUN_API_KEY').value;
        if (!apiKey || (apiKey.includes('*') && apiKey === originalApiKey)) {
            showNotification('请输入有效的阿里云 API Key', 'error');
            switchSection('api');
            return;
        }
        
        // 禁用按钮
        saveBtn.disabled = true;
        saveBtn.textContent = '⏳ 保存中...';
        
        // 构建配置对象
        const backgroundFacts = document.getElementById('backgroundFacts').value
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0);
        
        const config = {
            ACCESS_TOKEN: document.getElementById('ACCESS_TOKEN').value,
            ALIYUN_API_KEY: document.getElementById('ALIYUN_API_KEY').value,
            CHAT_MODEL: document.getElementById('CHAT_MODEL').value,
            INTENT_MODEL: document.getElementById('INTENT_MODEL').value,
            SYSTEM_PROMPT: document.getElementById('SYSTEM_PROMPT').value,
            ASR_DEVICE: document.getElementById('ASR_DEVICE').value,
            VAD_DEVICE: document.getElementById('VAD_DEVICE').value,
            API_TIMEOUT: parseInt(document.getElementById('API_TIMEOUT').value),
            ai_persona: {
                bot_name: document.getElementById('botName').value,
                system_content: document.getElementById('systemContent').value,
                background_facts: backgroundFacts
            }
        };
        
        // 发送保存请求
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('✅ 配置已保存成功！', 'success');
            originalApiKey = document.getElementById('ALIYUN_API_KEY').value;
            configData = config;
        } else {
            showNotification('❌ 保存失败：' + (result.error || '未知错误'), 'error');
        }
    } catch (error) {
        console.error('Error saving config:', error);
        showNotification('❌ 保存异常：' + error.message, 'error');
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;
    }
}

// ============ 服务重启 ============
async function restartService() {
    const restartBtn = document.getElementById('restartBtn');
    const originalText = restartBtn.textContent;
    
    // 确认对话
    if (!confirm('确定要重启服务吗？这会中断当前的连接。')) {
        return;
    }
    
    try {
        restartBtn.disabled = true;
        restartBtn.textContent = '⏳ 重启中...';
        
        // 使用服务管理 API 的重启端点
        const response = await fetch('/api/service/restart', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            if (result.method === 'docker') {
                showNotification(
                    '✅ 重启指令已发送，服务将在 10-30 秒内重启',
                    'success'
                );
                // 3秒后自动刷新页面
                setTimeout(() => {
                    location.reload();
                }, 3000);
            } else {
                // 需要手动重启
                showNotification(
                    '⚠️ 请手动执行以下命令重启容器：\n' +
                    'docker-compose restart',
                    'warning'
                );
            }
        }
    } catch (error) {
        console.error('Error restarting service:', error);
        showNotification('❌ 重启失败：' + error.message, 'error');
    } finally {
        restartBtn.disabled = false;
        restartBtn.textContent = originalText;
    }
}

// ============ 工具函数 ============
function togglePasswordVisibility() {
    const apiKeyInput = document.getElementById('ALIYUN_API_KEY');
    const showCheckbox = document.getElementById('showApiKey');
    
    if (showCheckbox.checked) {
        apiKeyInput.type = 'text';
    } else {
        apiKeyInput.type = 'password';
    }
}

function showLoading(show) {
    const loading = document.getElementById('loading');
    if (show) {
        loading.style.display = 'flex';
    } else {
        loading.style.display = 'none';
    }
}

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    const notificationMessage = document.getElementById('notificationMessage');
    
    // 移除现有的类
    notification.classList.remove('success', 'error', 'warning');
    
    // 添加新类
    notification.classList.add(type, 'show');
    notificationMessage.textContent = message;
    
    // 自动关闭（5秒后）
    setTimeout(() => {
        closeNotification();
    }, 5000);
}

function closeNotification() {
    const notification = document.getElementById('notification');
    notification.classList.remove('show');
}

// ============ 表单验证 ============
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('configForm');
    
    // 实时验证
    form.addEventListener('change', function() {
        validateForm();
    });
});

function validateForm() {
    const apiKey = document.getElementById('ALIYUN_API_KEY').value;
    const saveBtn = document.getElementById('saveBtn');
    
    // 简单验证：API Key 不为空
    if (!apiKey || (apiKey.includes('*') && apiKey === originalApiKey)) {
        saveBtn.disabled = false; // 允许用户重新输入
    }
}

// ============ 快捷键 ============
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + S: 保存
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveConfig();
    }
});
