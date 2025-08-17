import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { Conversation, ConversationSummary, ConversationFilter, ConversationHistoryState } from '../types/Conversation';
import { Message } from '../types/Message';
import conversationService from '../services/conversationService';
import authService from '../services/authService';

interface ConversationHistoryContextType {
  state: ConversationHistoryState;
  saveConversation: (messages: Message[], username: string, language: 'en' | 'ja') => Promise<string>;
  updateCurrentConversation: (messages: Message[], username: string, language: 'en' | 'ja') => Promise<string>;
  loadConversation: (conversationId: string) => Promise<Conversation | null>;
  deleteConversation: (conversationId: string) => Promise<void>;
  getConversationSummaries: () => ConversationSummary[];
  setFilter: (filter: Partial<ConversationFilter>) => void;
  clearFilter: () => void;
  searchConversations: (query: string) => ConversationSummary[];
  setCurrentConversation: (conversationId: string | null) => void;
  startNewConversation: () => void;
  clearLocalStorage: () => void;
  syncWithBackend: () => Promise<void>;
  refreshConversations: () => Promise<void>;
}

const ConversationHistoryContext = createContext<ConversationHistoryContextType | undefined>(undefined);

interface ConversationHistoryProviderProps {
  children: ReactNode;
}

export const ConversationHistoryProvider: React.FC<ConversationHistoryProviderProps> = ({ children }) => {
  const [state, setState] = useState<ConversationHistoryState>({
    conversations: [],
    currentConversationId: null,
    isLoading: false,
    filter: {},
  });

  // Load conversations based on authentication status
  useEffect(() => {
    const loadConversations = async () => {
      setState(prev => ({ ...prev, isLoading: true }));

      if (authService.isAuthenticated()) {
        try {
          console.log('User authenticated, loading from backend');
          const response = await conversationService.getConversations(1, 100);
          
          const conversations = response.results.map((backendConv: any) => 
            conversationService.convertToFrontendFormat(backendConv)
          );

          setState(prev => ({ 
            ...prev, 
            conversations,
            isLoading: false 
          }));
          
          console.log(`Loaded ${conversations.length} conversations from backend`);
          
          // Clear localStorage when using backend to avoid confusion
          try {
            localStorage.removeItem('conversationHistory');
            console.log('Cleared localStorage conversation history after loading from backend');
            
            // Also clear current conversation cache if it no longer exists in backend
            const currentConversationId = localStorage.getItem('currentConversationId');
            if (currentConversationId) {
              const conversationExists = conversations.some(conv => conv.id === currentConversationId);
              if (!conversationExists) {
                localStorage.removeItem('currentConversationId');
                localStorage.removeItem('chatMessages');
                console.log('Cleared stale current conversation cache - conversation no longer exists in backend');
              }
            }
          } catch (error) {
            console.error('Error clearing localStorage:', error);
          }
        } catch (error) {
          console.error('Error loading conversation history from backend:', error);
          setState(prev => ({ ...prev, isLoading: false }));
        }
      } else {
        try {
          console.log('User not authenticated, loading from localStorage');
          const stored = localStorage.getItem('conversationHistory');
          if (stored) {
            const parsed = JSON.parse(stored);
            const conversations = parsed.map((conv: any) => ({
              ...conv,
              createdAt: new Date(conv.createdAt),
              updatedAt: new Date(conv.updatedAt),
              messages: conv.messages.map((msg: any) => ({
                ...msg,
                timestamp: new Date(msg.timestamp),
              })),
            }));
            setState(prev => ({ 
              ...prev, 
              conversations,
              isLoading: false 
            }));
            console.log(`Loaded ${conversations.length} conversations from localStorage`);
          } else {
            setState(prev => ({ ...prev, isLoading: false }));
          }
        } catch (error) {
          console.error('Error loading from localStorage:', error);
          setState(prev => ({ ...prev, isLoading: false }));
        }
      }
    };

    loadConversations();
  }, []); // Run once on mount
  
  // Auto-refresh conversations from backend periodically when authenticated
  useEffect(() => {
    if (!authService.isAuthenticated()) return;
    
    const refreshInterval = setInterval(async () => {
      try {
        console.log('Auto-refreshing conversations from backend');
        const response = await conversationService.getConversations(1, 100);
        
        const backendConversations = response.results.map((backendConv: any) => 
          conversationService.convertToFrontendFormat(backendConv)
        );

        setState(prev => ({ 
          ...prev, 
          conversations: backendConversations
        }));
        
        // Check if current conversation cache is stale during auto-refresh
        try {
          const currentConversationId = localStorage.getItem('currentConversationId');
          if (currentConversationId) {
            const conversationExists = backendConversations.some(conv => conv.id === currentConversationId);
            if (!conversationExists) {
              localStorage.removeItem('currentConversationId');
              localStorage.removeItem('chatMessages');
              console.log('Auto-refresh: Cleared stale current conversation cache');
            }
          }
        } catch (error) {
          console.error('Error checking conversation cache during auto-refresh:', error);
        }
        
        console.log(`Auto-refresh: ${backendConversations.length} conversations from backend`);
      } catch (error) {
        console.error('Error during auto-refresh:', error);
      }
    }, 30000); // Refresh every 30 seconds

    return () => clearInterval(refreshInterval);
  }, []); // Set up once on mount

  // Keep localStorage as backup only (deprecated - now using backend)
  useEffect(() => {
    if (state.conversations.length > 0 && !authService.isAuthenticated()) {
      try {
        // Only save to localStorage for unauthenticated users as fallback
        localStorage.setItem('conversationHistory', JSON.stringify(state.conversations));
      } catch (error) {
        console.error('Error saving conversation history to localStorage:', error);
      }
    }
  }, [state.conversations]);

  const generateConversationTitle = useCallback((messages: Message[], language: 'en' | 'ja'): string => {
    if (messages.length === 0) {
      return language === 'ja' ? '新しい会話' : 'New Conversation';
    }

    // Find first user message
    const firstUserMessage = messages.find(msg => msg.sender === 'user');
    if (firstUserMessage && firstUserMessage.text.length > 0) {
      // Use first 30 characters of first user message as title
      return firstUserMessage.text.length > 30 
        ? firstUserMessage.text.substring(0, 30) + '...'
        : firstUserMessage.text;
    }

    // Fallback to date-based title
    const date = new Date().toLocaleDateString(language === 'ja' ? 'ja-JP' : 'en-US');
    return language === 'ja' ? `会話 - ${date}` : `Conversation - ${date}`;
  }, []);

  const saveConversation = useCallback(async (messages: Message[], username: string, language: 'en' | 'ja'): Promise<string> => {
    try {
      const title = generateConversationTitle(messages, language);
      
      if (!authService.isAuthenticated()) {
        // Fallback to localStorage for unauthenticated users
        const conversationId = Date.now().toString();
        const lastMessage = messages.length > 0 ? messages[messages.length - 1].text : undefined;

        const conversation: Conversation = {
          id: conversationId,
          title,
          messages: [...messages],
          createdAt: new Date(),
          updatedAt: new Date(),
          username,
          language,
          messageCount: messages.length,
          lastMessage,
        };

        setState(prev => ({
          ...prev,
          conversations: [conversation, ...prev.conversations],
          currentConversationId: conversationId,
        }));

        return conversationId;
      }

      // Create conversation in backend
      const backendConv = await conversationService.createConversation({
        title,
        is_active: true,
      });

      // Add messages to the conversation using UUID
      for (const message of messages) {
        await conversationService.addMessage(
          backendConv.id,  // Backend now returns UUID as id field
          message.text,
          message.sender === 'user' ? 'user' : 'bot'
        );
      }

      // Get the full conversation with messages using UUID
      const fullConversation = await conversationService.getConversation(backendConv.id);
      const frontendConv = conversationService.convertToFrontendFormat(fullConversation);
      frontendConv.username = username;
      frontendConv.language = language;

      setState(prev => ({
        ...prev,
        conversations: [frontendConv, ...prev.conversations],
        currentConversationId: backendConv.id,
      }));

      console.log(`Saved conversation to backend: ${backendConv.id}`);
      return backendConv.id;
    } catch (error) {
      console.error('Error saving conversation to backend:', error);
      
      // Fallback to localStorage
      const conversationId = Date.now().toString();
      const title = generateConversationTitle(messages, language);
      const lastMessage = messages.length > 0 ? messages[messages.length - 1].text : undefined;

      const conversation: Conversation = {
        id: conversationId,
        title,
        messages: [...messages],
        createdAt: new Date(),
        updatedAt: new Date(),
        username,
        language,
        messageCount: messages.length,
        lastMessage,
      };

      setState(prev => ({
        ...prev,
        conversations: [conversation, ...prev.conversations],
        currentConversationId: conversationId,
      }));

      return conversationId;
    }
  }, [generateConversationTitle]);

  const updateCurrentConversation = useCallback(async (messages: Message[], username: string, language: 'en' | 'ja'): Promise<string> => {
    const currentId = state.currentConversationId;
    
    if (currentId) {
      // Update existing conversation
      const title = generateConversationTitle(messages, language);
      const lastMessage = messages.length > 0 ? messages[messages.length - 1].text : undefined;

      setState(prev => ({
        ...prev,
        conversations: prev.conversations.map(conv => 
          conv.id === currentId 
            ? {
                ...conv,
                title,
                messages: [...messages],
                updatedAt: new Date(),
                username,
                language,
                messageCount: messages.length,
                lastMessage,
              }
            : conv
        ),
      }));

      return currentId;
    } else {
      // No current conversation, create new one
      const newId = await saveConversation(messages, username, language);
      return newId;
    }
  }, [state.currentConversationId, generateConversationTitle, saveConversation]);

  const loadConversation = useCallback(async (conversationId: string): Promise<Conversation | null> => {
    return new Promise((resolve) => {
      const conversation = state.conversations.find(conv => conv.id === conversationId);
      if (conversation) {
        setState(prev => ({
          ...prev,
          currentConversationId: conversationId,
        }));
      }
      resolve(conversation || null);
    });
  }, [state.conversations]);

  const deleteConversation = useCallback(async (conversationId: string): Promise<void> => {
    try {
      console.log(`Attempting to delete conversation with ID: ${conversationId}`);
      
      // Find the conversation to check its origin
      const conversation = state.conversations.find(conv => conv.id === conversationId);
      console.log('Conversation to delete:', conversation);
      
      if (authService.isAuthenticated()) {
        // Check if this is a timestamp-based ID (localStorage conversation)
        const isTimestampId = /^\d{13}$/.test(conversationId); // 13-digit timestamp
        
        if (isTimestampId) {
          console.log('Detected localStorage conversation (timestamp ID), skipping backend delete');
        } else {
          console.log('Deleting from backend with ID:', conversationId);
          // Delete from backend - handle both UUID strings and integer IDs
          await conversationService.deleteConversation(conversationId);
          console.log(`Deleted conversation from backend: ${conversationId}`);
          
          // Immediately refresh conversations from backend after successful deletion
          try {
            const response = await conversationService.getConversations(1, 100);
            const updatedConversations = response.results.map((backendConv: any) => 
              conversationService.convertToFrontendFormat(backendConv)
            );
            console.log(`Refreshed conversations after deletion: ${updatedConversations.length} total`);
            
            // Update state with fresh backend data
            setState(prev => ({
              ...prev,
              conversations: updatedConversations,
              currentConversationId: prev.currentConversationId === conversationId ? null : prev.currentConversationId,
            }));
            
            return; // Exit early since we've updated state with fresh data
          } catch (refreshError) {
            console.error('Failed to refresh conversations after deletion:', refreshError);
            // Fall through to manual state update as fallback
          }
        }
      } else {
        // For unauthenticated users, only handle localStorage conversations
        console.log('User not authenticated, only deleting from localStorage');
      }
      
      // Update local state
      setState(prev => ({
        ...prev,
        conversations: prev.conversations.filter(conv => conv.id !== conversationId),
        currentConversationId: prev.currentConversationId === conversationId ? null : prev.currentConversationId,
      }));
    } catch (error) {
      console.error('Error deleting conversation from backend:', error);
      console.error('Failed conversation ID:', conversationId);
      
      // Still update local state even if backend fails
      setState(prev => ({
        ...prev,
        conversations: prev.conversations.filter(conv => conv.id !== conversationId),
        currentConversationId: prev.currentConversationId === conversationId ? null : prev.currentConversationId,
      }));
      
      throw error; // Let the UI handle the error
    }
  }, [state.conversations]);

  const getConversationSummaries = useCallback((): ConversationSummary[] => {
    let filtered = state.conversations;

    // Apply filters
    if (state.filter.username) {
      filtered = filtered.filter(conv => conv.username.toLowerCase().includes(state.filter.username!.toLowerCase()));
    }

    if (state.filter.language) {
      filtered = filtered.filter(conv => conv.language === state.filter.language);
    }

    if (state.filter.dateRange) {
      filtered = filtered.filter(conv => 
        conv.createdAt >= state.filter.dateRange!.start && 
        conv.createdAt <= state.filter.dateRange!.end
      );
    }

    if (state.filter.searchQuery) {
      const query = state.filter.searchQuery.toLowerCase();
      filtered = filtered.filter(conv => 
        conv.title.toLowerCase().includes(query) ||
        conv.lastMessage?.toLowerCase().includes(query) ||
        conv.messages.some(msg => msg.text.toLowerCase().includes(query))
      );
    }

    // Convert to summaries and sort by updatedAt descending
    return filtered
      .map(conv => ({
        id: conv.id,
        title: conv.title,
        createdAt: conv.createdAt,
        updatedAt: conv.updatedAt,
        username: conv.username,
        language: conv.language,
        messageCount: conv.messageCount,
        lastMessage: conv.lastMessage,
      }))
      .sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime());
  }, [state.conversations, state.filter]);

  const setFilter = useCallback((filter: Partial<ConversationFilter>) => {
    setState(prev => ({
      ...prev,
      filter: { ...prev.filter, ...filter },
    }));
  }, []);

  const clearFilter = useCallback(() => {
    setState(prev => ({
      ...prev,
      filter: {},
    }));
  }, []);

  const searchConversations = useCallback((query: string): ConversationSummary[] => {
    const searchFilter = { ...state.filter, searchQuery: query };
    const searchResults = state.conversations.filter(conv => {
      const lowerQuery = query.toLowerCase();
      return conv.title.toLowerCase().includes(lowerQuery) ||
             conv.lastMessage?.toLowerCase().includes(lowerQuery) ||
             conv.messages.some(msg => msg.text.toLowerCase().includes(lowerQuery));
    });

    return searchResults
      .map(conv => ({
        id: conv.id,
        title: conv.title,
        createdAt: conv.createdAt,
        updatedAt: conv.updatedAt,
        username: conv.username,
        language: conv.language,
        messageCount: conv.messageCount,
        lastMessage: conv.lastMessage,
      }))
      .sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime());
  }, [state.conversations, state.filter]);

  const setCurrentConversation = useCallback((conversationId: string | null) => {
    setState(prev => ({
      ...prev,
      currentConversationId: conversationId,
    }));
  }, []);

  const startNewConversation = useCallback(() => {
    setState(prev => ({
      ...prev,
      currentConversationId: null,
    }));
  }, []);

  const clearLocalStorage = useCallback(() => {
    try {
      localStorage.removeItem('conversationHistory');
      console.log('Cleared localStorage conversation history');
    } catch (error) {
      console.error('Error clearing localStorage:', error);
    }
  }, []);

  const syncWithBackend = useCallback(async () => {
    if (!authService.isAuthenticated()) {
      console.log('User not authenticated, cannot sync with backend');
      return;
    }

    try {
      setState(prev => ({ ...prev, isLoading: true }));
      const response = await conversationService.getConversations(1, 100);
      
      const conversations = response.results.map((backendConv: any) => 
        conversationService.convertToFrontendFormat(backendConv)
      );

      setState(prev => ({ 
        ...prev, 
        conversations,
        isLoading: false 
      }));
      
      console.log(`Synced ${conversations.length} conversations with backend`);
    } catch (error) {
      console.error('Error syncing with backend:', error);
      setState(prev => ({ ...prev, isLoading: false }));
    }
  }, []);

  const refreshConversations = useCallback(async () => {
    if (!authService.isAuthenticated()) {
      console.log('User not authenticated, skipping refresh');
      return;
    }

    try {
      console.log('🔄 Refreshing conversations immediately...');
      const response = await conversationService.getConversations(1, 100);
      
      const backendConversations = response.results.map((backendConv: any) => 
        conversationService.convertToFrontendFormat(backendConv)
      );

      setState(prev => ({ 
        ...prev, 
        conversations: backendConversations
      }));
      
      // Check if current conversation cache is stale during refresh
      try {
        const currentConversationId = localStorage.getItem('currentConversationId');
        if (currentConversationId) {
          const conversationExists = backendConversations.some(conv => conv.id === currentConversationId);
          if (!conversationExists) {
            localStorage.removeItem('currentConversationId');
            localStorage.removeItem('chatMessages');
            console.log('Refresh: Cleared stale current conversation cache');
          }
        }
      } catch (error) {
        console.error('Error checking conversation cache during refresh:', error);
      }
      
      console.log(`✅ Immediate refresh: ${backendConversations.length} conversations loaded`);
    } catch (error) {
      console.error('Error during immediate conversation refresh:', error);
    }
  }, []);

  const contextValue: ConversationHistoryContextType = {
    state,
    saveConversation,
    updateCurrentConversation,
    loadConversation,
    deleteConversation,
    getConversationSummaries,
    setFilter,
    clearFilter,
    searchConversations,
    setCurrentConversation,
    startNewConversation,
    clearLocalStorage,
    syncWithBackend,
    refreshConversations,
  };

  return (
    <ConversationHistoryContext.Provider value={contextValue}>
      {children}
    </ConversationHistoryContext.Provider>
  );
};

export const useConversationHistory = () => {
  const context = useContext(ConversationHistoryContext);
  if (context === undefined) {
    throw new Error('useConversationHistory must be used within a ConversationHistoryProvider');
  }
  return context;
};