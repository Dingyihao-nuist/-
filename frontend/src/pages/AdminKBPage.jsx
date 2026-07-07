import { useState, useEffect } from 'react';
import { Typography, Button, Input, Space, Statistic, Modal, message } from 'antd';
import { UploadOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import DocumentTable from '../components/kb/DocumentTable';
import UploadModal from '../components/kb/UploadModal';
import { kbAPI } from '../api/kb';

const { Title } = Typography;

export default function AdminKBPage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ total_documents: 0, total_chunks: 0, total_size: 0 });
  const [search, setSearch] = useState('');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [chunkViewOpen, setChunkViewOpen] = useState(false);
  const [viewingChunks, setViewingChunks] = useState([]);

  useEffect(() => {
    loadDocuments();
    loadStats();
  }, []);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const { data } = await kbAPI.getDocuments({ search, page: 1, per_page: 100 });
      setDocuments(data.documents || []);
    } catch {
      message.error('加载文档列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const { data } = await kbAPI.getStats();
      setStats(data);
    } catch {
      // ignore
    }
  };

  const handleDelete = async (id) => {
    try {
      await kbAPI.deleteDocument(id);
      message.success('文档已删除');
      loadDocuments();
      loadStats();
    } catch {
      message.error('删除失败');
    }
  };

  const handleReindex = async (id) => {
    try {
      await kbAPI.reindex(id);
      message.success('重建索引任务已提交');
      loadDocuments();
    } catch {
      message.error('重建失败');
    }
  };

  const handleView = async (record) => {
    try {
      const { data } = await kbAPI.getChunks(record.id);
      setViewingChunks(data.chunks || []);
      setChunkViewOpen(true);
    } catch {
      message.error('获取分块详情失败');
    }
  };

  const handleUploadSuccess = () => {
    setUploadOpen(false);
    loadDocuments();
    loadStats();
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>📁 知识库管理</Title>

      {/* 统计卡片 */}
      <div style={{ display: 'flex', gap: 24, marginBottom: 24 }}>
        <Statistic title="文档数量" value={stats.total_documents || documents.length} />
        <Statistic title="分块总数" value={stats.total_chunks || 0} />
        <Statistic
          title="总大小"
          value={stats.total_size ? `${(stats.total_size / 1024 / 1024).toFixed(1)} MB` : '-'}
        />
      </div>

      {/* 操作栏 */}
      <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
        <Button type="primary" icon={<UploadOutlined />} onClick={() => setUploadOpen(true)}>
          上传文档
        </Button>
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索文档..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onPressEnter={loadDocuments}
          style={{ width: 240 }}
          allowClear
        />
        <Button icon={<ReloadOutlined />} onClick={() => { loadDocuments(); loadStats(); }}>
          刷新
        </Button>
      </div>

      {/* 文档表格 */}
      <DocumentTable
        documents={documents}
        loading={loading}
        onDelete={handleDelete}
        onReindex={handleReindex}
        onView={handleView}
      />

      {/* 上传弹窗 */}
      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onSuccess={handleUploadSuccess}
      />

      {/* 分块查看弹窗 */}
      <Modal
        title="文档分块详情"
        open={chunkViewOpen}
        onCancel={() => setChunkViewOpen(false)}
        footer={null}
        width={700}
      >
        <div style={{ maxHeight: 400, overflow: 'auto' }}>
          {viewingChunks.map((chunk, idx) => (
            <div
              key={idx}
              style={{
                padding: 12,
                marginBottom: 8,
                background: '#f9fafb',
                borderRadius: 8,
                border: '1px solid #e5e7eb',
              }}
            >
              <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>分块 #{chunk.chunk_index}</div>
              <div style={{ fontSize: 13, lineHeight: 1.6 }}>{chunk.content}</div>
            </div>
          ))}
          {viewingChunks.length === 0 && <div style={{ textAlign: 'center', color: '#999' }}>暂无分块数据</div>}
        </div>
      </Modal>
    </div>
  );
}
