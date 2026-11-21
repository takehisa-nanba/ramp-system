import { mergeConfig } from 'vite';
import config from './vite.config';

export default mergeConfig(config, {
  server: {
    host: 'localhost',
    port: 5178,
    strictPort: true,
    proxy: { '/api': { target: 'http://127.0.0.1:5001' } },
  },
});
