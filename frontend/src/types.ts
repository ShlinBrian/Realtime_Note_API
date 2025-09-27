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

// Search Types
export interface SearchRequest {
  query: string;
  top_k?: number;
  filters?: SearchFilters;
}

export interface SearchResult {
  note_id: string;
  similarity_score: number;
  title: string;
  snippet: string;
  highlighted_content?: string;
  created_at?: string;
  updated_at?: string;
}

export interface SearchResponse {
  results: SearchResult[];
  total_results: number;
  query_time_ms: number;
  query: string;
}

export interface SearchFilters {
  date_range?: {
    start?: string;
    end?: string;
  };
  min_score?: number;
  title_only?: boolean;
}

export interface SearchState {
  query: string;
  isSearching: boolean;
  results: SearchResult[];
  totalResults: number;
  queryTimeMs: number;
  error: string | null;
  filters: SearchFilters;
  history: string[];
  selectedResultId: string | null;
}

export interface SearchHistoryItem {
  query: string;
  timestamp: string;
  resultCount: number;
}

export interface SearchSuggestion {
  type: 'query' | 'title' | 'tag' | 'recent';
  text: string;
  context?: string;
  score?: number;
}

export interface AutocompleteResponse {
  suggestions: SearchSuggestion[];
  query: string;
}

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

  // Search elements
  searchContainer: HTMLDivElement;
  searchInput: HTMLInputElement;
  searchBtn: HTMLButtonElement;
  searchClearBtn: HTMLButtonElement;
  searchResults: HTMLDivElement;
  searchFilters: HTMLDivElement;
  searchStats: HTMLDivElement;
  searchHistory: HTMLDivElement;
  searchSuggestions: HTMLDivElement;

  // Editor elements
  noteTitle: HTMLInputElement;
  markdownEditor: HTMLTextAreaElement;
  markdownPreview: HTMLDivElement;
  noteVersion: HTMLSpanElement;
  deleteNoteBtn: HTMLButtonElement;
}