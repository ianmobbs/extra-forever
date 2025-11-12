import type { Message, Category, ClassifyResponse } from './types';

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

  async classifyMessage(messageId: string, topN = 3, threshold = 0.5): Promise<ClassifyResponse> {
    const response = await fetch(
      `${API_BASE}/messages/${messageId}/classify?top_n=${topN}&threshold=${threshold}`,
      { method: 'POST' },
    );
    if (!response.ok) {
      throw new Error('Failed to classify message');
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

  async createCategory(name: string, description: string): Promise<Category> {
    const response = await fetch(`${API_BASE}/categories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description }),
    });
    if (!response.ok) {
      throw new Error('Failed to create category');
    }

    return response.json();
  },

  async deleteCategory(id: number): Promise<void> {
    const response = await fetch(`${API_BASE}/categories/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete category');
    }
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
