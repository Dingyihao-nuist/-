import { Typography } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';

const { Text } = Typography;

export default function SourceCard({ source, index }) {
  return (
    <div className="source-card">
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <FileTextOutlined style={{ color: '#1677ff' }} />
        <Text strong style={{ fontSize: 12 }}>
          来源{index}：{source.doc_name || source.filename || '未知文档'}
        </Text>
      </div>
      <Text style={{ fontSize: 12, color: '#666' }}>
        {source.preview || source.content?.slice(0, 150) || '...'}
      </Text>
    </div>
  );
}
