import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { Conversation, ConversationSummary, ConversationFilter, ConversationHistoryState } from '../types/Conversation';
import { Message } from '../types/Message';

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

  // Load conversations from localStorage on mount
  useEffect(() => {
    const loadConversations = () => {
      try {
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
          setState(prev => ({ ...prev, conversations }));
        }
      } catch (error) {
        console.error('Error loading conversation history:', error);
      }
    };

    loadConversations();
  }, []);

  // Save conversations to localStorage whenever conversations change
  useEffect(() => {
    if (state.conversations.length > 0) {
      try {
        localStorage.setItem('conversationHistory', JSON.stringify(state.conversations));
      } catch (error) {
        console.error('Error saving conversation history:', error);
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
    return new Promise((resolve) => {
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

      resolve(conversationId);
    });
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
    return new Promise((resolve) => {
      setState(prev => ({
        ...prev,
        conversations: prev.conversations.filter(conv => conv.id !== conversationId),
        currentConversationId: prev.currentConversationId === conversationId ? null : prev.currentConversationId,
      }));
      resolve();
    });
  }, []);

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