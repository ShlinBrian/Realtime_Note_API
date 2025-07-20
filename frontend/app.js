class RealtimeNotesApp {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000';
        this.wsBaseUrl = 'ws://localhost:8000';
        this.apiKey = '';
        this.currentNote = null;
        this.notes = [];
        this.websocket = null;
        this.isConnected = false;
        this.debounceTimer = null;
        this.lastVersion = 0;
        
        this.initializeElements();
        this.bindEvents();
        this.loadApiKeyFromStorage();
    }

    initializeElements() {
        // Main elements
        this.apiKeyInput = document.getElementById('apiKey');
        this.connectBtn = document.getElementById('connectBtn');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        this.notesList = document.getElementById('notesList');
        this.newNoteTitle = document.getElementById('newNoteTitle');
        this.createNoteBtn = document.getElementById('createNoteBtn');
        
        // Editor elements
        this.noteTitle = document.getElementById('noteTitle');
        this.markdownEditor = document.getElementById('markdownEditor');
        this.markdownPreview = document.getElementById('markdownPreview');
        this.noteVersion = document.getElementById('noteVersion');
        this.deleteNoteBtn = document.getElementById('deleteNoteBtn');
    }

    bindEvents() {
        // Connection events
        this.connectBtn.addEventListener('click', () => this.toggleConnection());
        this.apiKeyInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.toggleConnection();
        });

        // Note creation
        this.createNoteBtn.addEventListener('click', () => this.createNote());
        this.newNoteTitle.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.createNote();
        });

        // Editor events
        this.noteTitle.addEventListener('input', () => this.debouncedSave());
        this.markdownEditor.addEventListener('input', () => {
            this.updatePreview();
            this.debouncedSave();
        });
    }

    loadApiKeyFromStorage() {
        const stored = localStorage.getItem('realtime-notes-api-key');
        if (stored) {
            this.apiKeyInput.value = stored;
        }
    }

    saveApiKeyToStorage() {
        localStorage.setItem('realtime-notes-api-key', this.apiKey);
    }

    async toggleConnection() {
        if (this.isConnected) {
            this.disconnect();
        } else {
            await this.connect();
        }
    }

    async connect() {
        const apiKey = this.apiKeyInput.value.trim();
        if (!apiKey) {
            this.showNotification('Please enter an API key', 'error');
            return;
        }

        this.apiKey = apiKey;
        this.saveApiKeyToStorage();
        
        try {
            this.updateConnectionStatus('connecting', 'Connecting...');
            this.connectBtn.disabled = true;

            // Test API connection by fetching notes
            await this.fetchNotes();
            
            this.isConnected = true;
            this.updateConnectionStatus('connected', 'Connected');
            this.connectBtn.textContent = 'Disconnect';
            this.connectBtn.disabled = false;
            this.apiKeyInput.disabled = true;
            
            this.showNotification('Connected successfully!', 'success');
        } catch (error) {
            console.error('Connection error:', error);
            this.updateConnectionStatus('disconnected', 'Connection failed');
            this.connectBtn.disabled = false;
            this.showNotification(`Connection failed: ${error.message}`, 'error');
        }
    }

    disconnect() {
        this.isConnected = false;
        this.disconnectWebSocket();
        this.updateConnectionStatus('disconnected', 'Disconnected');
        this.connectBtn.textContent = 'Connect';
        this.apiKeyInput.disabled = false;
        this.clearEditor();
        this.clearNotesList();
    }

    updateConnectionStatus(status, text) {
        this.statusIndicator.className = `status-indicator ${status}`;
        this.statusText.textContent = text;
    }

    async fetchNotes() {
        const response = await fetch(`${this.apiBaseUrl}/v1/notes`, {
            headers: {
                'x-api-key': this.apiKey
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error?.message || 'Failed to fetch notes');
        }

        this.notes = await response.json();
        this.renderNotesList();
        return this.notes;
    }

    renderNotesList() {
        if (this.notes.length === 0) {
            this.notesList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-sticky-note"></i>
                    <p>No notes yet. Create your first note!</p>
                </div>
            `;
            return;
        }

        this.notesList.innerHTML = this.notes.map(note => `
            <div class="note-item" data-note-id="${note.note_id}" onclick="app.selectNote('${note.note_id}')">
                <div class="note-title">${this.escapeHtml(note.title || 'Untitled')}</div>
                <div class="note-preview">${this.escapeHtml(this.getPreview(note.content_md))}</div>
            </div>
        `).join('');
    }

    getPreview(content) {
        if (!content) return 'Empty note';
        return content.replace(/[#*`]/g, '').substring(0, 60) + (content.length > 60 ? '...' : '');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    clearNotesList() {
        this.notesList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-sticky-note"></i>
                <p>Enter your API key to load notes</p>
            </div>
        `;
    }

    async createNote() {
        const title = this.newNoteTitle.value.trim();
        if (!title) {
            this.showNotification('Please enter a note title', 'error');
            return;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/v1/notes`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': this.apiKey
                },
                body: JSON.stringify({
                    title: title,
                    content_md: '# ' + title + '\n\nStart writing your note here...'
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error?.message || 'Failed to create note');
            }

            const note = await response.json();
            this.newNoteTitle.value = '';
            this.showNotification('Note created successfully!', 'success');
            
            // Refresh notes list and select the new note
            await this.fetchNotes();
            this.selectNote(note.note_id);
        } catch (error) {
            console.error('Create note error:', error);
            this.showNotification(`Failed to create note: ${error.message}`, 'error');
        }
    }

    async selectNote(noteId) {
        try {
            // Disconnect from current note's WebSocket
            this.disconnectWebSocket();
            
            // Update UI to show selected note
            document.querySelectorAll('.note-item').forEach(item => {
                item.classList.remove('active');
            });
            document.querySelector(`[data-note-id="${noteId}"]`)?.classList.add('active');

            // Fetch note details
            const response = await fetch(`${this.apiBaseUrl}/v1/notes/${noteId}`, {
                headers: {
                    'x-api-key': this.apiKey
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error?.message || 'Failed to fetch note');
            }

            this.currentNote = await response.json();
            this.loadNoteIntoEditor();
            this.connectWebSocket(noteId);
        } catch (error) {
            console.error('Select note error:', error);
            this.showNotification(`Failed to load note: ${error.message}`, 'error');
        }
    }

    loadNoteIntoEditor() {
        if (!this.currentNote) return;

        this.noteTitle.value = this.currentNote.title || '';
        this.markdownEditor.value = this.currentNote.content_md || '';
        this.noteVersion.textContent = this.currentNote.version || 0;
        this.lastVersion = this.currentNote.version || 0;
        
        this.noteTitle.disabled = false;
        this.markdownEditor.disabled = false;
        
        this.updatePreview();
    }

    clearEditor() {
        this.currentNote = null;
        this.noteTitle.value = '';
        this.markdownEditor.value = '';
        this.noteVersion.textContent = '-';
        this.noteTitle.disabled = true;
        this.markdownEditor.disabled = true;
        
        this.markdownPreview.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-file-alt"></i>
                <p>Select a note to start editing</p>
            </div>
        `;
    }

    updatePreview() {
        const markdown = this.markdownEditor.value;
        if (!markdown.trim()) {
            this.markdownPreview.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-edit"></i>
                    <p>Start typing to see preview</p>
                </div>
            `;
            return;
        }

        try {
            const html = marked.parse(markdown);
            this.markdownPreview.innerHTML = html;
            
            // Highlight code blocks
            this.markdownPreview.querySelectorAll('pre code').forEach((block) => {
                Prism.highlightElement(block);
            });
        } catch (error) {
            console.error('Preview error:', error);
            this.markdownPreview.innerHTML = '<p>Preview error: Invalid markdown</p>';
        }
    }

    connectWebSocket(noteId) {
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

            this.websocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleWebSocketMessage(message);
                } catch (error) {
                    console.error('WebSocket message error:', error);
                }
            };

            this.websocket.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                if (this.isConnected) {
                    this.updateConnectionStatus('connected', 'Connected');
                }
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.showNotification('Real-time connection failed', 'error');
            };
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.showNotification('Failed to establish real-time connection', 'error');
        }
    }

    disconnectWebSocket() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
    }

    handleWebSocketMessage(message) {
        console.log('WebSocket message:', message);

        switch (message.type) {
            case 'init':
                // Server sent initial note state
                this.currentNote = message.data;
                this.loadNoteIntoEditor();
                break;

            case 'update':
                // Server sent note update from another client
                const data = message.data;
                this.noteTitle.value = data.title || '';
                this.markdownEditor.value = data.content_md || '';
                this.noteVersion.textContent = data.version || 0;
                this.lastVersion = data.version || 0;
                this.updatePreview();
                break;

            case 'error':
                const error = message.data;
                console.error('WebSocket error:', error);
                this.showNotification(`Real-time error: ${error.message}`, 'error');
                
                if (error.code === 'VERSION_MISMATCH') {
                    // Reload the note to get the latest version
                    this.selectNote(this.currentNote.note_id);
                }
                break;

            default:
                console.log('Unknown WebSocket message type:', message.type);
        }
    }

    debouncedSave() {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        this.debounceTimer = setTimeout(() => {
            this.sendPatch();
        }, 500); // 500ms delay
    }

    async sendPatch() {
        if (!this.websocket || !this.currentNote || this.websocket.readyState !== WebSocket.OPEN) {
            return;
        }

        try {
            // Create patch data
            const currentContent = {
                title: this.noteTitle.value,
                content_md: this.markdownEditor.value
            };

            // Encode patch as base64
            const patchData = btoa(JSON.stringify(currentContent));

            const message = {
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

    showNotification(message, type = 'info') {
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