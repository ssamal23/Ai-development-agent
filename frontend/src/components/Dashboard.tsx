import { useState } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import MainContent from './MainContent'
import '../styles/Dashboard.css'

interface DashboardProps {
  onLogout: () => void
}

export default function Dashboard({ onLogout }: DashboardProps) {
  const [activeSection, setActiveSection] = useState('dashboard')

  return (
    <div className="dashboard-container">
      <Sidebar activeSection={activeSection} setActiveSection={setActiveSection} />
      <div className="dashboard-main">
        <Header onLogout={onLogout} />
        <MainContent activeSection={activeSection} />
      </div>
    </div>
  )
}
