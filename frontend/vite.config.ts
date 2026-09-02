import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { NaiveUiResolver } from 'unplugin-vue-components/resolvers'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  plugins: [
    vue(),
    Components({
      resolvers: [NaiveUiResolver()]
    }),
  ],
  server: {
    port: 1420,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    // 构建目标：现代浏览器 (ES2020+，消除 polyfill 开销)
    target: 'es2020',
    // 代码分包: 路由级 lazy loading (() => import(...)) 自动按路由拆分
    // 提取共享 vendor chunk 减少首屏加载体积
    manualChunks: {
      'naive-ui': ['naive-ui'],
      'echarts': ['echarts', 'vue-echarts'],
      'tiptap': ['@tiptap/vue-3', '@tiptap/starter-kit', '@tiptap/extension-placeholder'],
      'vue-vendor': ['vue', 'vue-router', 'pinia'],
    },
    rollupOptions: {
      output: {
        // 资源命名：包含 chunk 哈希，便于长期缓存
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      },
      // Tree shaking: 标记未使用的导出供 Rollup 消除
      treeshake: {
        preset: 'recommended',
      },
    },
    // 提高告警阈值（大 chunk 警告）
    chunkSizeWarningLimit: 600,
    // 启用 CSS 代码分割
    cssCodeSplit: true,
    // 压缩选项: esbuild (快速构建) 或 terser (更高压缩率)
    // 如需更高压缩率可切换为 'terser' 并安装 terser 依赖:
    //   npm i -D terser
    //   minify: 'terser'
    //   terserOptions: { compress: { drop_console: true, drop_debugger: true } }
    minify: 'esbuild',
    // 生成 sourcemap 用于调试（生产可关闭）
    sourcemap: false,
  },
  // 生产环境可选插件 (按需启用):
  // import compression from 'vite-plugin-compression'
  // plugins: [
  //   compression({ algorithm: 'brotli', ext: '.br', threshold: 10240 }),
  //   compression({ algorithm: 'gzip', ext: '.gz', threshold: 10240 }),
  // ],
})
