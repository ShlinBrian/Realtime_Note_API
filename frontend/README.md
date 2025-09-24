# Realtime Notes Frontend

A collaborative Markdown editor built with TypeScript that connects to the Realtime Notes API for real-time multi-user editing.

## Features

- **Real-time Collaboration**: Multiple users can edit the same note simultaneously
- **Live Markdown Preview**: See your formatted content as you type
- **Dark Theme**: Developer-friendly dark interface
- **API Key Authentication**: Secure connection to the backend
- **Note Management**: Create, edit, delete, and switch between notes
- **WebSocket Connection**: Real-time updates with automatic conflict resolution
- **Type Safety**: Built with TypeScript for better developer experience

## Quick Start

1. **Start the API server**:
   ```bash
   cd ..
   make run
   ```

2. **Build and serve the frontend**:
   ```bash
   # Install dependencies
   npm install

   # Build TypeScript
   npm run build

   # Serve the frontend
   npm run serve
   ```

   Or for development with file watching:
   ```bash
   npm run dev
   ```

3. **Get your API key**:
   ```bash
   # From the project root
   cat local_api_key.txt
   ```

4. **Open the app**: Navigate to `http://localhost:8080` and enter your API key

## Usage

### Authentication
1. Enter your API key in the sidebar
2. Click "Connect" to establish connection with the API
3. The status indicator will show green when connected

### Creating Notes
1. Enter a title in the "New note title" field
2. Click "Create" or press Enter
3. The note will be created and automatically selected

### Editing Notes
1. Click on any note in the sidebar to select it
2. Edit the title in the header input field
3. Type Markdown content in the left editor pane
4. See the live preview in the right pane
5. Changes are automatically saved with a 500ms debounce

### Real-time Collaboration
1. Open the same note in multiple browser windows/tabs
2. Edit in one window and see changes appear in others instantly
3. Version conflicts are automatically resolved by the server

## Technical Details

### WebSocket Protocol

The frontend communicates with the backend using WebSocket connections at `/ws/notes/{note_id}`.

**Message Types:**

1. **init** (server → client): Initial note state when connecting
   ```json
   {
     "type": "init",
     "data": {
       "note_id": "uuid",
       "title": "Note Title",
       "content_md": "# Markdown content",
       "version": 1
     }
   }
   ```

2. **patch** (client → server): Send changes to the server
   ```json
   {
     "type": "patch", 
     "data": {
       "version": 1,
       "patch": "base64-encoded-json-content"
     }
   }
   ```

3. **update** (server → client): Broadcast changes to all connected clients
   ```json
   {
     "type": "update",
     "data": {
       "title": "Updated Title",
       "content_md": "Updated content",
       "version": 2
     }
   }
   ```

4. **error** (server → client): Error notifications
   ```json
   {
     "type": "error",
     "data": {
       "code": "VERSION_MISMATCH",
       "message": "Note version mismatch",
       "current_version": 2
     }
   }
   ```

### File Structure

```
frontend/
├── src/
│   ├── app.ts         # Main TypeScript application logic
│   └── types.ts       # Type definitions and interfaces
├── dist/              # Compiled JavaScript (generated)
├── index.html         # Main HTML structure
├── package.json       # npm configuration and scripts
├── tsconfig.json      # TypeScript configuration
└── README.md          # This file
```

### Dependencies

**Runtime Dependencies:**
- **Marked**: Markdown parsing and rendering (CDN + npm)

**Development Dependencies:**
- **TypeScript**: Type-safe JavaScript compilation

**CDN Libraries:**
- **Prism**: Syntax highlighting for code blocks
- **Font Awesome**: Icons
- **Prism Tomorrow Theme**: Code syntax theme

### Development

#### Prerequisites
- Node.js (v16 or higher)
- npm

#### Available Scripts
- `npm run build`: Compile TypeScript to JavaScript
- `npm run watch`: Watch for changes and recompile automatically
- `npm run serve`: Start HTTP server on port 8080
- `npm run dev`: Build and serve (development workflow)

#### Browser Compatibility

- Modern browsers with WebSocket and ES2018 support
- TypeScript compiles to ES2018 for broad compatibility
- Modules are loaded as ES modules

## Configuration

### API Endpoints

The frontend connects to these endpoints:
- **REST API**: `http://localhost:8000/v1/notes`
- **WebSocket**: `ws://localhost:8000/ws/notes/{note_id}`

To change the backend URL, modify these variables in `app.js`:
```javascript
this.apiBaseUrl = 'http://localhost:8000';
this.wsBaseUrl = 'ws://localhost:8000';
```

### Local Storage

The app stores your API key in browser localStorage for convenience. Clear browser data to reset.

## Troubleshooting

### Connection Issues
- Ensure the API server is running on port 8000
- Check that your API key is valid
- Verify CORS is enabled on the backend (it is by default)

### WebSocket Issues
- WebSocket connections require the note to exist
- Version mismatches will trigger automatic reload
- Connection status is shown in the header

### Performance
- The app debounces changes (500ms) to avoid excessive API calls
- Large notes may take longer to sync
- Browser console shows detailed WebSocket activity for debugging