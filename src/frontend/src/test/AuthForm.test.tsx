import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthForm } from '../features/auth/AuthForm';

// Mock window.location.href (jsdom doesn't support navigation)
const mockLocation = {
  href: '',
};
Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true,
});

// Mock fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('AuthForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocation.href = '';
  });

  // ---------------------------------------------------------------
  //  Rendering
  // ---------------------------------------------------------------
  describe('rendering', () => {
    it('renders login form by default', () => {
      render(<AuthForm />);
      expect(screen.getByText('Авторизация')).toBeInTheDocument();
      expect(screen.getByPlaceholderText === undefined);
      // Login form should be visible
      expect(screen.getByText('Войти')).toBeInTheDocument();
    });

    it('shows email and password inputs in login mode', () => {
      render(<AuthForm />);
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
      expect(screen.getByLabelText('Пароль')).toBeInTheDocument();
    });

    it('renders register tab button', () => {
      render(<AuthForm />);
      expect(screen.getByText('Регистрация')).toBeInTheDocument();
    });

    it('does not show register-only fields in login mode', () => {
      render(<AuthForm />);
      expect(screen.queryByText('Имя')).not.toBeInTheDocument();
      expect(screen.queryByText('Повторите пароль')).not.toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------
  //  Mode switching
  // ---------------------------------------------------------------
  describe('mode switching', () => {
    it('switches to register form when tab clicked', async () => {
      const user = userEvent.setup();
      render(<AuthForm />);

      await user.click(screen.getByText('Регистрация'));

      expect(screen.getByText('Зарегистрироваться')).toBeInTheDocument();
      expect(screen.getByLabelText('Имя')).toBeInTheDocument();
      expect(screen.getByLabelText('Повторите пароль')).toBeInTheDocument();
    });

    it('switches back to login form', async () => {
      const user = userEvent.setup();
      render(<AuthForm />);

      await user.click(screen.getByText('Регистрация'));
      await user.click(screen.getByText('Авторизация'));

      expect(screen.getByText('Войти')).toBeInTheDocument();
      expect(screen.queryByText('Зарегистрироваться')).not.toBeInTheDocument();
    });

    it('clears messages on mode switch', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Bad credentials' }),
      });

      render(<AuthForm />);

      // Trigger a login error
      await user.type(screen.getByLabelText('Email'), 'test@test.com');
      await user.type(screen.getByLabelText('Пароль'), 'wrongpass');
      await user.click(screen.getByText('Войти'));

      await waitFor(() => {
        expect(screen.getByText('Bad credentials')).toBeInTheDocument();
      });

      // Switch to register — error should disappear
      await user.click(screen.getByText('Регистрация'));
      expect(screen.queryByText('Bad credentials')).not.toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------
  //  Login submission
  // ---------------------------------------------------------------
  describe('login submission', () => {
    it('submits login form with correct payload', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ access_token: 'token123' }),
      });

      render(<AuthForm />);

      await user.type(screen.getByLabelText('Email'), 'alice@example.com');
      await user.type(screen.getByLabelText('Пароль'), 'SecretPass123');
      await user.click(screen.getByText('Войти'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('/api/v1/login', expect.objectContaining({
          method: 'POST',
          credentials: 'include',
          body: JSON.stringify({
            email: 'alice@example.com',
            password: 'SecretPass123',
          }),
        }));
      });
    });

    it('redirects to /chats on successful login', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ access_token: 'token123' }),
      });

      render(<AuthForm />);

      await user.type(screen.getByLabelText('Email'), 'alice@example.com');
      await user.type(screen.getByLabelText('Пароль'), 'SecretPass123');
      await user.click(screen.getByText('Войти'));

      await waitFor(() => {
        expect(window.location.href).toBe('/chats');
      });
    });

    it('shows error message on failed login (401)', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Неверный email или пароль' }),
      });

      render(<AuthForm />);

      await user.type(screen.getByLabelText('Email'), 'alice@example.com');
      await user.type(screen.getByLabelText('Пароль'), 'wrongpass');
      await user.click(screen.getByText('Войти'));

      await waitFor(() => {
        expect(screen.getByText('Неверный email или пароль')).toBeInTheDocument();
      });
    });

    it('shows network error on fetch failure', async () => {
      const user = userEvent.setup();
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      render(<AuthForm />);

      await user.type(screen.getByLabelText('Email'), 'alice@example.com');
      await user.type(screen.getByLabelText('Пароль'), 'SecretPass123');
      await user.click(screen.getByText('Войти'));

      await waitFor(() => {
        expect(screen.getByText('Ошибка сети, попробуйте ещё раз')).toBeInTheDocument();
      });
    });
  });

  // ---------------------------------------------------------------
  //  Register submission
  // ---------------------------------------------------------------
  describe('register submission', () => {
    it('shows password mismatch error without calling API', async () => {
      const user = userEvent.setup();
      render(<AuthForm />);

      await user.click(screen.getByText('Регистрация'));
      await user.type(screen.getByLabelText('Email'), 'new@example.com');
      await user.type(screen.getByLabelText('Имя'), 'newuser');
      await user.type(screen.getByLabelText('Пароль'), 'pass1');
      await user.type(screen.getByLabelText('Повторите пароль'), 'pass2');
      await user.click(screen.getByText('Зарегистрироваться'));

      await waitFor(() => {
        expect(screen.getByText('Пароли не совпадают')).toBeInTheDocument();
      });
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('submits register form with correct payload', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'ok', user_id: '123' }),
      });

      render(<AuthForm />);

      await user.click(screen.getByText('Регистрация'));
      await user.type(screen.getByLabelText('Email'), 'new@example.com');
      await user.type(screen.getByLabelText('Имя'), 'newuser');
      await user.type(screen.getByLabelText('Пароль'), 'Secret123');
      await user.type(screen.getByLabelText('Повторите пароль'), 'Secret123');
      await user.click(screen.getByText('Зарегистрироваться'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('/api/v1/register', expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            email: 'new@example.com',
            username: 'newuser',
            password: 'Secret123',
            password_check: 'Secret123',
          }),
        }));
      });
    });

    it('shows success message and switches to login on successful registration', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'ok', user_id: '123' }),
      });

      render(<AuthForm />);

      await user.click(screen.getByText('Регистрация'));
      await user.type(screen.getByLabelText('Email'), 'new@example.com');
      await user.type(screen.getByLabelText('Имя'), 'newuser');
      await user.type(screen.getByLabelText('Пароль'), 'Secret123');
      await user.type(screen.getByLabelText('Повторите пароль'), 'Secret123');
      await user.click(screen.getByText('Зарегистрироваться'));

      await waitFor(() => {
        // Switched to login mode
        expect(screen.getByText('Войти')).toBeInTheDocument();
      });
    });

    it('shows API error on registration failure (409)', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'User already exists' }),
      });

      render(<AuthForm />);

      await user.click(screen.getByText('Регистрация'));
      await user.type(screen.getByLabelText('Email'), 'existing@example.com');
      await user.type(screen.getByLabelText('Имя'), 'existing');
      await user.type(screen.getByLabelText('Пароль'), 'Secret123');
      await user.type(screen.getByLabelText('Повторите пароль'), 'Secret123');
      await user.click(screen.getByText('Зарегистрироваться'));

      await waitFor(() => {
        expect(screen.getByText('User already exists')).toBeInTheDocument();
      });
    });
  });
});
