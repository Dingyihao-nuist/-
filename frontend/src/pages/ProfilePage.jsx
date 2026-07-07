import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Card, message, Typography, Divider } from 'antd';
import { authAPI } from '../api/auth';
import { useAuthStore } from '../stores/useAuthStore';

const { Title, Text } = Typography;

export default function ProfilePage() {
  const [loading, setLoading] = useState(false);
  const { user } = useAuthStore();

  const handleChangePassword = async (values) => {
    setLoading(true);
    try {
      await authAPI.changePassword(values);
      message.success('密码修改成功');
    } catch (err) {
      message.error(err.response?.data?.detail || '修改失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      <Title level={4}>个人设置</Title>

      <Card style={{ marginBottom: 24 }}>
        <div style={{ marginBottom: 12 }}>
          <Text strong>用户名：</Text>
          <Text>{user?.username}</Text>
        </div>
        <div style={{ marginBottom: 12 }}>
          <Text strong>邮箱：</Text>
          <Text>{user?.email}</Text>
        </div>
        <div style={{ marginBottom: 12 }}>
          <Text strong>角色：</Text>
          <Text>{user?.role === 'admin' ? '管理员' : '普通用户'}</Text>
        </div>
        <div>
          <Text strong>注册时间：</Text>
          <Text>{user?.created_at ? new Date(user.created_at).toLocaleDateString('zh-CN') : '-'}</Text>
        </div>
      </Card>

      <Card title="修改密码">
        <Form name="changePassword" onFinish={handleChangePassword} layout="vertical">
          <Form.Item name="old_password" label="当前密码" rules={[{ required: true, message: '请输入当前密码' }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, min: 6, message: '密码至少 6 位' }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item
            name="confirm_password"
            label="确认新密码"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) return Promise.resolve();
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>
              修改密码
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
