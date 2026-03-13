import React from 'react';
import { Chat } from '../features/chat/Chat';
import '../styles/chat.css';

export const ChatPage: React.FC = () => (
    <div className="chat-wrapper">
      <div className="chat-card">
        <Chat />
      </div>
    </div>
);
