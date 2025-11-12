# Extra Forever UI

A modern, beautiful UI for the Gmail Custom Category Builder built with Preact, Vite, and DaisyUI.

## Features

- 📧 **Message Management**: View all imported messages with their details
- 🏷️ **Category Management**: Create, view, and delete custom categories
- 🤖 **AI Classification**: Classify messages into categories with a single click
- 🎨 **Modern UI**: Built with DaisyUI components for a beautiful, responsive design
- ⚡ **Fast**: Powered by Vite and Preact for blazing-fast performance

## Prerequisites

- Node.js 18+
- pnpm (install with `npm install -g pnpm`)
- Backend API running on `http://localhost:8000`

## Getting Started

### Installation

```bash
cd ui
pnpm install
```

### Development

Start the development server:

```bash
pnpm dev
```

The UI will be available at `http://localhost:5173` (or the next available port).

The dev server includes a proxy to forward `/api/*` requests to `http://localhost:8000`.

### Build for Production

```bash
pnpm build
```

The built files will be in the `dist/` directory.

### Preview Production Build

```bash
pnpm preview
```

## Project Structure

```
ui/
├── src/
│   ├── components/          # Preact components
│   │   ├── MessageCard.tsx       # Individual message card
│   │   ├── MessageList.tsx       # List of messages
│   │   ├── CategoryCard.tsx      # Individual category card
│   │   ├── CategoryList.tsx      # List of categories
│   │   └── CreateCategoryModal.tsx # Modal for creating categories
│   ├── api.ts              # API client functions
│   ├── types.ts            # TypeScript type definitions
│   ├── app.tsx             # Main App component
│   ├── main.tsx            # App entry point
│   └── style.css           # Global styles + Tailwind
├── index.html              # HTML template
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # Tailwind CSS configuration
└── package.json            # Dependencies
```

## Tech Stack

- **Preact**: Fast 3kb alternative to React
- **Vite**: Next-generation frontend tooling
- **TypeScript**: Type safety and better DX
- **DaisyUI**: Beautiful Tailwind CSS components
- **Tailwind CSS**: Utility-first CSS framework

## Usage

### Viewing Messages

1. Navigate to the **Messages** tab
2. See all imported messages with their subjects, senders, and snippets
3. Messages already classified show category badges

### Classifying Messages

1. Click the **Classify** button on any message card
2. The system will automatically match the message to relevant categories
3. Category badges will appear on the message once classified

### Managing Categories

1. Navigate to the **Categories** tab
2. Click **+ New Category** to create a category
3. Enter a name and natural language description
4. Click **Create** to save
5. Delete categories by clicking the **Delete** button on any card

## API Integration

The UI communicates with the FastAPI backend through these endpoints:

- `GET /api/messages` - List all messages
- `GET /api/messages/{id}` - Get a specific message
- `POST /api/messages/{id}/classify` - Classify a message
- `GET /api/categories` - List all categories
- `POST /api/categories` - Create a new category
- `DELETE /api/categories/{id}` - Delete a category

## Theming

DaisyUI themes can be changed in `tailwind.config.js`. Available themes include:
- light (default)
- dark
- cupcake
- And many more!

## Contributing

When adding new features:

1. Create components in `src/components/`
2. Add types to `src/types.ts`
3. Add API functions to `src/api.ts`
4. Follow the existing component patterns

## License

MIT
