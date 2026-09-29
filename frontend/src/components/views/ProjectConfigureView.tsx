import { useState, useEffect } from 'react'
import { loadProjectConfig, saveProjectConfig, type ProjectConfig } from '../../api'
import '../../styles/ProjectConfigureView.css'

const DEFAULT_CONFIG: ProjectConfig = {
  gitRepoUrl: '',
  baseBranch: 'main',
  gitToken: '',
  boardProvider: 'none',
  boardOrgOrUrl: '',
  boardProjectKey: '',
  boardToken: '',
}

interface ProjectConfigureViewProps {
  onSaved?: (config: ProjectConfig) => void
}

export default function ProjectConfigureView({ onSaved }: ProjectConfigureViewProps) {
  const [config, setConfig] = useState<ProjectConfig>(
    () => loadProjectConfig() ?? DEFAULT_CONFIG
  )
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!saved) return
    const timeout = setTimeout(() => setSaved(false), 2500)
    return () => clearTimeout(timeout)
  }, [saved])

  const handleChange = (field: keyof ProjectConfig, value: string) => {
    setConfig((prev) => ({ ...prev, [field]: value }))
    setSaved(false)
  }

  const handleSave = (event: React.FormEvent) => {
    event.preventDefault()

    if (!config.gitRepoUrl.trim()) {
      setError('Git repository URL is required.')
      return
    }

    setError('')

    try {
      saveProjectConfig(config)
      setSaved(true)
      onSaved?.(config)
    } catch {
      setError('Could not save configuration in this browser.')
    }
  }

  return (
    <div className="project-configure-view">
      <div className="section-card">
        <div className="section-header">
          <h2 className="section-title">Project Configuration</h2>
        </div>

        <p className="config-hint">
          Set this up once. The AI agent will use this repository and
          branch for every ticket you submit, instead of asking for it
          each time.
        </p>

        <form className="config-form" onSubmit={handleSave}>
          <div className="config-group">
            <h3 className="config-group-title">Git Repository</h3>

            <label className="config-field">
              <span>Repository URL *</span>
              <input
                type="text"
                placeholder="https://github.com/owner/repo.git"
                value={config.gitRepoUrl}
                onChange={(e) => handleChange('gitRepoUrl', e.target.value)}
              />
            </label>

            <label className="config-field">
              <span>Base Branch</span>
              <input
                type="text"
                placeholder="main"
                value={config.baseBranch}
                onChange={(e) => handleChange('baseBranch', e.target.value)}
              />
            </label>

            <label className="config-field">
              <span>Access Token (optional, for private repos)</span>
              <input
                type="password"
                placeholder="ghp_..."
                value={config.gitToken}
                onChange={(e) => handleChange('gitToken', e.target.value)}
              />
            </label>
          </div>

          <div className="config-group">
            <h3 className="config-group-title">Agile Ticket Board</h3>

            <label className="config-field">
              <span>Provider</span>
              <select
                value={config.boardProvider}
                onChange={(e) => handleChange('boardProvider', e.target.value)}
              >
                <option value="none">None (manual tickets only)</option>
                <option value="azure_boards">Azure Boards</option>
                <option value="jira">Jira</option>
                <option value="github_issues">GitHub Issues</option>
              </select>
            </label>

            {config.boardProvider !== 'none' && (
              <>
                <label className="config-field">
                  <span>
                    {config.boardProvider === 'azure_boards'
                      ? 'Organization URL'
                      : config.boardProvider === 'jira'
                      ? 'Jira Site URL'
                      : 'Repository (owner/repo)'}
                  </span>
                  <input
                    type="text"
                    value={config.boardOrgOrUrl}
                    onChange={(e) => handleChange('boardOrgOrUrl', e.target.value)}
                  />
                </label>

                <label className="config-field">
                  <span>Project / Board Key</span>
                  <input
                    type="text"
                    value={config.boardProjectKey}
                    onChange={(e) => handleChange('boardProjectKey', e.target.value)}
                  />
                </label>

                <label className="config-field">
                  <span>Access Token</span>
                  <input
                    type="password"
                    value={config.boardToken}
                    onChange={(e) => handleChange('boardToken', e.target.value)}
                  />
                </label>
              </>
            )}
          </div>

          {error && <p className="config-error">{error}</p>}

          <div className="config-actions">
            <button type="submit" className="save-button">
              Save Configuration
            </button>
            {saved && <span className="save-confirmation">Saved ✓</span>}
          </div>
        </form>
      </div>
    </div>
  )
}
