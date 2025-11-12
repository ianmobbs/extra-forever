import type { Category, Message } from '../types';
import { MessageRow } from './MessageRow';

type CategoryModalProps = {
  category: Category;
  messages: Message[];
  onClose: () => void;
  onMessageUpdate: (messageId: string) => void;
};

export function CategoryModal({
  category,
  messages,
  onClose,
  onMessageUpdate,
}: CategoryModalProps) {
  return (
    <div
      class="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50 p-8"
      onClick={onClose}
    >
      <div
        class="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div class="px-8 py-6 border-b border-gray-100">
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <h2 class="text-xl font-semibold text-gray-900 mb-2">{category.name}</h2>
              <p class="text-sm text-gray-500 leading-relaxed">{category.description}</p>
            </div>
            <button
              onClick={onClose}
              class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors ml-4"
            >
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Messages List */}
        <div class="flex-1 overflow-y-auto px-8 py-6">
          <h3 class="text-sm font-medium text-gray-900 mb-4">
            Messages in this category ({messages.length})
          </h3>

          {messages.length === 0 ? (
            <div class="text-center py-12 text-gray-500 text-sm">
              No messages in this category yet.
            </div>
          ) : (
            <div class="space-y-px border border-gray-100 rounded-lg overflow-hidden">
              {messages.map((message, index) => (
                <MessageRow
                  key={message.id}
                  message={message}
                  isLast={index === messages.length - 1}
                  onUpdate={onMessageUpdate}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
