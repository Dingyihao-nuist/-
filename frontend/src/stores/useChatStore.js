import { create } from 'zustand';

export const useChatStore = create((set) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',
  streamingSources: null,

  setSessions: (sessions) => set({ sessions }),
  addSession: (session) =>
    set((state) => ({ sessions: [session, ...state.sessions] })),
  removeSession: (id) =>
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== id),
      currentSessionId: state.currentSessionId === id ? null : state.currentSessionId,
      messages: state.currentSessionId === id ? [] : state.messages,
    })),
  updateSession: (id, updates) =>
    set((state) => ({
      sessions: state.sessions.map((s) => (s.id === id ? { ...s, ...updates } : s)),
    })),

  setCurrentSessionId: (id) => set({ currentSessionId: id }),
  setMessages: (messages) => set({ messages }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  setStreaming: (isStreaming) => set({ isStreaming }),
  appendStreamToken: (token) =>
    set((state) => ({ streamingContent: state.streamingContent + token })),
  setStreamingSources: (sources) => set({ streamingSources: sources }),
  resetStreaming: () => set({ isStreaming: false, streamingContent: '', streamingSources: null }),
}));
