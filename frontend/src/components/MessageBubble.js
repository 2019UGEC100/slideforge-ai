import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Bot, User, Download } from 'lucide-react';
import { getDownloadUrl } from '../services/api';
import './MessageBubble.css';

function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  return (
    <div className={`message-row ${isUser ? 'user-row' : 'assistant-row'}`}>
      <div className={`message-avatar ${isUser ? 'user-avatar' : 'assistant-avatar'}`}>
        {isUser ? <User size={20} /> : <Bot size={20} />}
      </div>
      <div className={`message-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'} ${isSystem ? 'system-bubble' : ''}`}>
        <div className="message-sender">
          {isUser ? 'You' : 'SlideForge AI'}
        </div>
        <div className="message-content">
          {isSystem ? (
            <div className="system-message">{message.content}</div>
          ) : (
            <ReactMarkdown>{message.content}</ReactMarkdown>
          )}
        </div>
        {message.slideDownloadUrl && (
          <a
            href={getDownloadUrl(message.slideDownloadUrl)}
            className="download-button"
            download
          >
            <Download size={16} />
            Download Slide Deck (.pptx)
          </a>
        )}
        {message.files && message.files.length > 0 && (
          <div className="message-files">
            {message.files.map((f, i) => (
              <div key={i} className="file-chip">
                📎 {f.name}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default MessageBubble;
