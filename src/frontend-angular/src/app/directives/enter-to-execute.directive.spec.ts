/**
 * EnterToExecuteDirective Unit Tests
 *
 * Tests for keyboard handler directive.
 * Target: 80%+ coverage
 */

import { Component, DebugElement } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { EnterToExecuteDirective } from './enter-to-execute.directive';

// Host component for testing directive
@Component({
  template: `
    <textarea
      appEnterToExecute
      [disabled]="isDisabled"
      (executeTriggered)="onExecute()"
    >
    </textarea>
  `,
  standalone: true,
  imports: [EnterToExecuteDirective],
})
class TestHostComponent {
  isDisabled = false;
  executeCount = 0;

  onExecute(): void {
    this.executeCount++;
  }
}

describe('EnterToExecuteDirective', () => {
  let component: TestHostComponent;
  let fixture: ComponentFixture<TestHostComponent>;
  let textareaElement: HTMLTextAreaElement;
  let directiveInstance: EnterToExecuteDirective;
  let textareaDebug: DebugElement;

  beforeEach(async () => {
    // Clear localStorage before each test
    localStorage.clear();

    await TestBed.configureTestingModule({
      imports: [TestHostComponent, EnterToExecuteDirective],
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    component = fixture.componentInstance;

    textareaDebug = fixture.debugElement.query(
      By.directive(EnterToExecuteDirective)
    );
    textareaElement = textareaDebug.nativeElement;
    directiveInstance = textareaDebug.injector.get(EnterToExecuteDirective);

    fixture.detectChanges();
  });

  it('should create directive', () => {
    expect(directiveInstance).toBeTruthy();
  });

  // ========================================================================
  // Enter Key Behavior Tests
  // ========================================================================

  describe('Enter key behavior', () => {
    it('should trigger execution on Enter key', () => {
      // Ensure directive is enabled
      directiveInstance.appEnterToExecute = true;
      fixture.detectChanges();

      const event = new KeyboardEvent('keydown', {
        key: 'Enter',
        bubbles: true,
        cancelable: true,
      });

      const spy = jest.spyOn(event, 'preventDefault');
      // Call the directive method directly since HostListener
      // doesn't work reliably in Jest environment
      directiveInstance.onKeyDown(event);
      fixture.detectChanges();

      expect(component.executeCount).toBe(1);
      expect(spy).toHaveBeenCalled();
    });

    it('should allow newline on Shift+Enter', () => {
      // Ensure directive is enabled
      directiveInstance.appEnterToExecute = true;
      fixture.detectChanges();

      const event = new KeyboardEvent('keydown', {
        key: 'Enter',
        shiftKey: true,
        bubbles: true,
        cancelable: true,
      });

      const spy = jest.spyOn(event, 'preventDefault');
      directiveInstance.onKeyDown(event);
      fixture.detectChanges();

      expect(component.executeCount).toBe(0);
      expect(spy).not.toHaveBeenCalled();
    });

    it('should not trigger when disabled', () => {
      // Use fresh fixture with isDisabled true before first detectChanges to avoid NG0100
      const disabledFixture = TestBed.createComponent(TestHostComponent);
      const disabledHost = disabledFixture.componentInstance;
      const disabledDirective = disabledFixture.debugElement.query(
        By.directive(EnterToExecuteDirective)
      ).injector.get(EnterToExecuteDirective);
      disabledHost.isDisabled = true;
      disabledFixture.detectChanges();

      const event = new KeyboardEvent('keydown', {
        key: 'Enter',
        bubbles: true,
        cancelable: true,
      });
      disabledDirective.onKeyDown(event);
      disabledFixture.detectChanges();
      expect(disabledHost.executeCount).toBe(0);
    });

    it('should not trigger when directive disabled', () => {
      directiveInstance.appEnterToExecute = false;

      const event = new KeyboardEvent('keydown', {
        key: 'Enter',
        bubbles: true,
        cancelable: true,
      });

      directiveInstance.onKeyDown(event);
      fixture.detectChanges();

      expect(component.executeCount).toBe(0);
    });

    it('should not trigger on other keys', () => {
      const event = new KeyboardEvent('keydown', {
        key: 'a',
        bubbles: true,
        cancelable: true,
      });

      directiveInstance.onKeyDown(event);
      fixture.detectChanges();

      expect(component.executeCount).toBe(0);
    });
  });

  // ========================================================================
  // localStorage Tests
  // ========================================================================

  describe('localStorage preference', () => {
    it('should load true preference from localStorage', () => {
      localStorage.setItem('enterToExecuteEnabled', 'true');

      // Create new instance
      const newFixture = TestBed.createComponent(TestHostComponent);
      const newDebug = newFixture.debugElement.query(
        By.directive(EnterToExecuteDirective)
      );
      const newDirective = newDebug.injector.get(EnterToExecuteDirective);

      newFixture.detectChanges();

      expect(newDirective.isEnabled()).toBe(true);
    });

    it('should load false preference from localStorage', () => {
      localStorage.setItem('enterToExecuteEnabled', 'false');

      // Create new instance
      const newFixture = TestBed.createComponent(TestHostComponent);
      const newDebug = newFixture.debugElement.query(
        By.directive(EnterToExecuteDirective)
      );
      const newDirective = newDebug.injector.get(EnterToExecuteDirective);

      newFixture.detectChanges();

      expect(newDirective.isEnabled()).toBe(false);
    });

    it('should save preference to localStorage', () => {
      directiveInstance.setEnabled(false);

      const saved = localStorage.getItem('enterToExecuteEnabled');
      expect(saved).toBe('false');
    });

    it('should toggle preference', () => {
      directiveInstance.setEnabled(false);
      expect(directiveInstance.isEnabled()).toBe(false);

      directiveInstance.setEnabled(true);
      expect(directiveInstance.isEnabled()).toBe(true);
    });

    it('should handle localStorage not available', () => {
      // Mock localStorage instance to throw error (not Storage.prototype)
      const getItemSpy = jest
        .spyOn(localStorage, 'getItem')
        .mockImplementation(() => {
          throw new Error('Not available');
        });

      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();

      // Create new instance
      const newFixture = TestBed.createComponent(TestHostComponent);
      newFixture.detectChanges();

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'localStorage not available:',
        expect.any(Error)
      );

      getItemSpy.mockRestore();
      consoleWarnSpy.mockRestore();
    });

    it('should handle setItem failure', () => {
      // Mock localStorage instance to throw error (not Storage.prototype)
      const setItemSpy = jest
        .spyOn(localStorage, 'setItem')
        .mockImplementation(() => {
          throw new Error('Quota exceeded');
        });

      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();

      directiveInstance.setEnabled(false);

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Failed to save preference:',
        expect.any(Error)
      );

      setItemSpy.mockRestore();
      consoleWarnSpy.mockRestore();
    });
  });

  // ========================================================================
  // Integration Tests
  // ========================================================================

  describe('Integration', () => {
    it('should enable/disable based on preference', () => {
      // Disable
      directiveInstance.setEnabled(false);

      const event = new KeyboardEvent('keydown', {
        key: 'Enter',
        bubbles: true,
        cancelable: true,
      });

      directiveInstance.onKeyDown(event);
      fixture.detectChanges();
      expect(component.executeCount).toBe(0);

      // Enable
      directiveInstance.setEnabled(true);
      directiveInstance.onKeyDown(event);
      fixture.detectChanges();
      expect(component.executeCount).toBe(1);
    });

    it('should work with multiple Enter presses', () => {
      // Ensure directive is enabled
      directiveInstance.appEnterToExecute = true;
      fixture.detectChanges();

      const event = new KeyboardEvent('keydown', {
        key: 'Enter',
        bubbles: true,
        cancelable: true,
      });

      directiveInstance.onKeyDown(event);
      directiveInstance.onKeyDown(event);
      directiveInstance.onKeyDown(event);
      fixture.detectChanges();

      expect(component.executeCount).toBe(3);
    });

    it('should respect disabled input', () => {
      // Ensure directive is enabled first
      directiveInstance.appEnterToExecute = true;
      component.isDisabled = false;
      fixture.detectChanges();

      const event = new KeyboardEvent('keydown', {
        key: 'Enter',
        bubbles: true,
        cancelable: true,
      });
      directiveInstance.onKeyDown(event);
      fixture.detectChanges();
      expect(component.executeCount).toBe(1);

      // Use fresh fixture with disabled=true so we don't flip binding (avoids NG0100)
      const disabledFixture = TestBed.createComponent(TestHostComponent);
      const disabledHost = disabledFixture.componentInstance;
      const disabledDir = disabledFixture.debugElement
        .query(By.directive(EnterToExecuteDirective))
        .injector.get(EnterToExecuteDirective);
      disabledDir.appEnterToExecute = true;
      disabledHost.isDisabled = true;
      disabledFixture.detectChanges();
      disabledDir.onKeyDown(
        new KeyboardEvent('keydown', {
          key: 'Enter',
          bubbles: true,
          cancelable: true,
        })
      );
      disabledFixture.detectChanges();
      expect(disabledHost.executeCount).toBe(0);
    });
  });

  // ========================================================================
  // Edge Cases
  // ========================================================================

  describe('Edge cases', () => {
    it('should handle rapid key presses', () => {
      // Ensure directive is enabled
      directiveInstance.appEnterToExecute = true;
      fixture.detectChanges();

      const event = new KeyboardEvent('keydown', {
        key: 'Enter',
        bubbles: true,
        cancelable: true,
      });

      for (let i = 0; i < 10; i++) {
        directiveInstance.onKeyDown(event);
      }
      fixture.detectChanges();

      expect(component.executeCount).toBe(10);
    });

    it('should handle mixed key events', () => {
      // Ensure directive is enabled
      directiveInstance.appEnterToExecute = true;
      fixture.detectChanges();

      const enterEvent = new KeyboardEvent('keydown', {
        key: 'Enter',
        bubbles: true,
        cancelable: true,
      });

      const shiftEnterEvent = new KeyboardEvent('keydown', {
        key: 'Enter',
        shiftKey: true,
        bubbles: true,
        cancelable: true,
      });

      const otherKeyEvent = new KeyboardEvent('keydown', {
        key: 'a',
        bubbles: true,
        cancelable: true,
      });

      directiveInstance.onKeyDown(enterEvent);
      directiveInstance.onKeyDown(shiftEnterEvent);
      directiveInstance.onKeyDown(otherKeyEvent);
      directiveInstance.onKeyDown(enterEvent);
      fixture.detectChanges();

      expect(component.executeCount).toBe(2);
    });
  });
});
