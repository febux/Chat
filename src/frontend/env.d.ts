/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CENT_WS_URL: string;
  readonly VITE_CENT_TOKEN_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
