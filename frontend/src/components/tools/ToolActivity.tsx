interface Props {
  tool: string;
  description?: string;
}

export function ToolActivity({ tool, description }: Props) {
  return (
    <div className="tool-activity">
      <div className="tool-label">TOOL</div>

      <strong>{tool}</strong>

      {description && <span>{description}</span>}
    </div>
  );
}