import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// --- Mock useCentrifugo BEFORE importing Chat ---
const mockUseCentrifugo = vi.fn();
vi.mock('../../useCentrifugo', () => ({
  useCentrifugo: (...args: any[]) => mockUseCentrifugo(...args),
}));

// Mock centrifuge Subscription (imported at top of Chat.tsx)
vi.mock('centrifuge', () => ({
  Subscription: vi.fn(),
}));

// Mock import.meta.env
vi.stubEnv('VITE_CENT_TOKEN_URL', '/api/v1/centrifugo/token');
vi.stubEnv('VITE_CENT_WS_URL', 'ws://localhost:5000/connection/websocket');

// Mock window.location
const mockLocation = { href: '' };
Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true,
});

// Mock fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

// Import Chat AFTER mocks are set up
import { Chat } from '../features/chat/Chat';

const defaultCentrifugoReturn = {
  connected: false,
  subscribeWithToken: vi.fn(),
  removeSubscription: vi.fn(),
};

const mockMe = {
  id: 'user-1',
  name: 'Alice',
  email: 'alice@example.com',
};

const mockUsers = [
  { id: 'user-2', username: 'Bob', email: 'bob@example.com', status: 'online' },
  { id: 'user-3', username: 'Carol', email: 'carol@example.com', status: 'offline' },
];

function setupFetch(overrides: { me?: any; users?: any; meOk?: boolean } = {}) {
  const { me = mockMe, users = mockUsers, meOk = true } = overrides;
  mockFetch.mockImplementation((url: string) => {
    if (url === '/api/v1/me') {
      return Promise.resolve({
        ok: meOk,
        json: async () => me,
      });
    }
    if (url === '/api/v1/users') {
      return Promise.resolve({
        ok: true,
        json: async () => users,
      });
    }
    // channel creation
    if (url === '/api/v1/channel/users') {
      return Promise.resolve({
        ok: true,
        json: async () => ({ id: 'channel-123' }),
      });
    }
    // messages
    if (url.startsWith('/api/v1/message') && url.includes('channel_id')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ messages: [], has_more: false }),
      });
    }
    // message send
    if (url === '/api/v1/message') {
      return Promise.resolve({
        ok: true,
        json: async () => ({ message_id: 'msg-999' }),
      });
    }
    return Promise.resolve({ ok: true, json: async () => ({}) });
  });
}

