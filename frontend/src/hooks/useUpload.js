import { useCallback, useState } from "react";
import { uploadDocument } from "../services/documentApi";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt"];
const ACCEPTED_MIME = {
  "application/pdf": true,
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": true,
  "text/plain": true,
};
const MAX_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB, per API_CONTRACT.md

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function validateFile(file) {
  const extension = `.${file.name.split(".").pop().toLowerCase()}`;
  if (!ACCEPTED_EXTENSIONS.includes(extension) && !ACCEPTED_MIME[file.type]) {
    return `"${file.name}" isn't a supported file type. Upload a PDF, DOCX, or TXT file.`;
  }
  if (file.size > MAX_SIZE_BYTES) {
    return `"${file.name}" is ${formatBytes(file.size)}, which is over the 20 MB limit.`;
  }
  return null;
}

function makeId(file) {
  return `${file.name}-${file.size}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

/**
 * useUpload
 *
 * Owns the upload queue for document ingestion: client-side validation,
 * sequential-per-file upload via documentApi.uploadDocument, per-file
 * status tracking, retry, and dismissal. Designed to be driven by any UI
 * (FileUploader's dropzone, a simple <input>, etc.) — this hook holds no
 * rendering logic.
 *
 * Each queue entry: {
 *   id: string,
 *   file: File,
 *   status: "pending" | "uploading" | "indexed" | "failed",
 *   progress: number,       // 0-100, only meaningful while "uploading"
 *   error?: string,
 *   documentId?: string,    // set once indexed
 * }
 *
 * @param {object} [options]
 * @param {(document: object) => void} [options.onUploadComplete] called once per successfully indexed document
 * @returns {{
 *   queue: Array,
 *   addFiles: (fileList: FileList | File[]) => void,
 *   retry: (id: string) => void,
 *   dismiss: (id: string) => void,
 *   clearCompleted: () => void,
 *   isUploading: boolean,
 * }}
 */
export function useUpload({ onUploadComplete } = {}) {
  const [queue, setQueue] = useState([]);

  const updateEntry = useCallback((id, patch) => {
    setQueue((prev) => prev.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  }, []);

  const runUpload = useCallback(
    async (id, file) => {
      updateEntry(id, { status: "uploading", progress: 0, error: undefined });
      try {
        const result = await uploadDocument(file, (percent) => updateEntry(id, { progress: percent }));

        if (result.status === "failed") {
          updateEntry(id, { status: "failed", error: "Indexing failed on the server." });
          return;
        }

        updateEntry(id, { status: "indexed", progress: 100, documentId: result.document_id });
        onUploadComplete?.(result);
      } catch (err) {
        updateEntry(id, {
          status: "failed",
          error: err?.message || "Upload failed. Check your connection and try again.",
        });
      }
    },
    [onUploadComplete, updateEntry]
  );

  const addFiles = useCallback(
    (fileList) => {
      const files = Array.from(fileList);
      const entries = files.map((file) => {
        const error = validateFile(file);
        return {
          id: makeId(file),
          file,
          status: error ? "failed" : "pending",
          progress: 0,
          error: error || undefined,
        };
      });

      setQueue((prev) => [...prev, ...entries]);

      entries
        .filter((e) => e.status === "pending")
        .forEach((entry) => runUpload(entry.id, entry.file));
    },
    [runUpload]
  );

  const retry = useCallback(
    (id) => {
      setQueue((prev) => {
        const entry = prev.find((e) => e.id === id);
        if (entry) runUpload(id, entry.file);
        return prev;
      });
    },
    [runUpload]
  );

  const dismiss = useCallback((id) => {
    setQueue((prev) => prev.filter((e) => e.id !== id));
  }, []);

  const clearCompleted = useCallback(() => {
    setQueue((prev) => prev.filter((e) => e.status === "pending" || e.status === "uploading"));
  }, []);

  const isUploading = queue.some((e) => e.status === "uploading");

  return { queue, addFiles, retry, dismiss, clearCompleted, isUploading };
}
