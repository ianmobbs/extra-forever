import { useState, useEffect } from 'preact/hooks';
import type { Category } from '../types';
import { api } from '../api';
import { CategoryCard } from './CategoryCard';
import { CreateCategoryModal } from './CreateCategoryModal';

export function CategoryList() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();
  const [showModal, setShowModal] = useState(false);

  const loadCategories = async () => {
    setLoading(true);
    setError(undefined);
    try {
      const data = await api.getCategories();
      setCategories(data);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to load categories');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCategories();
  }, []);

  const handleDeleted = (categoryId: number) => {
    setCategories((previous) => previous.filter((category) => category.id !== categoryId));
  };

  const handleCreated = (newCategory: Category) => {
    setCategories((previous) => [...previous, newCategory]);
    setShowModal(false);
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

  return (
    <div>
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-2xl font-bold">Categories</h2>
        <button
          class="btn btn-primary"
          onClick={() => {
            setShowModal(true);
          }}
        >
          + New Category
        </button>
      </div>

      {categories.length === 0 ? (
        <div class="alert alert-info">
          <span>No categories found. Create a category to classify messages!</span>
        </div>
      ) : (
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {categories.map((category) => (
            <CategoryCard key={category.id} category={category} onDeleted={handleDeleted} />
          ))}
        </div>
      )}

      {showModal && (
        <CreateCategoryModal
          onClose={() => {
            setShowModal(false);
          }}
          onCreated={handleCreated}
        />
      )}
    </div>
  );
}
