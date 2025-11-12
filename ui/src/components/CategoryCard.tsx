import { useState } from 'preact/hooks';
import type { Category } from '../types';
import { api } from '../api';

type CategoryCardProps = {
  category: Category;
  onDeleted: (categoryId: number) => void;
};

export function CategoryCard({ category, onDeleted }: CategoryCardProps) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete "${category.name}"?`)) {
      return;
    }

    setDeleting(true);
    try {
      await api.deleteCategory(category.id);
      onDeleted(category.id);
    } catch (error) {
      alert(
        `Failed to delete category: ${error instanceof Error ? error.message : 'Unknown error'}`,
      );
      setDeleting(false);
    }
  };

  return (
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title">{category.name}</h2>
        <p class="text-sm opacity-70">{category.description}</p>
        <div class="card-actions justify-end mt-2">
          <button
            class={`btn btn-sm btn-error ${deleting ? 'btn-disabled' : ''}`}
            onClick={handleDelete}
            disabled={deleting}
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}
