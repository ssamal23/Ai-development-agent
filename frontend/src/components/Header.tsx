import { parseGitRepoUrl, type ProjectConfig } from '../api'
import '../styles/Header.css'

interface HeaderProps {
  onLogout: () => void
  projectConfig: ProjectConfig | null
}

function getInitials(name: string): string {
  const parts = name.split(/[-_ ]+/).filter(Boolean)

  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }

  return name.slice(0, 2).toUpperCase()
}

export default function Header({ onLogout, projectConfig }: HeaderProps) {
  const repoInfo = projectConfig?.gitRepoUrl
    ? parseGitRepoUrl(projectConfig.gitRepoUrl)
    : null

  const gitUser = repoInfo?.owner ?? null

  return (
    <header className="dashboard-header">
      <div className="header-content">
        <div className="project-selector">
          <span className="project-label">Project</span>
          <select className="project-dropdown">
            {repoInfo ? (
              <option>
                {repoInfo.repo} ({repoInfo.owner})
              </option>
            ) : (
              <option>No project configured</option>
            )}
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
              <div className="user-avatar">
                {gitUser ? getInitials(gitUser) : '?'}
              </div>
              <div className="user-details">
                <p className="user-name">{gitUser ?? 'No project configured'}</p>
                <p className="user-role">{gitUser ? 'Git Repository Owner' : ''}</p>
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
