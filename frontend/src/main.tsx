import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider } from 'next-themes'
import { Toaster } from 'sonner'

import App from './App.tsx'
import { AuthProvider } from '@/hooks/use-auth'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* `attribute="class"` puts `dark` on <html>, which is the signal
        ThinkingOrb's `theme="auto"` watches for. */}
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <BrowserRouter>
        <AuthProvider>
          <App />
          <Toaster position="bottom-right" richColors closeButton />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
)
