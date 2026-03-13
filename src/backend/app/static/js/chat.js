// Chat frontend logic integrated with FastAPI-SocketIO backend.
const SocketEvent = Object.freeze({
    CHAT_MESSAGE: 'chat_message',
    JSON_MESSAGE: 'json_message',
    PERSONAL_MESSAGE: 'personal_message',
    SYSTEM_MESSAGE: 'system_message',
    SEND_MESSAGE: 'send_message',
    PRIVATE_MESSAGE: 'private_message',
    TYPING: 'typing',
    ROOM_MESSAGE: 'room_message',
    JOIN_ROOM: 'join_room',
    LEAVE_ROOM: 'leave_room',
    ERROR: 'error',
});
// Глобальные переменные
let currentUser = null;
let users = [];
let selectedUser = null;
let messages = {};
let socket = null;
let loadingMore = {};
let hasMoreMessages = {};
let messagesContainer = null;

// Инициализация
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await initApp();
        initSocket(); // подключаем WebSocket
    } catch (error) {
        console.error('Ошибка инициализации:', error);
        window.location.href = '/auth';
    }
});

// ------------------- API ------------------- //

async function initApp() {
    currentUser = await fetchCurrentUser();
    document.getElementById('currentUser').textContent = currentUser.name;

    users = await fetchUsers();
    renderUsers();
    setupEventListeners();
    initMessagesContainer();
}

async function fetchCurrentUser() {
    const response = await fetch('/api/v1/me', {
        credentials: 'include'
    });

    if (!response.ok) {
        throw new Error('Не авторизован');
    }

    const user = await response.json();
    return {
        id: user.id,
        name: user.name,
        avatar: getAvatarByName(user.name)
    };
}

async function fetchUsers() {
    const response = await fetch('/api/v1/users', {
        credentials: 'include'
    });

    if (!response.ok) {
        throw new Error('Ошибка загрузки пользователей');
    }

    const apiUsers = await response.json();

    return apiUsers.map(user => ({
        id: user.id,
        name: user.name || user.email.split('@')[0],
        status: 'unknown',
        lastMessage: 'Пока нет сообщений',
        avatar: getAvatarByName(user.name || user.email),
        email: user.email
    }));
}

async function loadMessagesForUser(userId, beforeId = null) {
    if (loadingMore[userId]) return;

    try {
        if (!messages[userId]) messages[userId] = [];
        if (!loadingMore[userId]) loadingMore[userId] = false;

        loadingMore[userId] = true;

        const params = new URLSearchParams({ limit: 30 });
        if (beforeId) params.append('before_id', beforeId);

        const response = await fetch(`/api/v1/message/${userId}?${params}`, {
            credentials: 'include'
        });

        const data = await response.json();

        if (response.ok) {
            const apiMessages = data.messages || [];
            const prevScrollHeight = messagesContainer.scrollHeight;
            const wasAtTop = messagesContainer.scrollTop === 0;

            if (beforeId) {
                const oldMessages = messages[userId];
                messages[userId] = [...apiMessages, ...oldMessages];

                if (wasAtTop && apiMessages.length > 0) {
                    messagesContainer.scrollTop = messagesContainer.scrollHeight - prevScrollHeight;
                }

            } else {
                // ПЕРВЫЙ ЗАПРОС: полная замена
                messages[userId] = apiMessages;
                // Автоскролл вниз к последнему сообщению
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }

            hasMoreMessages[userId] = data.has_more || false;

        } else {
            console.error('Ошибка API:', data.detail || 'Unknown error');
            if (!beforeId) messages[userId] = [];
        }

    } catch (error) {
        console.error('Ошибка загрузки сообщений:', error);
        if (!beforeId) messages[userId] = [];
    } finally {
        loadingMore[userId] = false;
        loadMessages();
    }
}


async function loadMoreMessages() {
    if (!selectedUser || loadingMore[selectedUser.id] || !hasMoreMessages[selectedUser.id]) {
        return;
    }

    const oldestMessageId = messages[selectedUser.id][0]?.id;
    if (oldestMessageId) {
        await loadMessagesForUser(selectedUser.id, oldestMessageId);
    }
}

const throttle = (func, wait) => {
    let inThrottle, lastFn, lastTime;
    return function() {
        const context = this,
            args = arguments;
        if (!inThrottle) {
            func.apply(context, args);
            lastTime = Date.now();
            inThrottle = true;
            setTimeout(function() {
                inThrottle = false;
                if (lastFn) {
                    lastFn.apply(context, args);
                    lastFn = null;
                }
            }, wait);
        } else {
            lastFn = function() {
                func.apply(context, args);
            };
            lastTime = Date.now();
        }
    };
};

function initMessagesContainer() {
    messagesContainer = document.getElementById('messagesContainer');
    if (messagesContainer) {
        messagesContainer.addEventListener('scroll', throttle(async () => {
            if (messagesContainer.scrollTop <= 30 && hasMoreMessages[selectedUser?.id]) {
                await loadMoreMessages();
            }
        }, 500));
    }
}

// ------------------- SOCKET.IO ------------------- //

