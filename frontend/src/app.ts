import type {
  Note,
  CreateNoteRequest,
  ApiError,
  WebSocketMessage,
  InitMessage,
  PatchMessage,
  UpdateMessage,
  ErrorMessage,
  ConnectionStatus,
  NotificationType,
  AppElements
} from './types.js';
import { SearchService } from './search.js';

// Declare global objects
declare global {
  interface Window {
    Prism: {
      highlightElement: (element: Element) => void;
    };
    marked: {
      parse: (markdown: string) => string;
    };
    app: RealtimeNotesApp;
  }
}

class RealtimeNotesApp {
  private apiBaseUrl: string = 'http://localhost:8000';
  private wsBaseUrl: string = 'ws://localhost:8000';
  private apiKey: string = '';
  private currentNote: Note | null = null;
  private notes: Note[] = [];
  private websocket: WebSocket | null = null;
  private isConnected: boolean = false;
  private debounceTimer: number | null = null;
  private lastVersion: number = 0;
  private searchService: SearchService | null = null;

  // DOM Elements
  private elements: AppElements;

  constructor() {
    this.elements = this.initializeElements();
    this.bindEvents();
    this.loadApiKeyFromStorage();
  }

  private initializeElements(): AppElements {
    const getElementById = <T extends HTMLElement>(id: string): T => {
      const element = document.getElementById(id) as T;
      if (!element) {
        throw new Error(`Element with id '${id}' not found`);
      }
      return element;
    };

    return {
      // Main elements
      apiKeyInput: getElementById<HTMLInputElement>('apiKey'),
      connectBtn: getElementById<HTMLButtonElement>('connectBtn'),
      statusIndicator: getElementById<HTMLDivElement>('statusIndicator'),
      statusText: getElementById<HTMLSpanElement>('statusText'),
      notesList: getElementById<HTMLDivElement>('notesList'),
      newNoteTitle: getElementById<HTMLInputElement>('newNoteTitle'),
      createNoteBtn: getElementById<HTMLButtonElement>('createNoteBtn'),

      // Search elements
      searchContainer: getElementById<HTMLDivElement>('searchContainer'),
      searchInput: getElementById<HTMLInputElement>('searchInput'),
      searchBtn: getElementById<HTMLButtonElement>('searchBtn'),
      searchClearBtn: getElementById<HTMLButtonElement>('searchClearBtn'),
      searchResults: getElementById<HTMLDivElement>('searchResults'),
      searchFilters: getElementById<HTMLDivElement>('searchFilters'),
      searchStats: getElementById<HTMLDivElement>('searchStats'),
      searchHistory: getElementById<HTMLDivElement>('searchHistory'),
      searchSuggestions: getElementById<HTMLDivElement>('searchSuggestions'),

      // Editor elements
      noteTitle: getElementById<HTMLInputElement>('noteTitle'),
      markdownEditor: getElementById<HTMLTextAreaElement>('markdownEditor'),
      markdownPreview: getElementById<HTMLDivElement>('markdownPreview'),
      noteVersion: getElementById<HTMLSpanElement>('noteVersion'),
      deleteNoteBtn: getElementById<HTMLButtonElement>('deleteNoteBtn')
    };
  }

  private bindEvents(): void {
    // Connection events
    this.elements.connectBtn.addEventListener('click', () => this.toggleConnection());
    this.elements.apiKeyInput.addEventListener('keypress', (e: KeyboardEvent) => {
      if (e.key === 'Enter') this.toggleConnection();
    });

    // Note creation
    this.elements.createNoteBtn.addEventListener('click', () => this.createNote());
    this.elements.newNoteTitle.addEventListener('keypress', (e: KeyboardEvent) => {
      if (e.key === 'Enter') this.createNote();
    });

    // Editor events
    this.elements.noteTitle.addEventListener('input', () => this.debouncedSave());
    this.elements.markdownEditor.addEventListener('input', () => {
      this.updatePreview();
      this.debouncedSave();
    });

    // Delete note event
    this.elements.deleteNoteBtn.addEventListener('click', () => this.deleteCurrentNote());

    // Search event handlers
    document.addEventListener('searchResultSelected', (e: any) => {
      this.openNoteById(e.detail.noteId);
    });

    document.addEventListener('showNotification', (e: any) => {
      this.showNotification(e.detail.message, e.detail.type);
    });
  }

  private loadApiKeyFromStorage(): void {
    const stored = localStorage.getItem('realtime-notes-api-key');
    if (stored) {
      this.elements.apiKeyInput.value = stored;
    }
  }

  private saveApiKeyToStorage(): void {
    localStorage.setItem('realtime-notes-api-key', this.apiKey);
  }

