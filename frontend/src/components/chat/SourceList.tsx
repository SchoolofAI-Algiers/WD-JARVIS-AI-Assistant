interface Source {
  title: string;
  url?: string;
}

interface Props {
  sources: Source[];
}

export function SourceList({ sources }: Props) {
  if (!sources.length) return null;

  return (
    <div className="source-list">
      <span className="source-title">SOURCES</span>

      {sources.map((source) => (
        <div key={source.title} className="source">
          <span>◈</span>
          {source.url ? (
            <a href={source.url} target="_blank" rel="noreferrer">
              {source.title}
            </a>
          ) : (
            <span>{source.title}</span>
          )}
        </div>
      ))}
    </div>
  );
}