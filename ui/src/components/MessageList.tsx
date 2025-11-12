import { useState, useEffect } from 'preact/hooks';
import type { Message } from '../types';
import { api } from '../api';
import { MessageCard } from './MessageCard';

export function MessageList() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();

  const loadMessages = async () => {
    setLoading(true);
    setError(undefined);
    try {
      const data = await api.getMessages();
      setMessages(data);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to load messages');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMessages();
  }, []);

  const handleClassified = async (messageId: string) => {
    // Reload the specific message to get updated categories
    try {
      const updatedMessage = await api.getMessage(messageId);
      setMessages((previous) =>
        previous.map((message) => (message.id === messageId ? updatedMessage : message)),
      );
    } catch (error) {
      console.error('Failed to reload message:', error);
    }
  };

  if (loading) {
    return (
      <div class="flex justify-center items-center min-h-64">
        <span class="loading loading-spinner loading-lg"></span>
      </div>
    );
  }

  if (error) {
    return (
      <div class="alert alert-error">
        <span>{error}</span>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div class="alert alert-info">
        <span>No messages found. Import some messages to get started!</span>
      </div>
    );
  }

  return (
    <div class="space-y-4">
      {messages.map((message) => (
        <MessageCard key={message.id} message={message} onClassified={handleClassified} />
      ))}
    </div>
  );
}
