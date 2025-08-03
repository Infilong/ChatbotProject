import { messageUtils } from './messageUtils';
import { Message, MessageStatus } from '../types/Message';

describe('messageUtils', () => {
  describe('createMessage', () => {
    it('creates a user message with default status', () => {
      const message = messageUtils.createMessage('Hello world', 'user');
      
      expect(message).toEqual({
        id: expect.any(String),
        text: 'Hello world',
        sender: 'user',
        timestamp: expect.any(Date),
        status: 'sent',
        retryCount: 0,
      });
    });

    it('creates a bot message with custom status', () => {
      const message = messageUtils.createMessage('Bot response', 'bot', undefined, 'delivered');
      
      expect(message).toEqual({
        id: expect.any(String),
        text: 'Bot response',
        sender: 'bot',
        timestamp: expect.any(Date),
        status: 'delivered',
        retryCount: 0,
      });
    });

    it('creates message with file attachment', () => {
      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const message = messageUtils.createMessage('', 'user', file);
      
      expect(message.text).toBe('📎 test.txt');
      expect(message.file).toEqual({
        name: 'test.txt',
        size: file.size,
        type: 'text/plain',
      });
    });
  });

  describe('createWelcomeMessage', () => {
    it('creates welcome message with username', () => {
      const message = messageUtils.createWelcomeMessage('John');
      
      expect(message.id).toBe('1');
      expect(message.sender).toBe('bot');
      expect(message.text).toContain('Hello John!');
      expect(message.text).toContain('Welcome to DataPro Solutions');
    });
  });

  describe('updateMessageFeedback', () => {
    const messages: Message[] = [
      {
        id: '1',
        text: 'Message 1',
        sender: 'bot',
        timestamp: new Date(),
      },
      {
        id: '2',
        text: 'Message 2',
        sender: 'bot',
        timestamp: new Date(),
      },
    ];

    it('updates feedback for specific message', () => {
      const updatedMessages = messageUtils.updateMessageFeedback(messages, '1', 'up');
      
      expect(updatedMessages[0].feedback).toBe('up');
      expect(updatedMessages[1].feedback).toBeUndefined();
    });

    it('toggles feedback when same feedback is given', () => {
      const messagesWithFeedback = [
        { ...messages[0], feedback: 'up' as const },
        messages[1],
      ];
      
      const updatedMessages = messageUtils.updateMessageFeedback(messagesWithFeedback, '1', 'up');
      
      expect(updatedMessages[0].feedback).toBeNull();
    });

    it('changes feedback when different feedback is given', () => {
      const messagesWithFeedback = [
        { ...messages[0], feedback: 'up' as const },
        messages[1],
      ];
      
      const updatedMessages = messageUtils.updateMessageFeedback(messagesWithFeedback, '1', 'down');
      
      expect(updatedMessages[0].feedback).toBe('down');
    });
  });

  describe('updateMessageStatus', () => {
    const messages: Message[] = [
      {
        id: '1',
        text: 'Message 1',
        sender: 'user',
        timestamp: new Date(),
        status: 'sending',
      },
    ];

    it('updates message status', () => {
      const updatedMessages = messageUtils.updateMessageStatus(messages, '1', 'sent');
      
      expect(updatedMessages[0].status).toBe('sent');
    });

    it('updates message status with error', () => {
      const updatedMessages = messageUtils.updateMessageStatus(messages, '1', 'failed', 'Network error');
      
      expect(updatedMessages[0].status).toBe('failed');
      expect(updatedMessages[0].error).toBe('Network error');
    });
  });

  describe('incrementRetryCount', () => {
    const messages: Message[] = [
      {
        id: '1',
        text: 'Message 1',
        sender: 'user',
        timestamp: new Date(),
        status: 'failed',
        retryCount: 1,
      },
    ];

    it('increments retry count and sets status to sending', () => {
      const updatedMessages = messageUtils.incrementRetryCount(messages, '1');
      
      expect(updatedMessages[0].retryCount).toBe(2);
      expect(updatedMessages[0].status).toBe('sending');
    });

    it('handles messages with no retry count', () => {
      const messagesNoRetry = [
        {
          ...messages[0],
          retryCount: undefined,
        },
      ];
      
      const updatedMessages = messageUtils.incrementRetryCount(messagesNoRetry, '1');
      
      expect(updatedMessages[0].retryCount).toBe(1);
    });
  });

  describe('canRetryMessage', () => {
    it('returns true for failed message with retry count less than 3', () => {
      const message: Message = {
        id: '1',
        text: 'Failed message',
        sender: 'user',
        timestamp: new Date(),
        status: 'failed',
        retryCount: 2,
      };
      
      expect(messageUtils.canRetryMessage(message)).toBe(true);
    });

    it('returns false for failed message with retry count 3 or more', () => {
      const message: Message = {
        id: '1',
        text: 'Failed message',
        sender: 'user',
        timestamp: new Date(),
        status: 'failed',
        retryCount: 3,
      };
      
      expect(messageUtils.canRetryMessage(message)).toBe(false);
    });

    it('returns false for non-failed messages', () => {
      const message: Message = {
        id: '1',
        text: 'Sent message',
        sender: 'user',
        timestamp: new Date(),
        status: 'sent',
      };
      
      expect(messageUtils.canRetryMessage(message)).toBe(false);
    });
  });

  describe('validateMessage', () => {
    it('returns true for non-empty text', () => {
      expect(messageUtils.validateMessage('Hello')).toBe(true);
    });

    it('returns false for empty text', () => {
      expect(messageUtils.validateMessage('')).toBe(false);
    });

    it('returns false for whitespace-only text', () => {
      expect(messageUtils.validateMessage('   ')).toBe(false);
    });

    it('returns true when file is provided even with empty text', () => {
      const file = new File(['content'], 'test.txt');
      expect(messageUtils.validateMessage('', file)).toBe(true);
    });
  });

  describe('formatFileSize', () => {
    it('formats file size in KB', () => {
      expect(messageUtils.formatFileSize(1024)).toBe('1.0');
      expect(messageUtils.formatFileSize(2048)).toBe('2.0');
      expect(messageUtils.formatFileSize(1536)).toBe('1.5');
    });
  });

  describe('formatTime', () => {
    it('formats time correctly', () => {
      const date = new Date('2023-01-01T10:30:00Z');
      const formatted = messageUtils.formatTime(date);
      
      // Should contain time in some format (could be 24h or 12h depending on locale)
      expect(formatted).toMatch(/\d{1,2}:\d{2}/);
      expect(typeof formatted).toBe('string');
      expect(formatted.length).toBeGreaterThan(0);
    });
  });
});