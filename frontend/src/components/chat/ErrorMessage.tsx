interface Props {
  onRetry: () => void;
}

export function ErrorMessage({ onRetry }: Props) {
  return (
    <div className="error-message">
      <div className="error-icon">!</div>

      <div className="error-content">
        <strong>CONNECTION ERROR</strong>

        <span>
          JARVIS could not connect to the assistant service.
        </span>

        <button onClick={onRetry}>
          Try again
        </button>
      </div>
    </div>
  );
}