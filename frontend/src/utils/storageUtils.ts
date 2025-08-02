import { Message } from '../types/Message';

export const STORAGE_KEYS = {
  CHAT_SESSION: 'chatSession',
  CHAT_MESSAGES: 'chatMessages',
  GLOBAL_THUMB_DOWN_COUNT: 'globalThumbDownCount',
  TOTAL_THUMB_UP_COUNT: 'totalThumbUpCount',
  TOTAL_THUMB_DOWN_COUNT: 'totalThumbDownCount',
} as const;

export interface SessionData {
  isLoggedIn: boolean;
  username: string;
  loginTime: string;
}

export const storageUtils = {
  // Session management
  saveSession: (sessionData: SessionData): void => {
    try {
      localStorage.setItem(STORAGE_KEYS.CHAT_SESSION, JSON.stringify(sessionData));
    } catch (error) {
      console.error('Error saving session:', error);
    }
  },

  getSession: (): SessionData | null => {
    try {
      const savedSession = localStorage.getItem(STORAGE_KEYS.CHAT_SESSION);
      return savedSession ? JSON.parse(savedSession) : null;
    } catch (error) {
      console.error('Error loading session:', error);
      localStorage.removeItem(STORAGE_KEYS.CHAT_SESSION);
      return null;
    }
  },

  clearSession: (): void => {
    localStorage.removeItem(STORAGE_KEYS.CHAT_SESSION);
    localStorage.removeItem(STORAGE_KEYS.CHAT_MESSAGES);
    localStorage.removeItem(STORAGE_KEYS.GLOBAL_THUMB_DOWN_COUNT);
    localStorage.removeItem(STORAGE_KEYS.TOTAL_THUMB_UP_COUNT);
    localStorage.removeItem(STORAGE_KEYS.TOTAL_THUMB_DOWN_COUNT);
  },

  // Message management
  saveMessages: (messages: Message[]): void => {
    try {
      if (messages.length > 0) {
        localStorage.setItem(STORAGE_KEYS.CHAT_MESSAGES, JSON.stringify(messages));
      }
    } catch (error) {
      console.error('Error saving messages:', error);
    }
  },

  getMessages: (): Message[] => {
    try {
      const savedMessages = localStorage.getItem(STORAGE_KEYS.CHAT_MESSAGES);
      if (savedMessages) {
        const parsedMessages = JSON.parse(savedMessages);
        // Convert timestamp strings back to Date objects
        return parsedMessages.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }));
      }
      return [];
    } catch (error) {
      console.error('Error loading messages:', error);
      return [];
    }
  },

  // Feedback counts (for future analytics)
  saveFeedbackCount: (key: string, count: number): void => {
    try {
      localStorage.setItem(key, count.toString());
    } catch (error) {
      console.error('Error saving feedback count:', error);
    }
  },

  getFeedbackCount: (key: string): number => {
    try {
      const count = localStorage.getItem(key);
      return count ? parseInt(count, 10) : 0;
    } catch (error) {
      console.error('Error loading feedback count:', error);
      return 0;
    }
  },
};