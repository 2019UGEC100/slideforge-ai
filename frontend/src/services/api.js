import axios from 'axios';

const API_BASE = 'http://localhost:8001';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // 2 minutes for LLM calls
});

export const uploadFile = async (file, conversationId, filePurpose = 'document') => {
  const formData = new FormData();
  formData.append('file', file);
  if (conversationId) {
    formData.append('conversation_id', conversationId);
  }
  formData.append('file_purpose', filePurpose);

  const response = await api.post('/api/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params: { conversation_id: conversationId, file_purpose: filePurpose },
  });
  return response.data;
};

export const sendMessage = async (message, conversationId, history = []) => {
  const response = await api.post('/api/chat', {
    message,
    conversation_id: conversationId,
    history,
  });
  return response.data;
};

export const generateSlides = async (conversationId) => {
  const response = await api.post('/api/generate-slides', null, {
    params: { conversation_id: conversationId },
  });
  return response.data;
};

export const getDownloadUrl = (path) => {
  return `${API_BASE}${path}`;
};

export default api;
