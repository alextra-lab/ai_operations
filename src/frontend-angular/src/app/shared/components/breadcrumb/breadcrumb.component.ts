import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { filter, startWith } from 'rxjs/operators';

import { Breadcrumb } from '../../../core/models/navigation.models';
import { NavigationService } from '../../../core/services/navigation.service';

@Component({
  selector: 'app-breadcrumb',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule],
  templateUrl: './breadcrumb.component.html',
  styleUrls: ['./breadcrumb.component.scss'],
})
export class BreadcrumbComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly navigationService = inject(NavigationService);
  private readonly destroyRef = inject(DestroyRef);

  readonly breadcrumbs = signal<Breadcrumb[]>([]);

  constructor() {
    // Do not initialize breadcrumbs in constructor
    // Wait for ngOnInit and router events
  }

  ngOnInit(): void {
    // Only build breadcrumbs after router has completed navigation
    this.router.events
      .pipe(
        filter((event) => event instanceof NavigationEnd),
        startWith(null), // Trigger initial load
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe(() => {
        this.updateBreadcrumbs();
      });
  }

  private updateBreadcrumbs(): void {
    try {
      const breadcrumbs = this.navigationService.getBreadcrumbs(
        this.activatedRoute
      );
      this.breadcrumbs.set(breadcrumbs);
    } catch (error) {
      console.warn('Error updating breadcrumbs:', error);
      this.breadcrumbs.set([]);
    }
  }

  onBreadcrumbClick(breadcrumb: Breadcrumb): void {
    if (breadcrumb.route && !breadcrumb.disabled) {
      this.navigationService.navigateToRoute(breadcrumb.route);
    }
  }

  isLastBreadcrumb(index: number): boolean {
    return index === this.breadcrumbs().length - 1;
  }

  getBreadcrumbLabel(breadcrumb: Breadcrumb): string {
    return breadcrumb.label;
  }

  getBreadcrumbIcon(breadcrumb: Breadcrumb): string {
    return breadcrumb.icon || 'circle';
  }

  isBreadcrumbDisabled(breadcrumb: Breadcrumb): boolean {
    return breadcrumb.disabled || false;
  }

  trackByBreadcrumb(index: number, breadcrumb: Breadcrumb): string {
    return breadcrumb.label + index;
  }

  /**
   * Get the last breadcrumb (current page)
   */
  getLastBreadcrumb(): Breadcrumb | null {
    const breadcrumbs = this.breadcrumbs();
    return breadcrumbs.length > 0 ? breadcrumbs[breadcrumbs.length - 1] : null;
  }

  /**
   * Get the parent breadcrumb (second to last)
   */
  getParentBreadcrumb(): Breadcrumb | null {
    const breadcrumbs = this.breadcrumbs();
    return breadcrumbs.length > 1 ? breadcrumbs[breadcrumbs.length - 2] : null;
  }
}
