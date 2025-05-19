import React, { useState, useRef, useEffect } from 'react';
import ChatbotIcon from './Components/ChatboxIcon';
import Chartform from './Components/Chatform'; // Note: File is Chatform.jsx
import Chatmessage from './Components/Chatmessage';
import logo from './assets/logo.png';
import './index.css';
import { v4 as uuidv4 } from 'uuid'; // For session ID generation

const App = () => {
  const [chathistory, setChathistory] = useState(() => {
    // Load chat history from sessionStorage on mount
    const savedHistory = sessionStorage.getItem('chatHistory');
    return savedHistory ? JSON.parse(savedHistory) : [];
  });
  const [showchatbot, setShowchatbot] = useState(false);
  const [sessionId] = useState(() => {
    // Generate or retrieve session ID
    const savedSession = sessionStorage.getItem('chatSessionId');
    return savedSession || uuidv4();
  });
  const chatBodyRef = useRef();
  const maxHistoryLength = 20; // Limit to last 20 messages

  // Save chat history and session ID to sessionStorage on update
  useEffect(() => {
    sessionStorage.setItem('chatHistory', JSON.stringify(chathistory));
    sessionStorage.setItem('chatSessionId', sessionId);
  }, [chathistory, sessionId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTo({
        top: chatBodyRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [chathistory]);

  const generateBotResponse = async (history) => {
    const updateHistory = (text, images = [], prices = []) => {
      setChathistory((prev) => {
        const newHistory = [
          ...prev.filter((msg) => msg.text !== 'Thinking...'),
          { from: 'model', text, image: images, price: prices, sessionId },
        ].slice(-maxHistoryLength);
        return newHistory;
      });
    };

    try {
      const userMessage = history[history.length - 1].text;

      const formattedHistory = history.slice(0, -1).map((msg) => ({
        role: msg.from === 'user' ? 'user' : 'assistant',
        content: msg.text,
      }));

      const response = await fetch('http://127.0.0.1:8000/generate-response', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: userMessage,
          chat_history: formattedHistory,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Error from backend:', errorData);
        updateHistory('Error: ' + (errorData.detail || 'Unknown error occurred.'));
        return;
      }

      const data = await response.json();

      // Extract arrays of images and prices from all products
      const images = data.products?.map((p) => p.image) || [];
      const prices = data.products?.map((p) => p.price) || [];

      updateHistory(data.response, images, prices);
    } catch (error) {
      console.error('Fetch/network error:', error);
      updateHistory('Sorry, the chatbot is unavailable due to a network error.');
    }
  };

  return (
    <div className={`container ${showchatbot ? 'show-chatbot' : ''}`}>
      <div className="App">
        <header className="header-container">
          <div className="logo-section">
            <img src={logo} alt="AristoMax Logo" className="company-logo" />
            <h1 className="gradient-header">Ecommerce - Clothing </h1>
          </div>
          <div className="blue-bar"></div>
        </header>
        <main className="p-4"></main>
        <footer
          className="bg-gray-800 p-4 text-white text-center relative w-full top-[22rem]"
          style={{ fontFamily: 'Poppins, sans-serif' }}
        ></footer>
      </div>

      <button
        onClick={() => setShowchatbot((prev) => !prev)}
        className="chatbot-toggler"
      >
        <span className="material-symbols-outlined">chat</span>
        <span className="material-symbols-outlined">close</span>
      </button>

      <div className="chatbot-popup">
        <div className="chat-header">
          <div className="header-info">
            <ChatbotIcon />
            <h1 className="logo-text">AristoMax - Chatbot</h1>
          </div>
          <button
            onClick={() => setShowchatbot((prev) => !prev)}
            className="material-symbols-outlined"
          >
            keyboard_arrow_down
          </button>
        </div>

        <div ref={chatBodyRef} className="Chatbot-body">
          <br />
          <div className="message bot-message">
            <ChatbotIcon />
            <p className="message-text">
              Hello, <br /> How can I assist you?
            </p>
          </div>
          {chathistory.map((message, index) => (
            <Chatmessage
              key={`${message.sessionId || 'initial'}-${index}`} // Use sessionId for unique keys
              role={message.from === 'user' ? 'user' : 'model'}
              text={message.text}
              image={message.image}
              price={message.price}
            />
          ))}
        </div>

        <div className="chat-footer">
          <Chartform
            setchathistory={setChathistory}
            chathistory={chathistory}
            generateBotResponse={generateBotResponse}
            sessionId={sessionId} // Pass sessionId to Chatform
          />
        </div>
      </div>

      <footer className="footer">
        <div className="blue-bar-footer"></div>
        <p>
          © 2025 <b>Aristomax Technologies Pvt. Ltd.</b>, All Right Reserved.
        </p>
      </footer>
    </div>
  );
};

export default App;
