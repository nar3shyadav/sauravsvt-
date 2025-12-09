import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { Router } from '@angular/router';

export interface User {
  _id?: string;
  email: string;
  role: 'admin' | 'recruiter' | 'user';
  token?: string;
}

interface AuthResponse {
  token: string;
  user_id?: string;
  role?: string;
  message?: string;
}

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private apiUrl = '/api/auth'; // Using proxy, or full URL if proxy not set. Assuming we will set up proxy.
  // Actually, let's use full URL for now or define a base API URL in environment. 
  // Given user didn't ask for environment, I'll hardcode 'http://localhost:5002/auth' for now but proxy is better.
  // I will use /auth and assume proxy config later.

  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  // Base URL
  private readonly BASE_URL = 'http://localhost:5002/auth';

  constructor(private http: HttpClient, private router: Router) {
    this.loadUserFromStorage();
  }

  public get currentUserValue(): User | null {
    return this.currentUserSubject.value;
  }

  private loadUserFromStorage(): void {
    const token = localStorage.getItem('token');
    if (token) {
      // Ideally we decode token here to get user info if not stored separately
      const user = this.decodeToken(token);
      if (user) {
        this.currentUserSubject.next(user);
      }
    }
  }

  register(user: any): Observable<any> {
    return this.http.post(`${this.BASE_URL}/register`, user);
  }

  login(credentials: { email: string, password: string }): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.BASE_URL}/login`, credentials)
      .pipe(tap(response => {
        if (response.token) {
          localStorage.setItem('token', response.token);
          const user = this.decodeToken(response.token);
          this.currentUserSubject.next(user);
        }
      }));
  }

  logout(): void {
    // Optional: Call server logout if needed
    localStorage.removeItem('token');
    this.currentUserSubject.next(null);
    this.router.navigate(['/auth/login']);
  }

  isAuthenticated(): boolean {
    return !!this.currentUserValue;
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }

  private decodeToken(token: string): User | null {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return {
        _id: payload.user_id,
        email: payload.email, // backend token payload might need to include email or we fetch it
        role: payload.role,
        token: token
      };
    } catch (e) {
      return null;
    }
  }
}
