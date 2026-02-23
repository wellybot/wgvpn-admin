// API 配置 - 使用相對路徑，自動適應當前主機
const API_BASE = '';  // 使用相對路徑

export const API = {
    base: API_BASE,
    auth: {
        login: `${API_BASE}/api/auth/login`,
        logout: `${API_BASE}/api/auth/logout`,
    },
    users: `${API_BASE}/api/users`,
    traffic: `${API_BASE}/api/traffic`,
    alerts: `${API_BASE}/api/alerts`,
    logs: `${API_BASE}/api/logs`,
    reports: `${API_BASE}/api/reports`,
};

export const WS_API = `ws://${window.location.host}/api`;
