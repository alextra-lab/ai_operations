import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { Router } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-unauthorized',
  standalone: true,
  imports: [
    LucideAngularModule,MatCardModule, MatButtonModule],
  template: `
    <mat-card class="unauthorized-card">
      <mat-card-header>
        <lucide-icon mat-card-avatar color="warn" name="ban"></lucide-icon>
        <mat-card-title>Access Denied</mat-card-title>
        <mat-card-subtitle
          >You don't have permission to access this resource</mat-card-subtitle
        >
      </mat-card-header>
      <mat-card-content>
        <p>
          Your account doesn't have the required permissions to view this page.
          Please contact your administrator if you believe this is an error.
        </p>
        <div class="actions">
          <button mat-raised-button color="primary" (click)="goBack()">
            <lucide-icon name="arrow-left"></lucide-icon>
            Go Back
          </button>
          <button mat-button (click)="goHome()">
            <lucide-icon name="home"></lucide-icon>
            Home
          </button>
        </div>
      </mat-card-content>
    </mat-card>
  `,
  styles: [
    `
      :host {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: calc(100vh - 64px);
        background: radial-gradient(circle at top, #f0f4ff, #e6f9f7 70%);
      }
      .unauthorized-card {
        max-width: 500px;
        width: 100%;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        border-radius: 8px;
        text-align: center;
      }
      mat-card-title {
        color: #f44336;
        margin-bottom: 10px;
      }
      mat-card-subtitle {
        color: #666;
        margin-bottom: 20px;
      }
      .actions {
        margin-top: 20px;
        display: flex;
        gap: 10px;
        justify-content: center;
        flex-wrap: wrap;
      }
      button {
        margin: 5px;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UnauthorizedComponent {
  private readonly router = inject(Router);

  goBack(): void {
    window.history.back();
  }

  goHome(): void {
    void this.router.navigate(['/dashboard']);
  }
}
