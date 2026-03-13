// src/frontend/src/features/chat/Chat.tsx
import React, { useEffect, useRef, useState } from 'react';
import { useCentrifugo } from '../../useCentrifugo';
import '../../styles/chat.css';

type User = {
  id: string;
  name: string;
  email: string;
  status: 'online' | 'offline' | 'typing' | 'unknown';
  avatar: string;
};

type Message = {
  id?: string;
  temp_id: number;
  sender_id: string;
  channel_id: string;
  content: string;
  created_at: string;
  status: 'sending' | 'saved' | 'delivered' | 'saved_only' | 'error';
};

type CurrentUser = {
  id: string;
  name: string;
  avatar: string;
};

type MessagesMap = Record<string, Message[]>;
type FlagsMap = Record<string, boolean>;

export const Chat: React.FC = () => {
  const {
    connected,
    subscribe,
    // publish
  } = useCentrifugo({
    // @ts-ignore
    tokenUrl: import.meta.env.VITE_CENT_TOKEN_URL || '/api/v1/centrifugo/token',
    // @ts-ignore
    wsUrl: import.meta.env.VITE_CENT_WS_URL || 'ws://localhost:5000/connection/websocket',
  });

  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  // выбранный канал (id канала, а не пользователя)
  const [selectedChannelId, setSelectedChannelId] = useState<string | null>(null);

  // сообщения, флаги пагинации привязаны к channel_id
  const [messages, setMessages] = useState<MessagesMap>({});
  const [hasMoreMessages, setHasMoreMessages] = useState<FlagsMap>({});
  const [loadingMore, setLoadingMore] = useState<FlagsMap>({});
  const [input, setInput] = useState('');
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);

  // загрузка текущего пользователя и списка юзеров
  useEffect(() => {
    (async () => {
      try {
        const meRes = await fetch('/api/v1/me', { credentials: 'include' });
        if (!meRes.ok) throw new Error('Не авторизован');
        const me = await meRes.json();
        const cur: CurrentUser = {
          id: me.id,
          name: me.name,
          avatar: getAvatarByName(me.name),
        };
        setCurrentUser(cur);

        const usersRes = await fetch('/api/v1/users', { credentials: 'include' });
        if (!usersRes.ok) throw new Error('Ошибка загрузки пользователей');
        const apiUsers = await usersRes.json();
        const mapped: User[] = apiUsers.map((u: any) => ({
          id: u.id,
          name: u.username || u.email.split('@')[0],
          email: u.email,
          status: 'unknown',
          avatar: getAvatarByName(u.username || u.email),
        }));
        setUsers(mapped);
      } catch (e) {
        console.error(e);
        window.location.href = '/auth';
      }
    })();
  }, []);

  // helper: получить или создать канал между текущим пользователем и собеседником
  const ensureChannelForUser = async (peerId: string): Promise<string | null> => {
    if (!currentUser) return null;

    console.log(JSON.stringify({
          user_ids: [currentUser.id, peerId],
        }))
    try {
      const res = await fetch('/api/v1/channel/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify([
          currentUser.id,
          peerId,
        ]),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        console.error('Ошибка получения/создания канала:', err?.detail || res.statusText);
        return null;
      }

      const data = await res.json();
      // предполагаем, что backend возвращает объект канала с полем id
      return data.id as string;
    } catch (e) {
      console.error('Ошибка сети при получении/создании канала:', e);
      return null;
    }
  };

  // загрузка сообщений по channel_id
  const loadMessagesForChannel = async (channelId: string, beforeId?: string) => {
    if (loadingMore[channelId]) return;

    setLoadingMore(prev => ({ ...prev, [channelId]: true }));
    try {
      const params = new URLSearchParams({ limit: '30' });
      if (beforeId) params.append('before_id', beforeId);

      const res = await fetch(`/api/v1/message/${channelId}?${params.toString()}`, {
        credentials: 'include',
      });
      const data = await res.json();

      if (!res.ok) {
        console.error('Ошибка API:', data.detail || 'Unknown error');
        if (!beforeId) {
          setMessages(prev => ({ ...prev, [channelId]: [] }));
        }
        return;
      }

      const apiMessages: Message[] = data.messages.map((m: any) => ({
        id: m.id,
        sender_id: m.sender_id,
        channel_id: m.channel_id || channelId,
        content: m.content,
        created_at: m.created_at,
        temp_id: 0,
        status: 'delivered' as const,
      }));

      setMessages(prev => {
        const prevList = prev[channelId] || [];
        return {
          ...prev,
          [channelId]: beforeId ? [...apiMessages, ...prevList] : apiMessages,
        };
      });

      setHasMoreMessages(prev => ({
        ...prev,
        [channelId]: data.has_more || false,
      }));

      if (!beforeId && messagesContainerRef.current) {
        const container = messagesContainerRef.current;
        setTimeout(() => {
          container.scrollTop = container.scrollHeight;
        }, 0);
      }
    } catch (e) {
      console.error('Ошибка загрузки сообщений:', e);
      if (!beforeId) {
        setMessages(prev => ({ ...prev, [channelId]: [] }));
      }
    } finally {
      setLoadingMore(prev => ({ ...prev, [channelId]: false }));
    }
  };

  // подписка на канал при выборе собеседника (по channel_id)
  useEffect(() => {
    if (!selectedChannelId || !connected) return;

    const channelId = selectedChannelId;
    const channelName = `chat:${channelId}`;

    const sub = subscribe(channelName, {
      onPublication: data => {
        if (data.sender_id === currentUser?.id) {
          return;
        }
        setMessages(prev => {
          const msg: Message = {
            id: data.id,
            temp_id: data.temp_id || 0,
            sender_id: data.sender_id,
            channel_id: data.channel_id,
            content: data.content,
            created_at: data.created_at,
            status: 'delivered',
          };
          const list = prev[channelId] || [];
          return {
            ...prev,
            [channelId]: [...list, msg],
          };
        });
      },
    });

    // первая загрузка истории
    loadMessagesForChannel(channelId);

    return () => {
      if (sub) sub.unsubscribe();
    };
  }, [selectedChannelId, connected]);

  const handleSelectUser = async (user: User) => {
    setSelectedUser(user);

    // получаем или создаём канал между текущим пользователем и собеседником
    const channelId = await ensureChannelForUser(user.id);
    if (channelId) {
      setSelectedChannelId(channelId);
    } else {
      // если канал не удалось получить — сбрасываем выбор
      setSelectedChannelId(null);
    }
  };

  const handleSend = async () => {
    if (!selectedUser || !selectedChannelId || !input.trim() || !currentUser) return;

    const text = input.trim();
    const tempId = Date.now();
    const channelId = selectedChannelId;

    const optimistic: Message = {
      temp_id: tempId,
      sender_id: currentUser.id,
      channel_id: channelId,
      content: text,
      created_at: new Date().toISOString(),
      status: 'sending',
    };

    setMessages(prev => {
      const list = prev[channelId] || [];
      return {
        ...prev,
        [channelId]: [...list, optimistic],
      };
    });
    setInput('');

    // 1) запись в БД
    try {
      const res = await fetch('/api/v1/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          // подстрой под свой backend: теперь используем channel_id
          channel_id: channelId,
          content: text,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'API error');
      }
      const { message_id } = await res.json();
      setMessages(prev =>
        updateMessageStatus(prev, tempId, message_id, 'saved'),
      );
    } catch (e) {
      console.error('Ошибка записи в БД:', e);
      setMessages(prev =>
        updateMessageStatus(prev, tempId, undefined, 'error'),
      );
      return;
    }

    // // 2) публикация в Centrifugo
    // try {
    //   await publish(`chat:${channelId}`, {
    //     temp_id: tempId,
    //     sender_id: currentUser.id,
    //     channel_id: channelId,
    //     content: text,
    //     created_at: new Date().toISOString(),
    //   });
    //   setMessages(prev =>
    //     updateMessageStatus(prev, tempId, undefined, 'delivered'),
    //   );
    // } catch (e) {
    //   console.warn('Centrifugo недоступен, сообщение сохранено только в БД:', e);
    //   setMessages(prev =>
    //     updateMessageStatus(prev, tempId, undefined, 'saved_only'),
    //   );
    // }

    if (messagesContainerRef.current) {
      const container = messagesContainerRef.current;
      setTimeout(() => {
        container.scrollTop = container.scrollHeight;
      }, 0);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (e) {
      console.error(e);
    } finally {
      window.location.href = '/auth';
    }
  };

  const currentChannelId = selectedChannelId;
  const currentMessages = currentChannelId ? messages[currentChannelId] || [] : [];

  return (
    <div className="chat-layout">
      {/* SIDEBAR */}
      <aside className="chat-sidebar">
        <header className="sidebar-header">
          <div className="sidebar-title">Чаты</div>
          {currentUser && (
            <div className="sidebar-user">
              <span className="sidebar-avatar">{currentUser.avatar}</span>
              <span className="sidebar-name">{currentUser.name}</span>
            </div>
          )}
        </header>

        <div className="users-list">
          {users.map(user => (
            <button
              key={user.id}
              type="button"
              className={
                'user-item' +
                (selectedUser?.id === user.id ? ' active' : '')
              }
              onClick={() => handleSelectUser(user)}
            >
              <div className="user-avatar">{user.avatar}</div>
              <div className="user-info">
                <h3>{user.name}</h3>
                <span className="user-status">
                  {getStatusText(user)}
                </span>
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* MAIN CHAT AREA */}
      <section className="chat-main">
        {!selectedUser || !currentChannelId ? (
          <div className="empty-state">
            <h2>Выберите собеседника</h2>
            <p>Чтобы начать общение, выберите пользователя из списка слева.</p>
          </div>
        ) : (
          <>
            <header className="chat-header">
              <div className="chat-user">
                <div className="chat-avatar">{selectedUser.avatar}</div>
                <div>
                  <h2>{selectedUser.name}</h2>
                  <span className="chat-user-status">
                    {connected ? 'online' : 'offline'}
                  </span>
                </div>
              </div>

              <div className="chat-header-right">
                <span
                  className={
                    'connection-status ' +
                    (connected ? 'connected' : 'disconnected')
                  }
                >
                  {connected ? 'Подключено' : 'Отключено'}
                </span>

                <button className="logout-btn" onClick={handleLogout}>
                  Выйти
                </button>
              </div>
            </header>

            <div
              className="chat-messages"
              ref={messagesContainerRef}
            >
              {hasMoreMessages[currentChannelId] && (
                <button
                  type="button"
                  className="load-more-btn"
                  disabled={loadingMore[currentChannelId]}
                  onClick={() => {
                    const oldest = currentMessages[0];
                    loadMessagesForChannel(
                      currentChannelId,
                      oldest?.id || undefined,
                    );
                  }}
                >
                  Загрузить ещё
                </button>
              )}

              {currentMessages.map(m => (
                <div
                  key={m.id ?? m.temp_id}
                  className={
                    'message-row ' +
                    (m.sender_id === currentUser?.id
                      ? 'own'
                      : 'other')
                  }
                >
                  <div className="message-bubble">
                    <div className="message-text">{m.content}</div>
                    <div className="message-meta">
                      <span>
                        {new Date(
                          m.created_at,
                        ).toLocaleTimeString()}
                      </span>
                      {m.status === 'error' && (
                        <span className="message-status error">
                          Ошибка
                        </span>
                      )}
                      {m.status === 'saved_only' && (
                        <span className="message-status saved-only">
                          Сохранено в БД
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="chat-input-area">
              <textarea
                className="chat-input"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Напишите сообщение…"
              />
              <button
                type="button"
                className="send-btn"
                onClick={handleSend}
                disabled={!input.trim()}
              >
                Отправить
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
};

/* helpers */

const getAvatarByName = (name: string): string => {
  const emojis = ['👨', '👩', '🧑', '👦', '👧', '🧒'];
  const hash = Array.from(name).reduce(
    (a, b) => ((a << 5) - a) + b.charCodeAt(0),
    0,
  );
  return emojis[Math.abs(hash) % emojis.length];
};

const getStatusText = (user: User): string => {
  const map: Record<User['status'], string> = {
    online: 'онлайн',
    typing: 'печатает…',
    offline: 'офлайн',
    unknown: 'неизвестно',
  };
  return map[user.status] ?? 'офлайн';
};

const updateMessageStatus = (
  prev: MessagesMap,
  tempId: number,
  messageId: string | undefined,
  status: Message['status'],
): MessagesMap => {
  const channelId = Object.keys(prev).find(k =>
    prev[k].some(m => m.temp_id === tempId),
  );
  if (!channelId) return prev;

  return {
    ...prev,
    [channelId]: prev[channelId].map(m =>
      m.temp_id === tempId ? { ...m, id: messageId, status } : m,
    ),
  };
};
