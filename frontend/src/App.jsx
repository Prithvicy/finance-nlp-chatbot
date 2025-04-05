import { useState } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const sendMessage = async () => {
    if (!input.trim()) return;
  
    const userMessage = { text: input, sender: 'user' };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
  
    try {
      const response = await fetch(`http://localhost:8000/chat?query=${encodeURIComponent(input)}`);
      console.log('Raw response:', response); // Log the response object
  
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
  
      const data = await response.json();
      console.log('Parsed data:', data); // Log the parsed JSON
  
      let botMessage;
      if (data.price) {
        botMessage = {
          text: `${data.ticker} is $${data.price} as of ${data.timestamp} (Source: ${data.source})`,
          sender: 'bot',
        };
      } else {
        botMessage = { text: data.message || 'Sorry, I can’t help with that yet!', sender: 'bot' };
      }
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error('Fetch error:', error); // Log the exact error
      const errorMessage = { text: `Error: ${error.message}`, sender: 'bot' };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') sendMessage();
  };

  return (
    <div className="chat-container">
      <h1>Finance Chatbot</h1>
      <div className="messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.sender}`}>
            {msg.text}
          </div>
        ))}
      </div>
      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask me about stock/crypto prices..."
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}

export default App;