// src/frontend/src/features/auth/AuthForm.tsx
import React, { useState } from 'react';
import '../../styles/auth.css';

type Mode = 'login' | 'register';

export const AuthForm: React.FC = () => {
  const [mode, setMode] = useState<Mode>('login');
  const [loginMessage, setLoginMessage] = useState('');
  const [registerMessage, setRegisterMessage] = useState('');

  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({
    email: '',
    username: '',
    password: '',
    password_check: '',
  });

  const switchMode = (next: Mode) => {
    setMode(next);
    setLoginMessage('');
    setRegisterMessage('');
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginMessage('');
    try {
      const res = await fetch('/api/v1/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(loginForm),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setLoginMessage(data?.detail || 'Ошибка авторизации');
        return;
      }
      // успех — идём в /chats
      window.location.href = '/chats';
    } catch (err) {
      console.error(err);
      setLoginMessage('Ошибка сети, попробуйте ещё раз');
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegisterMessage('');

    if (registerForm.password !== registerForm.password_check) {
      setRegisterMessage('Пароли не совпадают');
      return;
    }

    try {
      const res = await fetch('/api/v1/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(registerForm),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        setRegisterMessage(data?.detail || 'Ошибка регистрации');
        return;
      }
      setRegisterMessage('Регистрация успешна, войдите под своими данными');
      setMode('login');
    } catch (err) {
      console.error(err);
      setRegisterMessage('Ошибка сети, попробуйте ещё раз');
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-tabs">
          <button
            className={`tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => switchMode('login')}
          >
            Авторизация
          </button>
          <button
            className={`tab ${mode === 'register' ? 'active' : ''}`}
            onClick={() => switchMode('register')}
          >
            Регистрация
          </button>
        </div>

        {mode === 'login' ? (
          <form id="login-form" className="form-container active" onSubmit={handleLoginSubmit}>
            <div className="form-group">
              <label htmlFor="login-email">Email</label>
              <input
                id="login-email"
                type="email"
                value={loginForm.email}
                onChange={e => setLoginForm(p => ({ ...p, email: e.target.value }))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="login-password">Пароль</label>
              <input
                id="login-password"
                type="password"
                value={loginForm.password}
                onChange={e => setLoginForm(p => ({ ...p, password: e.target.value }))}
              />
            </div>
            {loginMessage && <div id="login-message" className="message">{loginMessage}</div>}
            <button type="submit" className="btn-primary">
              Войти
            </button>
          </form>
        ) : (
          <form id="register-form" className="form-container active" onSubmit={handleRegisterSubmit}>
            <div className="form-group">
              <label htmlFor="register-email">Email</label>
              <input
                id="register-email"
                type="email"
                value={registerForm.email}
                onChange={e => setRegisterForm(p => ({ ...p, email: e.target.value }))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="register-name">Имя</label>
              <input
                id="register-name"
                type="text"
                value={registerForm.username}
                onChange={e => setRegisterForm(p => ({ ...p, username: e.target.value }))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="register-password">Пароль</label>
              <input
                id="register-password"
                type="password"
                value={registerForm.password}
                onChange={e => setRegisterForm(p => ({ ...p, password: e.target.value }))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="register-password-check">Повторите пароль</label>
              <input
                id="register-password-check"
                type="password"
                value={registerForm.password_check}
                onChange={e => setRegisterForm(p => ({ ...p, password_check: e.target.value }))}
              />
            </div>
            {registerMessage && (
              <div id="register-message" className="message">{registerMessage}</div>
            )}
            <button type="submit" className="btn-primary">
              Зарегистрироваться
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
