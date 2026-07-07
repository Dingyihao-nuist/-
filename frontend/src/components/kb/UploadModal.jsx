import { useState } from 'react';
import { Modal, Upload, message } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { kbAPI } from '../../api/kb';

const { Dragger } = Upload;

export default function UploadModal({ open, onClose, onSuccess }) {
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (file) => {
    setUploading(true);
    const formData = new FormData();
    formData.append('files', file);
    try {
      await kbAPI.upload(formData);
      message.success(`${file.name} 上传成功，正在处理中...`);
      onSuccess?.();
    } catch (err) {
      message.error(err.response?.data?.detail || '上传失败');
    } finally {
      setUploading(false);
    }
    return false; // 阻止默认上传行为
  };

  return (
    <Modal title="上传知识库文档" open={open} onCancel={onClose} footer={null} destroyOnClose>
      <Dragger
        multiple
        beforeUpload={handleUpload}
        showUploadList={false}
        disabled={uploading}
        accept=".pdf,.docx,.txt,.md,.csv,.xlsx"
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
        <p className="ant-upload-hint">
          支持 PDF、Word、Excel、TXT、Markdown、CSV 格式（单个文件不超过 20MB）
        </p>
      </Dragger>
    </Modal>
  );
}
