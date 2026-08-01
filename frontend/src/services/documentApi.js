const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Failed to upload document");
  }

  return response.json();
}

export async function getDocuments() {
  const response = await fetch(`${API_BASE_URL}/documents`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to load documents");
  }
  return response.json();
}

export async function getDocumentViewerData(documentId) {
  const [fileResponse, textResponse] = await Promise.all([
    fetch(`${API_BASE_URL}/documents/${documentId}/file`),
    fetch(`${API_BASE_URL}/documents/${documentId}/text`),
  ]);

  if (!fileResponse.ok) {
    const errorData = await fileResponse.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to load the PDF");
  }

  const file = await fileResponse.blob();
  let extraction = null;
  if (textResponse.ok) {
    extraction = await textResponse.json();
  } else if (textResponse.status !== 404) {
    const errorData = await textResponse.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to load extracted text");
  }

  return { file, extraction };
}

export async function renameDocument(documentId, filename) {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to rename document");
  }

  return response.json();
}

export async function deleteDocument(documentId) {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to delete document");
  }
}

export async function getDocumentStatus(documentId) {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}/status`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to get processing status");
  }
  return response.json();
}

export async function retryDocumentProcessing(documentId) {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}/retry`, {
    method: "POST",
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to retry document processing");
  }
  return response.json();
}

export async function searchDocuments(query, topK = 20) {
  const response = await fetch(`${API_BASE_URL}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      top_k: topK,
      similarity_threshold: 0.15,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to search documents");
  }

  return response.json();
}

export async function askDocuments(question, documentIds = null) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, document_ids: documentIds, top_k: 8 }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to answer the question");
  }
  return response.json();
}
