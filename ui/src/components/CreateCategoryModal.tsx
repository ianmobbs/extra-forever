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

  const handleSubmit = async (event: Event) => {
    event.preventDefault();
    setCreating(true);
    setError(undefined);

    try {
      const newCategory = await api.createCategory(name, description);
      onCreated(newCategory);
    } catch (error_) {
      setError(error_ instanceof Error ? error_.message : 'Failed to create category');
      setCreating(false);
    }
  };

  return (
    <div class="modal modal-open">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Create New Category</h3>
        <form onSubmit={handleSubmit}>
          <div class="form-control mb-4">
            <label class="label">
              <span class="label-text">Category Name</span>
            </label>
            <input
              type="text"
              placeholder="e.g., Work Travel Receipts"
              class="input input-bordered"
              value={name}
              onInput={(event) => {
                setName((event.target as HTMLInputElement).value);
              }}
              required
            />
          </div>

          <div class="form-control mb-4">
            <label class="label">
              <span class="label-text">Description</span>
            </label>
            <textarea
              class="textarea textarea-bordered"
              placeholder="Describe what messages should be in this category..."
              rows={4}
              value={description}
              onInput={(event) => {
                setDescription((event.target as HTMLTextAreaElement).value);
              }}
              required
            />
          </div>

          {error && (
            <div class="alert alert-error mb-4">
              <span class="text-sm">{error}</span>
            </div>
          )}

          <div class="modal-action">
            <button type="button" class="btn" onClick={onClose} disabled={creating}>
              Cancel
            </button>
            <button
              type="submit"
              class={`btn btn-primary ${creating ? 'btn-disabled' : ''}`}
              disabled={creating}
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
