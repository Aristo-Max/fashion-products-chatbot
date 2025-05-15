import AristoMaxLogo from '../assets/AristoMaxLogo-OnlyIcon.png' //Displays the bot's icon

const ChatboxIcon = () => {
  return (
    <div className="icon-wrapper">
      <img 
        src={AristoMaxLogo}
        alt="Chatbot Icon"
        className="chat-icon"
      />
    </div>
  )
}

export default ChatboxIcon