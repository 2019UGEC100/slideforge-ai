import React from 'react';
import {
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Presentation,
  FileText,
  Palette,
  Github,
} from 'lucide-react';
import './Sidebar.css';

function Sidebar({ collapsed, onToggle, onNewChat, hasDocuments, hasBrand }) {
  return (
    <div className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      {/* Header */}
      <div className="sidebar-header">
        {!collapsed && (
          <div className="sidebar-logo">
            <Presentation size={22} />
            <span>SlideForge AI</span>
          </div>
        )}
        <button className="toggle-btn" onClick={onToggle}>
          {collapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
        </button>
      </div>

      {/* New Chat */}
      <button className="new-chat-btn" onClick={onNewChat}>
        <Plus size={18} />
        {!collapsed && <span>New Presentation</span>}
      </button>

      {/* Status indicators */}
      {!collapsed && (
        <div className="sidebar-status">
          <div className="status-section-title">Session Status</div>
          <div className={`status-item ${hasDocuments ? 'active' : ''}`}>
            <FileText size={16} />
            <span>{hasDocuments ? 'Document loaded' : 'No document'}</span>
          </div>
          <div className={`status-item ${hasBrand ? 'active' : ''}`}>
            <Palette size={16} />
            <span>{hasBrand ? 'Brand guide loaded' : 'No brand guide'}</span>
          </div>
        </div>
      )}

      {/* Spacer */}
      <div className="sidebar-spacer" />

      {/* Footer */}
      {!collapsed && (
        <div className="sidebar-footer">
          <div className="sidebar-info">
            <span className="info-label">Powered by Groq (Llama 3.3)</span>
            <span className="info-version">v1.0.0</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default Sidebar;
