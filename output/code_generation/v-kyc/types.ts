export interface User {
  id: string;
  name: string;
  role: 'Team Leader' | 'Process Manager';
}

export interface Recording {
  lanId: string;
  date: string; // YYYY-MM-DD format
  fileName: string;
  size: string; // e.g., "15.4 MB"
  sizeInBytes: number;
  streamUrl: string; // URL for video streaming
  // New fields from BRD
  callDuration: string; // e.g., "0:05:54"
  status: 'APPROVED';
  time: string; // e.g., "9:54:45 PM"
  uploadTime: string; // YYYY-MM-DD format
}

export enum SearchType {
    SINGLE_ID = 'SINGLE_ID',
    DATE = 'DATE',
    BULK = 'BULK',
}

export type SortDirection = 'ascending' | 'descending';

export interface SortConfig {
    key: keyof Recording;
    direction: SortDirection;
}

export type ToastType = 'success' | 'error' | 'info';

export interface ToastMessage {
    id: number;
    type: ToastType;
    message: string;
}
