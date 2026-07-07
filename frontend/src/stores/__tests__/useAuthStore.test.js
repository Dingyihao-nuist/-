import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuthStore } from '../useAuthStore';

describe('useAuthStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAuthStore.setState({ user: null, isAuthenticated: false, isAdmin: false });
    localStorage.clear();
    vi.clearAllMocks();
  });

  // ---------- 初始状态 ----------
  describe('初始状态', () => {
    it('user 为 null', () => {
      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
    });

    it('isAuthenticated 为 false', () => {
      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
    });

    it('isAdmin 为 false', () => {
      const state = useAuthStore.getState();
      expect(state.isAdmin).toBe(false);
    });
  });

  // ---------- setUser ----------
  describe('setUser', () => {
    it('设置普通用户 → isAuthenticated 为 true, isAdmin 为 false', () => {
      const user = { id: 1, username: 'testuser', role: 'user' };
      useAuthStore.getState().setUser(user);

      const state = useAuthStore.getState();
      expect(state.user).toEqual(user);
      expect(state.isAuthenticated).toBe(true);
      expect(state.isAdmin).toBe(false);
    });

    it('设置 admin 用户 → isAdmin 为 true', () => {
      const user = { id: 2, username: 'admin', role: 'admin' };
      useAuthStore.getState().setUser(user);

      const state = useAuthStore.getState();
      expect(state.user).toEqual(user);
      expect(state.isAuthenticated).toBe(true);
      expect(state.isAdmin).toBe(true);
    });

    it('传入 null → isAuthenticated 和 isAdmin 均为 false', () => {
      useAuthStore.getState().setUser(null);

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isAdmin).toBe(false);
    });

    it('传入 undefined → isAuthenticated 和 isAdmin 均为 false', () => {
      useAuthStore.getState().setUser(undefined);

      const state = useAuthStore.getState();
      expect(state.user).toBeUndefined();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isAdmin).toBe(false);
    });

    it('传入空对象 → isAuthenticated 为 true, isAdmin 为 false', () => {
      useAuthStore.getState().setUser({});

      const state = useAuthStore.getState();
      expect(state.user).toEqual({});
      expect(state.isAuthenticated).toBe(true);
      expect(state.isAdmin).toBe(false);
    });
  });

  // ---------- login ----------
  describe('login', () => {
    it('存储 access_token 到 localStorage', () => {
      useAuthStore.getState().login('access-123', 'refresh-456', { id: 1, username: 'u' });
      expect(localStorage.getItem('access_token')).toBe('access-123');
    });

    it('存储 refresh_token 到 localStorage', () => {
      useAuthStore.getState().login('access-123', 'refresh-456', { id: 1, username: 'u' });
      expect(localStorage.getItem('refresh_token')).toBe('refresh-456');
    });

    it('设置用户状态', () => {
      const user = { id: 1, username: 'test', role: 'user' };
      useAuthStore.getState().login('a', 'r', user);

      const state = useAuthStore.getState();
      expect(state.user).toEqual(user);
      expect(state.isAuthenticated).toBe(true);
      expect(state.isAdmin).toBe(false);
    });

    it('admin 用户登录 → isAdmin 为 true', () => {
      const user = { id: 2, username: 'boss', role: 'admin' };
      useAuthStore.getState().login('a', 'r', user);

      const state = useAuthStore.getState();
      expect(state.isAdmin).toBe(true);
    });

    it('Token 为特殊字符时正常存储', () => {
      const specialToken = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmQ';
      useAuthStore.getState().login(specialToken, specialToken, { id: 1 });
      expect(localStorage.getItem('access_token')).toBe(specialToken);
    });

    it('Token 为空字符串时正常存储', () => {
      useAuthStore.getState().login('', '', { id: 1 });
      expect(localStorage.getItem('access_token')).toBe('');
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });
  });

  // ---------- logout ----------
  describe('logout', () => {
    it('清除 localStorage 中的 access_token', () => {
      localStorage.setItem('access_token', 'old-token');
      useAuthStore.getState().logout();
      expect(localStorage.getItem('access_token')).toBeNull();
    });

    it('清除 localStorage 中的 refresh_token', () => {
      localStorage.setItem('refresh_token', 'old-refresh');
      useAuthStore.getState().logout();
      expect(localStorage.getItem('refresh_token')).toBeNull();
    });

    it('重置所有状态为初始值', () => {
      useAuthStore.getState().login('a', 'r', { id: 1, username: 'u', role: 'admin' });
      useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isAdmin).toBe(false);
    });

    it('多次调用 logout 不抛出错误', () => {
      useAuthStore.getState().logout();
      expect(() => useAuthStore.getState().logout()).not.toThrow();
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });
  });

  // ---------- 完整流程 ----------
  describe('完整登录-登出流程', () => {
    it('login → logout → 状态正确切换', () => {
      // 初始状态
      expect(useAuthStore.getState().isAuthenticated).toBe(false);

      // 登录
      useAuthStore.getState().login('t1', 't2', { id: 1, username: 'u' });
      expect(useAuthStore.getState().isAuthenticated).toBe(true);

      // 登出
      useAuthStore.getState().logout();
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });

    it('重复登录覆盖之前的状态', () => {
      useAuthStore.getState().login('t1', 't2', { id: 1, username: 'first' });
      useAuthStore.getState().login('t3', 't4', { id: 2, username: 'second' });

      expect(useAuthStore.getState().user.username).toBe('second');
      expect(localStorage.getItem('access_token')).toBe('t3');
      expect(localStorage.getItem('refresh_token')).toBe('t4');
    });
  });
});
