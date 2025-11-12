import { useState, useEffect } from 'preact/hooks';
import { api } from './api';
import type { Category, Message } from './types';
import { CategoryCard } from './components/CategoryCard';
import { MessageRow } from './components/MessageRow';
import { CategoryModal } from './components/CategoryModal';

export function App() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [categoriesData, messagesData] = await Promise.all([
        api.getCategories(),
        api.getMessages(),
      ]);
      setCategories(categoriesData);
      setMessages(messagesData);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryClick = (category: Category) => {
    setSelectedCategory(category);
  };

  if (loading) {
    return (
      <div class="flex items-center justify-center min-h-screen bg-white">
        <div class="flex flex-col items-center gap-3">
          <div class="w-8 h-8 border-2 border-gray-300 border-t-gray-800 rounded-full animate-spin"></div>
          <p class="text-sm text-gray-500">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div class="min-h-screen bg-white">
      {/* Header */}
      <header class="border-b border-gray-100 py-6 px-8">
        <div class="max-w-[1400px] mx-auto">
          <h1 class="text-2xl font-semibold text-gray-900">Extra Forever</h1>
          <p class="text-sm text-gray-500 mt-1">Gmail Custom Category Builder</p>
        </div>
      </header>

      {/* Main Content */}
      <main class="max-w-[1400px] mx-auto px-8 py-12">
        {/* Categories Section */}
        <section class="mb-16">
          <h2 class="text-lg font-semibold text-gray-900 mb-6">Categories</h2>

          {categories.length === 0 ? (
            <div class="text-center py-12 text-gray-500 text-sm">No categories found.</div>
          ) : (
            <div class="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
              {categories.map((category) => (
                <CategoryCard
                  key={category.id}
                  category={category}
                  onClick={() => handleCategoryClick(category)}
                />
              ))}
            </div>
          )}
        </section>

        {/* Messages Section */}
        <section>
          <h2 class="text-lg font-semibold text-gray-900 mb-6">Messages</h2>

          {messages.length === 0 ? (
            <div class="text-center py-12 text-gray-500 text-sm">
              No messages found. Import some messages to get started.
            </div>
          ) : (
            <div class="space-y-px border border-gray-100 rounded-lg overflow-hidden">
              {messages.map((message, index) => (
                <MessageRow
                  key={message.id}
                  message={message}
                  isLast={index === messages.length - 1}
                />
              ))}
            </div>
          )}
        </section>
      </main>

      {/* Modals */}
      {selectedCategory && (
        <CategoryModal
          category={selectedCategory}
          messages={messages.filter((msg) =>
            msg.categories.some((cat) => cat.id === selectedCategory.id),
          )}
          onClose={() => setSelectedCategory(null)}
        />
      )}

      {/* Custom styles for hiding scrollbar */}
      <style>{`
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
    </div>
  );
}