function initSocket() {
    socket = io('/', {
        transports: ['websocket'],
        path: '/ws',
        // auth: { token: token }
    });

    socket.on('connect', () => {
        console.log('[socket] Connected:', socket.id);
    });

    socket.on('disconnect', () => {
        console.log('[socket] Disconnected');
    });

    socket.on('user_connected', (data) => {
        console.log('[socket] Пользователь подключился:', data);

        // Обновляем статус пользователя в списке
        const user = users.find(u => u.id == data.user_id);
        if (user) {
            user.status = 'online';
            renderUsers();  // перерисовываем список
            showSystemNotification(`${user.name || data.username} подключился`);
        }
    });

    socket.on('user_disconnected', (data) => {
        console.log('[socket] Пользователь отключился:', data);

        // Обновляем статус пользователя
        const user = users.find(u => u.id == data.user_id);
        if (user) {
            user.status = 'offline';
            renderUsers();
            showSystemNotification(`${user.name || data.username} отключился`);
        }
    });

    // Публичные сообщения (если будут использоваться)
    socket.on('chat_message', (data) => {
        console.log('[socket] chat_message:', data);
        handleIncomingMessage(data);
    });

    // Личные сообщения (от сервера через ConnectionManager.send_json_message)
    socket.on('json_message', (data) => {
        console.log('[socket] json_message:', data);
        handleIncomingJsonMessage(data);
    });

    socket.on('personal_message', (data) => {
        console.log('[socket] personal_message:', data);
        showSystemNotification(typeof data === 'string' ? data : data.content);
    });

    // Системные уведомления
    socket.on('system_message', (msg) => {
        showSystemNotification(typeof msg === 'string' ? msg : JSON.stringify(msg));
    });

    socket.on('room_message', (data) => {
        console.log('[socket] room_message:', data);
        handleIncomingMessage(data);
    });

    // typing
    socket.on('typing', (data) => {
        const { user_id } = data;
        const user = users.find(u => u.id === user_id);
        if (user && selectedUser && user.id === selectedUser.id) {
            user.status = 'typing';
            document.getElementById('chatStatus').textContent = 'печатает...';
            setTimeout(() => {
                user.status = 'online';
                document.getElementById('chatStatus').textContent = 'онлайн';
            }, 2000);
        }
    });

    socket.on('error', (err) => {
        console.error('[socket] Error:', err);
    });

    socket.on('connect_error', (error) => {
        console.error('[socket] ❌ Ошибка подключения:', error);
        if (error.message.includes('authentication') || error.message.includes('token')) {
            showSystemNotification('Сессия истекла. Перезагрузите страницу.');
            // Можно редирект на /auth
            setTimeout(() => window.location.href = '/auth', 2000);
        }
    });
}

// ------------------- MESSAGE HANDLING ------------------- //

function handleIncomingMessage(data) {
    if (typeof data === 'string') data = { text: data };
    showSystemNotification(data.text || JSON.stringify(data));
}

// сообщение формата, который ты отправляешь из ConnectionManager:
// { sender_id, recipient_id, content }
function handleIncomingJsonMessage(data) {
    try {
        const senderId = data.sender_id;
        const recipientId = data.recipient_id;

        // определяем, для кого это сообщение (мы — либо отправитель, либо получатель)
        const peerId = senderId === currentUser.id ? recipientId : senderId;
        if (!messages[peerId]) messages[peerId] = [];

        messages[peerId].push({
            id: data.id,
            content: data.content,
            recipient_id: recipientId,
            created_at: data.created_at,
            sender_id: senderId
        });

        if (selectedUser && selectedUser.id === peerId) {
            loadMessages();
        } else {
            const peerUser = users.find(u => u.id === peerId);
            const name = peerUser ? peerUser.name : 'Пользователь';
            showSystemNotification(`📨 Новое сообщение от ${name}`);
        }
    } catch (e) {
        console.error('Ошибка обработки входящего сообщения:', e, data);
    }
}

// ------------------- UI EVENTS ------------------- //

function renderUsers() {
    const usersList = document.getElementById('usersList');
    usersList.innerHTML = users.map(user => `
        <div class="user-item ${selectedUser?.id === user.id ? 'active' : ''}" data-user-id="${user.id}">
            <div class="user-avatar">${user.avatar}</div>
            <div class="user-info">
                <div class="user-name">${user.name}</div>
                <div class="user-preview">${getStatusText(user)}</div>
            </div>
        </div>
    `).join('');
}

