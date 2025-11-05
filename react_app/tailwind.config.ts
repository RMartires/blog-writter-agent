import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#1A202C',
        accent: '#10B981',
        'text-primary': '#FFFFFF',
        'text-secondary': '#A0AEC0',
        'input-bg': '#2D3748',
      },
    },
  },
  plugins: [],
}
export default config

