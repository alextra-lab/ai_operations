/**
 * EnterToExecuteDirective
 *
 * Keyboard handler for textarea elements that triggers execution on Enter key.
 *
 * Features:
 * - Enter key triggers execution (preventDefault)
 * - Shift+Enter creates newline (default behavior)
 * - Toggle enabled/disabled
 * - Save preference to localStorage
 *
 * Usage:
 * ```html
 * <textarea
 *   appEnterToExecute
 *   [disabled]="isExecuting"
 *   (executeTriggered)="onExecute()">
 * </textarea>
 * ```
 *
 * Related: P4-TOOLS-01, ADR-045
 */

import {
  Directive,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  OnInit,
  Output,
} from '@angular/core';

const STORAGE_KEY = 'enterToExecuteEnabled';

@Directive({
  selector: 'textarea[appEnterToExecute]',
  standalone: true,
})
export class EnterToExecuteDirective implements OnInit {
  /**
   * Whether the directive is enabled
   * Can be toggled by user preference
   */
  @Input() appEnterToExecute = true;

  /**
   * Whether the textarea is disabled (during execution)
   */
  @Input() disabled = false;

  /**
   * Event emitted when Enter key is pressed
   */
  @Output() executeTriggered = new EventEmitter<void>();

  constructor(private el: ElementRef<HTMLTextAreaElement>) {}

  ngOnInit(): void {
    // Load saved preference from localStorage
    this.loadPreference();
  }

  /**
   * Handle keyboard events
   */
  @HostListener('keydown', ['$event'])
  onKeyDown(event: KeyboardEvent): void {
    // Check if Enter key without Shift
    if (event.key === 'Enter' && !event.shiftKey) {
      // Only trigger if enabled and not disabled
      if (this.appEnterToExecute && !this.disabled) {
        event.preventDefault(); // Prevent newline
        this.executeTriggered.emit();
      }
    }
    // Shift+Enter allows newline (default behavior)
  }

  /**
   * Load preference from localStorage
   */
  private loadPreference(): void {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved !== null) {
        this.appEnterToExecute = saved === 'true';
      }
    } catch (error) {
      // localStorage not available (e.g., private mode)
      console.warn('localStorage not available:', error);
    }
  }

  /**
   * Save preference to localStorage
   * Call this method when user toggles the preference
   */
  setEnabled(enabled: boolean): void {
    this.appEnterToExecute = enabled;

    try {
      localStorage.setItem(STORAGE_KEY, String(enabled));
    } catch (error) {
      console.warn('Failed to save preference:', error);
    }
  }

  /**
   * Get current enabled state
   */
  isEnabled(): boolean {
    return this.appEnterToExecute;
  }
}
