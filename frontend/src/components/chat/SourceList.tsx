import type { Source } from "../../types/chat";
import { BookIcon } from "../layout/Icons";

interface Props {
  sources: Source[];
}

/** SOAI knowledge base passages used for an answer (metadata.sources from the backend). */
export function SourceList({ sources }: Props) {
  if (sources.length === 0) return null;

  return (
    <div className="source-list">
      <div className="source-title">SOAI KNOWLEDGE BASE</div>

      <div className="source-items">
        {sources.map((source) => (
          <span
            className="source"
            key={source.id}
            title={
              source.similarity !== undefined
                ? `${source.title} · match ${Math.round(source.similarity * 100)}%`
                : source.title
            }
          >
            <BookIcon />
            {source.section ?? source.title}
          </span>
        ))}
      </div>
    </div>
  );
}
