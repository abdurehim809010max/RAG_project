export default function CitationCard({ source }) {
  const similarityPercent = source.similarity ? Math.round(source.similarity * 100) : null;

  return (
    <div className="citation-card">
      <div className="citation-header">
        <span>መዝገብ ቁጥር (Case): {source.case_number || 'N/A'}</span>
        {similarityPercent && <span className="citation-match">Match: {similarityPercent}%</span>}
      </div>
      <div className="citation-meta">
        ገጽ (Page): {source.page_range || 'N/A'} | ዘርፍ (Category): {source.legal_category || 'General'}
      </div>
      <p className="citation-snippet">"{source.snippet || source.content}"</p>
    </div>
  );
}