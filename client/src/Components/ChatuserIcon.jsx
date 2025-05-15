import avtar from '../assets/avtar.png' //Displays the bot's icon

const ChatuserIcon = () => {
  return (
    <div className="user-icon">
      <img 
        src={avtar}
        alt="Chatbot userIcon"
        className="chat-usericon"
      />
    </div>
  )
}

export default ChatuserIcon