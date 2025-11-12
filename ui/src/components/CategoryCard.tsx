import type { Category } from '../types';

type CategoryCardProps = {
  category: Category;
  onClick: () => void;
};

export function CategoryCard({ category, onClick }: CategoryCardProps) {
  return (
    <button
      onClick={onClick}
      class="flex-shrink-0 w-80 group cursor-pointer text-left bg-white border border-gray-200 rounded-lg p-6 hover:border-gray-300 hover:shadow-sm transition-all"
    >
      <div class="flex flex-col h-full">
        <h3 class="text-base font-medium text-gray-900 mb-2">{category.name}</h3>
        <p class="text-sm text-gray-500 leading-relaxed flex-1">{category.description}</p>
        <div class="flex justify-end mt-4">
          <svg
            class="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </button>
  );
}
