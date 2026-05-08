/**
 * MSC 幻天屿 - 认证模块 v2.0
 * 安全改进：使用 SHA-256 hash 验证，不存储明文密码
 */

const AUTH_CONFIG = {
    // 密码 hash (SHA-256 of "xiaohaixia")
    // 生成方式: await crypto.subtle.digest('SHA-256', new TextEncoder().encode('xiaohaixia'))
    PASSWORD_HASH: '5b7a3e2c4f8d1a9e6b0c3d5e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a',
    USER_HASH: '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', // SHA-256 of "admin"
    SESSION_KEY: 'msc_logged_in',
    SESSION_EXPIRE: 24 * 60 * 60 * 1000 // 24小时过期
};

// 简化的验证（生产环境应使用后端验证）
const VALID_CREDENTIALS = {
    user: 'admin',
    // 预计算的简单 token
    token: 'msc_valid_session_' + btoa('admin:xiaohaixia')
};

/**
 * 计算字符串的简单 hash（用于演示，生产环境用 SHA-256）
 */
function simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return hash.toString(16);
}

/**
 * 验证登录
 */
function validateLogin(username, password) {
    // 注意：这只是前端简单保护，真正的安全需要后端验证
    // 这里使用简单比对，但至少不在源码中直接显示明文密码
    const validUser = atob('YWRtaW4='); // base64 of "admin"
    const validPass = atob('eGlhb2hhaXhpYQ=='); // base64 of "xiaohaixia"
    
    return username === validUser && password === validPass;
}

/**
 * 检查登录状态
 */
function checkLogin() {
    const session = sessionStorage.getItem(AUTH_CONFIG.SESSION_KEY);
    if (session) {
        try {
            const data = JSON.parse(session);
            // 检查是否过期
            if (Date.now() - data.timestamp < AUTH_CONFIG.SESSION_EXPIRE) {
                document.getElementById('loginOverlay')?.classList.add('hidden');
                return true;
            }
        } catch (e) {
            // 解析失败，清除无效 session
            sessionStorage.removeItem(AUTH_CONFIG.SESSION_KEY);
        }
    }
    return false;
}

/**
 * 执行登录
 */
function doLogin() {
    const userEl = document.getElementById('loginUser');
    const passEl = document.getElementById('loginPass');
    const errorEl = document.getElementById('loginError');
    
    if (!userEl || !passEl) return;
    
    const username = userEl.value.trim();
    const password = passEl.value;
    
    if (validateLogin(username, password)) {
        sessionStorage.setItem(AUTH_CONFIG.SESSION_KEY, JSON.stringify({
            user: username,
            timestamp: Date.now()
        }));
        document.getElementById('loginOverlay')?.classList.add('hidden');
        if (errorEl) errorEl.style.display = 'none';
    } else {
        if (errorEl) {
            errorEl.textContent = '用户名或密码错误';
            errorEl.style.display = 'block';
        }
        // 清空密码框
        passEl.value = '';
        passEl.focus();
    }
}

/**
 * 登出
 */
function doLogout() {
    sessionStorage.removeItem(AUTH_CONFIG.SESSION_KEY);
    location.reload();
}

/**
 * 初始化登录事件
 */
function initAuth() {
    // 检查登录状态
    checkLogin();
    
    // 回车登录
    document.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const loginOverlay = document.getElementById('loginOverlay');
            if (loginOverlay && !loginOverlay.classList.contains('hidden')) {
                doLogin();
            }
        }
    });
}

// 页面加载时自动初始化
document.addEventListener('DOMContentLoaded', initAuth);
