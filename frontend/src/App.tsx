import React, { useCallback, useEffect, useRef, useState } from 'react'
import avatarSvg from './assets/avatar.svg'

type Message = { id: string, role: 'user'|'assistant', text: string, at: string }

const API_BASE = ''

function MessageList({ messages }: { messages: Message[] }) {
  return (
    <div className="messages">
      {messages.map((m) => (
        <div key={m.id} className={`msg ${m.role}`}>
          <div className="bubble">
            <div className="meta">{m.role} • {new Date(m.at).toLocaleTimeString()}</div>
            <div className="text">{m.text}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

function Composer({ onSend }: { onSend: (t: string) => void }) {
  const [text, setText] = useState('')
  const submit = useCallback(() => {
    if (!text.trim()) return
    onSend(text)
    setText('')
  }, [text, onSend])
  return (
    <div className="composer">
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
        placeholder="メッセージを入力..."
      />
      <button onClick={submit}>送信</button>
    </div>
  )
}

function SidePanel() {
  const url = (import.meta as any).env?.VITE_CHARACTER_IMAGE_URL as string | undefined
  const src = url || avatarSvg
  return (
    <div className="side">
      <div className="avatar">
        <img className="avatar-img" src={src} alt="character" />
        <div className="avatar-caption">Assistant</div>
      </div>
    </div>
  )
}

export default function ChatApp() {
  const [messages, setMessages] = useState<Message[]>([])
  const evtRef = useRef<EventSource | null>(null)

  useEffect(() => () => { evtRef.current?.close() }, [])

  const send = useCallback((text: string) => {
    const now = new Date().toISOString()
    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', text, at: now }
    setMessages((prev) => [...prev, userMsg])

    // SSE stream
    evtRef.current?.close()
    const es = new EventSource(`${API_BASE}/api/chat/stream?message=${encodeURIComponent(text)}`)
    evtRef.current = es

    let acc = ''
    es.onmessage = (ev) => {
      acc += ev.data
      const aiMsg: Message = { id: 'ai-current', role: 'assistant', text: acc, at: new Date().toISOString() }
      setMessages((prev) => [...prev.filter(m => m.id !== 'ai-current'), aiMsg])
    }
    es.addEventListener('done', () => {
      // finalize id
      setMessages((prev) => prev.map(m => m.id === 'ai-current' ? { ...m, id: crypto.randomUUID() } : m))
      es.close()
    })
    es.onerror = () => {
      es.close()
    }
  }, [])

  return (
    <div className="app">
      <div className="chat">
        <MessageList messages={messages} />
        <Composer onSend={send} />
      </div>
      <SidePanel />
    </div>
  )
}
