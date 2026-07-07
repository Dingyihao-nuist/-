import { useState } from 'react';
import { Input, Button } from 'antd';
import { SendOutlined } from '@ant-design/icons';

const { TextArea } = Input;

export default function ChatInput({ onSend, onStop, isStreaming, disabled }) {
  const [value, setValue] = useState('');

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setValue('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      style={{
        padding: '12px 24px 20px',
        borderTop: '1px solid #f0f0f0',
        background: '#fff',
      }}
    >
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
        <TextArea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的问题... (Enter 发送，Shift+Enter 换行)"
          autoSize={{ minRows: 1, maxRows: 4 }}
          disabled={disabled}
          style={{ flex: 1, borderRadius: 8 }}
        />
        {isStreaming ? (
          <Button danger onClick={onStop} style={{ borderRadius: 8 }}>
            停止
          </Button>
        ) : (
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            disabled={!value.trim() || disabled}
            style={{ borderRadius: 8 }}
          >
            发送
          </Button>
        )}
      </div>
    </div>
  );
}
