import client from './client';

export const chatAPI = {
  getSessions: (page = 1) => client.get('/chat/sessions', { params: { page, per_page: 50 } }),
  createSession: (title) => client.post('/chat/sessions', { title }),
  renameSession: (id, title) => client.put(`/chat/sessions/${id}`, { title }),
  deleteSession: (id) => client.delete(`/chat/sessions/${id}`),
  getMessages: (id) => client.get(`/chat/sessions/${id}/messages`),
  sendFeedback: (messageId, feedback) => client.put(`/chat/messages/${messageId}/feedback`, { feedback }),
  exportChat: (sessionId, format = 'md') => client.get(`/chat/sessions/${sessionId}/export`, { params: { format }, responseType: 'blob' }),
};

// SSE 流式请求（不经过 Axios 拦截器，手动处理）
export function streamQuery(sessionId, question, { onToken, onSources, onDone, onError }) {
  const token = localStorage.getItem('access_token');
  const controller = new AbortController();

  fetch(`/api/chat/sessions/${sessionId}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ question }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: '请求失败' }));
        onError?.(err.detail || '请求失败');
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) continue;
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'token') onToken?.(data.content);
              else if (data.type === 'sources') onSources?.(data.sources);
              else if (data.type === 'done') onDone?.(data);
              else if (data.type === 'error') onError?.(data.message);
            } catch { /* skip parse errors */ }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError?.(err.message);
    });

  return controller; // 返回 AbortController 用于取消
}
