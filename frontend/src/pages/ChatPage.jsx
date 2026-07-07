import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { message, Spin } from 'antd';
import SessionList from '../components/chat/SessionList';
import ChatMessage from '../components/chat/ChatMessage';
import ChatInput from '../components/chat/ChatInput';
import { useChatStore } from '../stores/useChatStore';
import { chatAPI } from '../api/chat';
import { useStreamQuery } from '../utils/sse';

export default function ChatPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);

  const {
    sessions, currentSessionId, messages,
    isStreaming, streamingContent, streamingSources,
    setSessions, setCurrentSessionId, setMessages,
    addMessage, setStreaming, appendStreamToken,
    setStreamingSources, resetStreaming,
  } = useChatStore();

  const [loadingMessages, setLoadingMessages] = useState(false);
  const { send, cancel } = useStreamQuery(currentSessionId);

  // 加载会话列表
  useEffect(() => {
    loadSessions();
  }, []);

  // 切换会话时加载消息
  useEffect(() => {
    if (sessionId) {
      setCurrentSessionId(Number(sessionId));
      loadMessages(Number(sessionId));
    } else {
      setCurrentSessionId(null);
      setMessages([]);
    }
  }, [sessionId]);

  const loadSessions = async () => {
    try {
      const { data } = await chatAPI.getSessions();
      setSessions(data.sessions || []);
    } catch {
      // ignore
    }
  };

  const loadMessages = async (id) => {
    setLoadingMessages(true);
    try {
      const { data } = await chatAPI.getMessages(id);
      setMessages(data.messages || []);
    } catch {
      message.error('加载消息失败');
    } finally {
      setLoadingMessages(false);
    }
  };

  const handleNewSession = async () => {
    try {
      resetStreaming();
      const { data } = await chatAPI.createSession('新的聊天');
      setSessions([data, ...sessions]);
      navigate(`/chat/${data.id}`);
    } catch {
      message.error('创建会话失败');
    }
  };

  const handleDeleteSession = async (id) => {
    try {
      await chatAPI.deleteSession(id);
      const newSessions = sessions.filter((s) => s.id !== id);
      setSessions(newSessions);
      if (currentSessionId === id) {
        if (newSessions.length > 0) {
          navigate(`/chat/${newSessions[0].id}`);
        } else {
          navigate('/chat');
        }
      }
      message.success('会话已删除');
    } catch {
      message.error('删除失败');
    }
  };

  const handleRenameSession = async (id, title) => {
    try {
      await chatAPI.renameSession(id, title);
      const updated = sessions.map((s) => (s.id === id ? { ...s, title } : s));
      setSessions(updated);
    } catch {
      message.error('重命名失败');
    }
  };

  const handleSend = (question) => {
    if (isStreaming) return;

    // 如果没有当前会话，先创建一个
    if (!currentSessionId) {
      chatAPI.createSession(question.slice(0, 30)).then(({ data }) => {
        setSessions([data, ...sessions]);
        setCurrentSessionId(data.id);
        navigate(`/chat/${data.id}`);
        // 创建后发送消息
        sendMessage(data.id, question);
      });
      return;
    }

    sendMessage(currentSessionId, question);
  };

  const sendMessage = (sid, question) => {
    // 添加用户消息
    const userMsg = { id: Date.now(), role: 'user', content: question, created_at: new Date().toISOString() };
    addMessage(userMsg);

    setStreaming(true);
    appendStreamToken(''); // 初始化流式内容

    send(question, {
      onToken: (token) => {
        appendStreamToken(token);
      },
      onSources: (sources) => {
        setStreamingSources(sources);
      },
      onDone: (data) => {
        // 从 Zustand 读取最新的累积内容（避免闭包陷阱）
        const state = useChatStore.getState();
        const aiMsg = {
          id: data.message_id,
          role: 'assistant',
          content: state.streamingContent,
          sources: state.streamingSources ? JSON.stringify(state.streamingSources) : null,
          created_at: new Date().toISOString(),
        };
        // 添加到消息列表并清除流式状态
        state.addMessage(aiMsg);
        state.resetStreaming();
        loadSessions(); // 刷新会话列表（更新标题）
      },
      onError: (err) => {
        message.error(err || '请求失败');
        resetStreaming();
      },
    });
  };

  const handleFeedback = async (messageId, feedback) => {
    try {
      await chatAPI.sendFeedback(messageId, feedback);
      const updated = messages.map((m) => (m.id === messageId ? { ...m, feedback } : m));
      setMessages(updated);
      message.success(feedback ? '感谢点赞' : '感谢反馈');
    } catch {
      message.error('反馈失败');
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* 会话列表侧边栏 */}
      <SessionList
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelect={(id) => navigate(`/chat/${id}`)}
        onNew={handleNewSession}
        onDelete={handleDeleteSession}
        onRename={handleRenameSession}
        isStreaming={isStreaming}
      />

      {/* 聊天区域 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#fff', maxWidth: 'calc(100% - 280px)' }}>
        {/* 消息列表 */}
        <div style={{ flex: 1, overflow: 'auto', padding: '20px 24px' }}>
          {loadingMessages ? (
            <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
          ) : messages.length === 0 && !isStreaming ? (
            <div style={{ textAlign: 'center', padding: 80, color: '#999' }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>🤖</div>
              <div style={{ fontSize: 18 }}>欢迎使用电商知识库问答助手</div>
              <div style={{ marginTop: 8 }}>请先上传商品知识库文档，然后在下方输入您的问题</div>
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onFeedback={handleFeedback}
                />
              ))}
            </>
          )}

          {/* 流式生成中 */}
          {isStreaming && (
            <ChatMessage
              message={{
                id: 'streaming',
                role: 'assistant',
                content: streamingContent,
                isStreaming: true,
              }}
            />
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 输入框 */}
        <ChatInput
          onSend={handleSend}
          onStop={cancel}
          isStreaming={isStreaming}
          disabled={false}
        />
      </div>
    </div>
  );
}
