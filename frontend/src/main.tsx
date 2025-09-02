import React from 'react'
import { createRoot } from 'react-dom/client'
import ChatApp from './App'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ChatApp />
  </React.StrictMode>
)

