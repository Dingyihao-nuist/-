import { useState, useEffect } from 'react';
import { Typography, Card, Row, Col, Statistic, Table, Spin } from 'antd';
import { UserOutlined, MessageOutlined, LikeOutlined, FileTextOutlined } from '@ant-design/icons';
import { statsAPI } from '../api/stats';

const { Title } = Typography;

export default function AdminDashboard() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState({ total_users: 0, total_sessions: 0, total_messages: 0, feedback_rate: '0%' });
  const [popular, setPopular] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [overviewRes, popularRes] = await Promise.all([
        statsAPI.getOverview().catch(() => ({ data: {} })),
        statsAPI.getPopular(10).catch(() => ({ data: { questions: [] } })),
      ]);
      setOverview(overviewRes.data);
      setPopular(popularRes.data.questions || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;
  }

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>📊 统计仪表盘</Title>

      {/* 概览卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="总用户数" value={overview.total_users || 0} prefix={<UserOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="总会话数" value={overview.total_sessions || 0} prefix={<MessageOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="总问答量" value={overview.total_messages || 0} prefix={<FileTextOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="好评率" value={overview.feedback_rate || '0%'} prefix={<LikeOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* 热门问题 */}
      <Card title="🔥 热门问题 Top 10">
        <Table
          dataSource={popular}
          rowKey="question"
          pagination={false}
          size="small"
          columns={[
            { title: '排名', key: 'rank', width: 60, render: (_, __, i) => i + 1 },
            { title: '问题', dataIndex: 'question', key: 'question' },
            { title: '次数', dataIndex: 'count', key: 'count', width: 80 },
          ]}
          locale={{ emptyText: '暂无数据' }}
        />
      </Card>
    </div>
  );
}
