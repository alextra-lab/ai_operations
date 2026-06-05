import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnDestroy,
  OnInit,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { Router } from '@angular/router';
import { Observable, Subject, forkJoin, of } from 'rxjs';
import { catchError, take, takeUntil, tap } from 'rxjs/operators';

import { LucideAngularModule } from 'lucide-angular';
import {
  UseCaseListResponse,
  UseCaseResponse,
} from '../../../api/models/use-case-management.models';
import { UseCaseManagementService } from '../../../api/services/use-case-management.service';
import { UserProfile } from '../../../core/auth/auth.models';
import { AuthService } from '../../../core/auth/auth.service';
import { UserManagementService } from '../user-management/services/user-management.service';

interface TabState {
  data: UseCaseResponse[];
  isLoading: boolean;
  error: string | null;
}

@Component({
  selector: 'app-use-case-developer',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatTabsModule,
    MatListModule,
    MatButtonModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatCardModule,
  ],
  templateUrl: './use-case-developer.component.html',
  styleUrls: ['./use-case-developer.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UseCaseDeveloperComponent implements OnInit, OnDestroy {
  activeTab = 0;
  user: UserProfile | null = null;

  myDrafts: TabState = { data: [], isLoading: true, error: null };
  teamDrafts: TabState = { data: [], isLoading: true, error: null };
  reviewTab: TabState = { data: [], isLoading: true, error: null };
  publishedTab: TabState = { data: [], isLoading: true, error: null };

  teams: string[] = [];
  selectedTeam: string | null = null;
  userTeams: string[] = []; // Teams the current user belongs to
  hasTeams = false; // Whether user has any team memberships

  private readonly destroy$ = new Subject<void>();

  constructor(
    private readonly useCaseService: UseCaseManagementService,
    private readonly authService: AuthService,
    private readonly userManagementService: UserManagementService,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadUser();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  trackByUseCaseId(_: number, useCase: UseCaseResponse): string {
    return useCase.id;
  }

  filteredTeamDrafts(): UseCaseResponse[] {
    if (!this.selectedTeam) {
      return this.teamDrafts.data;
    }
    return this.teamDrafts.data.filter(
      (uc) => uc.team_id === this.selectedTeam
    );
  }

  selectTeam(teamId: string): void {
    this.selectedTeam = teamId;
  }

  openUseCase(useCaseId: string, mode: 'edit' | 'view'): void {
    const path =
      mode === 'edit'
        ? `/dev/use-cases/edit/${useCaseId}`
        : `/dev/use-cases/view/${useCaseId}`;
    void this.router.navigate([path]);
  }

  private loadUser(): void {
    this.authService
      .getCurrentUser()
      .pipe(
        take(1),
        tap((user) => {
          this.user = user;
          if (user) {
            this.loadUserTeams(user.id);
          } else {
            this.loadAllTabs();
          }
        }),
        takeUntil(this.destroy$)
      )
      .subscribe();
  }

  private loadUserTeams(userId: string): void {
    this.userManagementService
      .getUserRoles(userId)
      .pipe(
        take(1),
        tap((rolesResponse) => {
          this.userTeams = rolesResponse.teams || [];
          this.hasTeams = this.userTeams.length > 0;
          this.loadAllTabs();
        }),
        catchError((err) => {
          // If RBAC API fails, continue without team filtering
          console.warn('Failed to load user teams:', err);
          this.userTeams = [];
          this.hasTeams = false;
          this.loadAllTabs();
          return of(null);
        }),
        takeUntil(this.destroy$)
      )
      .subscribe();
  }

  private loadAllTabs(): void {
    this.resetState();

    const drafts$ = this.useCaseService.listUseCases({
      lifecycle_state: 'draft',
      page_size: 100,
    });
    const review$ = this.useCaseService.listUseCases({
      lifecycle_state: 'review',
      page_size: 100,
    });
    const published$ = this.useCaseService.listUseCases({
      lifecycle_state: 'published',
      page_size: 100,
    });

    forkJoin({
      drafts: drafts$.pipe(
        catchError((err) => this.handleTabError('draft', err))
      ),
      review: review$.pipe(
        catchError((err) => this.handleTabError('review', err))
      ),
      published: published$.pipe(
        catchError((err) => this.handleTabError('published', err))
      ),
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe(({ drafts, review, published }) => {
        this.handleDrafts(drafts);
        this.handleReview(review);
        this.handlePublished(published);
        this.cdr.markForCheck();
      });
  }

  private handleDrafts(response: UseCaseListResponse | null): void {
    if (!response) {
      this.myDrafts.isLoading = false;
      this.teamDrafts.isLoading = false;
      return;
    }

    const sortedDrafts = this.sortByUpdatedAt(response.use_cases);
    const currentUserId = this.user?.id ?? null;

    // My Drafts: drafts created by current user
    this.myDrafts.data = sortedDrafts.filter(
      (uc) => uc.created_by_user_id === currentUserId
    );

    // Team Drafts: drafts from user's teams (RBAC V2 filtering)
    // Only show drafts from teams the user belongs to
    if (this.hasTeams && this.userTeams.length > 0) {
      this.teamDrafts.data = sortedDrafts.filter(
        (uc) =>
          uc.team_id &&
          uc.created_by_user_id !== currentUserId &&
          this.userTeams.includes(uc.team_id)
      );
    } else {
      // If user has no teams, show no team drafts
      this.teamDrafts.data = [];
    }

    // Extract unique teams from filtered team drafts
    this.teams = Array.from(
      new Set(this.teamDrafts.data.map((uc) => uc.team_id || ''))
    ).filter(Boolean);

    // Auto-select first team if available
    if (!this.selectedTeam && this.teams.length) {
      this.selectedTeam = this.teams[0];
    }

    this.myDrafts.isLoading = false;
    this.teamDrafts.isLoading = false;
  }

  private handleReview(response: UseCaseListResponse | null): void {
    if (!response) {
      this.reviewTab.isLoading = false;
      return;
    }

    this.reviewTab.data = this.sortByUpdatedAt(response.use_cases);
    this.reviewTab.isLoading = false;
  }

  private handlePublished(response: UseCaseListResponse | null): void {
    if (!response) {
      this.publishedTab.isLoading = false;
      return;
    }

    this.publishedTab.data = this.sortByUpdatedAt(response.use_cases);
    this.publishedTab.isLoading = false;
  }

  private sortByUpdatedAt(useCases: UseCaseResponse[]): UseCaseResponse[] {
    return [...useCases].sort((a, b) => {
      return (
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );
    });
  }

  private handleTabError(
    tab: 'draft' | 'review' | 'published',
    error: any
  ): Observable<UseCaseListResponse | null> {
    const message =
      error?.error?.detail || 'Failed to load use cases. Please try again.';
    if (tab === 'draft') {
      this.myDrafts.error = message;
      this.teamDrafts.error = message;
      this.myDrafts.isLoading = false;
      this.teamDrafts.isLoading = false;
    } else if (tab === 'review') {
      this.reviewTab.error = message;
      this.reviewTab.isLoading = false;
    } else {
      this.publishedTab.error = message;
      this.publishedTab.isLoading = false;
    }
    this.cdr.markForCheck();
    return of(null as UseCaseListResponse | null);
  }

  private resetState(): void {
    this.myDrafts = { data: [], isLoading: true, error: null };
    this.teamDrafts = { data: [], isLoading: true, error: null };
    this.reviewTab = { data: [], isLoading: true, error: null };
    this.publishedTab = { data: [], isLoading: true, error: null };
    this.teams = [];
    this.selectedTeam = null;
    // NOTE: Do NOT reset userTeams and hasTeams here - they are user context
    // that persists across tab loads, not tab state. They are set by loadUserTeams()
    // and should remain until the user changes or component is destroyed.
  }
}
