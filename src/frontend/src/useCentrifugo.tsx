// src/frontend/src/useCentrifugo.ts
import { useCallback, useEffect, useRef, useState } from 'react';
import { Centrifuge, Subscription } from 'centrifuge';

type UseCentrifugoOptions = {
  tokenUrl: string;
  wsUrl: string;
};

type CentrifugoHandlers = {
  onPublication?: (data: any) => void;
  onSubscribed?: () => void;
  onUnsubscribed?: () => void;
};

export function useCentrifugo({ tokenUrl, wsUrl }: UseCentrifugoOptions) {
  const centrifugeRef = useRef<Centrifuge | null>(null);
  const [connected, setConnected] = useState(false);
  const pingIntervalRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const res = await fetch(tokenUrl, { credentials: 'include' });
        if (!res.ok) throw new Error('Failed to fetch Centrifugo token');
        const data = await res.json();

        if (cancelled) return;

        const centrifuge = new Centrifuge(wsUrl, {
          token: data.token,
        });

        centrifuge.on('connected', ctx => {
          console.log('[centrifugo] connected', ctx);
          setConnected(true);

          if (pingIntervalRef.current) {
            window.clearInterval(pingIntervalRef.current);
          }
          pingIntervalRef.current = window.setInterval(() => {
            fetch('/api/v1/users/ping', {
              method: 'POST',
              credentials: 'include',
            }).catch(() => {});
          }, 30_000); // каждые 30 сек
        });

        centrifuge.on('disconnected', ctx => {
          console.log('[centrifugo] disconnected', ctx);
          setConnected(false);
          if (pingIntervalRef.current) {
            window.clearInterval(pingIntervalRef.current);
            pingIntervalRef.current = null;
          }
        });

        centrifuge.connect();
        centrifugeRef.current = centrifuge;
      } catch (e) {
        console.error('Centrifugo init error:', e);
        if (!cancelled) setTimeout(init, 3000);
      }
    }

    init();

    return () => {
      cancelled = true;
      if (centrifugeRef.current) {
        centrifugeRef.current.disconnect();
        centrifugeRef.current = null;
      }
      if (pingIntervalRef.current) {
        window.clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
    };
  }, [tokenUrl, wsUrl]);

  const subscribeWithToken = useCallback(
    async (
      channel: string,
      handlers: CentrifugoHandlers,
      tokenEndpoint: string,
      tokenPayload: any,
    ): Promise<Subscription | null> => {
      const centrifuge = centrifugeRef.current;
      if (!centrifuge) return null;

      // 1) получаем subscription JWT
      const res = await fetch(tokenEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(tokenPayload),
      });

      if (!res.ok) {
        console.error('subscription token error', await res.text());
        return null;
      }

      const { token } = await res.json();

      // 2) создаём подписку с этим токеном
      const sub = centrifuge.newSubscription(channel, { token });

      if (handlers.onPublication) {
        sub.on('publication', ctx => handlers.onPublication!(ctx.data));
      }
      if (handlers.onSubscribed) {
        sub.on('subscribed', () => handlers.onSubscribed!());
      }
      if (handlers.onUnsubscribed) {
        sub.on('unsubscribed', () => handlers.onUnsubscribed!());
      }

      sub.on('join', ctx => {
        console.log('peer joined', ctx.info.user);
      });

      sub.on('leave', ctx => {
        console.log('peer left', ctx.info.user);
      });

      sub.subscribe();
      return sub;
    },
    [],
  );

  const subscribe = useCallback((
    channel: string,
    handlers: CentrifugoHandlers
  ): Subscription | null => {
    const centrifuge = centrifugeRef.current;
    if (!centrifuge) {
      console.warn('[centrifugo] not connected');
      return null;
    }

    // каждый раз создаём новую подписку для канала
    const sub = centrifuge.newSubscription(channel);

    if (handlers.onPublication) {
      sub.on('publication', ctx => handlers.onPublication!(ctx.data));
    }
    if (handlers.onSubscribed) {
      sub.on('subscribed', () => handlers.onSubscribed!());
    }
    if (handlers.onUnsubscribed) {
      sub.on('unsubscribed', () => handlers.onUnsubscribed!());
    }

    sub.on('join', ctx => {
      console.log('peer joined', ctx.info.user);
    });

    sub.on('leave', ctx => {
      console.log('peer left', ctx.info.user);
    });

    sub.subscribe();
    return sub;
  }, []);

  const removeSubscription = useCallback((sub: Subscription | null) => {
    const centrifuge = centrifugeRef.current;
    if (!centrifuge || !sub) return;
    // полностью удаляем subscription из реестра клиента
    centrifuge.removeSubscription(sub);  // без этого newSubscription позже падает[web:69][web:120]
  }, []);

  const publish = useCallback(async (channel: string, data: any) => {
    const centrifuge = centrifugeRef.current;
    if (!centrifuge) {
      throw new Error('Centrifugo not connected');
    }
    return centrifuge.publish(channel, data);
  }, []);

  return { connected, subscribe, subscribeWithToken, publish, removeSubscription };
}
