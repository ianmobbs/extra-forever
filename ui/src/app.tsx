import { useState } from 'preact/hooks';
import { MessageList } from './components/MessageList';
import { CategoryList } from './components/CategoryList';

type Tab = 'messages' | 'categories';

export function App() {
  const [activeTab, setActiveTab] = useState<Tab>('messages');

  return (
    <div class="min-h-screen bg-base-200">
      {/* Header */}
      <div class="navbar bg-base-100 shadow-lg">
        <div class="flex-1">
          <a class="btn btn-ghost text-xl">📧 Extra Forever</a>
        </div>
        <div class="flex-none">
          <span class="text-sm opacity-70">Gmail Custom Category Builder</span>
        </div>
      </div>

      {/* Tabs */}
      <div class="tabs tabs-boxed w-fit mx-auto mt-6">
        <a
          class={`tab ${activeTab === 'messages' ? 'tab-active' : ''}`}
          onClick={() => {
            setActiveTab('messages');
          }}
        >
          Messages
        </a>
        <a
          class={`tab ${activeTab === 'categories' ? 'tab-active' : ''}`}
          onClick={() => {
            setActiveTab('categories');
          }}
        >
          Categories
        </a>
      </div>

      {/* Content */}
      <div class="container mx-auto px-4 py-8 max-w-7xl">
        {activeTab === 'messages' && (
          <div>
            <h1 class="text-3xl font-bold mb-6">Messages</h1>
            <MessageList />
          </div>
        )}
        {activeTab === 'categories' && <CategoryList />}
      </div>

      {/* Footer */}
      <footer class="footer footer-center p-4 bg-base-300 text-base-content mt-12">
        <div>
          <p>Built with Preact + Vite + DaisyUI</p>
        </div>
      </footer>
    </div>
  );
}
