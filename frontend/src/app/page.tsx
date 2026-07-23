"use client";

import React, { useState, useEffect, useRef } from "react";

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [ws, setWs] = useState<WebSocket | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom whenever messages update
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    // Initialize WebSocket connection
    const websocket = new WebSocket("ws://localhost:8000/ws/audio");

    websocket.onopen = () => {
      console.log("Connected to E.R.A.");
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "message" && data.text) {
          // Append assistant message to UI
          setMessages((prev) => [
            ...prev,
            { id: Date.now().toString(), role: "assistant", text: data.text },
          ]);

          // Play Audio if provided
          if (data.audio) {
            const audioSrc = `data:audio/mp3;base64,${data.audio}`;
            const audio = new Audio(audioSrc);
            audio.play().catch(e => console.error("Audio play failed:", e));
          }
        } else if (data.error) {
           console.error("E.R.A Error:", data.error);
           setMessages((prev) => [
            ...prev,
            { id: Date.now().toString(), role: "assistant", text: `[Error: ${data.error}]` },
          ]);
        }
      } catch (err) {
        console.error("Failed to parse websocket message:", err);
      }
    };

    websocket.onclose = () => {
      console.log("Disconnected from E.R.A.");
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, []);

  const handleSend = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputValue.trim() || !ws || ws.readyState !== WebSocket.OPEN) return;

    // Optimistically add user message
    const newMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      text: inputValue.trim(),
    };
    setMessages((prev) => [...prev, newMessage]);

    // Send string payload over WS
    ws.send(JSON.stringify({ text: newMessage.text }));
    setInputValue("");
  };

  const handleClear = () => {
    setMessages([]);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100 font-sans">
      {/* Header */}
      <header className="flex justify-between items-center p-4 bg-gray-900 shadow-md">
        <h1 className="text-xl font-bold text-red-500 tracking-wider">
          E.R.A. <span className="text-sm font-light text-gray-400">Jeevan Route</span>
        </h1>
        <button
          onClick={handleClear}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md font-semibold transition-colors shadow-sm"
        >
          Clear / Reset Case
        </button>
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-gray-500">
            No active case. Send a message to begin.
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-lg p-3 rounded-lg shadow-md ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-br-none"
                    : "bg-gray-800 text-gray-100 rounded-bl-none border border-gray-700"
                }`}
              >
                <div className="text-xs font-semibold mb-1 opacity-70">
                  {msg.role === "user" ? "Paramedic" : "E.R.A."}
                </div>
                <div>{msg.text}</div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Input Area */}
      <footer className="p-4 bg-gray-900 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]">
        <form onSubmit={handleSend} className="flex gap-2 max-w-4xl mx-auto">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type patient symptoms or requirements..."
            className="flex-1 bg-gray-800 border border-gray-700 rounded-md px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-100"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || !ws || ws.readyState !== WebSocket.OPEN}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-md font-semibold transition-colors shadow-sm"
          >
            Send
          </button>
        </form>
      </footer>
    </div>
  );
}
