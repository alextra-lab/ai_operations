import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { QuickAction } from '../../../core/models/navigation.models';

@Component({
  selector: 'app-quick-actions-bar',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, MatTooltipModule],
  templateUrl: './quick-actions-bar.component.html',
  styleUrls: ['./quick-actions-bar.component.scss'],
})
export class QuickActionsBarComponent {
  @Input() quickActions: QuickAction[] = [];
  @Output() actionClick = new EventEmitter<QuickAction>();

  onActionClick(action: QuickAction): void {
    if (!action.disabled) {
      this.actionClick.emit(action);
    }
  }

  getActionIcon(action: QuickAction): string {
    return action.icon || 'circle';
  }

  getActionLabel(action: QuickAction): string {
    return action.label;
  }

  getActionTooltip(action: QuickAction): string {
    let tooltip = action.label;
    if (action.tooltip) {
      tooltip += ` - ${action.tooltip}`;
    }
    if (action.keyboardShortcut) {
      tooltip += ` (${action.keyboardShortcut})`;
    }
    return tooltip;
  }

  isActionDisabled(action: QuickAction): boolean {
    return action.disabled || false;
  }

  trackByActionId(index: number, action: QuickAction): string {
    return action.id;
  }
}
