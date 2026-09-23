import '../styles/Header.css'

interface HeaderProps {
  onLogout: () => void
}

export default function Header({ onLogout }: HeaderProps) {
  return (
    <header className="dashboard-header">
      <div className="header-content">
        <div className="project-selector">
          <span className="project-label">Project</span>
          <select className="project-dropdown">
            <option>Dealer Management System</option>
            <option>E-Commerce Platform</option>
            <option>Mobile App</option>
          </select>
        </div>

        <div className="header-actions">
          <button className="icon-button" title="Notifications">
            🔔
          </button>
          <button className="icon-button" title="Settings">
            ⚙️
          </button>
          <div className="user-menu">
            <div className="user-info">
              <div className="user-avatar">JD</div>
              <div className="user-details">
                <p className="user-name">John Doe</p>
                <p className="user-role">Developer</p>
              </div>
            </div>
            <button className="logout-button" onClick={onLogout}>
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
