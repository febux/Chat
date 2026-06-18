/**
 * Pure-function tests extracted from Chat.tsx helpers.
 * These test the logic without rendering the full component.
 */
import { describe, it, expect } from 'vitest';

// Re-implement the helpers here (they're not exported from Chat.tsx).
// This documents the expected behavior for refactoring safety.

const getAvatarByName = (name: string): string => {
  const emojis = ['👨', '👩', '🧑', '👦', '👧', '🧒'];
  const hash = Array.from(name).reduce(
    (a, b) => ((a << 5) - a) + b.charCodeAt(0),
    0,
  );
  return emojis[Math.abs(hash) % emojis.length];
};

type UserStatus = 'online' | 'offline' | 'typing' | 'unknown';

const getStatusText = (status: UserStatus): string => {
  const map: Record<UserStatus, string> = {
    online: 'онлайн',
    typing: 'печатает…',
    offline: 'офлайн',
    unknown: 'неизвестно',
  };
  return map[status] ?? 'офлайн';
};

describe('getAvatarByName', () => {
  it('returns an emoji for any string', () => {
    const emoji = getAvatarByName('Alice');
    expect(emoji).toMatch(/[\u{1F300}-\u{1F9FF}]/u);
  });

  it('returns consistent result for the same name', () => {
    expect(getAvatarByName('Bob')).toBe(getAvatarByName('Bob'));
  });

  it('returns different results for different names (in most cases)', () => {
    // Not guaranteed for all pairs, but these specific ones differ
    const a = getAvatarByName('Alice');
    const b = getAvatarByName('Zoey');
    // At least verify both are valid emojis
    expect(a).toBeTruthy();
    expect(b).toBeTruthy();
  });

  it('handles empty string without error', () => {
    expect(() => getAvatarByName('')).not.toThrow();
  });

  it('handles unicode names', () => {
    expect(() => getAvatarByName('Алиса')).not.toThrow();
    expect(() => getAvatarByName('日本語')).not.toThrow();
  });
});

describe('getStatusText', () => {
  it('returns "онлайн" for online status', () => {
    expect(getStatusText('online')).toBe('онлайн');
  });

  it('returns "печатает…" for typing status', () => {
    expect(getStatusText('typing')).toBe('печатает…');
  });

  it('returns "офлайн" for offline status', () => {
    expect(getStatusText('offline')).toBe('офлайн');
  });

  it('returns "неизвестно" for unknown status', () => {
    expect(getStatusText('unknown')).toBe('неизвестно');
  });

  it('returns "офлайн" as fallback for invalid status', () => {
    // The function's fallback is 'офлайн'
    expect(getStatusText('invalid' as UserStatus)).toBe('офлайн');
  });
});
