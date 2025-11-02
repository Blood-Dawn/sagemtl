# SageMTL UI (React + Vite)

This directory contains the mock SageMTL dashboard built with React, TypeScript, Tailwind CSS, Radix UI primitives, and shadcn-inspired components. All API calls are stubbed so the UI can be iterated on without the backend.

## HOW TO RUN UI

```bash
# install dependencies
npm install

# start development server
npm run dev

# build for production
npm run build

# preview the production build
npm run preview
```

The UI reads mock data from `src/mocks` and simulates latency via the stub API layer in `src/api`. Theme preference is stored in `localStorage` and survives reloads.
