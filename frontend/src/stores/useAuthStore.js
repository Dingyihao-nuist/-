import { create } from 'zustand';

export const useAuthStore = create((set) => ({
  user: null,
  isAuthenticated: false,
  isAdmin: false,

  setUser: (user) =>
    set({
      user,
      isAuthenticated: !!user,
      isAdmin: user?.role === 'admin',
    }),

  login: (accessToken, refreshToken, user) => {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    set({ user, isAuthenticated: true, isAdmin: user?.role === 'admin' });
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null, isAuthenticated: false, isAdmin: false });
  },
}));
