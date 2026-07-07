import { Table, Tag, Button, Space, Popconfirm } from 'antd';
import { EyeOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import { useState } from 'react';

const statusMap = {
  processing: { color: 'processing', text: '处理中' },
  ready: { color: 'success', text: '就绪' },
  error: { color: 'error', text: '失败' },
};

export default function DocumentTable({ documents, loading, onDelete, onReindex, onView }) {
  const columns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'file_type',
      key: 'file_type',
      width: 80,
      render: (type) => <Tag>{type?.toUpperCase()}</Tag>,
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 90,
      render: (size) => {
        if (!size) return '-';
        return size > 1024 * 1024 ? `${(size / 1024 / 1024).toFixed(1)}MB` : `${(size / 1024).toFixed(0)}KB`;
      },
    },
    {
      title: '分块数',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status) => {
        const info = statusMap[status] || { color: 'default', text: status };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (val) => val ? new Date(val).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => onView(record)}>
            查看
          </Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => onReindex(record.id)}>
            重建
          </Button>
          <Popconfirm title="确定删除此文档？将同时删除关联的向量数据。" onConfirm={() => onDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={documents}
      rowKey="id"
      loading={loading}
      pagination={{ pageSize: 20, showTotal: (total) => `共 ${total} 条` }}
      size="middle"
    />
  );
}
