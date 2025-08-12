/**
 * Migration utilities for transitioning from localStorage to backend storage
 */

import { Conversation } from '../types/Conversation';

export interface LocalStorageData {
  conversations: Conversation[];
  hasLocalData: boolean;
}

/**
 * Check if there's conversation data in localStorage
 */
export const checkLocalStorageData = (): LocalStorageData => {
  try {
    const stored = localStorage.getItem('conversationHistory');
    if (stored) {
      const rawConversations = JSON.parse(stored);
      if (Array.isArray(rawConversations)) {
        // Convert raw objects to proper Conversation objects with Date types
        const conversations: Conversation[] = rawConversations.map((conv: any) => ({
          ...conv,
          createdAt: new Date(conv.createdAt),
          updatedAt: new Date(conv.updatedAt),
          messages: conv.messages?.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp),
          })) || [],
        }));
        
        return {
          conversations,
          hasLocalData: conversations.length > 0,
        };
      }
    }
  } catch (error) {
    console.error('Error checking localStorage data:', error);
  }
  
  return {
    conversations: [],
    hasLocalData: false,
  };
};

/**
 * Clear localStorage conversation data
 */
export const clearLocalStorageData = (): boolean => {
  try {
    localStorage.removeItem('conversationHistory');
    console.log('Successfully cleared localStorage conversation data');
    return true;
  } catch (error) {
    console.error('Error clearing localStorage data:', error);
    return false;
  }
};

/**
 * Get summary of localStorage data
 */
export const getLocalDataSummary = (): { 
  totalConversations: number; 
  totalMessages: number; 
  oldestDate?: Date; 
  newestDate?: Date;
} => {
  const { conversations } = checkLocalStorageData();
  
  if (conversations.length === 0) {
    return { totalConversations: 0, totalMessages: 0 };
  }

  let totalMessages = 0;
  let oldestDate: Date | undefined;
  let newestDate: Date | undefined;

  conversations.forEach((conv: Conversation) => {
    if (conv.messages && Array.isArray(conv.messages)) {
      totalMessages += conv.messages.length;
    }
    
    const createdAt = conv.createdAt;
    if (!oldestDate || createdAt < oldestDate) {
      oldestDate = createdAt;
    }
    if (!newestDate || createdAt > newestDate) {
      newestDate = createdAt;
    }
  });

  return {
    totalConversations: conversations.length,
    totalMessages,
    oldestDate,
    newestDate,
  };
};