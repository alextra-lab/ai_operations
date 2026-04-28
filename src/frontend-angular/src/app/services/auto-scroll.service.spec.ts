/**
 * AutoScrollService Unit Tests
 *
 * Tests for automatic scrolling behavior during streaming responses.
 * Target: 80%+ coverage
 */

import { TestBed } from '@angular/core/testing';
import { AutoScrollService } from './auto-scroll.service';

describe('AutoScrollService', () => {
  let service: AutoScrollService;
  let mockElement: HTMLElement;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AutoScrollService],
    });
    service = TestBed.inject(AutoScrollService);

    // Create mock HTML element
    mockElement = document.createElement('div');
    Object.defineProperty(mockElement, 'scrollTop', {
      writable: true,
      value: 0,
    });
    Object.defineProperty(mockElement, 'scrollHeight', {
      writable: true,
      value: 1000,
    });
    Object.defineProperty(mockElement, 'clientHeight', {
      writable: true,
      value: 500,
    });
    // Mock scrollTo method
    mockElement.scrollTo = jest.fn();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // ========================================================================
  // isScrolledToBottom Tests
  // ========================================================================

  describe('isScrolledToBottom', () => {
    it('should return true when scrolled to bottom', () => {
      mockElement.scrollTop = 500; // scrollHeight - clientHeight
      const result = service.isScrolledToBottom(mockElement);
      expect(result).toBe(true);
    });

    it('should return true when within threshold', () => {
      mockElement.scrollTop = 470; // 30px from bottom
      const result = service.isScrolledToBottom(mockElement, 50);
      expect(result).toBe(true);
    });

    it('should return false when not at bottom', () => {
      mockElement.scrollTop = 100;
      const result = service.isScrolledToBottom(mockElement);
      expect(result).toBe(false);
    });

    it('should return false for null element', () => {
      const result = service.isScrolledToBottom(null as any);
      expect(result).toBe(false);
    });

    it('should use custom threshold', () => {
      mockElement.scrollTop = 480; // 20px from bottom
      expect(service.isScrolledToBottom(mockElement, 10)).toBe(false);
      expect(service.isScrolledToBottom(mockElement, 30)).toBe(true);
    });
  });

  // ========================================================================
  // scrollToBottom Tests
  // ========================================================================

  describe('scrollToBottom', () => {
    it('should scroll element to bottom', (done) => {
      const scrollToSpy = jest.spyOn(mockElement, 'scrollTo');

      service.scrollToBottom(mockElement);

      // Wait for setTimeout
      setTimeout(() => {
        expect(scrollToSpy).toHaveBeenCalledWith({
          top: mockElement.scrollHeight,
          behavior: 'smooth',
        });
        done();
      }, 100);
    });

    it('should use custom scroll behavior', (done) => {
      const scrollToSpy = jest.spyOn(mockElement, 'scrollTo');

      service.scrollToBottom(mockElement, { behavior: 'auto' });

      setTimeout(() => {
        expect(scrollToSpy).toHaveBeenCalledWith({
          top: mockElement.scrollHeight,
          behavior: 'auto',
        });
        done();
      }, 100);
    });

    it('should handle null element gracefully', () => {
      expect(() => {
        service.scrollToBottom(null as any);
      }).not.toThrow();
    });
  });

  // ========================================================================
  // scrollToElement Tests
  // ========================================================================

  describe('scrollToElement', () => {
    let container: HTMLElement;
    let target: HTMLElement;

    beforeEach(() => {
      container = document.createElement('div');
      target = document.createElement('div');

      // Mock getBoundingClientRect
      jest.spyOn(container, 'getBoundingClientRect').mockReturnValue({
        top: 100,
        left: 0,
        right: 500,
        bottom: 600,
        width: 500,
        height: 500,
        x: 0,
        y: 100,
        toJSON: () => ({}),
      });

      jest.spyOn(target, 'getBoundingClientRect').mockReturnValue({
        top: 300,
        left: 0,
        right: 500,
        bottom: 400,
        width: 500,
        height: 100,
        x: 0,
        y: 300,
        toJSON: () => ({}),
      });

      Object.defineProperty(container, 'scrollTop', {
        writable: true,
        value: 0,
      });

      // Mock scrollTo method
      container.scrollTo = jest.fn();
    });

    it('should scroll to target element', () => {
      const scrollToSpy = jest.spyOn(container, 'scrollTo');

      service.scrollToElement(container, target);

      // Offset = targetTop(300) - containerTop(100) + scrollTop(0)
      expect(scrollToSpy).toHaveBeenCalledWith({
        top: 200,
        behavior: 'smooth',
      });
    });

    it('should handle null container', () => {
      expect(() => {
        service.scrollToElement(null as any, target);
      }).not.toThrow();
    });

    it('should handle null target', () => {
      expect(() => {
        service.scrollToElement(container, null as any);
      }).not.toThrow();
    });
  });

  // ========================================================================
  // scrollToTop Tests
  // ========================================================================

  describe('scrollToTop', () => {
    it('should scroll element to top', () => {
      const scrollToSpy = jest.spyOn(mockElement, 'scrollTo');
      mockElement.scrollTop = 500;

      service.scrollToTop(mockElement);

      expect(scrollToSpy).toHaveBeenCalledWith({
        top: 0,
        behavior: 'smooth',
      });
    });

    it('should handle null element', () => {
      expect(() => {
        service.scrollToTop(null as any);
      }).not.toThrow();
    });
  });

  // ========================================================================
  // createScrollObserver Tests
  // ========================================================================

  describe('createScrollObserver', () => {
    it('should create observable that emits scroll state', (done) => {
      mockElement.scrollTop = 0;

      const observable = service.createScrollObserver(mockElement);

      observable.subscribe((isAtBottom) => {
        expect(typeof isAtBottom).toBe('boolean');
        done();
      });

      // Trigger scroll event
      mockElement.dispatchEvent(new Event('scroll'));
    });

    it('should call callback when provided', (done) => {
      mockElement.scrollTop = 500;

      const callback = jest.fn();
      const observable = service.createScrollObserver(mockElement, callback);

      observable.subscribe(() => {
        expect(callback).toHaveBeenCalledWith(true);
        done();
      });

      mockElement.dispatchEvent(new Event('scroll'));
    });

    it('should debounce scroll events', (done) => {
      const callback = jest.fn();
      const observable = service.createScrollObserver(
        mockElement,
        callback,
        50
      );

      observable.subscribe();

      // Trigger multiple scroll events
      mockElement.dispatchEvent(new Event('scroll'));
      mockElement.dispatchEvent(new Event('scroll'));
      mockElement.dispatchEvent(new Event('scroll'));

      setTimeout(() => {
        // Should only call once due to debounce
        expect(callback).toHaveBeenCalledTimes(1);
        done();
      }, 100);
    });
  });

  // ========================================================================
  // isScrolledToTop Tests
  // ========================================================================

  describe('isScrolledToTop', () => {
    it('should return true when at top', () => {
      mockElement.scrollTop = 0;
      expect(service.isScrolledToTop(mockElement)).toBe(true);
    });

    it('should return true when within threshold', () => {
      mockElement.scrollTop = 5;
      expect(service.isScrolledToTop(mockElement, 10)).toBe(true);
    });

    it('should return false when not at top', () => {
      mockElement.scrollTop = 100;
      expect(service.isScrolledToTop(mockElement)).toBe(false);
    });

    it('should handle null element', () => {
      expect(service.isScrolledToTop(null as any)).toBe(false);
    });
  });

  // ========================================================================
  // getScrollPercentage Tests
  // ========================================================================

  describe('getScrollPercentage', () => {
    it('should return 0 when at top', () => {
      mockElement.scrollTop = 0;
      expect(service.getScrollPercentage(mockElement)).toBe(0);
    });

    it('should return 100 when at bottom', () => {
      mockElement.scrollTop = 500;
      expect(service.getScrollPercentage(mockElement)).toBe(100);
    });

    it('should return 50 when halfway', () => {
      mockElement.scrollTop = 250;
      expect(service.getScrollPercentage(mockElement)).toBe(50);
    });

    it('should return 100 when no scrolling needed', () => {
      Object.defineProperty(mockElement, 'scrollHeight', {
        writable: true,
        value: 500,
      });
      expect(service.getScrollPercentage(mockElement)).toBe(100);
    });

    it('should handle null element', () => {
      expect(service.getScrollPercentage(null as any)).toBe(0);
    });
  });

  // ========================================================================
  // scrollToPercentage Tests
  // ========================================================================

  describe('scrollToPercentage', () => {
    it('should scroll to 0%', () => {
      const scrollToSpy = jest.spyOn(mockElement, 'scrollTo');

      service.scrollToPercentage(mockElement, 0);

      expect(scrollToSpy).toHaveBeenCalledWith({
        top: 0,
        behavior: 'smooth',
      });
    });

    it('should scroll to 50%', () => {
      const scrollToSpy = jest.spyOn(mockElement, 'scrollTo');

      service.scrollToPercentage(mockElement, 50);

      expect(scrollToSpy).toHaveBeenCalledWith({
        top: 250, // 50% of (1000 - 500)
        behavior: 'smooth',
      });
    });

    it('should scroll to 100%', () => {
      const scrollToSpy = jest.spyOn(mockElement, 'scrollTo');

      service.scrollToPercentage(mockElement, 100);

      expect(scrollToSpy).toHaveBeenCalledWith({
        top: 500,
        behavior: 'smooth',
      });
    });

    it('should handle null element', () => {
      expect(() => {
        service.scrollToPercentage(null as any, 50);
      }).not.toThrow();
    });
  });
});
