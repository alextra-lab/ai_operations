import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatTooltipModule } from '@angular/material/tooltip';

import { UserProfile } from '../../../core/auth/auth.models';
import { MenuItem } from '../../../core/models/navigation.models';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatDividerModule,
    MatExpansionModule,
    MatTooltipModule,
  ],
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.scss'],
})
export class SidebarComponent {
  @Input() menuItems: MenuItem[] = [];
  @Input() isCollapsed = false;
  @Input() currentUser: UserProfile | null = null;

  @Output() menuItemClick = new EventEmitter<MenuItem>();
  @Output() toggleCollapse = new EventEmitter<void>();

  readonly expandedPanels = signal<Set<string>>(new Set());

  onMenuItemClick(menuItem: MenuItem): void {
    if (menuItem.children && menuItem.children.length > 0) {
      // Toggle expansion for parent items
      this.toggleExpansion(menuItem.id);
    } else {
      // Navigate for leaf items
      this.menuItemClick.emit(menuItem);
    }
  }

  onToggleCollapse(): void {
    this.toggleCollapse.emit();
  }

  isPanelExpanded(menuItemId: string): boolean {
    return this.expandedPanels().has(menuItemId);
  }

  private toggleExpansion(menuItemId: string): void {
    const current = this.expandedPanels();
    const newSet = new Set(current);

    if (newSet.has(menuItemId)) {
      newSet.delete(menuItemId);
    } else {
      newSet.add(menuItemId);
    }

    this.expandedPanels.set(newSet);
  }

  getTooltipText(menuItem: MenuItem): string {
    if (!this.isCollapsed) {
      return '';
    }

    let tooltip = menuItem.label;
    if (menuItem.tooltip) {
      tooltip += ` - ${menuItem.tooltip}`;
    }
    return tooltip;
  }

  hasChildren(menuItem: MenuItem): boolean {
    return !!(menuItem.children && menuItem.children.length > 0);
  }

  getMenuItemIcon(menuItem: MenuItem): string {
    return menuItem.icon || 'circle';
  }

  getMenuItemLabel(menuItem: MenuItem): string {
    return menuItem.label;
  }

  isMenuItemDisabled(menuItem: MenuItem): boolean {
    return menuItem.disabled || false;
  }

  hasBadge(menuItem: MenuItem): boolean {
    return !!menuItem.badge;
  }

  getBadgeText(menuItem: MenuItem): string {
    return menuItem.badge?.text || '';
  }

  getBadgeColor(menuItem: MenuItem): string {
    return menuItem.badge?.color || 'primary';
  }

  trackByMenuItemId(index: number, menuItem: MenuItem): string {
    return menuItem.id;
  }
}
