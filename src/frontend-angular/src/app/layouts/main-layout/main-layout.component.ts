import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router, RouterOutlet } from '@angular/router';

import { UserProfile } from '../../core/auth/auth.models';
import { AuthService } from '../../core/auth/auth.service';
import { MenuItem, QuickAction } from '../../core/models/navigation.models';
import { KeyboardShortcutsService } from '../../core/services/keyboard-shortcuts.service';
import { NavigationService } from '../../core/services/navigation.service';
import { BreadcrumbComponent } from '../../shared/components/breadcrumb/breadcrumb.component';
import { QuickActionsBarComponent } from '../../shared/components/quick-actions-bar/quick-actions-bar.component';
import { SidebarComponent } from '../../shared/components/sidebar/sidebar.component';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    MatSidenavModule,
    MatToolbarModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    SidebarComponent,
    QuickActionsBarComponent,
    BreadcrumbComponent,
  ],
  templateUrl: './main-layout.component.html',
  styleUrls: ['./main-layout.component.scss'],
})
export class MainLayoutComponent {
  private readonly authService = inject(AuthService);
  private readonly navigationService = inject(NavigationService);
  private readonly keyboardShortcutsService = inject(KeyboardShortcutsService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);

  // Signals for reactive state
  readonly currentUser = signal<UserProfile | null>(null);
  readonly isAuthenticated = signal(false);
  readonly menuItems = signal<MenuItem[]>([]);
  readonly quickActions = signal<QuickAction[]>([]);
  readonly isSidebarOpen = signal(true);
  readonly isSidebarCollapsed = signal(false);

  // Layout configuration (design-system layout tokens: --sidebar-w / --sidebar-w-collapsed)
  readonly sidebarWidth = 264;
  readonly collapsedSidebarWidth = 68;

  constructor() {
    this.initializeLayout();
  }

  private initializeLayout(): void {
    // Subscribe to authentication state changes
    this.authService
      .getCurrentUser()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((user) => {
        this.currentUser.set(user);
        this.isAuthenticated.set(!!user);

        if (user) {
          // Update menu items and quick actions based on user roles
          this.updateNavigationItems(user.roles);
        }
      });

    // Set initial authentication status
    this.isAuthenticated.set(this.authService.isAuthenticated());

    // Demo mode: If no user is authenticated and we're on demo route, show demo user
    if (
      !this.authService.isAuthenticated() &&
      window.location.pathname.includes('/demo')
    ) {
      const demoUser = {
        id: 'demo-user',
        username: 'demo-user',
        full_name: 'Demo User',
        roles: ['admin', 'corpus_admin', 'user'] as const,
        expires_at: Date.now() + 3600000, // 1 hour from now
      };
      this.currentUser.set(demoUser);
      this.isAuthenticated.set(true);
      this.updateNavigationItems(demoUser.roles);
    }

    // Initialize keyboard shortcuts
    this.keyboardShortcutsService.registerShortcut({
      key: 'b',
      ctrlKey: true,
      callback: () => this.toggleSidebar(),
      description: 'Toggle Sidebar',
      roles: ['admin', 'corpus_admin', 'user'],
      preventDefault: true,
    });
  }

  private updateNavigationItems(roles: readonly string[]): void {
    const menuItems = this.navigationService.getMenuItems(roles as any);
    const quickActions = this.navigationService.getQuickActions(roles as any);

    this.menuItems.set(menuItems);
    this.quickActions.set(quickActions);
  }

  toggleSidebar(): void {
    this.isSidebarOpen.set(!this.isSidebarOpen());
  }

  toggleSidebarCollapse(): void {
    this.isSidebarCollapsed.set(!this.isSidebarCollapsed());
  }

  onSidebarToggle(): void {
    this.toggleSidebar();
  }

  onSidebarCollapseToggle(): void {
    this.toggleSidebarCollapse();
  }

  onMenuItemClick(menuItem: MenuItem): void {
    if (menuItem.route) {
      this.navigationService.navigateToRoute(menuItem.route);
    }
  }

  onQuickActionClick(action: QuickAction): void {
    action.action();
  }

  getSidebarWidth(): string {
    if (!this.isSidebarOpen()) {
      return '0px';
    }
    return this.isSidebarCollapsed()
      ? `${this.collapsedSidebarWidth}px`
      : `${this.sidebarWidth}px`;
  }

  getMainContentMarginLeft(): string {
    return this.getSidebarWidth();
  }

  logout(): void {
    this.authService.logout().subscribe({
      next: () => {
        // Navigation is handled by AuthService
      },
      error: (error) => {
        console.error('Logout error:', error);
        // Even if logout fails, clear local state and redirect
        void this.router.navigate(['/login']);
      },
    });
  }
}
