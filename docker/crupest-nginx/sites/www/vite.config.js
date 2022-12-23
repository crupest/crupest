/** @type {import('vite').UserConfig} */
export default {
  build: {
    sourcemap: true,
  },
  server: {
    port: 6123,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://localhost:5188",
        changeOrigin: true,
      },
    },
  },
};
