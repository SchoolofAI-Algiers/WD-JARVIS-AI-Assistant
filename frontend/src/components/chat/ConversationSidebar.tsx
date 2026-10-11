import { useState } from "react";

import type { Conversation } from "../../types/chat";
import { timeAgo } from "../../utils/time";
import type { Settings } from "../../utils/settings";
import {
  ChatIcon,
  ChevronRightIcon,
  DotsIcon,
  GearIcon,
} from "../layout/Icons";

interface Props {
  conversations: Conversation[];
  activeId: string;
  online: boolean;
  settings: Settings;
  onSettingsChange: (settings: Settings) => void;
  onNewChat: () => void;
  onSelect: (id: string) => void;
}

const SETTING_LABELS: [keyof Settings, string][] = [
  ["sound", "Sound effects"],
  ["boot", "Start-up animation"],
  ["motion", "Animations"],
];

/** Left panel, placed on the glass sidebar of the background picture. */
export function ConversationSidebar({
  conversations,
  activeId,
  online,
  settings,
  onSettingsChange,
  onNewChat,
  onSelect,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <aside className="conversation-sidebar">
      <div className="sidebar-brand">
        <div className="brand-emblem">
          <span className="brand-emblem-ring" />
          <span className="brand-emblem-ring dashed" />
          <span className="brand-emblem-core" />
        </div>

        <div>
          <strong>J.A.R.V.I.S.</strong>
          <span>ASSISTANT SYSTEM</span>
        </div>
      </div>

      <button className="new-chat-button" onClick={onNewChat} title="New conversation (Ctrl+K)">
        <ChatIcon />
        <span>New conversation</span>
        <ChevronRightIcon />
      </button>

      <span className="section-label">CONVERSATIONS</span>

      <div className="conversation-list">
        {conversations.map((conversation) => (
          <button
            key={conversation.id}
            className={`conversation-item ${conversation.id === activeId ? "active" : ""}`}
            onClick={() => onSelect(conversation.id)}
          >
            <ChatIcon />
            <span className="conversation-text">
              <strong>
                {conversation.id === activeId && conversation.messages.length === 0
                  ? "Current conversation"
                  : conversation.title}
              </strong>
              <span>
                {timeAgo(conversation.updatedAt)}
                {conversation.messages.length > 0 && ` · ${conversation.messages.length} messages`}
              </span>
            </span>
            <DotsIcon />
          </button>
        ))}
      </div>

      <div className="sidebar-spacer" />

      <div className="shortcuts">
        <span><kbd>/</kbd> type</span>
        <span><kbd>Ctrl</kbd>+<kbd>K</kbd> new chat</span>
        <span><kbd>Esc</kbd> stop</span>
      </div>

      <div className="sidebar-footer">
        <div className={`system-light ${online ? "" : "offline"}`}>
          <span />
        </div>

        <div className="system-info">
          <strong>LOCAL SYSTEM</strong>
          <span className={online ? "" : "offline"}>{online ? "ONLINE" : "OFFLINE"}</span>
        </div>

        <button
          className={`settings-button ${menuOpen ? "open" : ""}`}
          aria-label="Settings"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(!menuOpen)}
        >
          <GearIcon />
        </button>

        {menuOpen && (
          <div className="settings-menu" role="menu">
            <strong>SETTINGS</strong>
            {SETTING_LABELS.map(([key, label]) => (
              <label key={key} className="toggle">
                <span>{label}</span>
                <input
                  type="checkbox"
                  checked={settings[key]}
                  onChange={(event) => onSettingsChange({ ...settings, [key]: event.target.checked })}
                />
                <i />
              </label>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
