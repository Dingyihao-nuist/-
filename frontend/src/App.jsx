import { Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Spin } from 'antd';
import { routes } from './routes';
import { useAuthStore } from './stores/useAuthStore';
import AppLayout from './components/layout/AppLayout';

function ProtectedRoute({ children, adminOnly = false }) {
  const { isAuthenticated, isAdmin } = useAuthStore();

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (adminOnly && !isAdmin) return <Navigate to="/chat" replace />;
  return children;
}

export default function App() {
  const { isAuthenticated } = useAuthStore();

  return (
    <Suspense
      fallback={
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
          <Spin size="large" />
        </div>
      }
    >
      <Routes>
        {routes.map((route) => (
          <Route
            key={route.path}
            path={route.path}
            element={
              route.public ? (
                isAuthenticated ? <Navigate to="/chat" replace /> : route.element
              ) : (
                <ProtectedRoute adminOnly={route.adminOnly}>
                  <AppLayout>{route.element}</AppLayout>
                </ProtectedRoute>
              )
            }
          />
        ))}
        <Route path="*" element={<Navigate to={isAuthenticated ? '/chat' : '/login'} replace />} />
      </Routes>
    </Suspense>
  );
}
