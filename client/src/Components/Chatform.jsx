import React, { useRef } from 'react';

const Chatform = ({ chathistory, setchathistory, generateBotResponse, sessionId }) => {
  const inputRef = useRef();

  const handleformSubmit = (e) => {
    e.preventDefault();
    const usermessage = inputRef.current.value.trim();
    if (!usermessage) return;
    inputRef.current.value = '';
    inputRef.current.style.height = 'auto'; // Reset height after submission

    // Add user message with sessionId
    const userMessageObj = { from: 'user', text: usermessage, sessionId };
    setchathistory((history) => [...history, userMessageObj]);

    setTimeout(() => {
      setchathistory((history) => [...history, { from: 'model', text: 'Thinking...', sessionId }]);
      // Pass the updated history with consistent format
      generateBotResponse([...chathistory, userMessageObj]);
    }, 600); // Delay of 600ms before generating the bot's response
  };

  const handleInputChange = () => {
    const textarea = inputRef.current;
    textarea.style.height = 'auto'; // Reset height to calculate new height
    textarea.style.height = `${textarea.scrollHeight}px`; // Dynamically adjust height
  
    // Enable scrollbar only if content exceeds 3 lines
    if (textarea.scrollHeight > 4.5 * 16) {
      textarea.style.overflowY = 'auto'; // Show scrollbar
    } else {
      textarea.style.overflowY = 'hidden'; // Hide scrollbar
    }
  };

  return (
    <form action="" className="chat-from" onSubmit={handleformSubmit}>
      <textarea
        ref={inputRef}
        placeholder="Type your query here..."
        className="message-input"
        rows="1"
        onInput={handleInputChange} // Adjust height dynamically
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleformSubmit(e);
          }
        }}
        required
      ></textarea>
      <button className="material-symbols-outlined">send</button>
    </form>
  );
};

export default Chatform;