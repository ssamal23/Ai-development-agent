import '../styles/StatCard.css'

interface StatCardProps {
  title: string
  value: string
  subtitle: string
  action: string
}

export default function StatCard({ title, value, subtitle, action }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="stat-header">
        <h3 className="stat-title">{title}</h3>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-subtitle">{subtitle}</div>
      <a href="#" className="stat-action">
        {action} →
      </a>
    </div>
  )
}
