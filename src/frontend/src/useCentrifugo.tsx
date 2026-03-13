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
        });

        centrifuge.on('disconnected', ctx => {
          console.log('[centrifugo] disconnected', ctx);
          setConnected(false);
        });

        centrifuge.connect();
        centrifugeRef.current = centrifuge;
      } catch (e) {
        console.error('Centrifugo init error:', e);
        if (!cancelled) setTimeout(init, 3000);  // retry
      }
    }

    init();

    return () => {
      cancelled = true;
      if (centrifugeRef.current) {
        centrifugeRef.current.disconnect();
        centrifugeRef.current = null;
      }
    };
  }, [tokenUrl, wsUrl]);

  const subscribe = useCallback((
    channel: string,
    handlers: CentrifugoHandlers
  ): Subscription | null => {
    const centrifuge = centrifugeRef.current;
    if (!centrifuge) {
      console.warn('[centrifugo] not connected');
      return null;
    }

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

    sub.subscribe();
    return sub;
  }, []);

  const publish = useCallback(async (channel: string, data: any) => {
    const centrifuge = centrifugeRef.current;
    if (!centrifuge) {
      throw new Error('Centrifugo not connected');
    }
    return centrifuge.publish(channel, data);
  }, []);

  return { connected, subscribe, publish };
}
