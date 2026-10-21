/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Optional override for the backend base URL (no trailing slash, no
  // /api suffix). Leave UNSET in production and development: requests are
  // same-origin under /api (the Vite dev server proxies /api to the local
  // backend). Set this only to target a backend on a different origin.
  readonly VITE_API_BASE_URL?: string;
  // Build-time development/production flag provided by Vite.
  readonly DEV: boolean;
  readonly PROD: boolean;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
