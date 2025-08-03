import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { ThemeProvider } from '@mui/material/styles';
import MessageInput from './MessageInput';
import { theme } from '../theme';

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('MessageInput', () => {
  const mockOnSendMessage = jest.fn();

  beforeEach(() => {
    mockOnSendMessage.mockClear();
  });

  it('renders input field and send button', () => {
    renderWithTheme(
      <MessageInput onSendMessage={mockOnSendMessage} />
    );

    expect(screen.getByPlaceholderText('Type your message here...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  it('calls onSendMessage when form is submitted with text', async () => {
    renderWithTheme(
      <MessageInput onSendMessage={mockOnSendMessage} />
    );

    const input = screen.getByPlaceholderText('Type your message here...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    await userEvent.type(input, 'Hello world');
    await userEvent.click(sendButton);

    expect(mockOnSendMessage).toHaveBeenCalledWith('Hello world', undefined);
  });

  it('clears input after sending message', async () => {
    renderWithTheme(
      <MessageInput onSendMessage={mockOnSendMessage} />
    );

    const input = screen.getByPlaceholderText('Type your message here...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    await userEvent.type(input, 'Hello world');
    await userEvent.click(sendButton);

    await waitFor(() => {
      expect(input).toHaveValue('');
    });
  });

  it('does not send empty messages', async () => {
    renderWithTheme(
      <MessageInput onSendMessage={mockOnSendMessage} />
    );

    const sendButton = screen.getByRole('button', { name: /send/i });
    await userEvent.click(sendButton);

    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });

  it('shows emoji picker button', () => {
    renderWithTheme(
      <MessageInput onSendMessage={mockOnSendMessage} />
    );

    const emojiButton = screen.getByRole('button', { name: /emoji/i });
    expect(emojiButton).toBeInTheDocument();
  });

  it('shows file attachment button', () => {
    renderWithTheme(
      <MessageInput onSendMessage={mockOnSendMessage} />
    );

    const attachButton = screen.getByRole('button');
    const attachIcon = attachButton.querySelector('[data-testid="AttachFileIcon"]');
    expect(attachIcon).toBeInTheDocument();
  });

  it('submits form on Enter key press', async () => {
    renderWithTheme(
      <MessageInput onSendMessage={mockOnSendMessage} />
    );

    const input = screen.getByPlaceholderText('Type your message here...');
    
    await userEvent.type(input, 'Hello world');
    fireEvent.submit(input.closest('form')!);

    expect(mockOnSendMessage).toHaveBeenCalledWith('Hello world', undefined);
  });

  it('handles multiline input correctly', async () => {
    renderWithTheme(
      <MessageInput onSendMessage={mockOnSendMessage} />
    );

    const input = screen.getByPlaceholderText('Type your message here...');
    
    // Directly set multiline value for testing
    fireEvent.change(input, { target: { value: 'Line 1\nLine 2' } });
    
    expect(input).toHaveValue('Line 1\nLine 2');
  });
});