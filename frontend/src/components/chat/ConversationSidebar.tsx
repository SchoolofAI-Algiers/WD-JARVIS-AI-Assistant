interface Props {
  conversationTitle?: string;
  onNewChat: () => void;
}

export function ConversationSidebar({
  conversationTitle = "Current conversation",
  onNewChat,
}: Props) {
  return (
    <aside className="conversation-sidebar">
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-orb">J</div>

          <div>
            <strong>J.A.R.V.I.S.</strong>
            <span>ASSISTANT SYSTEM</span>
          </div>
        </div>
      </div>

      <button className="new-chat-button" onClick={onNewChat}>
        <span>+</span>
        New conversation
      </button>

      <div className="conversation-section">
        <span className="section-label">CONVERSATIONS</span>

        <button className="conversation-item active">
          <span className="conversation-icon">◈</span>

          <div>
            <strong>{conversationTitle}</strong>
            <span>Just now</span>
          </div>
        </button>
      </div>

      <div className="sidebar-footer">
        <div className="system-info">
          <span className="status-dot" />
          <div>
            <strong>LOCAL SYSTEM</strong>
            <span>ONLINE</span>
          </div>
        </div>
      </div>
    </aside>
  );
}