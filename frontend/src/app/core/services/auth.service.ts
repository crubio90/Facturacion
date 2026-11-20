import { Injectable, computed, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

import { environment } from '../../../environments/environment';
import { TokenResponse, User, UserRole } from '../models/api.models';

const TOKEN_KEY = 'daberusa_access_token';
const USER_KEY = 'daberusa_user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly userSignal = signal<User | null>(this.loadStoredUser());

  readonly user = this.userSignal.asReadonly();
  readonly isAuthenticated = computed(() => !!this.userSignal() && !!this.getToken());
  readonly isAdmin = computed(() => this.userSignal()?.role === 'ADMIN');
  readonly canManageCollections = computed(() => {
    const role = this.userSignal()?.role;
    return role === 'ADMIN' || role === 'COBRANZA';
  });
  readonly canManageSalesRisk = computed(() => {
    const role = this.userSignal()?.role;
    return role === 'ADMIN' || role === 'VENDEDOR' || role === 'COBRANZA';
  });

  constructor(private http: HttpClient, private router: Router) {}

  login(email: string, password: string): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${environment.apiBaseUrl}/auth/login`, { email, password })
      .pipe(
        tap((res) => {
          localStorage.setItem(TOKEN_KEY, res.access_token);
          localStorage.setItem(USER_KEY, JSON.stringify(res.user));
          this.userSignal.set(res.user);
        })
      );
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    this.userSignal.set(null);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  hasRole(...roles: UserRole[]): boolean {
    const current = this.userSignal()?.role;
    return !!current && roles.includes(current);
  }

  private loadStoredUser(): User | null {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? (JSON.parse(raw) as User) : null;
    } catch {
      return null;
    }
  }
}
