/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Base URL of the backend (no trailing slash, no /api suffix). Leave
  // unset in production so requests are same-origin under /api.
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
