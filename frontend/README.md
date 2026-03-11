# NotebookLLM Frontend

Vue 3 + TypeScript + Vite frontend application for NotebookLLM.

## Tech Stack

- **Vue 3** - Progressive JavaScript framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Next generation frontend tooling
- **Vue Router** - Official router for Vue.js
- **Pinia** - State management for Vue
- **Ant Design Vue** - UI component library
- **Axios** - HTTP client

## Project Structure

```
frontend/
├── src/
│   ├── api/           # API modules
│   ├── assets/        # Static assets
│   ├── layouts/       # Layout components
│   ├── router/        # Vue Router configuration
│   ├── stores/        # Pinia stores
│   ├── types/         # TypeScript type definitions
│   ├── views/         # Page components
│   ├── App.vue        # Root component
│   └── main.ts        # Application entry point
├── .env.development   # Development environment variables
├── .env.production    # Production environment variables
├── index.html         # HTML entry point
├── package.json       # Dependencies and scripts
├── tsconfig.json      # TypeScript configuration
└── vite.config.ts     # Vite configuration
```

## Getting Started

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Build

```bash
npm run build
```

### Preview

```bash
npm run preview
```

## Features

- User authentication (Login/Register)
- Note CRUD operations
- AI-powered note search (RAG)
- Secure note sharing with optional passwords
- Responsive design with Ant Design Vue

## API Configuration

API base URL is configured via `VITE_API_BASE_URL` environment variable.

Development: `/api` (proxied to backend)
Production: `/api` (served from same origin)

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
