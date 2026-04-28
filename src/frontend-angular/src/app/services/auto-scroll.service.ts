/**
 * AutoScrollService
 *
 * Manages automatic scrolling behavior during streaming responses.
 *
 * Features:
 * - Detect if scrolled to bottom
 * - Smooth scroll to bottom/element
 * - User manual scroll detection
 * - Scroll observer with debouncing
 *
 * Related: P4-TOOLS-01, ADR-045
 */

import { Injectable } from '@angular/core';
import {
  debounceTime,
  distinctUntilChanged,
  fromEvent,
  map,
  Observable,
  tap,
} from 'rxjs';

export interface ScrollOptions {
  behavior?: ScrollBehavior;
  block?: ScrollLogicalPosition;
  inline?: ScrollLogicalPosition;
}

@Injectable({
  providedIn: 'root',
})
export class AutoScrollService {
  /**
   * Check if element is scrolled to bottom (within threshold)
   *
   * @param element - HTML element to check
   * @param threshold - Pixel threshold for "at bottom" detection
   * @returns true if scrolled to bottom
   */
  isScrolledToBottom(element: HTMLElement, threshold = 50): boolean {
    if (!element) {
      return false;
    }

    const scrollTop = element.scrollTop;
    const scrollHeight = element.scrollHeight;
    const clientHeight = element.clientHeight;

    return scrollHeight - scrollTop - clientHeight <= threshold;
  }

  /**
   * Scroll element to bottom with smooth animation
   *
   * @param element - HTML element to scroll
   * @param options - Scroll behavior options
   */
  scrollToBottom(element: HTMLElement, options?: ScrollOptions): void {
    if (!element) {
      return;
    }

    // Small delay to ensure DOM updated
    setTimeout(() => {
      element.scrollTo({
        top: element.scrollHeight,
        behavior: options?.behavior || 'smooth',
      });
    }, 50);
  }

  /**
   * Scroll to specific element within container
   *
   * @param container - Container element
   * @param target - Target element to scroll to
   * @param options - Scroll behavior options
   */
  scrollToElement(
    container: HTMLElement,
    target: HTMLElement,
    options?: ScrollOptions
  ): void {
    if (!container || !target) {
      return;
    }

    const containerRect = container.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();

    const scrollOffset =
      targetRect.top - containerRect.top + container.scrollTop;

    container.scrollTo({
      top: scrollOffset,
      behavior: options?.behavior || 'smooth',
    });
  }

  /**
   * Scroll to top of element
   *
   * @param element - HTML element to scroll
   * @param options - Scroll behavior options
   */
  scrollToTop(element: HTMLElement, options?: ScrollOptions): void {
    if (!element) {
      return;
    }

    element.scrollTo({
      top: 0,
      behavior: options?.behavior || 'smooth',
    });
  }

  /**
   * Create scroll observer for detecting user interaction
   *
   * Emits true when user scrolls to bottom, false otherwise.
   * Debounced to avoid excessive updates.
   *
   * @param element - HTML element to observe
   * @param callback - Optional callback for scroll events
   * @param debounceMs - Debounce time in milliseconds
   * @returns Observable of scroll-to-bottom state
   */
  createScrollObserver(
    element: HTMLElement,
    callback?: (isAtBottom: boolean) => void,
    debounceMs = 100
  ): Observable<boolean> {
    return fromEvent(element, 'scroll').pipe(
      debounceTime(debounceMs),
      map(() => this.isScrolledToBottom(element)),
      distinctUntilChanged(),
      tap((isAtBottom) => {
        if (callback) {
          callback(isAtBottom);
        }
      })
    );
  }

  /**
   * Check if element is scrolled to top
   *
   * @param element - HTML element to check
   * @param threshold - Pixel threshold for "at top" detection
   * @returns true if scrolled to top
   */
  isScrolledToTop(element: HTMLElement, threshold = 10): boolean {
    if (!element) {
      return false;
    }

    return element.scrollTop <= threshold;
  }

  /**
   * Get scroll percentage (0-100)
   *
   * @param element - HTML element to check
   * @returns Scroll percentage (0 = top, 100 = bottom)
   */
  getScrollPercentage(element: HTMLElement): number {
    if (!element) {
      return 0;
    }

    const scrollTop = element.scrollTop;
    const scrollHeight = element.scrollHeight;
    const clientHeight = element.clientHeight;

    if (scrollHeight === clientHeight) {
      return 100; // No scrolling needed
    }

    const maxScroll = scrollHeight - clientHeight;
    return (scrollTop / maxScroll) * 100;
  }

  /**
   * Scroll to specific percentage
   *
   * @param element - HTML element to scroll
   * @param percentage - Target scroll percentage (0-100)
   * @param options - Scroll behavior options
   */
  scrollToPercentage(
    element: HTMLElement,
    percentage: number,
    options?: ScrollOptions
  ): void {
    if (!element) {
      return;
    }

    const scrollHeight = element.scrollHeight;
    const clientHeight = element.clientHeight;
    const maxScroll = scrollHeight - clientHeight;

    const targetScroll = (percentage / 100) * maxScroll;

    element.scrollTo({
      top: targetScroll,
      behavior: options?.behavior || 'smooth',
    });
  }
}
