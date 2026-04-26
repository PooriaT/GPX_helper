# GPX Helper Frontend

Svelte-based landing page for the GPX Helper tools.

## Prerequisites
- Python 3.13+
- Poetry
- Node.js 18+
- npm

## Install dependencies
```sh
cd ../backend
poetry install
cd ../frontend
npm install
```

## Run the dev server
```sh
npm run dev
```

This starts the FastAPI backend at <http://localhost:8000> and the frontend at <http://localhost:4173>.

To run only one side:
```sh
npm run dev:frontend
npm run dev:backend
```

## Build for production
```sh
npm run build
```

## Run tests
```sh
npm run test
```

## Run tests in watch mode
```sh
npm run test:watch
```
