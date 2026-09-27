interface Source {
  title: string;
  url?: string;
}

interface Props {
  sources: Source[];
}

export function SourceList({ sources }: Props) {
  if (sources.length === 0) {
    return null;
  }

  return (
    <div className="source-list">
      <div className="source-title">SOURCES</div>

      <div className="source-items">
        {sources.map((source, index) => (
          <div
            key={`${source.title}-${index}`}
            className="source"
          >
            <span className="source-icon">◈</span>

            {source.url ? (
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
              >
                {source.title}
              </a>
            ) : (
              <span>{source.title}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}