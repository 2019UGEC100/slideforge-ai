/**
 * ChatInterface.js
 * ================
 * Main chat component for SlideForge AI.
 * 
 * Features:
 * - File attachments (document + brand guide) with preview chips
 * - Message history with markdown rendering
 * - Slide generation via icon button or chat command
 * - Download button appears only when slides are generated
 * 
 * Props:
 * - conversationId: Current session ID (managed by App.js)
 * - setConversationId: Update session ID after first upload
 * - sidebarCollapsed: Adjusts layout when sidebar is hidden
 * - onDocumentLoaded/onBrandLoaded: Callbacks to update sidebar status
 */

import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Loader2, Presentation, Bot, X, FileText, Palette } from 'lucide-react';
import MessageBubble from './MessageBubble';
import { sendMessage, uploadFile, generateSlides, getDownloadUrl } from '../services/api';
import './ChatInterface.css';

function ChatInterface({ conversationId, setConversationId, sidebarCollapsed, onDocumentLoaded, onBrandLoaded }) {
  // ─────────────────────────────────────────────────────────────────────────
  // State
  // ─────────────────────────────────────────────────────────────────────────
  const [messages, setMessages] = useState([]);          // Chat history
  const [input, setInput] = useState('');                // Current input text
  const [loading, setLoading] = useState(false);         // API call in progress
  const [uploading, setUploading] = useState(false);     // File upload in progress
  const [hasDocuments, setHasDocuments] = useState(false); // Document uploaded flag
  const [hasBrand, setHasBrand] = useState(false);       // Brand guide uploaded flag
  
  // Pending files (attached but not yet sent)
  const [pendingDocument, setPendingDocument] = useState(null);
  const [pendingBrand, setPendingBrand] = useState(null);
  
  // Refs for DOM elements
  const messagesEndRef = useRef(null);   // Auto-scroll target
  const fileInputRef = useRef(null);     // Hidden file input (documents)
  const brandInputRef = useRef(null);    // Hidden file input (brand guide)
  const textareaRef = useRef(null);      // Auto-resize textarea

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
    }
  }, [input]);

  // Handle file selection (don't upload yet, just attach)
  const handleFileSelect = (e, purpose = 'document') => {
    const file = e.target.files[0];
    if (!file) return;
    if (purpose === 'brand') {
      setPendingBrand(file);
    } else {
      setPendingDocument(file);
    }
    e.target.value = '';
  };

  // Remove pending files
  const removePendingDocument = () => setPendingDocument(null);
  const removePendingBrand = () => setPendingBrand(null);
  
  // Check if any file is pending
  const hasPendingFiles = pendingDocument || pendingBrand;

  // Upload file (called when sending) - accepts optional convId for chaining uploads
  const doUploadFile = async (file, purpose, existingConvId = null) => {
    setUploading(true);

    try {
      // Use provided convId or current state
      const convIdToUse = existingConvId || conversationId;
      const result = await uploadFile(file, convIdToUse, purpose);

      // Capture conversation_id from upload response
      if (result.conversation_id && !conversationId) {
        setConversationId(result.conversation_id);
      }

      if (purpose === 'brand') {
        setHasBrand(true);
        onBrandLoaded?.(); // Notify parent
      } else {
        setHasDocuments(true);
        onDocumentLoaded?.(); // Notify parent
      }

      return result;
    } catch (err) {
      throw err;
    } finally {
      setUploading(false);
    }
  };

  const handleSend = async () => {
    // Allow sending if there's text OR any pending files
    if ((!input.trim() && !hasPendingFiles) || loading) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);

    // Collect pending files
    const docFile = pendingDocument;
    const brandFile = pendingBrand;
    setPendingDocument(null);
    setPendingBrand(null);

    // If there are pending files, upload them
    if (docFile || brandFile) {
      // Build user message showing attached files
      const attachments = [];
      if (docFile) attachments.push(`📄 ${docFile.name}`);
      if (brandFile) attachments.push(`🎨 ${brandFile.name}`);
      
      const fileMsg = {
        role: 'user',
        content: userMessage 
          ? `${userMessage}\n\n${attachments.join('\n')}`
          : `Uploading: ${attachments.join(', ')}`,
        files: [
          ...(docFile ? [{ name: docFile.name, type: 'document' }] : []),
          ...(brandFile ? [{ name: brandFile.name, type: 'brand' }] : []),
        ],
      };
      setMessages((prev) => [...prev, fileMsg]);

      try {
        // Track conversation_id through uploads (React state is async)
        let activeConvId = conversationId;

        // Upload document first if present
        if (docFile) {
          const docResult = await doUploadFile(docFile, 'document', activeConvId);
          activeConvId = docResult.conversation_id; // Capture for next upload
          setMessages((prev) => [...prev, {
            role: 'system',
            content: docResult.summary,
          }]);
        }

        // Upload brand guide if present - use the conversation_id from doc upload
        // Silently apply brand guidelines (don't show extraction details to user)
        if (brandFile) {
          const brandResult = await doUploadFile(brandFile, 'brand', activeConvId);
          activeConvId = brandResult.conversation_id;
          // Brand guide loaded silently - no message shown to user
        }

        // If user also included a message, send it to chat after uploads
        if (userMessage) {
          const history = messages
            .filter((m) => m.role !== 'system')
            .map((m) => ({ role: m.role, content: m.content }));
          
          // Use activeConvId which has the correct session ID
          const chatResult = await sendMessage(userMessage, activeConvId, history);
          
          if (chatResult.conversation_id) {
            setConversationId(chatResult.conversation_id);
          }

          setMessages((prev) => [...prev, {
            role: 'assistant',
            content: chatResult.reply,
            slideDownloadUrl: chatResult.slide_download_url,
          }]);
        }
      } catch (err) {
        setMessages((prev) => [...prev, {
          role: 'system',
          content: `Error: ${err.response?.data?.detail || err.message}`,
        }]);
      }
    } else {
      // No files, just send message
      setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);

      try {
        const history = messages
          .filter((m) => m.role !== 'system')
          .map((m) => ({ role: m.role, content: m.content }));

        const result = await sendMessage(userMessage, conversationId, history);

        if (result.conversation_id && !conversationId) {
          setConversationId(result.conversation_id);
        }

        setMessages((prev) => [...prev, {
          role: 'assistant',
          content: result.reply,
          slideDownloadUrl: result.slide_download_url,
        }]);
      } catch (err) {
        setMessages((prev) => [...prev, {
          role: 'system',
          content: `Error: ${err.response?.data?.detail || err.message}`,
        }]);
      }
    }

    setLoading(false);
  };

  const handleGenerateSlides = async () => {
    if (!conversationId || loading) return;

    setLoading(true);
    const userMsg = {
      role: 'user',
      content: 'Generate my slide deck now.',
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const result = await generateSlides(conversationId);

      const assistantMsg = {
        role: 'assistant',
        content: `Your presentation "${result.deck_title}" with ${result.num_slides} slides has been generated successfully!`,
        slideDownloadUrl: result.download_url,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg = {
        role: 'system',
        content: `Error generating slides: ${err.response?.data?.detail || err.message}`,
      };
      setMessages((prev) => [...prev, errorMsg]);
    }

    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div className={`chat-interface ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      {/* Messages Area */}
      <div className="messages-container">
        {isEmpty ? (
          <div className="welcome-screen">
            <div className="welcome-icon">
              <Presentation size={48} />
            </div>
            <h1>SlideForge AI</h1>
            <p className="welcome-subtitle">
              Transform your documents into polished, McKinsey-style presentations
            </p>
            <div className="welcome-steps">
              <div className="step-card">
                <div className="step-number">1</div>
                <div className="step-text">
                  <strong>Upload your document</strong>
                  <span>PDF, DOCX, or TXT — RFPs, proposals, reports</span>
                </div>
              </div>
              <div className="step-card">
                <div className="step-number">2</div>
                <div className="step-text">
                  <strong>Add brand guidelines</strong>
                  <span>Optional — style guide or reference deck</span>
                </div>
              </div>
              <div className="step-card">
                <div className="step-number">3</div>
                <div className="step-text">
                  <strong>Generate your deck</strong>
                  <span>Get a polished executive presentation in seconds</span>
                </div>
              </div>
            </div>
            {/* Upload buttons removed - use input bar icons instead */}
          </div>
        ) : (
          <div className="messages-list">
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}
            {/* Generate slides suggestion banner */}
            {hasDocuments && !loading && !messages.some(m => m.slideDownloadUrl) && (
              <div className="generate-suggestion">
                <div className="generate-suggestion-content">
                  <Presentation size={20} />
                  <span>Document ready! Generate your presentation now.</span>
                </div>
                <button 
                  className="generate-suggestion-btn"
                  onClick={handleGenerateSlides}
                >
                  Generate Slides
                </button>
              </div>
            )}
            {loading && (
              <div className="message-row assistant-row">
                <div className="message-avatar assistant-avatar">
                  <Bot size={20} />
                </div>
                <div className="typing-indicator">
                  <Loader2 size={18} className="spin" />
                  <span>SlideForge is thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="input-area">
        {/* Pending file attachments preview */}
        {hasPendingFiles && (
          <div className="pending-file-bar">
            <div className="pending-files-list">
              {pendingDocument && (
                <div className="pending-file-chip document-chip">
                  <FileText size={14} />
                  <span>{pendingDocument.name}</span>
                  <button className="remove-file-btn" onClick={removePendingDocument}>
                    <X size={14} />
                  </button>
                </div>
              )}
              {pendingBrand && (
                <div className="pending-file-chip brand-chip">
                  <Palette size={14} />
                  <span>{pendingBrand.name}</span>
                  <button className="remove-file-btn" onClick={removePendingBrand}>
                    <X size={14} />
                  </button>
                </div>
              )}
            </div>
            <span className="pending-file-hint">
              {pendingDocument && pendingBrand 
                ? 'Both files attached — add a message or click send'
                : pendingBrand 
                  ? 'Brand guide attached — you can also add a document'
                  : 'Document attached — you can also add a brand guide'}
            </span>
          </div>
        )}

        <div className="input-container">
          <div className="input-actions-left">
            <button
              className={`icon-btn ${pendingDocument ? 'has-file' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              title={pendingDocument ? "Replace document" : "Attach document"}
              disabled={uploading}
            >
              <Paperclip size={20} />
            </button>
            <button
              className={`icon-btn brand-btn ${pendingBrand ? 'has-file' : ''}`}
              onClick={() => brandInputRef.current?.click()}
              title={pendingBrand ? "Replace brand guide" : "Attach brand guide"}
              disabled={uploading}
            >
              <Palette size={20} />
            </button>
          </div>

          <textarea
            ref={textareaRef}
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              hasPendingFiles
                ? 'Add context about these files (optional)...'
                : isEmpty
                ? 'Upload a document to get started, or type a message...'
                : 'Type your message...'
            }
            rows={1}
            disabled={loading}
          />

          <div className="input-actions-right">
            <button
              className={`generate-btn ${hasDocuments ? 'ready' : ''}`}
              onClick={handleGenerateSlides}
              disabled={loading || !hasDocuments}
              title={
                hasDocuments 
                  ? "Generate slides" 
                  : hasPendingFiles 
                    ? "Click Send first to upload files" 
                    : "Upload a document first"
              }
            >
              <Presentation size={18} />
            </button>
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={(!input.trim() && !hasPendingFiles) || loading}
            >
              <Send size={18} />
            </button>
          </div>
        </div>

        <div className="input-footer">
          <span>
            {hasDocuments && '📄 Document loaded'}
            {hasDocuments && hasBrand && ' • '}
            {hasBrand && '🎨 Brand guide loaded'}
            {hasDocuments && !hasBrand && ' • Click 🎨 to add brand guide'}
            {!hasDocuments && !hasBrand && 'Attach a document using 📎 or brand guide using 🎨'}
          </span>
        </div>
      </div>

      {/* Hidden file inputs */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.doc,.txt,.md"
        onChange={(e) => handleFileSelect(e, 'document')}
        style={{ display: 'none' }}
      />
      <input
        ref={brandInputRef}
        type="file"
        accept=".pdf,.docx,.doc,.txt,.md,.pptx"
        onChange={(e) => handleFileSelect(e, 'brand')}
        style={{ display: 'none' }}
      />
    </div>
  );
}

export default ChatInterface;
