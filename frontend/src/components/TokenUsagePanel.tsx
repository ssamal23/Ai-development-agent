import type { TokenUsage } from '../api'

const fmt = (n: number) => n.toLocaleString()

export default function TokenUsagePanel({ usage }: { usage?: TokenUsage }) {
  if (!usage || usage.calls === 0) {
    return <p className="token-empty">Token usage will appear once the first AI call finishes.</p>
  }

  const total = usage.input_tokens + usage.output_tokens

  return (
    <div className="token-usage">
      <div className="token-summary">
        <strong>{fmt(total)} tokens</strong>
        {usage.models.length > 0 && (
          <span className="token-model">Model: {usage.models.join(', ')}</span>
        )}
        <span>
          {fmt(usage.input_tokens)} in · {fmt(usage.output_tokens)} out
          {usage.cache_read_tokens > 0 && ` · ${fmt(usage.cache_read_tokens)} cached`} ·{' '}
          {usage.calls} AI {usage.calls === 1 ? 'call' : 'calls'}
        </span>
      </div>

      <table className="token-table">
        <thead>
          <tr>
            <th>Step</th>
            <th>Calls</th>
            <th>Input</th>
            <th>Output</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          {usage.stages
            .filter((stage) => stage.calls > 0)
            .map((stage) => (
              <tr key={stage.name} className="token-stage-row">
                <td>{stage.name}</td>
                <td>{stage.calls}</td>
                <td>{fmt(stage.input_tokens)}</td>
                <td>{fmt(stage.output_tokens)}</td>
                <td>{fmt(stage.input_tokens + stage.output_tokens)}</td>
              </tr>
            ))}
        </tbody>
      </table>

      <details className="token-details">
        <summary>Per agent step</summary>
        <table className="token-table">
          <tbody>
            {usage.steps.map((step) => (
              <tr key={step.node}>
                <td>
                  {step.label}
                  {step.stage && <span className="token-stage-tag">{step.stage}</span>}
                  {step.models.length > 0 && (
                    <span className="token-stage-tag">{step.models.join(', ')}</span>
                  )}
                </td>
                <td>{step.calls}</td>
                <td>{fmt(step.input_tokens)}</td>
                <td>{fmt(step.output_tokens)}</td>
                <td>{fmt(step.input_tokens + step.output_tokens)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}
