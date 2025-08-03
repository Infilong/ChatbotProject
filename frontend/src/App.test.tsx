import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders DataPro Solutions app', () => {
  render(<App />);
  const titleElement = screen.getByText(/DataPro Solutions/i);
  expect(titleElement).toBeInTheDocument();
});

test('renders login form when not logged in', () => {
  render(<App />);
  const usernameInput = screen.getByLabelText(/username/i);
  expect(usernameInput).toBeInTheDocument();
});
