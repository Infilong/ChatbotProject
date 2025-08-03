import { debounce, throttle } from './debounce';

// Mock timers for testing
jest.useFakeTimers();

describe('debounce', () => {
  it('delays function execution until after wait time', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 1000);

    debouncedFn();
    expect(mockFn).not.toHaveBeenCalled();

    jest.advanceTimersByTime(999);
    expect(mockFn).not.toHaveBeenCalled();

    jest.advanceTimersByTime(1);
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  it('cancels previous timer when called multiple times', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 1000);

    debouncedFn();
    jest.advanceTimersByTime(500);
    
    debouncedFn(); // This should cancel the previous timer
    jest.advanceTimersByTime(999);
    expect(mockFn).not.toHaveBeenCalled();

    jest.advanceTimersByTime(1);
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  it('passes arguments correctly', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 1000);

    debouncedFn('arg1', 'arg2');
    jest.advanceTimersByTime(1000);

    expect(mockFn).toHaveBeenCalledWith('arg1', 'arg2');
  });

  it('executes immediately when immediate flag is true', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 1000, true);

    debouncedFn();
    expect(mockFn).toHaveBeenCalledTimes(1);

    // Subsequent calls within wait time should not execute
    debouncedFn();
    expect(mockFn).toHaveBeenCalledTimes(1);

    jest.advanceTimersByTime(1000);
    debouncedFn();
    expect(mockFn).toHaveBeenCalledTimes(2);
  });
});

describe('throttle', () => {
  it('executes function immediately on first call', () => {
    const mockFn = jest.fn();
    const throttledFn = throttle(mockFn, 1000);

    throttledFn();
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  it('ignores subsequent calls within wait time', () => {
    const mockFn = jest.fn();
    const throttledFn = throttle(mockFn, 1000);

    throttledFn();
    throttledFn();
    throttledFn();
    
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  it('allows execution after wait time has passed', () => {
    const mockFn = jest.fn();
    const throttledFn = throttle(mockFn, 1000);

    throttledFn();
    expect(mockFn).toHaveBeenCalledTimes(1);

    jest.advanceTimersByTime(1000);
    throttledFn();
    expect(mockFn).toHaveBeenCalledTimes(2);
  });

  it('passes arguments correctly', () => {
    const mockFn = jest.fn();
    const throttledFn = throttle(mockFn, 1000);

    throttledFn('arg1', 'arg2');
    expect(mockFn).toHaveBeenCalledWith('arg1', 'arg2');
  });
});

// Restore real timers after tests
afterAll(() => {
  jest.useRealTimers();
});