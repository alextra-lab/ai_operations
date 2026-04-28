import { Routes } from '@angular/router';

import { AuthGuard } from './core/auth/auth.guard';
import { RoleGuard } from './core/auth/role.guard';
import { LoginComponent } from './pages/login/login.component';

export const routes: Routes = [
  {
    path: 'login',
    component: LoginComponent,
    data: { breadcrumb: 'Login' },
  },
  {
    path: 'unauthorized',
    loadComponent: () =>
      import('./pages/unauthorized/unauthorized.component').then(
        (m) => m.UnauthorizedComponent
      ),
    data: { breadcrumb: 'Unauthorized' },
  },
  {
    path: 'demo',
    loadComponent: () =>
      import('./pages/layout-demo/layout-demo.component').then(
        (m) => m.LayoutDemoComponent
      ),
    data: { breadcrumb: 'Layout Demo', icon: 'demo' },
  },
  {
    path: 'api-test',
    loadComponent: () =>
      import('./pages/api-test/api-test.component').then(
        (m) => m.ApiTestComponent
      ),
    data: { breadcrumb: 'API Test', icon: 'api' },
  },
  {
    path: '',
    canActivate: [AuthGuard],
    loadComponent: () =>
      import('./layouts/main-layout/main-layout.component').then(
        (m) => m.MainLayoutComponent
      ),
    children: [
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/soc-dashboard.component').then(
            (m) => m.SocDashboardComponent
          ),
        data: { breadcrumb: 'Dashboard', icon: 'dashboard' },
      },
      {
        path: 'query',
        data: { breadcrumb: 'Query Interface', icon: 'search' },
        children: [
          {
            path: 'semantic',
            redirectTo: '/dev/query-tools',
            pathMatch: 'full',
          },
          {
            path: 'rag',
            redirectTo: '/dev/query-tools',
            pathMatch: 'full',
          },
          {
            path: 'history',
            redirectTo: '/dev/query-tools',
            pathMatch: 'full',
          },
          {
            path: '',
            redirectTo: '/dev/query-tools',
            pathMatch: 'full',
          },
        ],
      },
      {
        path: 'documents',
        data: { breadcrumb: 'Corpus Management', icon: 'folder' },
        children: [
          {
            path: 'upload',
            loadComponent: () =>
              import('./pages/documents/document-upload.component').then(
                (m) => m.DocumentUploadComponent
              ),
            data: { breadcrumb: 'Upload Documents', icon: 'upload' },
          },
          {
            path: 'library',
            loadComponent: () =>
              import('./pages/documents/document-library.component').then(
                (m) => m.DocumentLibraryComponent
              ),
            data: { breadcrumb: 'Document Library', icon: 'library_books' },
          },
          {
            path: 'processing',
            loadComponent: () =>
              import('./pages/documents/document-processing.component').then(
                (m) => m.DocumentProcessingComponent
              ),
            data: { breadcrumb: 'Processing Status', icon: 'pending_actions' },
          },
          {
            path: 'chunking-analysis',
            loadComponent: () =>
              import(
                './pages/documents/chunking-analysis/chunking-analysis.component'
              ).then((m) => m.ChunkingAnalysisComponent),
            data: { breadcrumb: 'Chunking Analysis', icon: 'analytics' },
          },
          {
            path: '',
            redirectTo: 'upload',
            pathMatch: 'full',
          },
        ],
      },
      {
        path: 'analytics',
        data: { breadcrumb: 'Analytics', icon: 'analytics' },
        children: [
          {
            path: 'usage',
            loadComponent: () =>
              import('./pages/analytics/usage-analytics.component').then(
                (m) => m.UsageAnalyticsComponent
              ),
            data: { breadcrumb: 'Corpus Usage', icon: 'insights' },
          },
          {
            path: 'performance',
            loadComponent: () =>
              import('./pages/analytics/performance-metrics.component').then(
                (m) => m.PerformanceMetricsComponent
              ),
            data: { breadcrumb: 'Corpus Performance', icon: 'speed' },
          },
          {
            path: 'security',
            loadComponent: () =>
              import('./pages/analytics/security-audit.component').then(
                (m) => m.SecurityAuditComponent
              ),
            data: { breadcrumb: 'Security Audit', icon: 'security' },
          },
          {
            path: '',
            redirectTo: 'usage',
            pathMatch: 'full',
          },
        ],
      },
      {
        path: 'templates',
        data: { breadcrumb: 'Templates', icon: 'template' },
        children: [
          {
            path: 'library',
            loadComponent: () =>
              import('./pages/templates/template-library.component').then(
                (m) => m.TemplateLibraryComponent
              ),
            data: { breadcrumb: 'Template Library', icon: 'library_books' },
          },
          {
            path: 'editor',
            loadComponent: () =>
              import('./pages/templates/template-editor.component').then(
                (m) => m.TemplateEditorComponent
              ),
            data: { breadcrumb: 'Template Editor', icon: 'edit' },
          },
          {
            path: 'builder',
            loadComponent: () =>
              import('./pages/templates/use-case-builder.component').then(
                (m) => m.UseCaseBuilderComponent
              ),
            data: { breadcrumb: 'Use Case Builder', icon: 'build' },
          },
          {
            path: 'new',
            loadComponent: () =>
              import('./pages/templates/prompt-template-editor.component').then(
                (m) => m.PromptTemplateEditorComponent
              ),
            data: { breadcrumb: 'New Template', icon: 'add' },
          },
          {
            path: ':id/edit',
            loadComponent: () =>
              import('./pages/templates/prompt-template-editor.component').then(
                (m) => m.PromptTemplateEditorComponent
              ),
            data: { breadcrumb: 'Edit Template', icon: 'edit' },
          },
          {
            path: ':id',
            loadComponent: () =>
              import('./pages/templates/template-detail.component').then(
                (m) => m.TemplateDetailComponent
              ),
            data: { breadcrumb: 'Template Details', icon: 'info' },
          },
          {
            path: '',
            redirectTo: 'library',
            pathMatch: 'full',
          },
        ],
      },
      {
        path: 'use-cases',
        data: { breadcrumb: 'AI Operations', icon: 'psychology' },
        children: [
          {
            path: '',
            loadComponent: () =>
              import('./pages/use-case-menu/use-case-menu.component').then(
                (m) => m.UseCaseMenuComponent
              ),
            data: { breadcrumb: 'AIOps Library', icon: 'library_books' },
          },
          {
            path: 'dynamic-form-test',
            loadComponent: () =>
              import(
                './pages/use-case-execution/dynamic-form-test.component'
              ).then((m) => m.DynamicFormTestComponent),
            data: { breadcrumb: 'Dynamic Form Test (P3-F1)', icon: 'science' },
          },
          {
            path: ':id',
            loadComponent: () =>
              import(
                './pages/use-case-execution/use-case-execution.component'
              ).then((m) => m.UseCaseExecutionComponent),
            data: { breadcrumb: 'Use Case Execution', icon: 'play_arrow' },
          },
        ],
      },
      {
        path: 'conversations',
        canActivate: [RoleGuard],
        data: {
          breadcrumb: 'Analyst Console',
          icon: 'forum',
          roles: ['conversations_privileged', 'admin'],
        },
        loadComponent: () =>
          import('./pages/conversations/conversation.component').then(
            (m) => m.ConversationComponent
          ),
      },
      {
        path: 'dev',
        data: { breadcrumb: 'AIOps Development', icon: 'code' },
        children: [
          {
            path: 'use-cases',
            data: { breadcrumb: 'My AI Operations', icon: 'folder' },
            children: [
              {
                path: '',
                loadComponent: () =>
                  import('./pages/use-cases/use-case-list.component').then(
                    (m) => m.UseCaseListComponent
                  ),
                data: { breadcrumb: '', icon: 'list', pageTitle: 'My AI Operations' },
              },
              {
                path: 'wizard',
                loadComponent: () =>
                  import('./pages/use-cases/use-case-wizard.component').then(
                    (m) => m.UseCaseWizardComponent
                  ),
                data: { breadcrumb: 'Create AI Operation', icon: 'add' },
              },
              {
                path: 'edit/:id',
                loadComponent: () =>
                  import('./pages/use-cases/use-case-wizard.component').then(
                    (m) => m.UseCaseWizardComponent
                  ),
                data: { breadcrumb: 'Edit AI Operation', icon: 'edit' },
              },
              {
                path: ':id',
                loadComponent: () =>
                  import(
                    './pages/use-case-execution/use-case-execution.component'
                  ).then((m) => m.UseCaseExecutionComponent),
                data: { breadcrumb: 'AIOps Execution', icon: 'play_arrow' },
              },
              {
                path: 'view/:id',
                loadComponent: () =>
                  import('./pages/use-cases/use-case-wizard.component').then(
                    (m) => m.UseCaseWizardComponent
                  ),
                data: { breadcrumb: 'View AI Operation', icon: 'visibility' },
              },
            ],
          },
          // Pattern Library - Week 2 implementation
          {
            path: 'patterns',
            loadComponent: () =>
              import('./pages/patterns/pattern-library.component').then(
                (m) => m.PatternLibraryComponent
              ),
            data: { breadcrumb: 'Pattern Library', icon: 'library_books' },
          },
          // Query Developer Tools - P4-TOOLS-04
          {
            path: 'query-tools',
            loadComponent: () =>
              import(
                './pages/query-developer-tools/query-developer-tools.component'
              ).then((m) => m.QueryDeveloperToolsComponent),
            data: { breadcrumb: 'Query Developer Tools', icon: 'science' },
          },
          // Tool Testing - T6-F4
          {
            path: 'tools/test',
            loadComponent: () =>
              import('./pages/dev/tool-testing/tool-testing.component').then(
                (m) => m.ToolTestingComponent
              ),
            data: { breadcrumb: 'Tool Testing', icon: 'science' },
          },
          // Intent Model Configuration - ADR-069 (admin only)
          {
            path: 'intent-model-config',
            loadComponent: () =>
              import(
                './pages/dev/intent-model-config/intent-model-config.component'
              ).then((m) => m.IntentModelConfigComponent),
            data: {
              breadcrumb: 'Intents Management',
              icon: 'tune',
            },
          },
        ],
      },
      {
        path: 'admin',
        data: { breadcrumb: 'Administration', icon: 'admin_panel_settings' },
        children: [
          // Use Case Approval - Week 3 implementation
          // {
          //     path: 'approvals',
          //     loadComponent: () =>
          //         import('./pages/admin/use-case-approvals.component').then((m) => m.UseCaseApprovalsComponent),
          //     data: { breadcrumb: 'Use Case Approval', icon: 'verified' }
          // },
          {
            path: 'users',
            loadComponent: () =>
              import('./pages/admin/user-management.component').then(
                (m) => m.UserManagementComponent
              ),
            data: { breadcrumb: 'User Management', icon: 'people' },
          },
          {
            path: 'roles',
            loadComponent: () =>
              import(
                './pages/admin/role-management/role-management.component'
              ).then((m) => m.RoleManagementComponent),
            data: { breadcrumb: 'Role Management', icon: 'manage_accounts' },
          },
          {
            path: 'developer-teams',
            loadComponent: () =>
              import(
                './pages/admin/developer-teams/developer-teams.component'
              ).then((m) => m.DeveloperTeamsComponent),
            data: { breadcrumb: 'Developer Teams', icon: 'groups_3' },
          },
          {
            path: 'use-case-developer',
            loadComponent: () =>
              import(
                './pages/admin/use-case-developer/use-case-developer.component'
              ).then((m) => m.UseCaseDeveloperComponent),
            data: { breadcrumb: 'AIO Manager', icon: 'psychology' },
          },
          {
            path: 'roles/grouping',
            loadComponent: () =>
              import(
                './pages/admin/use-case-role-management/use-case-role-management.component'
              ).then((m) => m.UseCaseRoleManagementComponent),
            data: { breadcrumb: 'Grouping Roles', icon: 'groups' },
          },
          {
            path: 'system',
            loadComponent: () =>
              import(
                './pages/admin/system-config/system-config.component'
              ).then((m) => m.SystemConfigComponent),
            data: { breadcrumb: 'System Configuration', icon: 'settings' },
          },
          {
            path: 'audit',
            loadComponent: () =>
              import('./pages/admin/audit-logs/audit-logs.component').then(
                (m) => m.AuditLogsComponent
              ),
            data: { breadcrumb: 'Audit Logs', icon: 'assignment' },
          },
          {
            path: 'models',
            loadComponent: () =>
              import('./pages/admin/model-management.component').then(
                (m) => m.ModelManagementComponent
              ),
            data: { breadcrumb: 'Model Management', icon: 'psychology' },
          },
          {
            path: 'token-usage',
            loadComponent: () =>
              import('./pages/admin/token-usage-dashboard.component').then(
                (m) => m.TokenUsageDashboardComponent
              ),
            data: { breadcrumb: 'Token Usage', icon: 'analytics' },
          },
          {
            path: 'providers',
            loadComponent: () =>
              import(
                './pages/admin/provider-management/provider-management.component'
              ).then((m) => m.ProviderManagementComponent),
            data: { breadcrumb: 'Provider Management', icon: 'cloud_queue' },
          },
          // More specific tool routes must come before generic 'tools' route
          {
            path: 'tools/health',
            loadComponent: () =>
              import('./pages/admin/tool-health/tool-health.component').then(
                (m) => m.ToolHealthComponent
              ),
            data: { breadcrumb: 'Tool Health', icon: 'monitor_heart' },
          },
          {
            path: 'tools/analytics',
            loadComponent: () =>
              import(
                './pages/admin/tool-analytics/tool-analytics.component'
              ).then((m) => m.ToolAnalyticsComponent),
            data: { breadcrumb: 'Tool Analytics', icon: 'analytics' },
          },
          {
            path: 'tools/register',
            loadComponent: () =>
              import(
                './pages/admin/tool-registration-wizard/tool-registration-wizard.component'
              ).then((m) => m.ToolRegistrationWizardComponent),
            data: { breadcrumb: 'Register Tool', icon: 'add_circle' },
          },
          {
            path: 'tools',
            loadComponent: () =>
              import(
                './pages/admin/tool-management/tool-management.component'
              ).then((m) => m.ToolManagementComponent),
            data: { breadcrumb: 'Tool Management', icon: 'build' },
          },
          {
            path: 'gateway-metrics',
            loadComponent: () =>
              import(
                './pages/admin/gateway-metrics/gateway-metrics.component'
              ).then((m) => m.GatewayMetricsComponent),
            data: { breadcrumb: 'Inference Gateway Metrics', icon: 'insights' },
          },
          {
            path: 'collections',
            loadComponent: () =>
              import('./pages/collections/collection-list.component').then(
                (m) => m.CollectionListComponent
              ),
            data: { breadcrumb: 'Collection Management', icon: 'inventory_2' },
          },
          {
            path: '',
            redirectTo: 'users',
            pathMatch: 'full',
          },
        ],
      },
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full',
      },
    ],
  },
  {
    path: '**',
    redirectTo: 'dashboard',
    pathMatch: 'full',
  },
];
