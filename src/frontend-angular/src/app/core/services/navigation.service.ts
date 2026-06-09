import { inject, Injectable } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { UserRole } from '../auth/auth.models';
import { AuthService } from '../auth/auth.service';
import { Breadcrumb, MenuItem, QuickAction } from '../models/navigation.models';

@Injectable({ providedIn: 'root' })
export class NavigationService {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  /**
   * Get menu items based on user roles
   */
  getMenuItems(roles: readonly UserRole[]): MenuItem[] {
    const allMenuItems = this.getAllMenuItems();
    return this.filterMenuItemsByRoles(allMenuItems, roles);
  }

  /**
   * Get breadcrumbs for current route
   */
  getBreadcrumbs(route: ActivatedRoute): Breadcrumb[] {
    const breadcrumbs: Breadcrumb[] = [];

    // Comprehensive safety checks
    if (!route || !route.root || !route.snapshot) {
      return breadcrumbs;
    }

    let currentRoute = route.root;
    const pathSegments: string[] = [];

    while (currentRoute && currentRoute.firstChild) {
      currentRoute = currentRoute.firstChild;

      // Safely access snapshot and data
      if (!currentRoute) {
        break;
      }

      const snapshot = currentRoute.snapshot;
      if (!snapshot) {
        continue;
      }

      // Build full path from root by accumulating segments
      const segments = snapshot.url?.map(seg => seg.path) || [];
      pathSegments.push(...segments);

      const data = snapshot.data;
      if (!data || !data['breadcrumb']) {
        continue;
      }

      // Use full path from root, not just current segment
      const routePath = '/' + pathSegments.join('/');

      // Check for duplicate breadcrumbs before adding
      const existingBreadcrumb = breadcrumbs.find(
        (b) => b.label === data['breadcrumb']
      );
      if (existingBreadcrumb) {
        continue; // Skip duplicate
      }

      breadcrumbs.push({
        label: data['breadcrumb'],
        route: routePath,
        icon: data['icon'],
        disabled: data['disabled'],
      });
    }

    return breadcrumbs;
  }

  /**
   * Get quick actions based on user roles
   */
  getQuickActions(roles: readonly UserRole[]): QuickAction[] {
    const allQuickActions = this.getAllQuickActions();
    return allQuickActions.filter(
      (action) =>
        action.roles.length === 0 ||
        roles.some((role) => action.roles.includes(role))
    );
  }

  /**
   * Navigate to a route with optional query parameters
   */
  navigateToRoute(
    route: string,
    queryParams?: Record<string, string | number | boolean>
  ): void {
    if (queryParams) {
      void this.router.navigate([route], { queryParams });
    } else {
      void this.router.navigate([route]);
    }
  }

  /**
   * Get menu items for a specific parent
   */
  getSubMenuItems(parentId: string, roles: readonly UserRole[]): MenuItem[] {
    const allMenuItems = this.getAllMenuItems();
    const parent = this.findMenuItemById(allMenuItems, parentId);
    return parent?.children
      ? this.filterMenuItemsByRoles(parent.children, roles)
      : [];
  }

  /**
   * Check if user has access to a specific route
   */
  hasAccessToRoute(route: string, roles: readonly UserRole[]): boolean {
    const allMenuItems = this.getAllMenuItems();
    const menuItem = this.findMenuItemByRoute(allMenuItems, route);

    if (!menuItem) {
      return true; // Allow access to routes not in menu
    }

    return (
      menuItem.roles.length === 0 ||
      roles.some((role) => menuItem.roles.includes(role))
    );
  }

