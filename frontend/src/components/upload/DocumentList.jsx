import { useEffect, useState, useCallback } from "react";
import { listDocuments, deleteDocument } from "../../services/documentApi";

function formatDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

const STATUS_STYLES = {
  indexed: "bg-emerald-100 text-emerald-700",
  processing: "bg-amber-100 text-amber-700",
  failed: "bg-red-100 text-red-700",
};

/**
 * DocumentList
 *
 * Fetches and displays indexed legal documents (GET /documents), with a
 * delete action per row (DELETE /documents/{id}) that removes both the
 * source file and its vector-store chunks on the backend. Exposes a
 * `refreshToken` prop so a parent can force a re-fetch after a new upload
 * completes (e.g. pass a counter that increments on each successful upload).
 *
 * Props:
 *  - refreshToken?: any   change this value to trigger a re-fetch
 */
export default function DocumentList({ refreshToken }) {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pendingDeleteId, setPendingDeleteId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await listDocuments();
      setDocuments(result.documents || []);
    } catch (err) {
      setError(err?.message || "Couldn't load documents. Check your connection and try again.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments, refreshToken]);

  const confirmDelete = async (documentId) => {
    setDeletingId(documentId);
    const previous = documents;
    setDocuments((prev) => prev.filter((d) => d.document_id !== documentId));
    try {
      await deleteDocument(documentId);
    } catch (err) {
      setDocuments(previous); // roll back on failure
      setError(err?.message || "Couldn't delete that document. Try again.");
    } finally {
      setDeletingId(null);
      setPendingDeleteId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-14 animate-pulse rounded-md bg-stone-100" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        <p>{error}</p>
        <button
          onClick={fetchDocuments}
          className="mt-2 font-medium text-red-800 underline underline-offset-2"
        >
          Try again
        </button>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-stone-300 px-4 py-8 text-center">
        <p className="text-sm text-stone-600">No documents indexed yet.</p>
        <p className="mt-1 text-xs text-stone-400">
          Upload a legal document above to make it searchable in chat.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-md border border-stone-200">
      <table className="w-full min-w-[480px] text-left text-sm">
        <thead className="border-b border-stone-200 bg-stone-50 text-xs uppercase tracking-wide text-stone-500">
          <tr>
            <th className="px-4 py-2 font-medium">Document</th>
            <th className="px-4 py-2 font-medium">Status</th>
            <th className="px-4 py-2 font-medium">Chunks</th>
            <th className="px-4 py-2 font-medium">Uploaded</th>
            <th className="px-4 py-2" />
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100">
          {documents.map((doc) => (
            <tr key={doc.document_id} className="bg-white">
              <td className="max-w-[220px] truncate px-4 py-2.5 text-stone-800">
                {doc.filename}
              </td>
              <td className="px-4 py-2.5">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    STATUS_STYLES[doc.status] || "bg-stone-100 text-stone-600"
                  }`}
                >
                  {doc.status}
                </span>
              </td>
              <td className="px-4 py-2.5 text-stone-600">{doc.chunks ?? "—"}</td>
              <td className="px-4 py-2.5 text-stone-600">{formatDate(doc.uploaded_at)}</td>
              <td className="px-4 py-2.5 text-right">
                {pendingDeleteId === doc.document_id ? (
                  <span className="inline-flex items-center gap-2">
                    <button
                      onClick={() => confirmDelete(doc.document_id)}
                      disabled={deletingId === doc.document_id}
                      className="text-xs font-medium text-red-700 hover:underline disabled:opacity-50"
                    >
                      {deletingId === doc.document_id ? "Deleting…" : "Confirm"}
                    </button>
                    <button
                      onClick={() => setPendingDeleteId(null)}
                      className="text-xs text-stone-500 hover:underline"
                    >
                      Cancel
                    </button>
                  </span>
                ) : (
                  <button
                    onClick={() => setPendingDeleteId(doc.document_id)}
                    aria-label={`Delete ${doc.filename}`}
                    className="text-xs font-medium text-stone-500 hover:text-red-700 hover:underline"
                  >
                    Delete
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
