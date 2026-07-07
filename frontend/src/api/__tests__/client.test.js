import { describe, it, expect, vi } from 'vitest';

// Hoist the interceptor spies so the vi.mock factory can reference them
const { requestUseSpy, responseUseSpy } = vi.hoisted(() => ({
  requestUseSpy: vi.fn(),
  responseUseSpy: vi.fn(),
}));

// Mock axios — the client module will use this at import time
vi.mock('axios', () => {
  // This instance is what axios.create() returns
  const mockClientInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: requestUseSpy },
      response: { use: responseUseSpy },
    },
  };

  return {
    default: {
      create: vi.fn(() => mockClientInstance),
      post: vi.fn(),
      get: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    },
  };
});

// Explicitly import the client to trigger axios.create and interceptor registration
import client from '../client';
void client; // suppress unused warning

describe('API Client (axios 实例)', () => {
  // ---------- 实例创建 ----------
  describe('创建配置', () => {
    it('baseURL 为 /api', async () => {
      const { default: axiosMod } = await import('axios');
      expect(axiosMod.create).toHaveBeenCalledTimes(1);
      const config = axiosMod.create.mock.calls[0][0];
      expect(config.baseURL).toBe('/api');
    });

    it('timeout 为 30000ms', async () => {
      const { default: axiosMod } = await import('axios');
      const config = axiosMod.create.mock.calls[0][0];
      expect(config.timeout).toBe(30000);
    });

    it('默认 Content-Type 为 application/json', async () => {
      const { default: axiosMod } = await import('axios');
      const config = axiosMod.create.mock.calls[0][0];
      expect(config.headers['Content-Type']).toBe('application/json');
    });
  });

  // ---------- 请求拦截器 ----------
  describe('请求拦截器', () => {
    it('拦截器已注册', () => {
      expect(requestUseSpy).toHaveBeenCalledTimes(1);
    });

    it('access_token 存在时附加 Authorization header', () => {
      localStorage.setItem('access_token', 'test-token-123');

      const interceptor = requestUseSpy.mock.calls[0]?.[0];
      expect(interceptor).toBeDefined();

      const config = { headers: {} };
      const result = interceptor(config);

      expect(result.headers.Authorization).toBe('Bearer test-token-123');
    });

    it('access_token 不存在时不附加 Authorization header', () => {
      localStorage.removeItem('access_token');

      const interceptor = requestUseSpy.mock.calls[0]?.[0];
      const config = { headers: {} };
      const result = interceptor(config);

      expect(result.headers.Authorization).toBeUndefined();
    });

    it('保留已有自定义 headers', () => {
      localStorage.setItem('access_token', 'mytoken');

      const interceptor = requestUseSpy.mock.calls[0]?.[0];
      const config = { headers: { 'X-Custom': 'custom-value', 'Accept': 'text/plain' } };
      const result = interceptor(config);

      expect(result.headers['X-Custom']).toBe('custom-value');
      expect(result.headers['Accept']).toBe('text/plain');
      expect(result.headers.Authorization).toBe('Bearer mytoken');
    });

    it('无 headers 属性的 config 会抛出错误（需要调用方保证 headers 存在）', () => {
      localStorage.setItem('access_token', 'tok');

      const interceptor = requestUseSpy.mock.calls[0]?.[0];
      const config = {};

      // Source code does config.headers.Authorization = ... without checking
      // if config.headers exists. This throws if headers is missing.
      expect(() => interceptor(config)).toThrow(TypeError);
    });

    it('始终返回 config 对象', () => {
      const interceptor = requestUseSpy.mock.calls[0]?.[0];
      const config = { url: '/test', headers: {} };
      const result = interceptor(config);

      expect(result).toBe(config);
      expect(result.url).toBe('/test');
    });
  });

  // ---------- 响应拦截器 - 成功处理 ----------
  describe('响应拦截器 - 成功处理', () => {
    it('拦截器已注册', () => {
      expect(responseUseSpy).toHaveBeenCalledTimes(1);
    });

    it('成功响应原样透传', () => {
      const successHandler = responseUseSpy.mock.calls[0]?.[0];
      expect(successHandler).toBeDefined();

      const response = { data: { result: 'ok' }, status: 200, headers: {} };
      const result = successHandler(response);

      expect(result).toBe(response);
      expect(result.data.result).toBe('ok');
      expect(result.status).toBe(200);
    });
  });

  // ---------- 响应拦截器 - 错误处理 ----------
  describe('响应拦截器 - 错误处理', () => {
    let errorHandler;

    beforeAll(() => {
      // Capture the error handler once (second argument to response.use)
      errorHandler = responseUseSpy.mock.calls[0]?.[1];
    });

    it('错误处理器已注册', () => {
      expect(errorHandler).toBeDefined();
      expect(typeof errorHandler).toBe('function');
    });

    it('非 401 错误直接 reject', async () => {
      const error = {
        response: { status: 500, data: { message: 'Server Error' } },
        config: { url: '/api/test' },
      };

      await expect(errorHandler(error)).rejects.toEqual(error);
    });

    it('网络错误（无 response 属性）直接 reject', async () => {
      const networkError = new Error('Network Error');
      networkError.config = { url: '/api/data' };

      await expect(errorHandler(networkError)).rejects.toThrow('Network Error');
    });

    it('response 为 undefined 的 401 直接 reject（安全边界）', async () => {
      const error = { config: { url: '/api/unknown' } };

      // response is undefined, so error.response?.status is undefined
      // This should fall through to the final return Promise.reject(error)
      await expect(errorHandler(error)).rejects.toEqual(error);
    });

    it('401 且无 refresh_token 时清除 localStorage 中的 Token', async () => {
      // Set tokens first
      localStorage.setItem('access_token', 'expired-access');
      localStorage.setItem('refresh_token', ''); // Empty string

      const error = {
        response: { status: 401 },
        config: { url: '/api/protected', headers: {} },
      };

      // The interceptor will:
      // 1. Check error.response.status === 401
      // 2. Get refresh_token (empty string → falsy)
      // 3. Clear tokens and redirect
      // Redirect (window.location.href = '/login') may throw in jsdom
      try {
        await errorHandler(error);
      } catch (_) {
        // Redirect may fail in jsdom — that's expected
      }

      // Tokens should be cleared
      expect(localStorage.getItem('access_token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
    });
  });
});
