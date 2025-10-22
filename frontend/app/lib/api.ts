import { Case, UploadResponse, AIMessage, StatisticsData } from '../types';

const API_BASE = '/api';

export const api = {
  // Upload clinical note
  async uploadNote(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Upload failed');
    }

    return response.json();
  },

  // Orchestrate case processing
  async orchestrateCase(caseId: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE}/orchestrate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case_id: caseId }),
    });

    if (!response.ok) {
      throw new Error('Orchestration failed');
    }

    return response.json();
  },

  // Get all cases
  async getCases(): Promise<Case[]> {
    const response = await fetch(`${API_BASE}/cases`);

    if (!response.ok) {
      throw new Error('Failed to fetch cases');
    }

    return response.json();
  },

  // Get single case
  async getCase(caseId: string): Promise<Case> {
    const response = await fetch(`${API_BASE}/cases/${caseId}`);

    if (!response.ok) {
      throw new Error('Failed to fetch case');
    }

    return response.json();
  },

  // AI Assistant chat
  async chat(
    message: string,
    history: AIMessage[]
  ): Promise<{ response: string; success: boolean }> {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
    });

    if (!response.ok) {
      throw new Error('Chat failed');
    }

    return response.json();
  },

  // Get statistics
  async getStatistics(): Promise<StatisticsData> {
    const response = await fetch(`${API_BASE}/statistics`);

    if (!response.ok) {
      throw new Error('Failed to fetch statistics');
    }

    return response.json();
  },
};