  private async toggleConnection(): Promise<void> {
    if (this.isConnected) {
      this.disconnect();
    } else {
      await this.connect();
    }
  }

  private async connect(): Promise<void> {
    const apiKey = this.elements.apiKeyInput.value.trim();
    if (!apiKey) {
      this.showNotification('Please enter an API key', 'error');
      return;
    }

    this.apiKey = apiKey;
    this.saveApiKeyToStorage();

    try {
      this.updateConnectionStatus('connecting', 'Connecting...');
      this.elements.connectBtn.disabled = true;

      // Test API connection by fetching notes
      await this.fetchNotes();

      this.isConnected = true;
      this.updateConnectionStatus('connected', 'Connected');
      this.elements.connectBtn.textContent = 'Disconnect';
      this.elements.connectBtn.disabled = false;
      this.elements.apiKeyInput.disabled = true;

      // Initialize search service
      try {
        this.searchService = new SearchService(this.apiBaseUrl, this.apiKey);
        this.searchService.show();
      } catch (searchError) {
        console.error('Search service initialization error:', searchError);
        // Continue without search - connection is still successful
      }

      this.showNotification('Connected successfully!', 'success');
    } catch (error) {
      console.error('Connection error:', error);
      this.updateConnectionStatus('disconnected', 'Connection failed');
      this.elements.connectBtn.disabled = false;
      const message = error instanceof Error ? error.message : 'Unknown error';
      this.showNotification(`Connection failed: ${message}`, 'error');
    }
  }

  private disconnect(): void {
    this.isConnected = false;
    this.disconnectWebSocket();

    // Clean up search service
    if (this.searchService) {
      this.searchService.hide();
      this.searchService.destroy();
      this.searchService = null;
    }

    this.updateConnectionStatus('disconnected', 'Disconnected');
    this.elements.connectBtn.textContent = 'Connect';
    this.elements.apiKeyInput.disabled = false;
    this.clearEditor();
    this.clearNotesList();
  }

  private updateConnectionStatus(status: ConnectionStatus, text: string): void {
    this.elements.statusIndicator.className = `status-indicator ${status}`;
    this.elements.statusText.textContent = text;
  }

  private async fetchNotes(): Promise<Note[]> {
    const response = await fetch(`${this.apiBaseUrl}/v1/notes`, {
      headers: {
        'x-api-key': this.apiKey
      }
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.error?.message || 'Failed to fetch notes');
    }

    this.notes = await response.json() as Note[];
    this.renderNotesList();
    return this.notes;
  }

  private renderNotesList(): void {
    // Find the defaultNotesList element - it may not exist if already replaced
    let defaultNotesList = document.getElementById('defaultNotesList');
    if (!defaultNotesList) {
      // If it doesn't exist, we need to work with notesList directly
      // but preserve search results if they exist
      const searchResults = document.getElementById('searchResults');
      if (searchResults) {
        // Temporarily remove search results to preserve them
        searchResults.remove();
      }

      // Clear and add defaultNotesList back
      this.elements.notesList.innerHTML = '';
      defaultNotesList = document.createElement('div');
      defaultNotesList.id = 'defaultNotesList';
      this.elements.notesList.appendChild(defaultNotesList);

      // Re-add search results if they existed
      if (searchResults) {
        this.elements.notesList.insertBefore(searchResults, defaultNotesList);
      }
    }

    if (this.notes.length === 0) {
      defaultNotesList.innerHTML = `
        <div class="empty-state">
          <i class="fas fa-sticky-note"></i>
          <p>No notes yet. Create your first note!</p>
        </div>
      `;
      return;
    }

    defaultNotesList.innerHTML = this.notes.map(note => `
      <div class="card card-interactive note-item" data-note-id="${note.note_id}" onclick="app.selectNote('${note.note_id}')">
        <div class="note-title">${this.escapeHtml(note.title || 'Untitled')}</div>
        <div class="note-preview">${this.escapeHtml(this.getPreview(note.content_md))}</div>
      </div>
    `).join('');
  }