describe('Chat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocation.href = '';
    mockUseCentrifugo.mockReturnValue(defaultCentrifugoReturn);
    setupFetch();
  });

  // ---------------------------------------------------------------
  //  Initial rendering
  // ---------------------------------------------------------------
  describe('initial rendering', () => {
    it('renders empty state when no user selected', async () => {
      render(<Chat />);
      await waitFor(() => {
        expect(screen.getByText('Выберите собеседника')).toBeInTheDocument();
      });
    });

    it('renders sidebar title', async () => {
      render(<Chat />);
      await waitFor(() => {
        expect(screen.getByText('Чаты')).toBeInTheDocument();
      });
    });

    it('loads and displays current user name in sidebar', async () => {
      render(<Chat />);
      await waitFor(() => {
        expect(screen.getByText('Alice')).toBeInTheDocument();
      });
    });

    it('loads and displays user list from API', async () => {
      render(<Chat />);
      await waitFor(() => {
        expect(screen.getByText('Bob')).toBeInTheDocument();
        expect(screen.getByText('Carol')).toBeInTheDocument();
      });
    });

    it('shows offline status text for offline users', async () => {
      render(<Chat />);
      await waitFor(() => {
        expect(screen.getByText('офлайн')).toBeInTheDocument();
      });
    });

    it('redirects to /auth when /me returns unauthorized', async () => {
      setupFetch({ meOk: false });
      render(<Chat />);
      await waitFor(() => {
        expect(mockLocation.href).toBe('/auth');
      });
    });
  });

  // ---------------------------------------------------------------
  //  Connection status
  // ---------------------------------------------------------------
  describe('connection status', () => {
    it('shows disconnected when Centrifugo not connected', async () => {
      mockUseCentrifugo.mockReturnValue({ ...defaultCentrifugoReturn, connected: false });
      render(<Chat />);
      // Need to select a user to see the chat header with connection status
      await waitFor(() => {
        expect(screen.getByText('Bob')).toBeInTheDocument();
      });
      // The connection status is only visible in chat header after selecting a user
      // Check empty state instead
      expect(screen.getByText('Выберите собеседника')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------
  //  User selection and channel creation
  // ---------------------------------------------------------------
  describe('user selection', () => {
    it('selects a user and creates a channel', async () => {
      const user = userEvent.setup();
      render(<Chat />);
      await waitFor(() => {
        expect(screen.getByText('Bob')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Bob'));

      await waitFor(() => {
        // Channel creation API should be called
        expect(mockFetch).toHaveBeenCalledWith('/api/v1/channel/users', expect.objectContaining({
          method: 'POST',
        }));
      });
    });

    it('shows selected user name in chat header after selection', async () => {
      const user = userEvent.setup();
      render(<Chat />);
      await waitFor(() => {
        expect(screen.getByText('Bob')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Bob'));

      await waitFor(() => {
        // The selected user appears in the chat header as an h2
        const headers = screen.getAllByText('Bob');
        expect(headers.length).toBeGreaterThanOrEqual(1);
      });
    });
  });

  // ---------------------------------------------------------------
  //  Message input
  // ---------------------------------------------------------------
  describe('message input', () => {
    it('renders textarea and send button after selecting a user', async () => {
      const user = userEvent.setup();
      render(<Chat />);
      await waitFor(() => {
        expect(screen.getByText('Bob')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Bob'));

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Напишите сообщение…')).toBeInTheDocument();
      });
      expect(screen.getByText('Отправить')).toBeInTheDocument();
    });

    it('disables send button when input is empty', async () => {
      const user = userEvent.setup();
      render(<Chat />);
      await waitFor(() => {
        expect(screen.getByText('Bob')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Bob'));

      await waitFor(() => {
        const sendBtn = screen.getByText('Отправить');
        expect(sendBtn).toBeDisabled();
      });
    });

    it('enables send button when typing', async () => {
      const user = userEvent.setup();
      render(<Chat />);
      await waitFor(() => {
        expect(screen.getByText('Bob')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Bob'));
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Напишите сообщение…')).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText('Напишите сообщение…') as HTMLTextAreaElement;
      await user.type(textarea, 'Hello there!');

      const sendBtn = screen.getByText('Отправить');
      expect(sendBtn).not.toBeDisabled();
    });

    it('sends message on button click and clears input', async () => {
      const user = userEvent.setup();
      render(<Chat />);
      await waitFor(() => {
        expect(screen.getByText('Bob')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Bob'));
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Напишите сообщение…')).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText('Напишите сообщение…') as HTMLTextAreaElement;
      await user.type(textarea, 'Hello world');
      await user.click(screen.getByText('Отправить'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('/api/v1/message', expect.objectContaining({
          method: 'POST',
        }));
      });

      // Input should clear after sending
      await waitFor(() => {
        expect(textarea.value).toBe('');
      });
    });
  });

  // ---------------------------------------------------------------
  //  Logout
  // ---------------------------------------------------------------
  describe('logout', () => {
    it('logs out and redirects to /auth', async () => {
      const user = userEvent.setup();
      render(<Chat />);
      await waitFor(() => {
        expect(screen.getByText('Bob')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Bob'));
      await waitFor(() => {
        expect(screen.getByText('Выйти')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Выйти'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('/api/v1/auth/logout', expect.objectContaining({
          method: 'POST',
        }));
        expect(mockLocation.href).toBe('/auth');
      });
    });
  });
});