  private getAllMenuItems(): MenuItem[] {
    return [
      {
        id: 'dashboard',
        label: 'Dashboard',
        icon: 'layout-dashboard',
        route: '/dashboard',
        roles: ['admin', 'corpus_admin', 'user'],
        order: 1,
      },
      {
        id: 'use-cases',
        label: 'AI Operations',
        icon: 'brain-circuit',
        roles: ['admin', 'corpus_admin', 'user'],
        children: [
          {
            id: 'use-case-menu',
            label: 'Browse AI Operations',
            icon: 'library',
            route: '/use-cases',
            roles: ['admin', 'corpus_admin', 'user'],
          },
        ],
        order: 2,
      },
      {
        id: 'conversations',
        label: 'Analyst Console',
        icon: 'messages-square',
        route: '/conversations',
        roles: ['conversations_privileged', 'admin'],
        order: 3,
      },
      {
        id: 'use-case-development',
        label: 'AIOps Development',
        icon: 'code',
        roles: ['corpus_admin', 'admin', 'use_case_admin', 'developer'],
        children: [
          {
            id: 'use-case-developer',
            label: 'AIO Manager',
            icon: 'brain-circuit',
            route: '/admin/use-case-developer',
            roles: ['admin', 'use_case_admin', 'corpus_admin', 'developer'],
          },
          {
            id: 'create-use-case',
            label: 'Create AI Operation',
            icon: 'circle-plus',
            route: '/dev/use-cases/wizard',
            roles: ['corpus_admin', 'admin', 'use_case_admin', 'developer'],
          },
          {
            id: 'intent-model-config',
            label: 'Intents Management',
            icon: 'sliders-horizontal',
            route: '/dev/intent-model-config',
            roles: ['admin'],
          },
          {
            id: 'my-use-cases',
            label: 'My AI Operations',
            icon: 'folder',
            route: '/dev/use-cases',
            roles: ['corpus_admin', 'admin', 'use_case_admin', 'developer'],
          },
          {
            id: 'pattern-library',
            label: 'Pattern Library',
            icon: 'library',
            route: '/dev/patterns',
            roles: ['corpus_admin', 'admin', 'use_case_admin', 'developer'],
          },
          {
            id: 'query-developer-tools',
            label: 'Query Developer Tools',
            icon: 'flask-conical',
            route: '/dev/query-tools',
            roles: ['corpus_admin', 'admin', 'use_case_admin', 'developer'],
          },
          {
            id: 'tool-testing',
            label: 'Tool Testing',
            icon: 'flask-conical',
            route: '/dev/tools/test',
            roles: ['corpus_admin', 'admin', 'use_case_admin', 'developer'],
          },
        ],
        order: 4,
      },
      {
        id: 'documents',
        label: 'Corpus Management',
        icon: 'folder',
        roles: ['admin', 'corpus_admin'],
        children: [
          {
            id: 'chunking-analysis',
            label: 'Chunking Analysis',
            icon: 'chart-column',
            route: '/documents/chunking-analysis',
            roles: ['admin', 'corpus_admin'],
          },
          {
            id: 'collection-management',
            label: 'Collection Management',
            icon: 'package',
            route: '/admin/collections',
            roles: ['admin', 'corpus_admin'],
          },
          {
            id: 'document-library',
            label: 'Document Library',
            icon: 'library',
            route: '/documents/library',
            roles: ['admin', 'corpus_admin'],
          },
          {
            id: 'document-processing',
            label: 'Processing Status',
            icon: 'hourglass',
            route: '/documents/processing',
            roles: ['admin', 'corpus_admin'],
          },
          {
            id: 'document-upload',
            label: 'Upload Documents',
            icon: 'upload',
            route: '/documents/upload',
            roles: ['admin', 'corpus_admin'],
          },
        ],
        order: 5,
      },
      {
        id: 'model-management-section',
        label: 'Model Management',
        icon: 'brain-circuit',
        roles: ['admin'],
        children: [
          {
            id: 'gateway-metrics',
            label: 'Inference Gateway Metrics',
            icon: 'chart-line',
            route: '/admin/gateway-metrics',
            roles: ['admin'],
          },
          {
            id: 'model-management',
            label: 'Model Management',
            icon: 'brain-circuit',
            route: '/admin/models',
            roles: ['admin'],
          },
          {
            id: 'provider-management',
            label: 'Provider Management',
            icon: 'cloud',
            route: '/admin/providers',
            roles: ['admin'],
          },
        ],
        order: 6,
      },
      {
        id: 'tools-section',
        label: 'Tooling Management',
        icon: 'wrench',
        roles: ['admin'],
        children: [
          {
            id: 'tool-analytics',
            label: 'Tool Analytics',
            icon: 'chart-column',
            route: '/admin/tools/analytics',
            roles: ['admin'],
          },
          {
            id: 'tool-health',
            label: 'Tool Health',
            icon: 'activity',
            route: '/admin/tools/health',
            roles: ['admin'],
          },
          {
            id: 'tool-management',
            label: 'Tool Management',
            icon: 'wrench',
            route: '/admin/tools',
            roles: ['admin'],
          },
        ],
        order: 7,
      },
      {
        id: 'use-case-governance',
        label: 'Governance',
        icon: 'badge-check',
        roles: ['use_case_publisher', 'admin'],
        children: [
          {
            id: 'archived-use-cases',
            label: 'Archived Use Cases',
            icon: 'archive',
            route: '/governance/archived',
            roles: ['use_case_publisher', 'admin'],
          },
          {
            id: 'pending-reviews',
            label: 'Pending Reviews',
            icon: 'clock',
            route: '/governance/pending',
            roles: ['use_case_publisher', 'admin'],
          },
          {
            id: 'published-use-cases',
            label: 'Published Use Cases',
            icon: 'circle-check',
            route: '/governance/published',
            roles: ['use_case_publisher', 'admin'],
          },
        ],
        order: 8,
      },
      {
        id: 'admin',
        label: 'System Administration',
        icon: 'user-cog',
        roles: ['admin'],
        children: [
          {
            id: 'audit-logs',
            label: 'Audit Logs',
            icon: 'clipboard-list',
            route: '/admin/audit',
            roles: ['admin'],
          },
          {
            id: 'developer-teams',
            label: 'Developer Teams',
            icon: 'users-round',
            route: '/admin/developer-teams',
            roles: ['admin'],
          },
          {
            id: 'grouping-roles',
            label: 'Grouping Roles',
            icon: 'users',
            route: '/admin/roles/grouping',
            roles: ['admin'],
          },
          {
            id: 'role-management',
            label: 'Role Management',
            icon: 'user-cog',
            route: '/admin/roles',
            roles: ['admin'],
          },
          {
            id: 'system-config',
            label: 'System Configuration',
            icon: 'settings',
            route: '/admin/system',
            roles: ['admin'],
          },
          {
            id: 'user-management',
            label: 'User Management',
            icon: 'users',
            route: '/admin/users',
            roles: ['admin'],
          },
        ],
        order: 9,
      },
      {
        id: 'analytics',
        label: 'Analytics',
        icon: 'chart-column',
        roles: ['admin', 'corpus_admin'],
        children: [
          {
            id: 'corpus-performance',
            label: 'Corpus Performance',
            icon: 'gauge',
            route: '/analytics/performance',
            roles: ['admin', 'corpus_admin'],
          },
          {
            id: 'corpus-usage',
            label: 'Corpus Usage',
            icon: 'chart-line',
            route: '/analytics/usage',
            roles: ['admin', 'corpus_admin'],
          },
          {
            id: 'security-audit',
            label: 'Security Audit',
            icon: 'shield',
            route: '/analytics/security',
            roles: ['admin'],
          },
          {
            id: 'token-usage',
            label: 'Token Usage',
            icon: 'chart-column',
            route: '/admin/token-usage',
            roles: ['admin'],
          },
        ],
        order: 10,
      },
    ];
  }

