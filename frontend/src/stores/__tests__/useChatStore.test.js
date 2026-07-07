import { describe, it, expect, beforeEach } from 'vitest';
import { useChatStore } from '../useChatStore';

describe('useChatStore', () => {
  beforeEach(() => {
    useChatStore.setState({
      sessions: [],
      currentSessionId: null,
      messages: [],
      isStreaming: false,
      streamingContent: '',
      streamingSources: null,
    });
  });

  // ---------- 初始状态 ----------
  describe('初始状态', () => {
    it('sessions 为空数组', () => {
      expect(useChatStore.getState().sessions).toEqual([]);
    });

    it('currentSessionId 为 null', () => {
      expect(useChatStore.getState().currentSessionId).toBeNull();
    });

    it('messages 为空数组', () => {
      expect(useChatStore.getState().messages).toEqual([]);
    });

    it('isStreaming 为 false', () => {
      expect(useChatStore.getState().isStreaming).toBe(false);
    });

    it('streamingContent 为空字符串', () => {
      expect(useChatStore.getState().streamingContent).toBe('');
    });

    it('streamingSources 为 null', () => {
      expect(useChatStore.getState().streamingSources).toBeNull();
    });
  });

  // ---------- setSessions ----------
  describe('setSessions', () => {
    it('替换 sessions 列表', () => {
      const sessions = [
        { id: '1', title: 'Chat 1' },
        { id: '2', title: 'Chat 2' },
      ];
      useChatStore.getState().setSessions(sessions);
      expect(useChatStore.getState().sessions).toEqual(sessions);
    });

    it('设置为空数组', () => {
      useChatStore.getState().setSessions([{ id: '1' }]);
      useChatStore.getState().setSessions([]);
      expect(useChatStore.getState().sessions).toEqual([]);
    });
  });

  // ---------- addSession ----------
  describe('addSession', () => {
    it('添加到 sessions 列表头部', () => {
      useChatStore.setState({ sessions: [{ id: '1', title: 'Old' }] });
      useChatStore.getState().addSession({ id: '2', title: 'New' });

      const sessions = useChatStore.getState().sessions;
      expect(sessions).toHaveLength(2);
      expect(sessions[0]).toEqual({ id: '2', title: 'New' });
      expect(sessions[1]).toEqual({ id: '1', title: 'Old' });
    });

    it('空 sessions 时添加成功', () => {
      useChatStore.getState().addSession({ id: '1', title: 'First' });
      expect(useChatStore.getState().sessions).toHaveLength(1);
      expect(useChatStore.getState().sessions[0]).toEqual({ id: '1', title: 'First' });
    });
  });

  // ---------- removeSession ----------
  describe('removeSession', () => {
    it('按 id 删除会话', () => {
      useChatStore.setState({
        sessions: [
          { id: '1', title: 'A' },
          { id: '2', title: 'B' },
          { id: '3', title: 'C' },
        ],
      });
      useChatStore.getState().removeSession('2');

      const sessions = useChatStore.getState().sessions;
      expect(sessions).toHaveLength(2);
      expect(sessions.map((s) => s.id)).toEqual(['1', '3']);
    });

    it('删除当前会话时重置 currentSessionId 为 null', () => {
      useChatStore.setState({
        sessions: [{ id: '1' }, { id: '2' }],
        currentSessionId: '1',
        messages: [{ role: 'user', content: 'hello' }],
      });
      useChatStore.getState().removeSession('1');

      expect(useChatStore.getState().currentSessionId).toBeNull();
    });

    it('删除当前会话时清空 messages', () => {
      useChatStore.setState({
        sessions: [{ id: '1' }, { id: '2' }],
        currentSessionId: '1',
        messages: [{ role: 'user', content: 'hello' }],
      });
      useChatStore.getState().removeSession('1');

      expect(useChatStore.getState().messages).toEqual([]);
    });

    it('删除非当前会话时不改变 currentSessionId 和 messages', () => {
      useChatStore.setState({
        sessions: [{ id: '1' }, { id: '2' }],
        currentSessionId: '1',
        messages: [{ role: 'user', content: 'hello' }],
      });
      useChatStore.getState().removeSession('2');

      expect(useChatStore.getState().currentSessionId).toBe('1');
      expect(useChatStore.getState().messages).toHaveLength(1);
    });

    it('删除不存在的 id 不影响 sessions', () => {
      useChatStore.setState({ sessions: [{ id: '1' }] });
      useChatStore.getState().removeSession('nonexistent');

      expect(useChatStore.getState().sessions).toHaveLength(1);
    });
  });

  // ---------- updateSession ----------
  describe('updateSession', () => {
    it('更新指定会话的部分字段', () => {
      useChatStore.setState({
        sessions: [
          { id: '1', title: 'Old Title', count: 10 },
          { id: '2', title: 'Keep' },
        ],
      });
      useChatStore.getState().updateSession('1', { title: 'New Title' });

      const updated = useChatStore.getState().sessions.find((s) => s.id === '1');
      expect(updated.title).toBe('New Title');
      expect(updated.count).toBe(10); // 保留未更新的字段
    });

    it('更新不存在的 id 不改变 sessions', () => {
      useChatStore.setState({ sessions: [{ id: '1', title: 'A' }] });
      useChatStore.getState().updateSession('nonexistent', { title: 'X' });

      expect(useChatStore.getState().sessions).toHaveLength(1);
      expect(useChatStore.getState().sessions[0].title).toBe('A');
    });
  });

  // ---------- setCurrentSessionId ----------
  describe('setCurrentSessionId', () => {
    it('设置当前会话 ID', () => {
      useChatStore.getState().setCurrentSessionId('session-1');
      expect(useChatStore.getState().currentSessionId).toBe('session-1');
    });

    it('设置为 null', () => {
      useChatStore.getState().setCurrentSessionId('session-1');
      useChatStore.getState().setCurrentSessionId(null);
      expect(useChatStore.getState().currentSessionId).toBeNull();
    });
  });

  // ---------- setMessages ----------
  describe('setMessages', () => {
    it('替换消息列表', () => {
      const messages = [
        { id: '1', role: 'user', content: 'Hi' },
        { id: '2', role: 'assistant', content: 'Hello' },
      ];
      useChatStore.getState().setMessages(messages);
      expect(useChatStore.getState().messages).toEqual(messages);
    });

    it('设置为空数组', () => {
      useChatStore.getState().setMessages([{ id: '1' }]);
      useChatStore.getState().setMessages([]);
      expect(useChatStore.getState().messages).toEqual([]);
    });

    it('设置大量消息', () => {
      const manyMessages = Array.from({ length: 1000 }, (_, i) => ({
        id: `${i}`,
        role: 'user',
        content: `Message ${i}`,
      }));
      useChatStore.getState().setMessages(manyMessages);
      expect(useChatStore.getState().messages).toHaveLength(1000);
    });
  });

  // ---------- addMessage ----------
  describe('addMessage', () => {
    it('追加消息到列表末尾', () => {
      useChatStore.setState({ messages: [{ id: '1', role: 'user', content: 'Hi' }] });
      useChatStore.getState().addMessage({ id: '2', role: 'assistant', content: 'Hello' });

      const messages = useChatStore.getState().messages;
      expect(messages).toHaveLength(2);
      expect(messages[1].id).toBe('2');
    });

    it('空 messages 时添加成功', () => {
      useChatStore.getState().addMessage({ id: '1', role: 'user', content: 'First' });
      expect(useChatStore.getState().messages).toHaveLength(1);
    });
  });

  // ---------- 流式输出 ----------
  describe('流式输出', () => {
    it('setStreaming 切换流式状态', () => {
      useChatStore.getState().setStreaming(true);
      expect(useChatStore.getState().isStreaming).toBe(true);

      useChatStore.getState().setStreaming(false);
      expect(useChatStore.getState().isStreaming).toBe(false);
    });

    it('appendStreamToken 累积流式内容', () => {
      useChatStore.getState().appendStreamToken('Hello');
      useChatStore.getState().appendStreamToken(' ');
      useChatStore.getState().appendStreamToken('World');

      expect(useChatStore.getState().streamingContent).toBe('Hello World');
    });

    it('appendStreamToken 处理空字符串', () => {
      useChatStore.getState().appendStreamToken('');
      expect(useChatStore.getState().streamingContent).toBe('');
    });

    it('appendStreamToken 处理中文和特殊字符', () => {
      useChatStore.getState().appendStreamToken('你好');
      useChatStore.getState().appendStreamToken('🚀');
      useChatStore.getState().appendStreamToken('\n');

      expect(useChatStore.getState().streamingContent).toBe('你好🚀\n');
    });

    it('setStreamingSources 设置引用来源', () => {
      const sources = [
        { title: 'doc1.pdf', page: 3 },
        { title: 'doc2.pdf', page: 7 },
      ];
      useChatStore.getState().setStreamingSources(sources);
      expect(useChatStore.getState().streamingSources).toEqual(sources);
    });

    it('setStreamingSources 设置为 null', () => {
      useChatStore.getState().setStreamingSources([{ title: 'x' }]);
      useChatStore.getState().setStreamingSources(null);
      expect(useChatStore.getState().streamingSources).toBeNull();
    });

    it('resetStreaming 清空所有流式状态', () => {
      useChatStore.setState({
        isStreaming: true,
        streamingContent: 'some content',
        streamingSources: [{ title: 'ref' }],
      });
      useChatStore.getState().resetStreaming();

      expect(useChatStore.getState().isStreaming).toBe(false);
      expect(useChatStore.getState().streamingContent).toBe('');
      expect(useChatStore.getState().streamingSources).toBeNull();
    });
  });

  // ---------- 综合场景 ----------
  describe('综合场景', () => {
    it('切换会话后消息列表独立管理', () => {
      // 会话 1 的消息
      useChatStore.getState().setCurrentSessionId('s1');
      useChatStore.getState().setMessages([{ id: 'm1', content: 'Chat 1 msg' }]);

      // 切换会话后替换消息
      useChatStore.getState().setCurrentSessionId('s2');
      useChatStore.getState().setMessages([{ id: 'm2', content: 'Chat 2 msg' }]);

      expect(useChatStore.getState().messages).toHaveLength(1);
      expect(useChatStore.getState().messages[0].content).toBe('Chat 2 msg');
    });
  });
});
