import { useEffect, useState } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import MainContent from './MainContent'
import { loadProjectConfig, type ProjectConfig } from '../api'
import '../styles/Dashboard.css'

interface DashboardProps {
  onLogout: () => void
}

export default function Dashboard({ onLogout }: DashboardProps) {
  const [projectConfig, setProjectConfig] = useState<ProjectConfig | null>(
    () => loadProjectConfig()
  )
  const isConfigured = Boolean(projectConfig?.gitRepoUrl)

  const [activeSection, setActiveSection] = useState(
    isConfigured ? 'dashboard' : 'project-config'
  )

  // If the project is ever unconfigured (e.g. cleared),
  // force the user back to the config tab.
  useEffect(() => {
    if (!isConfigured) {
      setActiveSection('project-config')
    }
  }, [isConfigured])

  const handleConfigSaved = (config: ProjectConfig) => {
    setProjectConfig(config)
    setActiveSection('dashboard')
  }

  return (
    <div className="dashboard-container">
      <Sidebar
        activeSection={activeSection}
        setActiveSection={setActiveSection}
        isConfigured={isConfigured}
      />
      <div className="dashboard-main">
        <Header onLogout={onLogout} projectConfig={projectConfig} />
        <MainContent activeSection={activeSection} onConfigSaved={handleConfigSaved} />
      </div>
    </div>
  )
}
