import '../styles/Sidebar.css'

interface SidebarProps {
  activeSection: string
  setActiveSection: (section: string) => void
}

export default function Sidebar({ activeSection, setActiveSection }: SidebarProps) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '🏠' },
    { id: 'tickets', label: 'My Tickets', icon: '🎫' },
    { id: 'sessions', label: 'Active Sessions', icon: '👥' },
    { id: 'projects', label: 'Projects', icon: '📁' },
    { id: 'repositories', label: 'Repositories', icon: '📦' },
    { id: 'prs', label: 'Pull Requests', icon: '🔗' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
    { id: 'logs', label: 'Logs & History', icon: '📋' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>AI Development Agent</h1>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${activeSection === item.id ? 'active' : ''}`}
            onClick={() => setActiveSection(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="project-connections">
          <h3>PROJECT CONNECTIONS</h3>
          <div className="connection-item">
            <span className="status-dot connected"></span>
            <div>
              <p className="connection-name">Azure DevOps</p>
              <p className="connection-status">Connected</p>
            </div>
          </div>
          <div className="connection-item">
            <span className="status-dot connected"></span>
            <div>
              <p className="connection-name">GitHub</p>
              <p className="connection-status">Connected</p>
            </div>
          </div>
        </div>

        <div className="agent-ready">
          <p>AI Agent is ready!</p>
          <p className="small-text">Select a ticket and let AI handle the development from analysis to PR.</p>
        </div>
      </div>
    </aside>
  )
}
