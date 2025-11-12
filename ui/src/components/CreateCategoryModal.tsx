import { useState } from 'preact/hooks';
import type { Category } from '../types';
import { api } from '../api';

type CreateCategoryModalProps = {
  onClose: () => void;
  onCreated: (category: Category) => void;
};

export function CreateCategoryModal({ onClose, onCreated }: CreateCategoryModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | undefined>();

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    setError(undefined);

    if (!name.trim()) {
      setError('Name is required');
      return;
    }

    if (!description.trim()) {
      setError('Description is required');
      return;
    }

    setCreating(true);
    try {
      const category = await api.createCategory(name.trim(), description.trim());
      onCreated(category);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to create category');
      setCreating(false);
    }
  };

  return (
    <div
      class="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50 p-8"
      onClick={onClose}
    >
      <div
        class="bg-white rounded-xl shadow-2xl max-w-lg w-full"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div class="px-8 py-6 border-b border-gray-100">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-semibold text-gray-900">New Category</h2>
            <button
              onClick={onClose}
              class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
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

        {/* Form */}
        <form onSubmit={handleSubmit} class="px-8 py-6">
          <div class="space-y-5">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Name</label>
              <input
                type="text"
                value={name}
                onInput={(e) => setName((e.target as HTMLInputElement).value)}
                placeholder="e.g., Work, Personal, Newsletters"
                class="w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
                disabled={creating}
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Description</label>
              <textarea
                value={description}
                onInput={(e) => setDescription((e.target as HTMLTextAreaElement).value)}
                placeholder="Describe what types of messages belong in this category..."
                rows={4}
                class="w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent resize-none"
                disabled={creating}
              />
            </div>
          </div>

          {error && (
            <div class="mt-4 px-4 py-3 bg-red-50 border border-red-100 rounded-lg">
              <p class="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div class="mt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={creating}
              class="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={creating}
              class="px-4 py-2 text-sm font-medium text-white bg-gray-900 hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50"
            >
              {creating ? (
                <>
                  <span class="inline-block w-3 h-3 border-2 border-gray-300 border-t-white rounded-full animate-spin mr-2"></span>
                  Creating...
                </>
              ) : (
                'Create Category'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
