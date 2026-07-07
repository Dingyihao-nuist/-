import { useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Dropdown, Avatar } from 'antd';
import {
  MessageOutlined, FolderOutlined, DashboardOutlined,
  UserOutlined, LogoutOutlined, SettingOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../../stores/useAuthStore';

const { Header, Sider, Content } = Layout;

export default function AppLayout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAdmin, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const menuItems = [
    { key: '/chat', icon: <MessageOutlined />, label: '知识库问答' },
    ...(isAdmin
      ? [
          { key: '/admin/kb', icon: <FolderOutlined />, label: '知识库管理' },
          { key: '/admin/dashboard', icon: <DashboardOutlined />, label: '统计仪表盘' },
        ]
      : []),
  ];

  const userMenuItems = [
    { key: 'profile', icon: <SettingOutlined />, label: '个人设置', onClick: () => navigate('/profile') },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
  ];

  return (
    <Layout style={{ height: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#fff',
          borderBottom: '1px solid #f0f0f0',
          padding: '0 24px',
          height: 56,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 18, fontWeight: 600 }}>🤖 电商知识库问答系统</span>
        </div>
        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Avatar size="small" icon={<UserOutlined />} />
            <span>{user?.username || '用户'}</span>
          </div>
        </Dropdown>
      </Header>
      <Layout>
        <Sider
          width={200}
          style={{ background: '#fff', borderRight: '1px solid #f0f0f0' }}
        >
          <Menu
            mode="inline"
            selectedKeys={[location.pathname.startsWith('/admin/kb') ? '/admin/kb' : location.pathname.startsWith('/admin/dashboard') ? '/admin/dashboard' : '/chat']}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ borderRight: 0, marginTop: 8 }}
          />
        </Sider>
        <Content style={{ padding: 0, overflow: 'auto', background: '#f5f5f5' }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
