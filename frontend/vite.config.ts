import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiBase = env.OHM_API_BASE_URL || "http://localhost:8001";

  return {
    plugins: [react(), tailwindcss()],
    server: {
      proxy: {
        "/v1": {
          target: apiBase,
          changeOrigin: true,
        },
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            "vendor-react": ["react", "react-dom", "react-router-dom"],
            "vendor-query": ["@tanstack/react-query"],
            "vendor-cytoscape": ["cytoscape"],
            "vendor-echarts": ["echarts", "echarts-for-react"],
          },
        },
      },
    },
  };
});
