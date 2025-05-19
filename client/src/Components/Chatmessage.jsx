import React, { useRef, useState, useEffect } from 'react';
import ChatbotIcon from './ChatboxIcon';
import Usericon from './ChatuserIcon';
import { VscChevronLeft,VscChevronRight } from "react-icons/vsc"


const Chatmessage = ({ role, text, image = [], price = [] }) => {
  const scrollRef = useRef(null);
  const [showLeftArrow, setShowLeftArrow] = useState(false);
  const [showRightArrow, setShowRightArrow] = useState(false);

  const isArray = Array.isArray(image) && Array.isArray(price);
  const images = isArray ? image : image ? [image] : [];
  const prices = isArray ? price : price ? [price] : [];

  const groupImages = (images) => {
    const groups = [];
    for (let i = 0; i < images.length; i += 3) {
      groups.push(images.slice(i, i + 3));
    }
    return groups;
  };

  const handleScroll = (direction) => {
    const container = scrollRef.current;
    const scrollAmount = container.clientWidth * 0.8;
    container.scrollBy({
      left: direction === 'left' ? -scrollAmount : scrollAmount,
      behavior: 'smooth',
    });
  };

  const updateArrows = () => {
    const container = scrollRef.current;
    if (container) {
      setShowLeftArrow(container.scrollLeft > 0);
      setShowRightArrow(container.scrollLeft < container.scrollWidth - container.clientWidth - 1);
    }
  };

  useEffect(() => {
    const container = scrollRef.current;
    if (container) {
      container.addEventListener('scroll', updateArrows);
      updateArrows(); // initial state
      return () => container.removeEventListener('scroll', updateArrows);
    }
  }, []);

  const renderImageGrid = () => {
    const grouped = groupImages(images);

    return (
      <div
        className="image-grid-container"
        style={{ position: 'relative', marginTop: '16px' }}
      >
        {/* Scroll container */}
        <div
          ref={scrollRef}
          className="image-grid"
          style={{
            display: 'flex',
            overflowX: 'auto',
            scrollSnapType: 'x mandatory',
            gap: '20px',
            padding: '10px',
            scrollBehavior: 'smooth',
            scrollbarWidth: 'none',
            position: 'relative',
          }}
        >
          {grouped.map((group, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                gap: '12px',
                flexShrink: 0,
                scrollSnapAlign: 'start',
              }}
            >
              {group.map((url, index) => {
                const globalIndex =
                  grouped.slice(0, i).reduce((sum, g) => sum + g.length, 0) + index;
                const productPrice = prices[globalIndex] || 'N/A';

                return (
                  <div
                    key={index}
                    style={{ textAlign: 'center', position: 'relative' }}
                  >
                    <div style={{ position: 'relative' }}>
                      <img
                        src={url}
                        alt={`Product ${index + 1}`}
                        style={{
                          width: '120px',
                          height: 'auto',
                          borderRadius: '8px',
                          border: '1px solid #a6a6a6',
                          transition: 'all 0.3s ease',
                        }}
                        onMouseEnter={(e) => {
                          e.target.style.border = '2px solid black';
                          e.target.style.filter = 'grayscale(100%)';
                          const overlay = e.target.nextSibling;
                          if (overlay) overlay.style.opacity = 1;
                        }}
                        onMouseLeave={(e) => {
                          e.target.style.border = '1px solid #a6a6a6';
                          e.target.style.filter = 'grayscale(0%)';
                          const overlay = e.target.nextSibling;
                          if (overlay) overlay.style.opacity = 0;
                        }}
                      />
                      <div
                        className="hover-overlay"
                        style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          width: '100%',
                          height: '100%',
                          backgroundColor: 'rgba(0, 0, 0, 0.5)',
                          borderRadius: '8px',
                          opacity: 0,
                          transition: 'opacity 0.3s ease',
                          pointerEvents: 'none',
                          color: '#fff',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        Price: {productPrice !== 'N/A' ? `${productPrice}` : 'N/A'}
                      </div>
                    </div>
                    <a
                      href="#"
                      style={{
                        display: 'inline-block',
                        padding: '6px 12px',
                        backgroundColor: '#0d9eca',
                        color: '#fff',
                        textDecoration: 'none',
                        borderRadius: '4px',
                        marginTop: '8px',
                        border: '1px solid #a6a6a6',
                      }}
                      onMouseEnter={(e) => (e.target.style.border = '2px solid black')}
                      onMouseLeave={(e) => (e.target.style.border = '1px solid #a6a6a6')}
                    >
                      Buy Product
                    </a>
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* Left Arrow */}
        {images.length > 2 &&showLeftArrow && (
          <button
            onClick={() => handleScroll('left')}
            style={{
              position: 'absolute',
              top: '50%',
              left: '0',
              transform: 'translateY(-50%)',
              backgroundColor: 'rgba(0,0,0,0.5)',
              border: 'none',
              borderRadius: '50%',
              width: '30px',
              height: '30px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
            }}
            aria-label="Scroll Left"
          >
               <VscChevronLeft />
          </button>
        )}

        {/* Right Arrow */}
        {images.length > 2 && showRightArrow && (
          <button
            onClick={() => handleScroll('right')}
            style={{
              position: 'absolute',
              top: '50%',
              right: '0',
              transform: 'translateY(-50%)',
              backgroundColor: 'rgba(0,0,0,0.5)',
              border: 'none',
              borderRadius: '50%',
              width: '30px',
              height: '30px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
            }}
            aria-label="Scroll Right"
          >
               <VscChevronRight />

          </button>
        )}
      </div>
    );
  };

const renderContent = () => {
    const cleanedText =
      typeof text === 'string'
        ? text
            .replace('Here is a recommended product:', '')
            .replace(/price:\s*([\d.]+)/gi, '')
            .trim()
        : '';
  
    const textLines = cleanedText.split('\n').filter(line => line.trim() !== '');
  
    return (
      <>
        {textLines.map((line, idx) => (
          <p key={idx} style={{ marginBottom: '6px' }}>{line}</p>
        ))}
        {images.length > 0 && renderImageGrid()}</>
);};

  return (
    <div className={`message ${role === 'user' ? 'user-message' : 'bot-message'}`}>
      {role === 'model' && <ChatbotIcon />}
      <div className="message-text">{renderContent()}</div>
      {role === 'user' && <Usericon />}
    </div>
  );
};

export default Chatmessage;