  private getAllQuickActions(): QuickAction[] {
    return [
      {
        id: 'new-query',
        label: 'New Query',
        icon: 'plus',
        action: () => this.navigateToRoute('/dev/query-tools'),
        roles: ['admin', 'corpus_admin'],
        tooltip: 'Start a new semantic search query',
        keyboardShortcut: 'Ctrl+N',
      },
      {
        id: 'new-conversation',
        label: 'New Conversation',
        icon: 'message-square',
        action: () => this.navigateToRoute('/conversations'),
        roles: ['conversations_privileged', 'admin'],
        tooltip: 'Start a new conversation thread',
        keyboardShortcut: 'Ctrl+T',
      },
      {
        id: 'upload-document',
        label: 'Upload Document',
        icon: 'file-up',
        action: () => this.navigateToRoute('/documents/upload'),
        roles: ['admin', 'corpus_admin'],
        tooltip: 'Upload a new document',
        keyboardShortcut: 'Ctrl+U',
      },
      {
        id: 'view-analytics',
        label: 'View Analytics',
        icon: 'chart-column',
        action: () => this.navigateToRoute('/analytics/usage'),
        roles: ['admin', 'corpus_admin'],
        tooltip: 'View usage analytics',
      },
      {
        id: 'create-template',
        label: 'Create Template',
        icon: 'list-plus',
        action: () => this.navigateToRoute('/templates/editor'),
        roles: ['admin', 'corpus_admin'],
        tooltip: 'Create a new template',
      },
      {
        id: 'admin-panel',
        label: 'Admin Panel',
        icon: 'user-cog',
        action: () => this.navigateToRoute('/admin/users'),
        roles: ['admin'],
        tooltip: 'Access administration panel',
      },
    ];
  }

  private filterMenuItemsByRoles(
    menuItems: MenuItem[],
    roles: readonly UserRole[]
  ): MenuItem[] {
    return menuItems
      .filter(
        (item) =>
          item.roles.length === 0 ||
          roles.some((role) => item.roles.includes(role))
      )
      .map((item) => ({
        ...item,
        children: item.children
          ? this.filterMenuItemsByRoles(item.children, roles)
          : undefined,
      }))
      .sort((a, b) => (a.order || 999) - (b.order || 999));
  }

  private findMenuItemById(menuItems: MenuItem[], id: string): MenuItem | null {
    for (const item of menuItems) {
      if (item.id === id) {
        return item;
      }
      if (item.children) {
        const found = this.findMenuItemById(item.children, id);
        if (found) {
          return found;
        }
      }
    }
    return null;
  }

  private findMenuItemByRoute(
    menuItems: MenuItem[],
    route: string
  ): MenuItem | null {
    for (const item of menuItems) {
      if (item.route === route) {
        return item;
      }
      if (item.children) {
        const found = this.findMenuItemByRoute(item.children, route);
        if (found) {
          return found;
        }
      }
    }
    return null;
  }
}
