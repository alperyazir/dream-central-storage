import { ApiClient, apiClient } from './api';
import { buildAuthHeaders } from './http';

export interface TeacherMaterial {
  teacher_id: string;
  path: string;
  name: string;
  size: number;
  content_type: string;
  last_modified?: string;
}

interface StorageTreeNode {
  name: string;
  path: string;
  is_dir: boolean;
  size?: number;
  last_modified?: string;
  content_type?: string;
  children?: StorageTreeNode[];
}

interface TeachersListResponse {
  teachers: string[];
}

/**
 * Flatten a tree structure into a flat list of materials.
 */
const flattenTree = (
  node: StorageTreeNode,
  teacherId: string,
  basePath: string = ''
): TeacherMaterial[] => {
  const materials: TeacherMaterial[] = [];
  const currentPath = basePath ? `${basePath}/${node.name}` : node.name;

  if (!node.is_dir) {
    materials.push({
      teacher_id: teacherId,
      path: currentPath,
      name: node.name,
      size: node.size || 0,
      content_type: node.content_type || 'application/octet-stream',
      last_modified: node.last_modified,
    });
  }

  if (node.children) {
    for (const child of node.children) {
      materials.push(...flattenTree(child, teacherId, node.is_dir ? currentPath : basePath));
    }
  }

  return materials;
};

/**
 * List all teacher IDs that have materials stored.
 */
export const listAllTeachers = async (
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<string[]> => {
  const response = await client.get<TeachersListResponse>('/teachers/', {
    headers: buildAuthHeaders(token, tokenType),
  });
  return response.teachers;
};

/**
 * List unique teacher IDs for autocomplete.
 * Returns sorted list of teacher IDs.
 */
export const listUniqueTeacherIds = async (
  token: string,
  tokenType: string = 'Bearer'
): Promise<string[]> => {
  const teachers = await listAllTeachers(token, tokenType);
  return teachers.sort();
};

/**
 * Fetch all materials for a specific teacher.
 */
export const fetchTeacherMaterials = async (
  teacherId: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<TeacherMaterial[]> => {
  const tree = await client.get<StorageTreeNode>(
    `/teachers/${encodeURIComponent(teacherId)}/materials`,
    { headers: buildAuthHeaders(token, tokenType) }
  );

  // Flatten the tree structure
  const materials: TeacherMaterial[] = [];
  if (tree.children) {
    for (const child of tree.children) {
      materials.push(...flattenTree(child, teacherId, ''));
    }
  }

  return materials;
};

/**
 * Fetch materials for all teachers (parallel requests for performance).
 */
export const fetchAllTeacherMaterials = async (
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<TeacherMaterial[]> => {
  const teachers = await listAllTeachers(token, tokenType, client);

  // Fetch all teacher materials in parallel
  const results = await Promise.allSettled(
    teachers.map((teacherId) => fetchTeacherMaterials(teacherId, token, tokenType, client))
  );

  const allMaterials: TeacherMaterial[] = [];
  results.forEach((result, index) => {
    if (result.status === 'fulfilled') {
      allMaterials.push(...result.value);
    } else {
      console.error(`Failed to fetch materials for teacher ${teachers[index]}:`, result.reason);
    }
  });

  return allMaterials;
};

/**
 * Delete a teacher material (soft-delete to trash).
 */
export const deleteTeacherMaterial = async (
  teacherId: string,
  path: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<{ deleted: boolean; objects_moved: number }> => {
  return client.delete<{ deleted: boolean; objects_moved: number }>(
    `/teachers/${encodeURIComponent(teacherId)}/materials/${encodeURIComponent(path)}`,
    undefined,
    { headers: buildAuthHeaders(token, tokenType) }
  );
};

/**
 * Get the download URL for a teacher material.
 */
export const getTeacherMaterialUrl = (teacherId: string, path: string): string => {
  return `/api/teachers/${encodeURIComponent(teacherId)}/materials/${encodeURIComponent(path)}`;
};

/**
 * Download a teacher material with authentication.
 * Returns a blob URL that can be used directly in the browser.
 */
export const downloadTeacherMaterial = async (
  teacherId: string,
  path: string,
  token: string,
  tokenType: string = 'Bearer'
): Promise<string> => {
  const url = getTeacherMaterialUrl(teacherId, path);
  const response = await fetch(url, {
    headers: buildAuthHeaders(token, tokenType),
  });

  if (!response.ok) {
    throw new Error(`Failed to download material: ${response.status}`);
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
};

/**
 * Response from uploading a teacher material.
 */
export interface UploadTeacherMaterialResponse {
  teacher_id: string;
  filename: string;
  path: string;
  size: number;
  content_type: string;
}

/**
 * Upload a material file for a specific teacher.
 */
export const uploadTeacherMaterial = async (
  teacherId: string,
  file: File,
  token: string,
  tokenType: string = 'Bearer'
): Promise<UploadTeacherMaterialResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`/api/teachers/${encodeURIComponent(teacherId)}/upload`, {
    method: 'POST',
    headers: {
      Authorization: `${tokenType} ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const detail = errorBody?.detail || `Upload failed (${response.status})`;
    throw new Error(detail);
  }

  return response.json();
};
