import { useState } from 'preact/hooks';
import type { Message } from '../types';

type MessageRowProps = {
  message: Message;
  isLast: boolean;
};

export function MessageRow({ message, isLast }: MessageRowProps) {
  const [expanded, setExpanded] = useState(false);

  const formatDate = (dateString?: string) => {
    if (!dateString) return '';

    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    } else if (diffDays < 7) {
      return date.toLocaleDateString('en-US', { weekday: 'short' });
    } else if (date.getFullYear() === now.getFullYear()) {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
  };

  const truncateText = (text: string | undefined, maxLength: number) => {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div
      class={`bg-white hover:bg-gray-50 transition-colors ${!isLast ? 'border-b border-gray-100' : ''}`}
    >
      {/* Collapsed Row */}
      <button
        onClick={() => setExpanded(!expanded)}
        class="w-full px-6 py-4 flex items-center gap-4 text-left cursor-pointer"
      >
        {/* Date */}
        <div class="w-20 flex-shrink-0 text-xs text-gray-500">{formatDate(message.date)}</div>

        {/* Sender */}
        <div class="w-48 flex-shrink-0">
          <div class="text-sm font-medium text-gray-900 truncate">
            {message.sender.split('<')[0].trim() || message.sender}
          </div>
        </div>

        {/* Preview */}
        <div class="flex-1 min-w-0">
          <div class="text-sm text-gray-900">
            <span class="font-medium">{message.subject}</span>
            {message.snippet && (
              <span class="text-gray-500 ml-2">— {truncateText(message.snippet, 100)}</span>
            )}
          </div>
        </div>

        {/* Categories */}
        <div class="flex items-center gap-2 flex-shrink-0">
          {message.categories.length > 0 ? (
            message.categories.map((category) => (
              <span
                key={category.id}
                class="px-2 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded"
              >
                {category.name}
              </span>
            ))
          ) : (
            <span class="text-xs text-gray-400">No categories</span>
          )}
        </div>

        {/* Expand Arrow */}
        <div class="flex-shrink-0">
          <svg
            class={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-90' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </button>

      {/* Expanded Details */}
      {expanded && (
        <div class="px-6 pb-6 border-t border-gray-100">
          <div class="pt-4 space-y-4">
            {/* Message Details */}
            <div class="space-y-2">
              <div class="flex items-start gap-2">
                <span class="text-xs font-medium text-gray-500 w-16">From:</span>
                <span class="text-sm text-gray-900">{message.sender}</span>
              </div>
              <div class="flex items-start gap-2">
                <span class="text-xs font-medium text-gray-500 w-16">To:</span>
                <span class="text-sm text-gray-900">{message.to.join(', ')}</span>
              </div>
              <div class="flex items-start gap-2">
                <span class="text-xs font-medium text-gray-500 w-16">Date:</span>
                <span class="text-sm text-gray-900">
                  {message.date
                    ? new Date(message.date).toLocaleString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })
                    : 'No date'}
                </span>
              </div>
            </div>

            {/* Body/Snippet */}
            {(message.body || message.snippet) && (
              <div class="pt-4 border-t border-gray-100">
                <p class="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {message.body || message.snippet}
                </p>
              </div>
            )}

            {/* Categories with Explanations */}
            {message.categories.length > 0 && (
              <div class="pt-4 border-t border-gray-100">
                <h4 class="text-xs font-medium text-gray-500 mb-3">Categories</h4>
                <div class="space-y-3">
                  {message.categories.map((category) => (
                    <div key={category.id} class="flex items-start gap-3">
                      <span class="px-2 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded">
                        {category.name}
                      </span>
                      {category.explanation && (
                        <p class="flex-1 text-xs text-gray-500 leading-relaxed">
                          {category.explanation}
                        </p>
                      )}
                      {category.score != null && (
                        <span class="text-xs text-gray-400">
                          {Math.round(category.score * 100)}%
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
