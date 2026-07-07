import { List, Button, Input, Dropdown, Typography, Badge } from 'antd';
import { PlusOutlined, SearchOutlined, DeleteOutlined, EditOutlined, MoreOutlined, MessageOutlined } from '@ant-design/icons';
import { useState } from 'react';

const { Text } = Typography;

export default function SessionList({ sessions, currentSessionId, onSelect, onNew, onDelete, onRename, isStreaming }) {
  const [search, setSearch] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const filtered = sessions.filter((s) =>
    s.title.toLowerCase().includes(search.toLowerCase())
  );

  const handleStartRename = (session) => {
    setEditingId(session.id);
    setEditTitle(session.title);
  };

  const handleConfirmRename = (id) => {
    if (editTitle.trim()) {
      onRename(id, editTitle.trim());
    }
    setEditingId(null);
  };

  return (
    <div style={{ width: 280, borderRight: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column', background: '#fafafa' }}>
      {/* 搜索 + 新建 */}
      <div style={{ padding: 12, borderBottom: '1px solid #f0f0f0' }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          block
          onClick={onNew}
          disabled={isStreaming}
        >
          新会话
        </Button>
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索会话..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ marginTop: 8 }}
          size="small"
          allowClear
        />
      </div>

      {/* 会话列表 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <List
          dataSource={filtered}
          locale={{ emptyText: '暂无会话' }}
          renderItem={(session) => (
            <div
              key={session.id}
              onClick={() => onSelect(session.id)}
              style={{
                padding: '10px 12px',
                cursor: 'pointer',
                background: session.id === currentSessionId ? '#e6f4ff' : 'transparent',
                borderBottom: '1px solid #f0f0f0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ flex: 1, overflow: 'hidden' }}>
                {editingId === session.id ? (
                  <Input
                    size="small"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onBlur={() => handleConfirmRename(session.id)}
                    onPressEnter={() => handleConfirmRename(session.id)}
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <MessageOutlined style={{ fontSize: 12, color: '#999' }} />
                      <Text
                        style={{
                          fontWeight: session.id === currentSessionId ? 600 : 400,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxWidth: 160,
                        }}
                      >
                        {session.title}
                      </Text>
                    </div>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {new Date(session.updated_at).toLocaleDateString('zh-CN')}
                    </Text>
                  </>
                )}
              </div>

              {/* 操作菜单 */}
              <Dropdown
                menu={{
                  items: [
                    { key: 'rename', icon: <EditOutlined />, label: '重命名', onClick: (e) => { e.domEvent.stopPropagation(); handleStartRename(session); } },
                    { key: 'delete', icon: <DeleteOutlined />, label: '删除', danger: true, onClick: (e) => { e.domEvent.stopPropagation(); onDelete(session.id); } },
                  ],
                }}
                trigger={['click']}
              >
                <Button
                  type="text"
                  size="small"
                  icon={<MoreOutlined />}
                  onClick={(e) => e.stopPropagation()}
                />
              </Dropdown>
            </div>
          )}
        />
      </div>
    </div>
  );
}
