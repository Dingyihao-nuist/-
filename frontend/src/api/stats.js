import client from './client';

export const statsAPI = {
  getOverview: () => client.get('/stats/overview'),
  getTrends: (days = 7) => client.get('/stats/trends', { params: { days } }),
  getPopular: (limit = 10) => client.get('/stats/popular', { params: { limit } }),
};
