import DashboardView from './views/DashboardView'
import ProjectConfigureView from './views/ProjectConfigureView'
import type { ProjectConfig } from '../api'
import '../styles/MainContent.css'

interface MainContentProps {
  activeSection: string
  onConfigSaved: (config: ProjectConfig) => void
}

export default function MainContent({ activeSection, onConfigSaved }: MainContentProps) {
  return (
    <main className="main-content">
      {activeSection === 'dashboard' && <DashboardView />}
      {activeSection === 'tickets' && <div className="content-placeholder">My Tickets</div>}
      {activeSection === 'sessions' && <div className="content-placeholder">Active Sessions</div>}
      {activeSection === 'projects' && <div className="content-placeholder">Projects</div>}
      {activeSection === 'repositories' && <div className="content-placeholder">Repositories</div>}
      {activeSection === 'project-config' && (
        <ProjectConfigureView onSaved={onConfigSaved} />
      )}
      {activeSection === 'prs' && <div className="content-placeholder">Pull Requests</div>}
      {activeSection === 'settings' && <div className="content-placeholder">Settings</div>}
      {activeSection === 'logs' && <div className="content-placeholder">Logs & History</div>}
    </main>
  )
}
