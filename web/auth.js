/**
 * MSC 幻天屿 - 认证模块
 * 简单的登录验证
 */

const AUTH_CONFIG = {
    SESSION_KEY: 'msc_logged_in',
    SESSION_EXPIRE: 24 * 60 * 60 * 1000 // 24小时
};

/**
 * 验证登录
 */
function validateLogin(username, password) {
    return username === 'admin' && password === 'xiaohaixia';
}

/**
 * 检查登录状态
 */
function checkLogin() {
    const session = sessionStorage.getItem(AUTH_CONFIG.SESSION_KEY);
    if (session) {
        try {
            const data = JSON.parse(session);
            if (Date.now() - data.timestamp < AUTH_CONFIG.SESSION_EXPIRE) {
                document.getElementById('loginOverlay')?.classList.add('hidden');
                return true;
            }
        } catch (e) {}
    }
    return false;
}

/**
 * 执行登录
 */
function doLogin(username, password) {
    if (validateLogin(username, password)) {
        sessionStorage.setItem(AUTH_CONFIG.SESSION_KEY, JSON.stringify({
            user: username,
            timestamp: Date.now()
        }));
        document.getElementById('loginOverlay')?.classList.add('hidden');
        return true;
    }
    return false;
}

/**
 * 登出
 */
function logout() {
    sessionStorage.removeItem(AUTH_CONFIG.SESSION_KEY);
    location.reload();
}

// 页面加载时检查
document.addEventListener('DOMContentLoaded', checkLogin);