import { lazy } from 'react';

const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const ChatPage = lazy(() => import('./pages/ChatPage'));
const AdminKBPage = lazy(() => import('./pages/AdminKBPage'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));

export const routes = [
  { path: '/login', element: <LoginPage />, public: true },
  { path: '/register', element: <RegisterPage />, public: true },
  { path: '/chat', element: <ChatPage />, public: false },
  { path: '/chat/:sessionId', element: <ChatPage />, public: false },
  { path: '/admin/kb', element: <AdminKBPage />, public: false, adminOnly: true },
  { path: '/admin/dashboard', element: <AdminDashboard />, public: false, adminOnly: true },
  { path: '/profile', element: <ProfilePage />, public: false },
];
