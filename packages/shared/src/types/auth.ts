import { RoleName, User } from './domain';

export interface JwtTokenPayload {
  userId: string;
  organizationId: string;
  email: string;
  role: RoleName;
  storeId?: string | null;
  regionId?: string | null;
  teamId?: string | null;
  iat?: number;
  exp?: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: Omit<User, 'passwordHash'>;
  expiresIn: string;
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
}
