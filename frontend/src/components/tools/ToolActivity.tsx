import { BoltIcon } from "../layout/Icons";

interface Props {
  tool: string;
  description?: string;
}

export function ToolActivity({ tool, description }: Props) {
  return (
    <div className="tool-activity">
      <BoltIcon />
      <span className="tool-label">TOOL</span>
      <strong>{tool.toUpperCase()}</strong>
      {description && <span className="tool-description">{description}</span>}
    </div>
  );
}
