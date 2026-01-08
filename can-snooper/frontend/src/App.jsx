import { useEffect, useState, useRef } from "react";
import "./App.css";
import MessageList from "./components/MessageList";

const server = 8765;

function App() {
  const [messages, setMessages] = useState([]);
  const connected = useRef(false);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:${server}`);
    if (connected.current) return;
    connected.current = true;

    ws.onopen = () => {
      console.log("Connected to Python WebSocket Server");
    };

    ws.onmessage = (event) => {
      console.log(event);
      try {
        const data = JSON.parse(event.data); // the backend sends JSON
        const displayMsg = `[${data.timestamp}] ID:${data.can_id} Name:${
          data.signal_name
        }: ${
          typeof data.value === "boolean"
            ? data.value.toString()
            : typeof data.value === "number"
            ? data.value.toFixed(2)
            : "N/A"
        }`;
        setMessages((prev) => [...prev, displayMsg]);
      } catch (err) {
        console.error("Failed to parse message:", err);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      <h1 className="text-xl font-bold mb-4">Car Dashboard</h1>
      <MessageList messages={messages} />
    </div>
  );
}

export default App;
