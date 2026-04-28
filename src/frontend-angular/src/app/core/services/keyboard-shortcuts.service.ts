import { inject, Injectable, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { fromEvent, Subject } from 'rxjs';
import { filter, takeUntil } from 'rxjs/operators';

import { AuthService } from '../auth/auth.service';
import { KeyboardShortcut } from '../models/navigation.models';

@Injectable({ providedIn: 'root' })
export class KeyboardShortcutsService implements OnDestroy {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly destroy$ = new Subject<void>();

  private shortcuts = new Map<string, KeyboardShortcut>();
  private readonly keyEvent$ = fromEvent<KeyboardEvent>(document, 'keydown');

  constructor() {
    this.setupKeyboardListener();
    this.registerDefaultShortcuts();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Register a keyboard shortcut
   */
  registerShortcut(shortcut: KeyboardShortcut): void {
    const key = this.generateShortcutKey(shortcut);
    this.shortcuts.set(key, shortcut);
  }

  /**
   * Unregister a keyboard shortcut
   */
  unregisterShortcut(key: string): void {
    this.shortcuts.delete(key);
  }

  /**
   * Get all registered shortcuts for current user
   */
  getAvailableShortcuts(): KeyboardShortcut[] {
    const currentUser = this.authService.getCurrentUser();
    return Array.from(this.shortcuts.values()).filter((shortcut) => {
      if (!shortcut.roles || shortcut.roles.length === 0) {
        return true;
      }
      // This is a simplified check - in a real app you'd subscribe to user changes
      return true; // For now, assume user has appropriate roles
    });
  }

  /**
   * Check if a shortcut key combination is already registered
   */
  isShortcutRegistered(
    key: string,
    ctrlKey = false,
    altKey = false,
    shiftKey = false,
    metaKey = false
  ): boolean {
    const shortcutKey = this.generateShortcutKey({
      key,
      ctrlKey,
      altKey,
      shiftKey,
      metaKey,
      callback: () => { },
      description: '',
    });
    return this.shortcuts.has(shortcutKey);
  }

  private setupKeyboardListener(): void {
    this.keyEvent$
      .pipe(
        filter((event) => !this.isInputElement(event.target as Element)),
        takeUntil(this.destroy$)
      )
      .subscribe((event) => {
        this.handleKeyEvent(event);
      });
  }

  private handleKeyEvent(event: KeyboardEvent): void {
    const shortcutKey = this.generateShortcutKey({
      key: event.key,
      ctrlKey: event.ctrlKey,
      altKey: event.altKey,
      shiftKey: event.shiftKey,
      metaKey: event.metaKey,
      callback: () => { },
      description: '',
    });

    const shortcut = this.shortcuts.get(shortcutKey);
    if (shortcut) {
      // Check if user has required roles
      if (shortcut.roles && shortcut.roles.length > 0) {
        const hasRole = shortcut.roles.some((role) =>
          this.authService.hasRole(role)
        );
        if (!hasRole) {
          return;
        }
      }

      if (shortcut.preventDefault) {
        event.preventDefault();
      }
      if (shortcut.stopPropagation) {
        event.stopPropagation();
      }

      shortcut.callback();
    }
  }

  private registerDefaultShortcuts(): void {
    // Navigation shortcuts
    this.registerShortcut({
      key: 'h',
      ctrlKey: true,
      callback: () => this.router.navigate(['/dashboard']),
      description: 'Go to Dashboard',
      roles: ['admin', 'corpus_admin', 'user'],
      preventDefault: true,
    });

    this.registerShortcut({
      key: 'n',
      ctrlKey: true,
      callback: () => this.router.navigate(['/query/semantic']),
      description: 'New Query',
      roles: ['admin', 'corpus_admin', 'user'],
      preventDefault: true,
    });

    this.registerShortcut({
      key: 'u',
      ctrlKey: true,
      callback: () => this.router.navigate(['/documents/upload']),
      description: 'Upload Document',
      roles: ['admin', 'corpus_admin', 'user'],
      preventDefault: true,
    });

    // Admin shortcuts
    this.registerShortcut({
      key: 'a',
      ctrlKey: true,
      altKey: true,
      callback: () => this.router.navigate(['/admin/users']),
      description: 'Admin Panel',
      roles: ['admin'],
      preventDefault: true,
    });

    // Search shortcuts
    this.registerShortcut({
      key: '/',
      callback: () => {
        const searchInput = document.querySelector(
          'input[type="search"]'
        ) as HTMLInputElement;
        if (searchInput) {
          searchInput.focus();
        }
      },
      description: 'Focus Search',
      roles: ['admin', 'corpus_admin', 'user'],
      preventDefault: true,
    });

    // Help shortcut
    this.registerShortcut({
      key: 'F1',
      callback: () => {
        // In a real app, this would open help documentation
      },
      description: 'Show Help',
      preventDefault: true,
    });

    // Escape to close modals/dialogs
    this.registerShortcut({
      key: 'Escape',
      callback: () => {
        // Close any open modals or dialogs
        const modal = document.querySelector('.mat-dialog-container');
        if (modal) {
          const closeButton = modal.querySelector(
            '[mat-dialog-close]'
          ) as HTMLElement;
          if (closeButton) {
            closeButton.click();
          }
        }
      },
      description: 'Close Modal/Dialog',
      preventDefault: false,
    });
  }

  private generateShortcutKey(shortcut: KeyboardShortcut): string {
    const parts: string[] = [];

    if (shortcut.ctrlKey) parts.push('ctrl');
    if (shortcut.altKey) parts.push('alt');
    if (shortcut.shiftKey) parts.push('shift');
    if (shortcut.metaKey) parts.push('meta');

    parts.push(shortcut.key.toLowerCase());

    return parts.join('+');
  }

  private isInputElement(element: Element): boolean {
    const tagName = element.tagName.toLowerCase();
    const inputTypes = ['input', 'textarea', 'select'];

    if (inputTypes.includes(tagName)) {
      return true;
    }

    if (tagName === 'input') {
      const inputElement = element as HTMLInputElement;
      const inputType = inputElement.type?.toLowerCase();
      // Allow shortcuts in search inputs
      if (inputType === 'search') {
        return false;
      }
      return true;
    }

    // Check if element is contenteditable
    if (element.hasAttribute('contenteditable')) {
      return true;
    }

    return false;
  }
}
