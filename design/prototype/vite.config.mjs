import vue from '../../frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs'
import { fileURLToPath } from 'node:url'
export default {
  base: './',
  plugins: [vue()],
  resolve: { alias: {
    vue: fileURLToPath(new URL('../../frontend/node_modules/vue/dist/vue.runtime.esm-bundler.js',import.meta.url)),
    three: fileURLToPath(new URL('../../frontend/node_modules/three/build/three.module.js',import.meta.url)),
  } },
  server: { fs: { allow: [fileURLToPath(new URL('../..',import.meta.url))] } },
  build: { outDir:'dist',emptyOutDir:true },
}
