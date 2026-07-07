import client from './client';

export const kbAPI = {
  upload: (formData) =>
    client.post('/kb/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getDocuments: (params) => client.get('/kb/documents', { params }),
  deleteDocument: (id) => client.delete(`/kb/documents/${id}`),
  getChunks: (id) => client.get(`/kb/documents/${id}/chunks`),
  reindex: (id) => client.post(`/kb/documents/${id}/reindex`),
  getStats: () => client.get('/kb/stats'),
};
