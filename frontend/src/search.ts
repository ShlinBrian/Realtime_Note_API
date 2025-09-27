import type {
  SearchRequest,
  SearchResult,
  SearchResponse,
  SearchFilters,
  SearchState,
  SearchHistoryItem,
  SearchSuggestion,
  AutocompleteResponse,
  NotificationType
} from './types.js';

/**
 * Search Service for Vector-based Note Search
 * Handles API calls, state management, and UI interactions
 */
export class SearchService {
  private apiBaseUrl: string;
  private apiKey: string;
  private searchState: SearchState;
  private searchHistory: SearchHistoryItem[] = [];
  private maxHistoryItems = 10;
  private debounceTimer: number | null = null;
  private debounceMs = 300;
  private suggestionTimer: number | null = null;
  private suggestionMs = 150;
  private currentSuggestions: SearchSuggestion[] = [];
  private selectedSuggestionIndex = -1;

  // DOM elements
  private elements: {
    searchContainer: HTMLDivElement;
    searchInput: HTMLInputElement;
    searchBtn: HTMLButtonElement;
    searchClearBtn: HTMLButtonElement;
    searchResults: HTMLDivElement;
    searchResultsList: HTMLDivElement;
    searchLoading: HTMLDivElement;
    searchEmptyState: HTMLDivElement;
    searchFilters: HTMLDivElement;
    searchStats: HTMLDivElement;
    searchStatsText: HTMLSpanElement;
    searchHistory: HTMLDivElement;
    searchSuggestions: HTMLDivElement;
    filterTopK: HTMLInputElement;
    filterMinScore: HTMLInputElement;
    filterMinScoreValue: HTMLSpanElement;
    filterTitleOnly: HTMLInputElement;
    defaultNotesList: HTMLDivElement;
  } = {} as any;

  constructor(apiBaseUrl: string, apiKey: string) {
    this.apiBaseUrl = apiBaseUrl;
    this.apiKey = apiKey;

    // Initialize search state
    this.searchState = {
      query: '',
      isSearching: false,
      results: [],
      totalResults: 0,
      queryTimeMs: 0,
      error: null,
      filters: {
        min_score: 0,
        title_only: false
      },
      history: [],
      selectedResultId: null
    };

    this.initializeElements();
    this.bindEvents();
    this.loadSearchHistory();
  }

  /**
   * Initialize DOM element references
   */
  private initializeElements(): void {
    const getElementById = <T extends HTMLElement>(id: string): T => {
      const element = document.getElementById(id) as T;
      if (!element) {
        throw new Error(`Search element with id '${id}' not found`);
      }
      return element;
    };

    this.elements = {
      searchContainer: getElementById('searchContainer'),
      searchInput: getElementById('searchInput'),
      searchBtn: getElementById('searchBtn'),
      searchClearBtn: getElementById('searchClearBtn'),
      searchResults: getElementById('searchResults'),
      searchResultsList: getElementById('searchResultsList'),
      searchLoading: getElementById('searchLoading'),
      searchEmptyState: getElementById('searchEmptyState'),
      searchFilters: getElementById('searchFilters'),
      searchStats: getElementById('searchStats'),
      searchStatsText: getElementById('searchStatsText'),
      searchHistory: getElementById('searchHistory'),
      searchSuggestions: getElementById('searchSuggestions'),
      filterTopK: getElementById('filterTopK'),
      filterMinScore: getElementById('filterMinScore'),
      filterMinScoreValue: getElementById('filterMinScoreValue'),
      filterTitleOnly: getElementById('filterTitleOnly'),
      defaultNotesList: getElementById('defaultNotesList')
    };
  }

