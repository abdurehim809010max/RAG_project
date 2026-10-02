import { useRef, useState, useCallback } from "react";
import { uploadDocument } from "../../services/documentApi";

const ACCEPTED_TYPES = [".pdf", ".docx", ".txt"];
const ACCEPTED_MIME = {
  "application/pdf": true,
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": true,
  "text/plain": true,
};
const MAX_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB, per API contract

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function validateFile(file) {
  const extension = `.${file.name.split(".").pop().toLowerCase()}`;
  if (!ACCEPTED_TYPES.includes(extension) && !ACCEPTED_MIME[file.type]) {
    return `"${file.name}" isn't a supported file type. Upload a PDF, DOCX, or TXT file.`;
  }
  if (file.size > MAX_SIZE_BYTES) {
    return `"${file.name}" is ${formatBytes(file.size)}, which is over the 20 MB limit.`;
  }
  return null;
}

/**
 * FileUploader
 *
 * Drag-and-drop / click-to-browse uploader for legal source documents.
 * Validates type and size client-side, then uploads sequentially through
 * documentApi.uploadDocument (POST /documents/upload), tracking per-file
 * progress and status so a user can retry a single failed file without
 * re-uploading everything.
 *
 * Props:
 *  - onUploadComplete?: (document) => void   called once per successfully indexed document
 */
export default function FileUploader({ onUploadComplete }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  // queue entries: { id, file, status: 'pending'|'uploading'|'indexed'|'failed', error?, documentId? }
  const [queue, setQueue] = useState([]);

  const updateEntry = useCallback((id, patch) => {
    setQueue((prev) => prev.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  }, []);

  const uploadOne = useCallback(
    async (entry) => {
      updateEntry(entry.id, { status: "uploading" });
      try {
        const result = await uploadDocument(entry.file);
        // result: { document_id, filename, status, chunks }
        if (result.status === "failed") {
          updateEntry(entry.id, { status: "failed", error: "Indexing failed on the server." });
          return;
        }
        updateEntry(entry.id, { status: "indexed", documentId: result.document_id });
        onUploadComplete?.(result);
      } catch (err) {
        updateEntry(entry.id, {
          status: "failed",
          error: err?.message || "Upload failed. Check your connection and try again.",
        });
      }
    },
    [onUploadComplete, updateEntry]
  );

  const addFiles = useCallback(
    (fileList) => {
      const incoming = Array.from(fileList);
      const entries = incoming.map((file) => {
        const error = validateFile(file);
        return {
          id: `${file.name}-${file.size}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          file,
          status: error ? "failed" : "pending",
          error: error || undefined,
        };
      });
      setQueue((prev) => [...prev, ...entries]);
      entries.filter((e) => e.status === "pending").forEach((entry) => uploadOne(entry));
    },
    [uploadOne]
  );

  const handleInputChange = (e) => {
    if (e.target.files?.length) addFiles(e.target.files);
    e.target.value = ""; // allow re-selecting the same file later
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
  };

  const retry = (entry) => {
    updateEntry(entry.id, { status: "pending", error: undefined });
    uploadOne(entry);
  };

  const dismiss = (id) => setQueue((prev) => prev.filter((e) => e.id !== id));

  return (
    <div className="w-full">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-600 ${
          isDragging
            ? "border-amber-600 bg-amber-50"
            : "border-stone-300 bg-stone-50 hover:border-stone-400 hover:bg-stone-100"
        }`}
      >
        <svg
          className="h-8 w-8 text-stone-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 8.25L12 3.75m0 0L7.5 8.25M12 3.75v12.75"
          />
        </svg>
        <p className="text-sm font-medium text-stone-700">
          Drag legal documents here, or click to browse
        </p>
        <p className="text-xs text-stone-500">PDF, DOCX, or TXT — up to 20 MB each</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES.join(",")}
          onChange={handleInputChange}
          className="hidden"
        />
      </div>

      {queue.length > 0 && (
        <ul className="mt-4 space-y-2">
          {queue.map((entry) => (
            <li
              key={entry.id}
              className="flex items-center justify-between gap-3 rounded-md border border-stone-200 bg-white px-3 py-2"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-stone-800">{entry.file.name}</p>
                <p className="text-xs text-stone-500">
                  {formatBytes(entry.file.size)}
                  {entry.status === "failed" && entry.error ? ` — ${entry.error}` : ""}
                </p>
              </div>

              <StatusBadge status={entry.status} />

              {entry.status === "failed" && (
                <button
                  onClick={() => retry(entry)}
                  className="text-xs font-medium text-amber-700 hover:underline"
                >
                  Retry
                </button>
              )}
              {(entry.status === "indexed" || entry.status === "failed") && (
                <button
                  onClick={() => dismiss(entry.id)}
                  aria-label={`Remove ${entry.file.name} from list`}
                  className="text-stone-400 hover:text-stone-600"
                >
                  ×
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StatusBadge({ status }) {
  const styles = {
    pending: "bg-stone-100 text-stone-600",
    uploading: "bg-amber-100 text-amber-700",
    indexed: "bg-emerald-100 text-emerald-700",
    failed: "bg-red-100 text-red-700",
  };
  const labels = {
    pending: "Queued",
    uploading: "Uploading…",
    indexed: "Indexed",
    failed: "Failed",
  };
  return (
    <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  );
}
