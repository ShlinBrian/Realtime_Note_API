// API Types
export interface Note {
  note_id: string;
  title: string;
  content_md: string;
  version: number;
  created_at?: string;
  updated_at?: string;
}

export interface CreateNoteRequest {
  title: string;
  content_md: string;
}

export interface ApiError {
  error: {
    message: string;
    code?: string;
  };
}

// WebSocket Message Types
export interface WebSocketMessage {
  type: 'init' | 'patch' | 'update' | 'error';
  data: any;
}

export interface InitMessage extends WebSocketMessage {
  type: 'init';
  data: Note;
}

export interface PatchMessage extends WebSocketMessage {
  type: 'patch';
  data: {
    version: number;
    patch: string; // base64 encoded JSON
  };
}

export interface UpdateMessage extends WebSocketMessage {
  type: 'update';
  data: {
    title: string;
    content_md: string;
    version: number;
  };
}

export interface ErrorMessage extends WebSocketMessage {
  type: 'error';
  data: {
    code: string;
    message: string;
    current_version?: number;
  };
}

// Connection Status
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected';

export type NotificationType = 'info' | 'success' | 'error';

// DOM Elements Interface
export interface AppElements {
  // Main elements
  apiKeyInput: HTMLInputElement;
  connectBtn: HTMLButtonElement;
  statusIndicator: HTMLDivElement;
  statusText: HTMLSpanElement;
  notesList: HTMLDivElement;
  newNoteTitle: HTMLInputElement;
  createNoteBtn: HTMLButtonElement;

  // Editor elements
  noteTitle: HTMLInputElement;
  markdownEditor: HTMLTextAreaElement;
  markdownPreview: HTMLDivElement;
  noteVersion: HTMLSpanElement;
  deleteNoteBtn: HTMLButtonElement;
}