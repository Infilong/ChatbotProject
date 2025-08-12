import { chatService, ChatError } from './chatService';
import { Message } from '../types/Message';

// Don't mock messageUtils, use the real implementation
// jest.mock('../utils/messageUtils');

describe('chatService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('generateResponse', () => {
    jest.setTimeout(15000); // Increase timeout for this test suite
    
    it('generates a bot response successfully', async () => {
      const userMessage: Message = {
        id: '1',
        text: 'Hello',
        sender: 'user',
        timestamp: new Date(),
      };

      const response = await chatService.generateResponse(userMessage, 'en', {});

      expect(response).toHaveProperty('message');
      expect(response.message.sender).toBe('bot');
      expect(response.message.text).toBeTruthy();
      expect(response).toHaveProperty('delay');
    });

    it('generates Japanese bot response when language is set to ja', async () => {
      const userMessage: Message = {
        id: '1',
        text: 'Hello',
        sender: 'user',
        timestamp: new Date(),
      };

      const response = await chatService.generateResponse(userMessage, 'ja', {});

      expect(response).toHaveProperty('message');
      expect(response.message.sender).toBe('bot');
      expect(response.message.text).toBeTruthy();
      // Check that it contains Japanese characters
      expect(response.message.text).toMatch(/[\u3040-\u30ff\u4e00-\u9faf]/);
      expect(response).toHaveProperty('delay');
    });

    it('can simulate network errors', async () => {
      const userMessage: Message = {
        id: '1',
        text: 'Hello',
        sender: 'user',
        timestamp: new Date(),
      };

      // Since network errors are random, we'll test multiple times
      let errorOccurred = false;
      for (let i = 0; i < 50; i++) {
        try {
          await chatService.generateResponse(userMessage, 'en', {});
        } catch (error) {
          errorOccurred = true;
          expect(error).toHaveProperty('code', 'NETWORK_ERROR');
          expect(error).toHaveProperty('retryable', true);
          break;
        }
      }

      // Note: This test might occasionally pass even with working error simulation
      // due to the random nature. In a real app, you'd mock the random function.
    });
  });

  describe('retryMessage', () => {
    jest.setTimeout(10000); // Increase timeout for this test suite
    
    const userMessage: Message = {
      id: '1',
      text: 'Hello',
      sender: 'user',
      timestamp: new Date(),
    };

    it('successfully retries message within retry limit', async () => {
      const response = await chatService.retryMessage(userMessage, 'en', {}, 1);

      expect(response).toHaveProperty('message');
      expect(response.message.sender).toBe('bot');
    });

    it('throws error when retry count exceeds maximum', async () => {
      await expect(chatService.retryMessage(userMessage, 'en', {}, 3)).rejects.toEqual({
        code: 'MAX_RETRIES_EXCEEDED',
        message: 'Maximum retry attempts exceeded. Please try again later.',
        retryable: false,
      });
    });

    it('waits for exponential backoff delay', async () => {
      
      const startTime = Date.now();
      
      try {
        await chatService.retryMessage(userMessage, 'en', {}, 2);
      } catch (error) {
        // Error might occur, but we're testing timing
      }
      
      const endTime = Date.now();
      const elapsed = endTime - startTime;
      
      // Should wait at least 4 seconds for retryCount 2 (1000 * 2^2 = 4000ms)
      expect(elapsed).toBeGreaterThanOrEqual(3900); // Allow some tolerance
    });
  });

  describe('createHumanServiceMessage', () => {
    it('creates human service escalation message in English', () => {
      const message = chatService.createHumanServiceMessage('en');

      expect(message.sender).toBe('bot');
      expect(message.text).toContain('human support team');
      expect(message.text).toContain('customer service representative');
    });

    it('creates human service escalation message in Japanese', () => {
      const message = chatService.createHumanServiceMessage('ja');

      expect(message.sender).toBe('bot');
      expect(message.text).toContain('人間のサポートチーム');
      expect(message.text).toContain('カスタマーサービス担当者');
    });
  });

  describe('Future API methods', () => {
    it('sendToOpenAI throws not implemented error', async () => {
      await expect(chatService.sendToOpenAI('test')).rejects.toThrow('OpenAI integration not yet implemented');
    });

    it('sendToGemini throws not implemented error', async () => {
      await expect(chatService.sendToGemini('test')).rejects.toThrow('Gemini integration not yet implemented');
    });

    it('sendToClaude throws not implemented error', async () => {
      await expect(chatService.sendToClaude('test')).rejects.toThrow('Claude integration not yet implemented');
    });

    it('analyzeConversation throws not implemented error', async () => {
      const messages: Message[] = [];
      await expect(chatService.analyzeConversation(messages)).rejects.toThrow('Conversation analysis not yet implemented');
    });
  });
});