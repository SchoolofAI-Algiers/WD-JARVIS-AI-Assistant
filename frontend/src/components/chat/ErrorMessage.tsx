interface Props {
  onRetry: () => void;
}

export function ErrorMessage({ onRetry }: Props) {
  return (
    <div className="error-message" role="alert">
      <div className="error-icon">!</div>

      <div className="error-content">
        <strong>CONNECTION LOST</strong>
        <span>I couldn't reach the J.A.R.V.I.S. core. Is the backend running?</span>
      </div>

      <button onClick={onRetry}>Retry</button>
    </div>
  );
}
