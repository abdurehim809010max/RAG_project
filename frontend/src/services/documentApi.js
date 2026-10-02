import apiClient from "./apiClient";

/**
 * documentApi
 *
 * Thin wrapper around the /documents endpoints defined in API_CONTRACT.md.
 * Keeps fetch/axios details and error normalization in one place so
 * components (FileUploader, DocumentList) never touch the HTTP layer
 * directly. Every function throws a plain Error with a readable .message
 * on failure, which the components already catch and display.
 */

/**
 * Upload a single document for ingestion.
 *
 * POST /documents/upload  (multipart/form-data, field name "file")
 *
 * @param {File} file
 * @param {(percent: number) => void} [onProgress] optional upload-progress callback (0-100)
 * @returns {Promise<{document_id: string, filename: string, status: "processing"|"indexed"|"failed", chunks: number}>}
 */
export async function uploadDocument(file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: onProgress
      ? (event) => {
          if (event.total) onProgress(Math.round((event.loaded / event.total) * 100));
        }
      : undefined,
  });

  return response.data;
}

/**
 * List all indexed documents.
 *
 * GET /documents
 *
 * @returns {Promise<{documents: Array<{document_id: string, filename: string, status: string, chunks: number, uploaded_at: string}>}>}
 */
export async function listDocuments() {
  const response = await apiClient.get("/documents");
  return response.data;
}

/**
 * Delete a document and its indexed chunks.
 *
 * DELETE /documents/{document_id}  -> 204 No Content
 *
 * @param {string} documentId
 * @returns {Promise<void>}
 */
export async function deleteDocument(documentId) {
  if (!documentId) throw new Error("A document_id is required to delete a document.");
  await apiClient.delete(`/documents/${encodeURIComponent(documentId)}`);
}
