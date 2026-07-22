import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  root: "web",
  build: {
    outDir: resolve(import.meta.dirname, "dist"),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        explorer: resolve(import.meta.dirname, "web/index.html"),
        methodology: resolve(import.meta.dirname, "web/methodology/index.html"),
      },
    },
  },
  server: { port: 5173 },
  preview: { port: 4173 },
});
