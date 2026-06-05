import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnInit,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';

import { DeveloperTeamInfo } from '../role-management/models/role-management.models';
import { DeveloperTeamsService } from './services/developer-teams.service';
import { LucideAngularModule } from 'lucide-angular';

const TEAM_PATTERN = /^team:[a-z0-9_-]{1,64}$/;

@Component({
  selector: 'app-developer-teams',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './developer-teams.component.html',
  styleUrls: ['./developer-teams.component.scss'],
})
export class DeveloperTeamsComponent implements OnInit {
  teams: DeveloperTeamInfo[] = [];
  isLoading = false;
  isSaving = false;
  error: string | null = null;

  newTeamId = '';
  initialMemberId = '';

  displayedColumns: string[] = [
    'team_id',
    'member_count',
    'draft_count',
    'published_count',
    'actions',
  ];

  constructor(
    private readonly teamsService: DeveloperTeamsService,
    private readonly snackBar: MatSnackBar,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadTeams();
  }

  loadTeams(): void {
    this.isLoading = true;
    this.error = null;
    this.cdr.markForCheck();

    this.teamsService.listTeams().subscribe({
      next: (teams) => {
        this.teams = teams;
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to load teams', err);
        this.error = 'Failed to load teams';
        this.isLoading = false;
        this.cdr.markForCheck();
      },
    });
  }

  createTeam(): void {
    const teamId = this.newTeamId.trim();
    const memberId = this.initialMemberId.trim() || undefined;

    if (!teamId) {
      this.error = 'Team ID is required';
      this.cdr.markForCheck();
      return;
    }

    if (!TEAM_PATTERN.test(teamId)) {
      this.error =
        'Invalid team ID. Format: team:[a-z0-9_-]{1,64} (lowercase only).';
      this.cdr.markForCheck();
      return;
    }

    this.isSaving = true;
    this.error = null;
    this.cdr.markForCheck();

    this.teamsService.createTeam(teamId, memberId).subscribe({
      next: () => {
        this.snackBar.open('Team created', 'Close', { duration: 3000 });
        this.newTeamId = '';
        this.initialMemberId = '';
        this.isSaving = false;
        this.loadTeams();
      },
      error: (err) => {
        console.error('Failed to create team', err);
        this.error = 'Failed to create team';
        this.isSaving = false;
        this.cdr.markForCheck();
      },
    });
  }

  removeMember(team: DeveloperTeamInfo, userId: string): void {
    const confirmed = window.confirm(
      `Remove member ${userId} from ${team.team_id}?`
    );

    if (!confirmed) {
      return;
    }

    this.isSaving = true;
    this.cdr.markForCheck();

    this.teamsService.removeMember(team.team_id, userId).subscribe({
      next: () => {
        this.snackBar.open('Member removed', 'Close', { duration: 3000 });
        this.isSaving = false;
        this.loadTeams();
      },
      error: (err) => {
        console.error('Failed to remove member', err);
        this.error = 'Failed to remove member';
        this.isSaving = false;
        this.cdr.markForCheck();
      },
    });
  }
}
