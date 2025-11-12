import { useState } from 'preact/hooks';
import type { Message } from '../types';
import { api } from '../api';

type MessageCardProps = {
  message: Message;
  onClassified: (messageId: string) => void;
};

export function MessageCard({ message, onClassified }: MessageCardProps) {
  const [classifying, setClassifying] = useState(false);
  const [error, setError] = useState<string | undefined>();

  const handleClassify = async () => {
    setClassifying(true);
    setError(undefined);
    try {
      await api.classifyMessage(message.id);
      onClassified(message.id);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Classification failed');
    } finally {
      setClassifying(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) {
      return 'No date';
    }

    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title">
          {message.subject}
          {message.categories.length > 0 && (
            <div class="badge badge-secondary">{message.categories.length}</div>
          )}
        </h2>
        <div class="text-sm opacity-70">
          <p>
            <strong>From:</strong> {message.sender}
          </p>
          <p>
            <strong>To:</strong> {message.to.join(', ')}
          </p>
          <p>
            <strong>Date:</strong> {formatDate(message.date)}
          </p>
        </div>
        {message.snippet && <p class="text-sm mt-2">{message.snippet}</p>}
        {message.categories.length > 0 && (
          <div class="flex flex-wrap gap-2 mt-3">
            {message.categories.map((cat) => (
              <div key={cat.id} class="badge badge-primary badge-outline">
                {cat.name}
              </div>
            ))}
          </div>
        )}
        <div class="card-actions justify-end mt-4">
          <button
            class={`btn btn-sm ${classifying ? 'btn-disabled' : 'btn-primary'}`}
            onClick={handleClassify}
            disabled={classifying}
          >
            {classifying ? (
              <>
                <span class="loading loading-spinner loading-xs"></span>
                Classifying...
              </>
            ) : (
              'Classify'
            )}
          </button>
        </div>
        {error && (
          <div class="alert alert-error mt-2">
            <span class="text-xs">{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}
