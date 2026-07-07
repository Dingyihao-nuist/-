import { Typography } from 'antd';
import { UserOutlined, RobotOutlined } from '@ant-design/icons';
import MarkdownRenderer from '../../utils/markdown.jsx';
import SourceCard from './SourceCard';
import FeedbackButtons from './FeedbackButtons';

const { Text } = Typography;

export default function ChatMessage({ message, onFeedback }) {
  const isUser = message.role === 'user';
  const isStreaming = message.isStreaming;

  let sources = [];
  try {
    if (message.sources) {
      sources = typeof message.sources === 'string' ? JSON.parse(message.sources) : message.sources;
    }
  } catch {
    sources = [];
  }

  return (
    <div
      style={{
        display: 'flex',
        gap: 12,
        marginBottom: 20,
        flexDirection: isUser ? 'row-reverse' : 'row',
      }}
    >
      {/* 头像 */}
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          background: isUser ? '#1677ff' : '#52c41a',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontSize: 16,
          flexShrink: 0,
        }}
      >
        {isUser ? <UserOutlined /> : <RobotOutlined />}
      </div>

      {/* 消息内容 */}
      <div style={{ flex: 1, maxWidth: '75%' }}>
        {/* 角色标签 */}
        <div
          style={{
            marginBottom: 4,
            textAlign: isUser ? 'right' : 'left',
          }}
        >
          <Text type="secondary" style={{ fontSize: 12 }}>
            {isUser ? '我' : 'AI 助手'}
          </Text>
        </div>

        {/* 消息气泡 */}
        <div
          style={{
            padding: '12px 16px',
            borderRadius: 12,
            background: isUser ? '#e6f4ff' : '#f5f5f5',
            border: isUser ? '1px solid #91caff' : '1px solid #e5e7eb',
            lineHeight: 1.8,
          }}
        >
          {isUser ? (
            <div>{message.content}</div>
          ) : (
            <div className="markdown-body">
              <MarkdownRenderer content={message.content} />
              {isStreaming && (
                <span style={{ display: 'inline-block', width: 2, height: 16, background: '#1677ff', animation: 'blink 1s infinite' }} />
              )}
            </div>
          )}
        </div>

        {/* 来源引用 */}
        {!isUser && sources.length > 0 && (
          <div style={{ marginTop: 8 }}>
            {sources.map((source, idx) => (
              <SourceCard key={idx} source={source} index={idx + 1} />
            ))}
          </div>
        )}

        {/* 反馈按钮 */}
        {!isUser && !isStreaming && message.id !== 'streaming' && (
          <FeedbackButtons messageId={message.id} currentFeedback={message.feedback} onFeedback={onFeedback} />
        )}
      </div>
    </div>
  );
}
