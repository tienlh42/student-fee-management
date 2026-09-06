import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";

// Django serve build output qua django-vite: manifest BẮT BUỘC bật.
export default defineConfig({
  // django-vite ghép STATIC_URL vào trước đường dẫn asset ở cả dev lẫn prod,
  // nên Vite dev server cũng phải phục vụ dưới /static/ thì URL mới khớp.
  base: "/static/",
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  build: {
    manifest: true,
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: "src/main.js",
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    // django-vite trỏ thẻ <script> về đây khi DJANGO_DEBUG=True.
    origin: "http://localhost:5173",
    host: "0.0.0.0",
  },
});