  /**
   * Bind event listeners to search interface elements
   */
  private bindEvents(): void {
    // Search input events
    this.elements.searchInput.addEventListener('input', (e) => {
      const query = (e.target as HTMLInputElement).value;
      this.handleSearchInput(query);
    });

    this.elements.searchInput.addEventListener('keydown', (e) => {
      this.handleSearchKeydown(e);
    });

    this.elements.searchInput.addEventListener('focus', () => {
      this.showSuggestionsForCurrentQuery();
    });

    this.elements.searchInput.addEventListener('blur', () => {
      // Delay hiding suggestions to allow clicking
      setTimeout(() => this.hideSuggestions(), 150);
    });

    // Search button events
    this.elements.searchBtn.addEventListener('click', () => {
      this.performSearch();
    });

    this.elements.searchClearBtn.addEventListener('click', () => {
      this.clearSearch();
    });

    // Filter events
    this.elements.filterMinScore.addEventListener('input', (e) => {
      const value = (e.target as HTMLInputElement).value;
      this.elements.filterMinScoreValue.textContent = `${value}+`;
      this.searchState.filters.min_score = parseFloat(value);
    });

    this.elements.filterTitleOnly.addEventListener('change', (e) => {
      this.searchState.filters.title_only = (e.target as HTMLInputElement).checked;
    });

    // Toggle filters
    document.getElementById('searchToggleFilters')?.addEventListener('click', () => {
      this.toggleFilters();
    });

    // Toggle history
    document.getElementById('searchToggleHistory')?.addEventListener('click', () => {
      this.toggleHistory();
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      // Ctrl/Cmd + K to focus search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        this.focusSearch();
      }

      // Escape to clear search
      if (e.key === 'Escape' && this.searchState.query) {
        this.clearSearch();
      }
    });
  }

  /**
   * Update API key for authentication
   */
  public updateApiKey(apiKey: string): void {
    this.apiKey = apiKey;
  }

  /**
   * Show search interface when connected
   */
  public show(): void {
    this.elements.searchContainer.style.display = 'block';
  }

  /**
   * Hide search interface when disconnected
   */
  public hide(): void {
    this.elements.searchContainer.style.display = 'none';
    this.clearSearch();
  }

  /**
   * Focus on search input
   */
  public focusSearch(): void {
    this.elements.searchInput.focus();
  }

  /**
   * Handle search input with debouncing
   */
  private handleSearchInput(query: string): void {
    this.searchState.query = query;

    // Show/hide clear button
    this.elements.searchClearBtn.style.display = query ? 'block' : 'none';

    // Clear existing debounce timer
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    // Auto-search with debounce (only for queries longer than 2 characters)
    if (query.length > 2) {
      this.debounceTimer = window.setTimeout(() => {
        this.performSearch();
      }, this.debounceMs);
    } else if (query.length === 0) {
      this.clearSearch();
    }

    // Show suggestions with shorter debounce
    this.debouncedShowSuggestions(query);
  }

  /**
   * Handle keyboard navigation in search input
   */
  private handleSearchKeydown(e: KeyboardEvent): void {
    const suggestionsVisible = this.elements.searchSuggestions.classList.contains('active');

    switch (e.key) {
      case 'Enter':
        e.preventDefault();
        if (suggestionsVisible && this.selectedSuggestionIndex >= 0) {
          const suggestion = this.currentSuggestions[this.selectedSuggestionIndex];
          if (suggestion) {
            this.selectSuggestion(suggestion);
          }
        } else {
          this.performSearch();
        }
        break;

      case 'ArrowDown':
        e.preventDefault();
        if (suggestionsVisible && this.currentSuggestions.length > 0) {
          this.selectedSuggestionIndex = Math.min(
            this.selectedSuggestionIndex + 1,
            this.currentSuggestions.length - 1
          );
          this.updateSuggestionSelection();
        }
        break;

      case 'ArrowUp':
        e.preventDefault();
        if (suggestionsVisible && this.currentSuggestions.length > 0) {
          this.selectedSuggestionIndex = Math.max(this.selectedSuggestionIndex - 1, -1);
          this.updateSuggestionSelection();
        }
        break;

      case 'Escape':
        this.hideSuggestions();
        break;

      case 'Tab':
        if (suggestionsVisible && this.selectedSuggestionIndex >= 0) {
          e.preventDefault();
          const suggestion = this.currentSuggestions[this.selectedSuggestionIndex];
          if (suggestion) {
            this.selectSuggestion(suggestion);
          }
        }
        break;
    }
  }

  /**
   * Show suggestions with debouncing
   */
  private debouncedShowSuggestions(query: string): void {
    if (this.suggestionTimer) {
      clearTimeout(this.suggestionTimer);
    }

    if (query.length >= 1) {
      this.suggestionTimer = window.setTimeout(() => {
        this.generateAndShowSuggestions(query);
      }, this.suggestionMs);
    } else {
      this.hideSuggestions();
    }
  }

  /**
   * Generate and display autocomplete suggestions
   */
  private async generateAndShowSuggestions(query: string): Promise<void> {
    const suggestions: SearchSuggestion[] = [];

    // Add suggestions from search history
    const historySuggestions = this.searchHistory
      .filter(item => item.query.toLowerCase().includes(query.toLowerCase()))
      .slice(0, 3)
      .map(item => ({
        type: 'recent' as const,
        text: item.query,
        context: `${item.resultCount} results`
      }));

    suggestions.push(...historySuggestions);

    // Add common search suggestions
    const commonSuggestions = this.getCommonSearchSuggestions(query);
    suggestions.push(...commonSuggestions);

    // Could add API-based suggestions here for note titles, etc.
    // const apiSuggestions = await this.fetchSuggestionsFromAPI(query);
    // suggestions.push(...apiSuggestions);

    this.currentSuggestions = suggestions.slice(0, 6); // Limit to 6 suggestions
    this.selectedSuggestionIndex = -1;
    this.renderSuggestions();
  }

  /**
   * Get common search term suggestions based on input
   */
  private getCommonSearchSuggestions(query: string): SearchSuggestion[] {
    const suggestions: SearchSuggestion[] = [];
    const lowerQuery = query.toLowerCase();

    // Programming-related suggestions
    const programmingTerms = [
      'javascript', 'typescript', 'python', 'react', 'vue', 'angular',
      'node.js', 'api', 'database', 'algorithm', 'data structure',
      'machine learning', 'ai', 'neural network', 'frontend', 'backend'
    ];

    // General productivity suggestions
    const productivityTerms = [
      'meeting notes', 'project planning', 'todo list', 'brainstorm',
      'research', 'documentation', 'ideas', 'notes', 'draft'
    ];

    const allTerms = [...programmingTerms, ...productivityTerms];

    allTerms
      .filter(term => term.includes(lowerQuery) && term !== lowerQuery)
      .slice(0, 3)
      .forEach(term => {
        suggestions.push({
          type: 'query',
          text: term,
          context: 'Suggested search'
        });
      });

    return suggestions;
  }

  /**
   * Show suggestions for current query (when focusing input)
   */
  private showSuggestionsForCurrentQuery(): void {
    const query = this.elements.searchInput.value.trim();
    if (query.length >= 1) {
      this.generateAndShowSuggestions(query);
    }
  }

  /**
   * Render suggestions in dropdown
   */
  private renderSuggestions(): void {
    if (this.currentSuggestions.length === 0) {
      this.hideSuggestions();
      return;
    }

    const suggestionsHtml = this.currentSuggestions
      .map((suggestion, index) => {
        const isSelected = index === this.selectedSuggestionIndex;
        const typeIcon = this.getSuggestionTypeIcon(suggestion.type);

        return `
          <div class="search-suggestion-item ${isSelected ? 'selected' : ''}" data-index="${index}">
            <div class="search-suggestion-type">
              <i class="${typeIcon}"></i> ${this.getSuggestionTypeLabel(suggestion.type)}
            </div>
            <div class="search-suggestion-text">${this.escapeHtml(suggestion.text)}</div>
            ${suggestion.context ? `<div class="search-suggestion-context">${this.escapeHtml(suggestion.context)}</div>` : ''}
          </div>
        `;
      })
      .join('');

    this.elements.searchSuggestions.innerHTML = suggestionsHtml;
    this.elements.searchSuggestions.classList.add('active');

    // Bind click events
    this.elements.searchSuggestions.querySelectorAll('.search-suggestion-item').forEach((item, index) => {
      item.addEventListener('click', () => {
        const suggestion = this.currentSuggestions[index];
        if (suggestion) {
          this.selectSuggestion(suggestion);
        }
      });
    });
  }

  /**
   * Get icon for suggestion type
   */
  private getSuggestionTypeIcon(type: string): string {
    switch (type) {
      case 'recent': return 'fas fa-history';
      case 'title': return 'fas fa-file-alt';
      case 'tag': return 'fas fa-tag';
      case 'query': return 'fas fa-search';
      default: return 'fas fa-lightbulb';
    }
  }

  /**
   * Get label for suggestion type
   */
  private getSuggestionTypeLabel(type: string): string {
    switch (type) {
      case 'recent': return 'Recent';
      case 'title': return 'Title';
      case 'tag': return 'Tag';
      case 'query': return 'Suggested';
      default: return 'Suggestion';
    }
  }

  /**
   * Select a suggestion and trigger search
   */
  private selectSuggestion(suggestion: SearchSuggestion): void {
    this.elements.searchInput.value = suggestion.text;
    this.searchState.query = suggestion.text;
    this.hideSuggestions();
    this.performSearch();
  }

  /**
   * Update visual selection of suggestions
   */
  private updateSuggestionSelection(): void {
    this.elements.searchSuggestions.querySelectorAll('.search-suggestion-item').forEach((item, index) => {
      item.classList.toggle('selected', index === this.selectedSuggestionIndex);
    });
  }

  /**
   * Hide suggestions dropdown
   */
  private hideSuggestions(): void {
    this.elements.searchSuggestions.classList.remove('active');
    this.selectedSuggestionIndex = -1;
  }

  /**
   * Perform vector search API call
   */
  private async performSearch(): Promise<void> {
    const query = this.searchState.query.trim();
    if (!query) return;

    this.setSearchState(true);
    this.showSearchResults();

    try {
      const searchRequest: SearchRequest = {
        query,
        top_k: parseInt(this.elements.filterTopK.value) || 10,
        filters: {
          ...this.searchState.filters,
          min_score: this.searchState.filters.min_score || 0
        }
      };

      const startTime = Date.now();
      const response = await fetch(`${this.apiBaseUrl}/v1/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': this.apiKey
        },
        body: JSON.stringify(searchRequest)
      });

      const responseTime = Date.now() - startTime;

      if (!response.ok) {
        throw new Error(`Search failed: ${response.status} ${response.statusText}`);
      }

      const searchResponse: SearchResponse = await response.json();

      // Update search state
      this.searchState.results = searchResponse.results;
      this.searchState.totalResults = searchResponse.total_results;
      this.searchState.queryTimeMs = responseTime;
      this.searchState.error = null;

      // Add to search history
      this.addToHistory(query, searchResponse.results.length);

      // Render results
      this.renderSearchResults();
      this.updateSearchStats();

      // Show notification for successful search
      this.showNotification(`Found ${searchResponse.results.length} results`, 'success');

    } catch (error) {
      console.error('Search error:', error);
      this.searchState.error = error instanceof Error ? error.message : 'Search failed';
      this.showNotification(`Search failed: ${this.searchState.error}`, 'error');
      this.renderSearchError();
    } finally {
      this.setSearchState(false);
    }
  }

  /**
   * Set searching state and update UI
   */
  private setSearchState(isSearching: boolean): void {
    this.searchState.isSearching = isSearching;

    // Update button states
    this.elements.searchBtn.disabled = isSearching;
    this.elements.searchInput.disabled = isSearching;

    // Show/hide loading
    this.elements.searchLoading.style.display = isSearching ? 'block' : 'none';

    if (isSearching) {
      this.elements.searchEmptyState.style.display = 'none';
      this.elements.searchResultsList.innerHTML = '';
    }
  }

  /**
   * Show search results container and hide default notes list
   */
  private showSearchResults(): void {
    this.elements.searchResults.classList.add('active');
    this.elements.defaultNotesList.style.display = 'none';
  }

  /**
   * Hide search results container and show default notes list
   */
  private hideSearchResults(): void {
    this.elements.searchResults.classList.remove('active');
    this.elements.defaultNotesList.style.display = 'block';
  }

  /**
   * Clear search and return to default view
   */
  private clearSearch(): void {
    this.searchState.query = '';
    this.searchState.results = [];
    this.searchState.selectedResultId = null;
    this.searchState.error = null;

    this.elements.searchInput.value = '';
    this.elements.searchClearBtn.style.display = 'none';
    this.elements.searchStats.classList.remove('visible');

    this.hideSearchResults();
    this.hideHistory();
  }

  /**
   * Render search results in the UI
   */
  private renderSearchResults(): void {
    const resultsContainer = this.elements.searchResultsList;

    if (this.searchState.results.length === 0) {
      this.elements.searchEmptyState.style.display = 'block';
      resultsContainer.innerHTML = '';
      return;
    }

    this.elements.searchEmptyState.style.display = 'none';

    resultsContainer.innerHTML = this.searchState.results
      .map(result => this.renderSearchResultItem(result))
      .join('');

    // Bind click events to result items
    resultsContainer.querySelectorAll('.search-result-item').forEach((item, index) => {
      item.addEventListener('click', () => {
        const result = this.searchState.results[index];
        if (result) {
          this.selectSearchResult(result);
        }
      });
    });
  }

  /**
   * Render individual search result item
   */
  private renderSearchResultItem(result: SearchResult): string {
    const similarity = (result.similarity_score * 100).toFixed(1);
    const snippet = this.highlightSearchTerms(result.snippet, this.searchState.query);
    const date = result.updated_at ? new Date(result.updated_at).toLocaleDateString() : '';

    return `
      <div class="search-result-item" data-note-id="${result.note_id}">
        <div class="search-result-header">
          <h4 class="search-result-title">${this.escapeHtml(result.title)}</h4>
          <span class="search-result-score">${similarity}%</span>
        </div>
        <p class="search-result-snippet">${snippet}</p>
        <div class="search-result-meta">
          <span class="search-result-date">${date}</span>
          <div class="search-result-actions">
            <button class="btn search-result-action btn-small">Open</button>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Highlight search terms in text content
   */
  private highlightSearchTerms(text: string, query: string): string {
    if (!query.trim()) return this.escapeHtml(text);

    const terms = query.toLowerCase().split(' ').filter(term => term.length > 1);
    let highlightedText = this.escapeHtml(text);

    terms.forEach(term => {
      const regex = new RegExp(`(${this.escapeRegex(term)})`, 'gi');
      highlightedText = highlightedText.replace(regex, '<mark>$1</mark>');
    });

    return highlightedText;
  }

  /**
   * Select a search result and trigger note opening
   */
  private selectSearchResult(result: SearchResult): void {
    this.searchState.selectedResultId = result.note_id;

    // Update selected state in UI
    this.elements.searchResultsList.querySelectorAll('.search-result-item').forEach(item => {
      item.classList.remove('selected');
    });

    const selectedItem = this.elements.searchResultsList.querySelector(
      `[data-note-id="${result.note_id}"]`
    );
    selectedItem?.classList.add('selected');

    // Trigger note opening (this would typically call the main app's openNote method)
    this.dispatchNoteOpenEvent(result.note_id);

    this.showNotification(`Opening "${result.title}"`, 'info');
  }

  /**
   * Dispatch custom event for note opening
   */
  private dispatchNoteOpenEvent(noteId: string): void {
    const event = new CustomEvent('searchResultSelected', {
      detail: { noteId },
      bubbles: true
    });
    document.dispatchEvent(event);
  }

  /**
   * Update search statistics display
   */
  private updateSearchStats(): void {
    const { results, totalResults, queryTimeMs, query } = this.searchState;
    const statsText = `${results.length} results for "${query}" (${queryTimeMs}ms)`;

    this.elements.searchStatsText.textContent = statsText;
    this.elements.searchStats.classList.add('visible');
  }

  /**
   * Render search error state
   */
  private renderSearchError(): void {
    this.elements.searchResultsList.innerHTML = `
      <div class="search-empty-state">
        <i class="fas fa-exclamation-triangle"></i>
        <p>Search Error</p>
        <p style="font-size: 11px; margin: 4px 0 0 0;">${this.searchState.error}</p>
      </div>
    `;

    this.elements.searchEmptyState.style.display = 'none';
  }

  /**
   * Toggle search filters visibility
   */
  private toggleFilters(): void {
    this.elements.searchFilters.classList.toggle('active');
  }

  /**
   * Toggle search history visibility
   */
  private toggleHistory(): void {
    this.elements.searchHistory.classList.toggle('active');

    if (this.elements.searchHistory.classList.contains('active')) {
      this.renderSearchHistory();
    }
  }

  /**
   * Hide search history
   */
  private hideHistory(): void {
    this.elements.searchHistory.classList.remove('active');
  }

  /**
   * Add query to search history
   */
  private addToHistory(query: string, resultCount: number): void {
    // Remove existing entry for same query
    this.searchHistory = this.searchHistory.filter(item => item.query !== query);

    // Add new entry at beginning
    this.searchHistory.unshift({
      query,
      timestamp: new Date().toISOString(),
      resultCount
    });

    // Limit history size
    if (this.searchHistory.length > this.maxHistoryItems) {
      this.searchHistory = this.searchHistory.slice(0, this.maxHistoryItems);
    }

    this.saveSearchHistory();
  }

  /**
   * Render search history items
   */
  private renderSearchHistory(): void {
    if (this.searchHistory.length === 0) {
      this.elements.searchHistory.innerHTML = `
        <div class="search-empty-state">
          <p style="font-size: 12px;">No recent searches</p>
        </div>
      `;
      return;
    }

    this.elements.searchHistory.innerHTML = this.searchHistory
      .map(item => `
        <div class="search-history-item" data-query="${this.escapeHtml(item.query)}">
          <span class="search-history-query">${this.escapeHtml(item.query)}</span>
          <span class="search-history-meta">${item.resultCount} results</span>
        </div>
      `)
      .join('');

    // Bind click events
    this.elements.searchHistory.querySelectorAll('.search-history-item').forEach(item => {
      item.addEventListener('click', () => {
        const query = item.getAttribute('data-query');
        if (query) {
          this.elements.searchInput.value = query;
          this.searchState.query = query;
          this.hideHistory();
          this.performSearch();
        }
      });
    });
  }

  /**
   * Save search history to localStorage
   */
  private saveSearchHistory(): void {
    try {
      localStorage.setItem('realtimeNotes_searchHistory', JSON.stringify(this.searchHistory));
    } catch (error) {
      console.warn('Failed to save search history:', error);
    }
  }

  /**
   * Load search history from localStorage
   */
  private loadSearchHistory(): void {
    try {
      const stored = localStorage.getItem('realtimeNotes_searchHistory');
      if (stored) {
        this.searchHistory = JSON.parse(stored);
      }
    } catch (error) {
      console.warn('Failed to load search history:', error);
      this.searchHistory = [];
    }
  }

  /**
   * Show notification message
   */
  private showNotification(message: string, type: NotificationType): void {
    const event = new CustomEvent('showNotification', {
      detail: { message, type },
      bubbles: true
    });
    document.dispatchEvent(event);
  }

  /**
   * Utility function to escape HTML
   */
  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Utility function to escape regex special characters
   */
  private escapeRegex(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  /**
   * Get current search state (for debugging/integration)
   */
  public getSearchState(): SearchState {
    return { ...this.searchState };
  }

  /**
   * Clean up resources
   */
  public destroy(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    if (this.suggestionTimer) {
      clearTimeout(this.suggestionTimer);
    }

    // Save current state
    this.saveSearchHistory();
  }
}