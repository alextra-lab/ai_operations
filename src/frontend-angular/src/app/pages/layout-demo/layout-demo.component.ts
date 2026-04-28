import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';

@Component({
  selector: 'app-layout-demo',
  standalone: true,
  imports: [
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
  ],
  template: `
    <div class="layout-demo-container">
      <!-- Top Toolbar -->
      <mat-toolbar color="primary" class="demo-toolbar">
        <button mat-icon-button>
          <mat-icon>menu</mat-icon>
        </button>
        <span>AI Operations Platform - P1-F3 Layout Demo</span>
        <span class="spacer"></span>
        <span>Demo User (admin, corpus_admin, user)</span>
      </mat-toolbar>

      <!-- Quick Actions Bar -->
      <div class="quick-actions-bar">
        <div class="quick-actions-container">
          <span class="quick-actions-title">
            <mat-icon>flash_on</mat-icon>
            Quick Actions
          </span>
          <div class="quick-actions-list">
            <button mat-raised-button color="primary">
              <mat-icon>search</mat-icon>
              New Query
            </button>
            <button mat-raised-button color="accent">
              <mat-icon>upload</mat-icon>
              Upload Document
            </button>
            <button mat-raised-button>
              <mat-icon>analytics</mat-icon>
              View Analytics
            </button>
            <button mat-raised-button>
              <mat-icon>add_task</mat-icon>
              Create Template
            </button>
            <button mat-raised-button>
              <mat-icon>admin_panel_settings</mat-icon>
              Admin Panel
            </button>
          </div>
        </div>
      </div>

      <!-- Main Content -->
      <div class="main-content">
        <div class="content-grid">
          <!-- Sidebar Demo -->
          <mat-card class="demo-card">
            <mat-card-header>
              <mat-card-title>
                <mat-icon>menu</mat-icon>
                Sidebar Navigation
              </mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <mat-list>
                <mat-list-item>
                  <mat-icon matListItemIcon>dashboard</mat-icon>
                  <span matListItemTitle>Dashboard</span>
                </mat-list-item>
                <mat-list-item>
                  <mat-icon matListItemIcon>search</mat-icon>
                  <span matListItemTitle>Query Interface</span>
                </mat-list-item>
                <mat-list-item>
                  <mat-icon matListItemIcon>folder</mat-icon>
                  <span matListItemTitle>Document Management</span>
                </mat-list-item>
                <mat-list-item>
                  <mat-icon matListItemIcon>analytics</mat-icon>
                  <span matListItemTitle>Analytics</span>
                </mat-list-item>
                <mat-list-item>
                  <mat-icon matListItemIcon>template</mat-icon>
                  <span matListItemTitle>Templates</span>
                </mat-list-item>
                <mat-list-item>
                  <mat-icon matListItemIcon>admin_panel_settings</mat-icon>
                  <span matListItemTitle>Administration</span>
                </mat-list-item>
              </mat-list>
            </mat-card-content>
          </mat-card>

          <!-- Features Demo -->
          <mat-card class="demo-card">
            <mat-card-header>
              <mat-card-title>
                <mat-icon>check_circle</mat-icon>
                P1-F3 Implementation Status
              </mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <div class="feature-list">
                <div class="feature-item">
                  <mat-icon class="feature-icon">check</mat-icon>
                  <span
                    >Main Layout Component - Responsive sidebar navigation</span
                  >
                </div>
                <div class="feature-item">
                  <mat-icon class="feature-icon">check</mat-icon>
                  <span>Navigation Service - Role-based menu generation</span>
                </div>
                <div class="feature-item">
                  <mat-icon class="feature-icon">check</mat-icon>
                  <span>Sidebar Component - Dynamic menu items</span>
                </div>
                <div class="feature-item">
                  <mat-icon class="feature-icon">check</mat-icon>
                  <span>Breadcrumb Navigation - Deep workflow support</span>
                </div>
                <div class="feature-item">
                  <mat-icon class="feature-icon">check</mat-icon>
                  <span>Quick Actions Bar - Common actions toolbar</span>
                </div>
                <div class="feature-item">
                  <mat-icon class="feature-icon">check</mat-icon>
                  <span>Keyboard Shortcuts - Power user support</span>
                </div>
                <div class="feature-item">
                  <mat-icon class="feature-icon">check</mat-icon>
                  <span>Accessibility - WCAG 2.1 AA compliance</span>
                </div>
              </div>
            </mat-card-content>
          </mat-card>

          <!-- User Info Demo -->
          <mat-card class="demo-card">
            <mat-card-header>
              <mat-card-title>
                <mat-icon>account_circle</mat-icon>
                User Information
              </mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <div class="user-info">
                <div class="user-detail"><strong>Name:</strong> Demo User</div>
                <div class="user-detail">
                  <strong>Username:</strong> demo-user
                </div>
                <div class="user-detail">
                  <strong>Roles:</strong> admin, corpus_admin, user
                </div>
              </div>
            </mat-card-content>
          </mat-card>

          <!-- System Overview Demo -->
          <mat-card class="demo-card">
            <mat-card-header>
              <mat-card-title>
                <mat-icon>dashboard</mat-icon>
                System Overview
              </mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <div class="stat-item">
                <span class="stat-value">Active</span>
                <span class="stat-label">System Status</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">3</span>
                <span class="stat-label">User Roles</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">P1-F3</span>
                <span class="stat-label">Current Phase</span>
              </div>
            </mat-card-content>
          </mat-card>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .layout-demo-container {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
      }

      .demo-toolbar {
        position: sticky;
        top: 0;
        z-index: 1000;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      }

      .spacer {
        flex: 1;
      }

      .quick-actions-bar {
        background-color: var(--mat-surface-container-color);
        border-bottom: 1px solid var(--mat-divider-color);
        padding: 8px 16px;
      }

      .quick-actions-container {
        display: flex;
        align-items: center;
        gap: 16px;
      }

      .quick-actions-title {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--mat-on-surface-variant-color);
        font-size: 14px;
        font-weight: 500;
        white-space: nowrap;
      }

      .quick-actions-list {
        display: flex;
        align-items: center;
        gap: 8px;
        overflow-x: auto;
      }

      .main-content {
        flex: 1;
        padding: 24px;
        background-color: var(--mat-app-background-color);
      }

      .content-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 24px;
        max-width: 1200px;
        margin: 0 auto;
      }

      .demo-card {
        mat-card-header {
          mat-card-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 18px;
            font-weight: 500;

            mat-icon {
              color: var(--mat-primary-color);
            }
          }
        }

        mat-card-content {
          .feature-list {
            .feature-item {
              display: flex;
              align-items: center;
              gap: 12px;
              padding: 8px 0;
              border-bottom: 1px solid var(--mat-divider-color);

              &:last-child {
                border-bottom: none;
              }

              .feature-icon {
                color: #4caf50;
                font-size: 20px;
                width: 20px;
                height: 20px;
              }
            }
          }

          .user-info {
            .user-detail {
              padding: 8px 0;
              border-bottom: 1px solid var(--mat-divider-color);

              &:last-child {
                border-bottom: none;
              }

              strong {
                color: var(--mat-on-surface-color);
              }
            }
          }

          .stat-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid var(--mat-divider-color);

            &:last-child {
              border-bottom: none;
            }

            .stat-value {
              font-size: 24px;
              font-weight: 600;
              color: var(--mat-primary-color);
            }

            .stat-label {
              color: var(--mat-on-surface-variant-color);
            }
          }
        }
      }

      @media (max-width: 768px) {
        .main-content {
          padding: 16px;
        }

        .content-grid {
          grid-template-columns: 1fr;
          gap: 16px;
        }

        .quick-actions-container {
          flex-direction: column;
          gap: 12px;
        }

        .quick-actions-list {
          flex-wrap: wrap;
          justify-content: center;
        }
      }
    `,
  ],
})
export class LayoutDemoComponent {}
