import { describe, it, expect, beforeEach, vi } from 'vitest';

// Hoist the mockClient so it's available inside the vi.mock factory
const { mockClient } = vi.hoisted(() => ({
  mockClient: {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../client', () => ({
  default: mockClient,
}));

import { authAPI } from '../auth';

describe('authAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ---------- register ----------
  describe('register', () => {
    it('调用 POST /auth/register 并传递注册数据', async () => {
      const data = { username: 'newuser', email: 'a@b.com', password: 'pass123' };
      mockClient.post.mockResolvedValue({ data: { id: 1, username: 'newuser' } });

      await authAPI.register(data);

      expect(mockClient.post).toHaveBeenCalledWith('/auth/register', data);
      expect(mockClient.post).toHaveBeenCalledTimes(1);
    });

    it('注册失败时传递错误', async () => {
      const error = { response: { status: 409, data: { detail: '用户名已存在' } } };
      mockClient.post.mockRejectedValue(error);

      await expect(authAPI.register({ username: 'exist' })).rejects.toEqual(error);
      expect(mockClient.post).toHaveBeenCalledWith('/auth/register', { username: 'exist' });
    });

    it('注册数据为空对象时正常调用', async () => {
      mockClient.post.mockResolvedValue({ data: {} });
      await authAPI.register({});
      expect(mockClient.post).toHaveBeenCalledWith('/auth/register', {});
    });
  });

  // ---------- login ----------
  describe('login', () => {
    it('调用 POST /auth/login 并传递登录凭据', async () => {
      const data = { username: 'admin', password: '123456' };
      mockClient.post.mockResolvedValue({
        data: { access_token: 'token-xxx', refresh_token: 'rt-xxx', user: { id: 1 } },
      });

      const result = await authAPI.login(data);

      expect(mockClient.post).toHaveBeenCalledWith('/auth/login', data);
      expect(result.data.access_token).toBe('token-xxx');
      expect(result.data.user).toEqual({ id: 1 });
    });

    it('密码错误时传递错误响应', async () => {
      const error = { response: { status: 401, data: { detail: '密码错误' } } };
      mockClient.post.mockRejectedValue(error);

      await expect(authAPI.login({ username: 'admin', password: 'wrong' })).rejects.toEqual(error);
    });

    it('用户不存在时传递错误响应', async () => {
      const error = { response: { status: 404, data: { detail: '用户不存在' } } };
      mockClient.post.mockRejectedValue(error);

      await expect(authAPI.login({ username: 'nobody', password: 'x' })).rejects.toEqual(error);
    });
  });

  // ---------- refresh ----------
  describe('refresh', () => {
    it('调用 POST /auth/refresh 并传递 refresh_token', async () => {
      mockClient.post.mockResolvedValue({
        data: { access_token: 'new-access', refresh_token: 'new-refresh' },
      });

      const result = await authAPI.refresh('old-refresh-token');

      expect(mockClient.post).toHaveBeenCalledWith('/auth/refresh', {
        refresh_token: 'old-refresh-token',
      });
      expect(result.data.access_token).toBe('new-access');
    });

    it('refresh token 无效时传递错误', async () => {
      const error = { response: { status: 401, data: { detail: 'Token 已过期' } } };
      mockClient.post.mockRejectedValue(error);

      await expect(authAPI.refresh('invalid')).rejects.toEqual(error);
    });

    it('refresh token 为空字符串时正常调用', async () => {
      mockClient.post.mockResolvedValue({ data: {} });
      await authAPI.refresh('');
      expect(mockClient.post).toHaveBeenCalledWith('/auth/refresh', { refresh_token: '' });
    });
  });

  // ---------- getMe ----------
  describe('getMe', () => {
    it('调用 GET /auth/me 获取当前用户信息', async () => {
      const user = { id: 1, username: 'admin', role: 'admin', email: 'admin@test.com' };
      mockClient.get.mockResolvedValue({ data: user });

      const result = await authAPI.getMe();

      expect(mockClient.get).toHaveBeenCalledWith('/auth/me');
      expect(mockClient.get).toHaveBeenCalledTimes(1);
      expect(result.data).toEqual(user);
    });

    it('未认证时返回 401', async () => {
      const error = { response: { status: 401 } };
      mockClient.get.mockRejectedValue(error);

      await expect(authAPI.getMe()).rejects.toEqual(error);
    });
  });

  // ---------- changePassword ----------
  describe('changePassword', () => {
    it('调用 PUT /auth/change-password 传递新旧密码', async () => {
      const data = { old_password: 'old', new_password: 'new123' };
      mockClient.put.mockResolvedValue({ data: { message: '密码修改成功' } });

      const result = await authAPI.changePassword(data);

      expect(mockClient.put).toHaveBeenCalledWith('/auth/change-password', data);
      expect(mockClient.put).toHaveBeenCalledTimes(1);
      expect(result.data.message).toBe('密码修改成功');
    });

    it('旧密码错误时传递错误', async () => {
      const error = { response: { status: 400, data: { detail: '旧密码不正确' } } };
      mockClient.put.mockRejectedValue(error);

      await expect(
        authAPI.changePassword({ old_password: 'wrong', new_password: 'n' })
      ).rejects.toEqual(error);
    });

    it('新密码为空时正常调用 API', async () => {
      mockClient.put.mockResolvedValue({ data: {} });
      await authAPI.changePassword({ old_password: 'old', new_password: '' });
      expect(mockClient.put).toHaveBeenCalledWith('/auth/change-password', {
        old_password: 'old',
        new_password: '',
      });
    });
  });

  // ---------- API 方法导出完整性 ----------
  describe('API 导出完整性', () => {
    it('authAPI 包含所有预期的方法', () => {
      expect(authAPI).toHaveProperty('register');
      expect(authAPI).toHaveProperty('login');
      expect(authAPI).toHaveProperty('refresh');
      expect(authAPI).toHaveProperty('getMe');
      expect(authAPI).toHaveProperty('changePassword');

      expect(typeof authAPI.register).toBe('function');
      expect(typeof authAPI.login).toBe('function');
      expect(typeof authAPI.refresh).toBe('function');
      expect(typeof authAPI.getMe).toBe('function');
      expect(typeof authAPI.changePassword).toBe('function');
    });
  });
});
