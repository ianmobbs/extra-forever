import type { Message, Category } from './types';

const API_BASE = '/api';

export const api = {
  // Messages endpoints
  async getMessages(): Promise<Message[]> {
    const response = await fetch(`${API_BASE}/messages`);
    if (!response.ok) {
      throw new Error('Failed to fetch messages');
    }

    return response.json();
  },

  async getMessage(id: string): Promise<Message> {
    const response = await fetch(`${API_BASE}/messages/${id}`);
    if (!response.ok) {
      throw new Error('Failed to fetch message');
    }

    return response.json();
  },

  // Categories endpoints
  async getCategories(): Promise<Category[]> {
    const response = await fetch(`${API_BASE}/categories`);
    if (!response.ok) {
      throw new Error('Failed to fetch categories');
    }

    return response.json();
  },

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await fetch(`${API_BASE}/health`);
    if (!response.ok) {
      throw new Error('Health check failed');
    }

    return response.json();
  },
};