  private getPreview(content: string): string {
    if (!content) return 'Empty note';
    return content.replace(/[#*`]/g, '').substring(0, 60) + (content.length > 60 ? '...' : '');
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  private clearNotesList(): void {
    // Find the defaultNotesList element
    let defaultNotesList = document.getElementById('defaultNotesList');
    if (!defaultNotesList) {
      // If it doesn't exist, clear everything and recreate structure
      this.elements.notesList.innerHTML = `
        <div id="searchResults" class="search-results">
          <div id="searchLoading" class="search-loading" style="display: none;">
            <i class="fas fa-spinner"></i>
            <p style="margin: 8px 0 0 0;">Searching...</p>
          </div>
          <div id="searchEmptyState" class="search-empty-state" style="display: none;">
            <i class="fas fa-search"></i>
            <p style="margin: 8px 0 0 0;">No results found</p>
            <p style="font-size: 11px; margin: 4px 0 0 0;">Try different keywords or adjust filters</p>
          </div>
          <div id="searchResultsList"></div>
        </div>
        <div id="defaultNotesList">
          <div class="empty-state">
            <i class="fas fa-sticky-note"></i>
            <p>Enter your API key to load notes</p>
          </div>
        </div>
      `;
    } else {
      defaultNotesList.innerHTML = `
        <div class="empty-state">
          <i class="fas fa-sticky-note"></i>
          <p>Enter your API key to load notes</p>
        </div>
      `;
    }
  }

  private async createNote(): Promise<void> {
    const title = this.elements.newNoteTitle.value.trim();
    if (!title) {
      this.showNotification('Please enter a note title', 'error');
      return;
    }

    try {
      const noteData: CreateNoteRequest = {
        title: title,
        content_md: '# ' + title + '\\n\\nStart writing your note here...'
      };

      const response = await fetch(`${this.apiBaseUrl}/v1/notes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': this.apiKey
        },
        body: JSON.stringify(noteData)
      });

      if (!response.ok) {
        const error: ApiError = await response.json();
        throw new Error(error.error?.message || 'Failed to create note');
      }

      const noteId: string = await response.json();
      this.elements.newNoteTitle.value = '';
      this.showNotification('Note created successfully!', 'success');

      // Refresh notes list and select the new note
      await this.fetchNotes();
      this.selectNote(noteId);
    } catch (error) {
      console.error('Create note error:', error);
      const message = error instanceof Error ? error.message : 'Unknown error';
      this.showNotification(`Failed to create note: ${message}`, 'error');
    }
  }

  public async selectNote(noteId: string): Promise<void> {
    try {
      // Disconnect from current note's WebSocket
      this.disconnectWebSocket();

      // Update UI to show selected note
      document.querySelectorAll('.note-item').forEach(item => {
        item.classList.remove('active', 'card-active');
      });
      const selectedItem = document.querySelector(`[data-note-id="${noteId}"]`);
      selectedItem?.classList.add('active', 'card-active');

      // Fetch note details
      const response = await fetch(`${this.apiBaseUrl}/v1/notes/${noteId}`, {
        headers: {
          'x-api-key': this.apiKey
        }
      });

      if (!response.ok) {
        const error: ApiError = await response.json();
        throw new Error(error.error?.message || 'Failed to fetch note');
      }

      this.currentNote = await response.json() as Note;
      this.loadNoteIntoEditor();
      this.connectWebSocket(noteId);
    } catch (error) {
      console.error('Select note error:', error);
      const message = error instanceof Error ? error.message : 'Unknown error';
      this.showNotification(`Failed to load note: ${message}`, 'error');
    }
  }

  /**
   * Open note by ID (used by search service)
   */
  private async openNoteById(noteId: string): Promise<void> {
    await this.selectNote(noteId);
  }

  private loadNoteIntoEditor(): void {
    if (!this.currentNote) return;

    this.elements.noteTitle.value = this.currentNote.title || '';
    this.elements.markdownEditor.value = this.currentNote.content_md || '';
    this.elements.noteVersion.textContent = this.currentNote.version.toString();
    this.lastVersion = this.currentNote.version;

    this.elements.noteTitle.disabled = false;
    this.elements.markdownEditor.disabled = false;
    this.elements.deleteNoteBtn.disabled = false;

    this.updatePreview();
  }

  private clearEditor(): void {
    this.currentNote = null;
    this.elements.noteTitle.value = '';
    this.elements.markdownEditor.value = '';
    this.elements.noteVersion.textContent = '-';
    this.elements.noteTitle.disabled = true;
    this.elements.markdownEditor.disabled = true;
    this.elements.deleteNoteBtn.disabled = true;

    this.elements.markdownPreview.innerHTML = `
      <div class="empty-state">
        <i class="fas fa-file-alt"></i>
        <p>Select a note to start editing</p>
      </div>
    `;
  }

  private updatePreview(): void {
    const markdown = this.elements.markdownEditor.value;
    if (!markdown.trim()) {
      this.elements.markdownPreview.innerHTML = `
        <div class="empty-state">
          <i class="fas fa-edit"></i>
          <p>Start typing to see preview</p>
        </div>
      `;
      return;
    }

    try {
      const html = window.marked.parse(markdown);
      this.elements.markdownPreview.innerHTML = html;

      // Highlight code blocks
      this.elements.markdownPreview.querySelectorAll('pre code').forEach((block) => {
        if (window.Prism) {
          window.Prism.highlightElement(block);
        }
      });
    } catch (error) {
      console.error('Preview error:', error);
      this.elements.markdownPreview.innerHTML = '<p>Preview error: Invalid markdown</p>';
    }
  }

  private connectWebSocket(noteId: string): void {
    if (this.websocket) {
      this.websocket.close();
    }

    try {
      const wsUrl = `${this.wsBaseUrl}/ws/notes/${noteId}?api_key=${encodeURIComponent(this.apiKey)}`;
      this.websocket = new WebSocket(wsUrl);

      this.websocket.onopen = () => {
        console.log('WebSocket connected');
        this.updateConnectionStatus('connected', 'Connected (Real-time)');
      };

      this.websocket.onmessage = (event: MessageEvent) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleWebSocketMessage(message);
        } catch (error) {
          console.error('WebSocket message error:', error);
        }
      };

      this.websocket.onclose = (event: CloseEvent) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        if (this.isConnected) {
          this.updateConnectionStatus('connected', 'Connected');
        }
      };

      this.websocket.onerror = (error: Event) => {
        console.error('WebSocket error:', error);
        this.showNotification('Real-time connection failed', 'error');
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.showNotification('Failed to establish real-time connection', 'error');
    }
  }

  private disconnectWebSocket(): void {
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
  }

  private handleWebSocketMessage(message: WebSocketMessage): void {
    console.log('WebSocket message:', message);

    switch (message.type) {
      case 'init': {
        const initMsg = message as InitMessage;
        this.currentNote = initMsg.data;
        this.loadNoteIntoEditor();
        break;
      }

      case 'update': {
        const updateMsg = message as UpdateMessage;
        this.elements.noteTitle.value = updateMsg.data.title || '';
        this.elements.markdownEditor.value = updateMsg.data.content_md || '';
        this.elements.noteVersion.textContent = updateMsg.data.version.toString();
        this.lastVersion = updateMsg.data.version;
        this.updatePreview();
        break;
      }

      case 'error': {
        const errorMsg = message as ErrorMessage;
        console.error('WebSocket error:', errorMsg.data);
        this.showNotification(`Real-time error: ${errorMsg.data.message}`, 'error');

        if (errorMsg.data.code === 'VERSION_MISMATCH' && this.currentNote) {
          // Reload the note to get the latest version
          this.selectNote(this.currentNote.note_id);
        }
        break;
      }

      default:
        console.log('Unknown WebSocket message type:', message.type);
    }
  }

  private debouncedSave(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    this.debounceTimer = setTimeout(() => {
      this.sendPatch();
    }, 500); // 500ms delay
  }

  private async sendPatch(): Promise<void> {
    if (!this.websocket || !this.currentNote || this.websocket.readyState !== WebSocket.OPEN) {
      return;
    }

    try {
      // Create patch data
      const currentContent = {
        title: this.elements.noteTitle.value,
        content_md: this.elements.markdownEditor.value
      };

      // Encode patch as base64 with proper Unicode support
      const jsonString = JSON.stringify(currentContent);
      const encoder = new TextEncoder();
      const uint8Array = encoder.encode(jsonString);
      const binaryString = String.fromCharCode(...uint8Array);
      const patchData = btoa(binaryString);

      const message: PatchMessage = {
        type: 'patch',
        data: {
          version: this.lastVersion,
          patch: patchData
        }
      };

      this.websocket.send(JSON.stringify(message));
    } catch (error) {
      console.error('Send patch error:', error);
      this.showNotification('Failed to send changes', 'error');
    }
  }

  private async deleteCurrentNote(): Promise<void> {
    if (!this.currentNote) {
      this.showNotification('No note selected', 'error');
      return;
    }

    if (!confirm(`Are you sure you want to delete "${this.currentNote.title}"?`)) {
      return;
    }

    try {
      const response = await fetch(`${this.apiBaseUrl}/v1/notes/${this.currentNote.note_id}`, {
        method: 'DELETE',
        headers: {
          'x-api-key': this.apiKey
        }
      });

      if (!response.ok) {
        const error: ApiError = await response.json();
        throw new Error(error.error?.message || 'Failed to delete note');
      }

      this.showNotification('Note deleted successfully!', 'success');
      this.clearEditor();
      this.disconnectWebSocket();
      await this.fetchNotes();
    } catch (error) {
      console.error('Delete note error:', error);
      const message = error instanceof Error ? error.message : 'Unknown error';
      this.showNotification(`Failed to delete note: ${message}`, 'error');
    }
  }

  private showNotification(message: string, type: NotificationType = 'info'): void {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, 3000);
  }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.app = new RealtimeNotesApp();
});