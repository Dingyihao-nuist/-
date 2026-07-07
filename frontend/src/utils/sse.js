import { useEffect, useRef, useCallback } from 'react';

// SSE 流式请求 Hook
export function useStreamQuery(sessionId) {
  const abortRef = useRef(null);

  const send = useCallback(
    (question, callbacks) => {
      // 取消之前正在进行的请求
      if (abortRef.current) {
        abortRef.current.abort();
      }

      const token = localStorage.getItem('access_token');
      const controller = new AbortController();
      abortRef.current = controller;

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
            callbacks.onError?.(err.detail || '请求失败');
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

            let currentEvent = '';
            for (const line of lines) {
              if (line.startsWith('event: ')) {
                currentEvent = line.slice(7).trim();
                continue;
              }
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6));
                  if (currentEvent === 'token' || data.type === 'token')
                    callbacks.onToken?.(data.content || data.token);
                  else if (data.type === 'sources')
                    callbacks.onSources?.(data.sources);
                  else if (data.type === 'done')
                    callbacks.onDone?.(data);
                  else if (data.type === 'error')
                    callbacks.onError?.(data.message);
                } catch {
                  /* skip */
                }
              }
            }
          }
        })
        .catch((err) => {
          if (err.name !== 'AbortError') callbacks.onError?.(err.message);
        });

      return controller;
    },
    [sessionId]
  );

  const cancel = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  // 组件卸载时取消
  useEffect(() => {
    return () => cancel();
  }, [cancel]);

  return { send, cancel };
}