function setupEventListeners() {
    // выбор пользователя
    document.getElementById('usersList').addEventListener('click', (e) => {
        const userItem = e.target.closest('.user-item');
        if (userItem) {
            const userId = userItem.dataset.userId;
            selectUser(userId);
        }
    });

    // поиск
    document.getElementById('searchUsers').addEventListener('input', (e) => {
        filterUsers(e.target.value);
    });

    // отправка сообщения
    document.getElementById('sendBtn').addEventListener('click', sendMessage);
    document.getElementById('messageInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        } else {
            sendTypingEvent();
        }
    });

    // блокировка кнопки отправки
    document.getElementById('messageInput').addEventListener('input', (e) => {
        document.getElementById('sendBtn').disabled = e.target.value.trim() === '';
    });

    // кнопки навигации
    const backBtn = document.getElementById('backBtn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            window.location.href = '/auth';
        });
    }

    document.getElementById('logoutBtn').addEventListener('click', logout);

    // периодическое обновление пользователей
    setInterval(async () => {
        try {
            users = await fetchUsers();
            renderUsers();
            if (selectedUser) {
                await loadMessagesForUser(selectedUser.id);
            }
        } catch (error) {
            console.error('Ошибка обновления:', error);
        }
    }, 3000);
}

function selectUser(userId) {
    selectedUser = users.find(u => String(u.id) === String(userId));
    if (!selectedUser) return;

    document.querySelectorAll('.user-item').forEach(item => item.classList.remove('active'));
    const activeItem = document.querySelector(`[data-user-id="${userId}"]`);
    if (activeItem) activeItem.classList.add('active');

    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('activeChat').style.display = 'flex';
    document.getElementById('chatUsername').textContent = selectedUser.name;
    document.getElementById('chatStatus').textContent = getStatusText(selectedUser);

    const avatarEl = document.getElementById('chatAvatar');
    if (avatarEl) avatarEl.textContent = selectedUser.avatar;

    loadMessagesForUser(selectedUser.id);
}

function filterUsers(query) {
    const filtered = users.filter(user =>
        user.name.toLowerCase().includes(query.toLowerCase()) ||
        user.email.toLowerCase().includes(query.toLowerCase())
    );
    const usersList = document.getElementById('usersList');
    usersList.innerHTML = filtered.map(user => `
        <div class="user-item ${selectedUser?.id === user.id ? 'active' : ''}" data-user-id="${user.id}">
            <div class="user-avatar">${user.avatar}</div>
            <div class="user-info">
                <div class="user-name">${user.name}</div>
                <div class="user-preview">${getStatusText(user)}</div>
            </div>
        </div>
    `).join('');
}

// ------------------- MESSAGE DISPLAY ------------------- //

function loadMessages() {
    if (!selectedUser || !messagesContainer) {
        return;
    }

    const userMessages = messages[selectedUser.id] || [];

    messagesContainer.innerHTML = userMessages.map(msg => `
        <div key="${msg.id}" class="message ${msg.sender_id === currentUser.id ? 'sent' : 'received'}">
            <div class="message-content">${escapeHtml(msg.text || msg.content)}</div>
            <div class="message-time">${new Date(msg.created_at).toLocaleTimeString()}</div>
        </div>
    `).join('');

    // messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ------------------- SENDING ------------------- //

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const text = input.value.trim();
    if (!text || !selectedUser) return;

    try {
        const response = await fetch('/api/v1/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                recipient_id: selectedUser.id,
                content: text
            })
        });

        if (response.ok) {
            input.value = '';
            document.getElementById('sendBtn').disabled = true;

            if (!messages[selectedUser.id]) messages[selectedUser.id] = [];
            messages[selectedUser.id].push({
                id: Date.now(),
                content: text,
                created_at: new Date(),
                recipient_id: null,
                sender_id: currentUser.id
            });
            loadMessages();
        } else {
            console.error('Ошибка отправки сообщения:', await response.text());
        }
    } catch (error) {
        console.error('Ошибка отправки сообщения:', error);
    }
}

function sendTypingEvent() {
    if (socket && socket.connected && selectedUser) {
        socket.emit('typing', { user_id: currentUser.id, to: selectedUser.id });
    }
}

// ------------------- AUTH ------------------- //

async function logout() {
    if (confirm('Выйти из аккаунта?')) {
        try {
            await fetch('/api/v1/logout', {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Ошибка выхода:', error);
        } finally {
            if (socket && socket.connected && selectedUser) {
                socket.disconnect();
                const user = users.find(u => u.id === selectedUser.id);
                if (user && selectedUser && user.id === selectedUser.id) {
                    user.status = 'offline';
                    document.getElementById('chatStatus').textContent = 'офлайн';
                }
            }
            window.location.href = '/auth';
        }

    }
}

// ------------------- HELPERS ------------------- //

function getAvatarByName(name) {
    const emojis = ['👨', '👩', '🧑', '👦', '👧', '🧒'];
    const hash = Array.from(name).reduce((a, b) => ((a << 5) - a) + b.charCodeAt(0), 0);
    return emojis[Math.abs(hash) % emojis.length];
}

function getStatusText(user) {
    const statusMap = {
        'online': 'онлайн',
        'typing': 'печатает...',
        'offline': 'офлайн',
        'unknown': 'неизвестно'
    };
    return statusMap[user.status] || 'офлайн';
}

function showSystemNotification(text) {
    const notifBox = document.getElementById('systemNotifications');
    if (!notifBox) return;

    const notif = document.createElement('div');
    notif.className = 'notification';
    notif.textContent = text;
    notifBox.appendChild(notif);

    setTimeout(() => notif.remove(), 5000);
}

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}
