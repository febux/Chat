// Переключение табов
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const target = tab.dataset.tab;

        // Активный таб
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Активная форма
        document.querySelectorAll('.form-container').forEach(form => form.classList.remove('active'));
        document.getElementById(target).classList.add('active');

        // Очистка сообщений
        document.getElementById('login-message').innerHTML = '';
        document.getElementById('register-message').innerHTML = '';
    });
});

// Регистрация
document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const messageEl = document.getElementById('register-message');
    const formData = {
        email: document.getElementById('register-email').value,
        username: document.getElementById('register-name').value,
        password: document.getElementById('register-password').value,
        password_check: document.getElementById('register-password-check').value
    };

    // Проверка паролей
    if (formData.password !== formData.password_check) {
        messageEl.innerHTML = '<div class="error">Пароли не совпадают</div>';
        return;
    }

    try {
        messageEl.innerHTML = '<div class="success">Регистрация...</div>';
        const response = await fetch('/api/v1/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (response.ok) {
            messageEl.innerHTML = '<div class="success">' + data.message + '</div>';
            setTimeout(() => window.location.href = '/chats', 1500);
        } else {
            messageEl.innerHTML = '<div class="error">' + (data.detail || 'Ошибка регистрации') + '</div>';
        }
    } catch (error) {
        messageEl.innerHTML = '<div class="error">Ошибка сети</div>';
    }
});

// Авторизация
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const messageEl = document.getElementById('login-message');
    const formData = {
        email: document.getElementById('login-email').value,
        password: document.getElementById('login-password').value
    };

    try {
        messageEl.innerHTML = '<div class="success">Авторизация...</div>';
        const response = await fetch('/api/v1/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include', // Для cookie
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (response.ok) {
            messageEl.innerHTML = '<div class="success">' + data.message + '</div>';
            setTimeout(() => window.location.href = '/chats', 1500);
        } else {
            messageEl.innerHTML = '<div class="error">' + (data.error || 'Ошибка авторизации') + '</div>';
        }
    } catch (error) {
        messageEl.innerHTML = '<div class="error">Ошибка сети</div>';
    }
});
