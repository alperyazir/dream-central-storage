import { ApiClient, apiClient } from './api';
import { buildAuthHeaders } from './http';

// =============================================================================
// Teacher Interfaces
// =============================================================================

export interface Teacher {
  id: number;
  teacher_id: string;
  display_name: string | null;
  email: string | null;
  status: 'active' | 'inactive' | 'suspended';
  ai_auto_process_enabled: boolean | null;
  ai_processing_priority: string | null;
  ai_audio_languages: string | null;
  created_at: string;
  updated_at: string;
}

export interface TeacherListItem extends Teacher {
  material_count: number;
  total_storage_size: number;
}

export interface TeacherCreate {
  teacher_id: string;
  display_name?: string;
  email?: string;
  ai_auto_process_enabled?: boolean | null;
  ai_processing_priority?: string;
  ai_audio_languages?: string;
}

export interface TeacherUpdate {
  display_name?: string;
  email?: string;
  status?: string;
  ai_auto_process_enabled?: boolean | null;
  ai_processing_priority?: string | null;
  ai_audio_languages?: string | null;
}

export interface TeacherListResponse {
  items: TeacherListItem[];
  total: number;
}

// =============================================================================
// Material Interfaces
// =============================================================================

export interface Material {
  id: number;
  material_name: string;
  display_name: string | null;
  file_type: string;
  content_type: string;
  size: number;
  status: string;
  ai_processing_status: string;
  ai_processed_at: string | null;
  ai_job_id: string | null;
  teacher_id: number;
  created_at: string;
  updated_at: string;
}

export interface MaterialListResponse {
  items: Material[];
  total: number;
}

// =============================================================================
// Storage Stats Interface
// =============================================================================

export interface FileTypeStats {
  count: number;
  size: number;
}

export interface StorageStats {
  total_size: number;
  total_count: number;
  by_type: Record<string, FileTypeStats>;
  ai_processable_count: number;
  ai_processed_count: number;
}

// =============================================================================
// Teacher API Functions
// =============================================================================

/**
 * Fetch all active teachers.
 */
export const fetchTeachers = async (
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<TeacherListItem[]> => {
  const response = await client.get<TeacherListResponse>('/teachers-manage/', {
    headers: buildAuthHeaders(token, tokenType),
  });
  return response.items;
};

/**
 * Fetch trashed teachers.
 */
export const fetchTrashedTeachers = async (
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<TeacherListItem[]> => {
  const response = await client.get<TeacherListResponse>('/teachers-manage/trash', {
    headers: buildAuthHeaders(token, tokenType),
  });
  return response.items;
};

/**
 * Fetch a single teacher by database ID.
 */
export const fetchTeacher = (
  id: number,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<Teacher> =>
  client.get<Teacher>(`/teachers-manage/${id}`, {
    headers: buildAuthHeaders(token, tokenType),
  });

/**
 * Fetch a single teacher by external teacher_id.
 */
export const fetchTeacherByExternalId = (
  teacherId: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<Teacher> =>
  client.get<Teacher>(`/teachers-manage/by-teacher-id/${encodeURIComponent(teacherId)}`, {
    headers: buildAuthHeaders(token, tokenType),
  });

/**
 * Create a new teacher.
 */
export const createTeacher = (
  data: TeacherCreate,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<Teacher> =>
  client.post<Teacher, TeacherCreate>('/teachers-manage/', data, {
    headers: buildAuthHeaders(token, tokenType),
  });

/**
 * Update an existing teacher.
 */
export const updateTeacher = (
  id: number,
  data: TeacherUpdate,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<Teacher> =>
  client.put<Teacher, TeacherUpdate>(`/teachers-manage/${id}`, data, {
    headers: buildAuthHeaders(token, tokenType),
  });

/**
 * Soft-delete a teacher (move to trash).
 */
export const deleteTeacher = (
  id: number,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<Teacher> =>
  client.delete<Teacher, never>(`/teachers-manage/${id}`, undefined, {
    headers: buildAuthHeaders(token, tokenType),
  });

/**
 * Restore a trashed teacher.
 */
export const restoreTeacher = (
  id: number,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<Teacher> =>
  client.post<Teacher, never>(`/teachers-manage/${id}/restore`, undefined, {
    headers: buildAuthHeaders(token, tokenType),
  });

/**
 * Permanently delete a trashed teacher.
 */
export const permanentDeleteTeacher = async (
  id: number,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<void> => {
  await client.delete<void, never>(`/teachers-manage/${id}/permanent`, undefined, {
    headers: buildAuthHeaders(token, tokenType),
  });
};

// =============================================================================
// Storage Stats API Functions
// =============================================================================

/**
 * Fetch storage statistics for a teacher.
 */
export const fetchTeacherStorageStats = (
  teacherId: number,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<StorageStats> =>
  client.get<StorageStats>(`/teachers-manage/${teacherId}/storage-stats`, {
    headers: buildAuthHeaders(token, tokenType),
  });

// =============================================================================
// Materials API Functions
// =============================================================================

/**
 * Fetch materials for a teacher.
 */
export const fetchTeacherMaterials = async (
  teacherId: number,
  token: string,
  tokenType: string = 'Bearer',
  fileType?: string,
  client: ApiClient = apiClient
): Promise<Material[]> => {
  const params = new URLSearchParams();
  if (fileType) params.append('file_type', fileType);
  const query = params.toString() ? `?${params.toString()}` : '';

  const response = await client.get<MaterialListResponse>(
    `/teachers-manage/${teacherId}/materials${query}`,
    { headers: buildAuthHeaders(token, tokenType) }
  );
  return response.items;
};

/**
 * Fetch a single material.
 */
export const fetchMaterial = (
  teacherId: number,
  materialId: number,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<Material> =>
  client.get<Material>(`/teachers-manage/${teacherId}/materials/${materialId}`, {
    headers: buildAuthHeaders(token, tokenType),
  });

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format bytes to human-readable string.
 */
export const formatBytes = (bytes: number, decimals = 2): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 * Get color for AI processing status.
 */
export const getAIStatusColor = (status: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
  switch (status) {
    case 'completed':
      return 'success';
    case 'processing':
    case 'queued':
      return 'info';
    case 'failed':
      return 'error';
    case 'partial':
      return 'warning';
    case 'not_applicable':
      return 'default';
    case 'not_started':
    default:
      return 'default';
  }
};

/**
 * Get human-readable AI status label.
 */
export const getAIStatusLabel = (status: string): string => {
  switch (status) {
    case 'completed':
      return 'Completed';
    case 'processing':
      return 'Processing';
    case 'queued':
      return 'Queued';
    case 'failed':
      return 'Failed';
    case 'partial':
      return 'Partial';
    case 'not_applicable':
      return 'N/A';
    case 'not_started':
      return 'Not Started';
    default:
      return status;
  }
};
