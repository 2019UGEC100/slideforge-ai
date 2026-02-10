import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import './App.css';

function App() {
  const [conversationId, setConversationId] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [hasDocuments, setHasDocuments] = useState(false);
  const [hasBrand, setHasBrand] = useState(false);
  const [chatKey, setChatKey] = useState(0); // Used to reset ChatInterface

  const handleNewChat = () => {
    setConversationId(null);
    setHasDocuments(false);
    setHasBrand(false);
    setChatKey((prev) => prev + 1); // Force re-render without page reload
  };

  return (
    <div className="app">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        onNewChat={handleNewChat}
        hasDocuments={hasDocuments}
        hasBrand={hasBrand}
      />
      <ChatInterface
        key={chatKey}
        conversationId={conversationId}
        setConversationId={setConversationId}
        sidebarCollapsed={sidebarCollapsed}
        onDocumentLoaded={() => setHasDocuments(true)}
        onBrandLoaded={() => setHasBrand(true)}
      />
    </div>
  );
}

export default App;
