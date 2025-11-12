import {defineConfig} from 'vite';
import preact from '@preact/preset-vite';

// https://vite.dev/config/
export default defineConfig({
	plugins: [preact()],
	server: {
		proxy: {
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: true,
				rewrite: path => path.replace(/^\/api/, ''),
			},
		},
	},
});
