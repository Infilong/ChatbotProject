/**
 * Authentication Service
 * Handles user registration, login, logout, and token management
 */

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  first_name?: string;
  last_name?: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name?: string;
  is_staff?: boolean;
  is_superuser?: boolean;
  date_joined?: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  user?: User;
  token?: string;
  access?: string;
  refresh?: string;
  login_time?: string;
}

export interface AuthError {
  error: string;
  details?: Record<string, string[]>;
  message?: string;
}

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const AUTH_API_URL = `${API_BASE_URL}/api/auth`;

class AuthService {
  private token: string | null = null;

  constructor() {
    // Load token from localStorage on initialization
    this.token = localStorage.getItem('authToken');
  }

  /**
   * Register a new user account
   */
  async register(data: RegisterData): Promise<AuthResponse> {
    try {
      const response = await fetch(`${AUTH_API_URL}/register/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (response.ok) {
        // Store tokens if provided
        if (result.access) {
          this.setToken(result.access);
        }
        return result;
      } else {
        throw result;
      }
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  }

  /**
   * Authenticate user with username and password
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      const response = await fetch(`${AUTH_API_URL}/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      const result = await response.json();

      if (response.ok && result.success) {
        // Store authentication token
        if (result.token) {
          this.setToken(result.token);
        }
        return result;
      } else {
        throw result;
      }
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  /**
   * Logout current user
   */
  async logout(): Promise<void> {
    try {
      if (this.token) {
        await fetch(`${AUTH_API_URL}/logout/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Token ${this.token}`,
          },
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Always clear local token regardless of API call success
      this.clearToken();
    }
  }

  /**
   * Get current user profile
   */
  async getProfile(): Promise<User> {
    if (!this.token) {
      throw new Error('No authentication token');
    }

    try {
      const response = await fetch(`${AUTH_API_URL}/profile/`, {
        method: 'GET',
        headers: {
          'Authorization': `Token ${this.token}`,
        },
      });

      if (response.ok) {
        return await response.json();
      } else {
        throw new Error('Failed to fetch profile');
      }
    } catch (error) {
      console.error('Profile fetch error:', error);
      throw error;
    }
  }

  /**
   * Validate current token
   */
  async validateToken(): Promise<{ valid: boolean; user?: User }> {
    if (!this.token) {
      return { valid: false };
    }

    try {
      const response = await fetch(`${AUTH_API_URL}/validate-token/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token: this.token }),
      });

      const result = await response.json();

      if (!result.valid) {
        this.clearToken();
      }

      return result;
    } catch (error) {
      console.error('Token validation error:', error);
      this.clearToken();
      return { valid: false };
    }
  }

  /**
   * Check authentication status
   */
  async getAuthStatus(): Promise<{ authenticated: boolean; user?: User }> {
    try {
      const headers: Record<string, string> = {};
      if (this.token) {
        headers['Authorization'] = `Token ${this.token}`;
      }

      const response = await fetch(`${AUTH_API_URL}/status/`, {
        method: 'GET',
        headers,
      });

      return await response.json();
    } catch (error) {
      console.error('Auth status error:', error);
      return { authenticated: false };
    }
  }

  /**
   * Change user password
   */
  async changePassword(currentPassword: string, newPassword: string, confirmPassword: string): Promise<AuthResponse> {
    if (!this.token) {
      throw new Error('No authentication token');
    }

    try {
      const response = await fetch(`${AUTH_API_URL}/change-password/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Token ${this.token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });

      const result = await response.json();

      if (response.ok && result.success) {
        // Update token if provided
        if (result.token) {
          this.setToken(result.token);
        }
        return result;
      } else {
        throw result;
      }
    } catch (error) {
      console.error('Password change error:', error);
      throw error;
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.token;
  }

  /**
   * Get current auth token
   */
  getToken(): string | null {
    return this.token;
  }

  /**
   * Set authentication token
   */
  private setToken(token: string): void {
    this.token = token;
    localStorage.setItem('authToken', token);
  }

  /**
   * Clear authentication token
   */
  private clearToken(): void {
    this.token = null;
    localStorage.removeItem('authToken');
  }

  /**
   * Get auth headers for API requests
   */
  getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Token ${this.token}`;
    }

    return headers;
  }
}

export const authService = new AuthService();
export default authService;