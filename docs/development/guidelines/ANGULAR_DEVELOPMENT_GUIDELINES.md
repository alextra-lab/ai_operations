# Angular Development Guidelines

This document outlines the Angular TypeScript development guidelines integrated from the [awesome-cursorrules repository](https://github.com/PatrickJS/awesome-cursorrules/tree/main/rules/angular-typescript-cursorrules-prompt-file).

## Overview

Our Angular development follows strict TypeScript standards with Angular 21 and Jest testing, focusing on:
- **Code Quality**: Clear, readable, and maintainable code
- **Performance**: Optimized for speed and efficiency
- **Accessibility**: WCAG compliance and inclusive design
- **Standards**: ESLint, Prettier, HTMLHint, and EditorConfig compliance

## Core Principles

### 1. Code Structure
- **Maximum nesting depth**: 2 levels
- **Function parameters**: Maximum 4 parameters
- **Function length**: Maximum 50 executable lines
- **Line length**: Maximum 80 characters
- **Loop preference**: Use `forNext` function instead of traditional loops

### 2. TypeScript Standards
- Use TypeScript 5.x with strict mode
- Implement proper type annotations
- Use interfaces for object shapes
- Prefer type guards over type assertions
- Use enums for constants

### 3. Angular Best Practices
- Use Angular 21 features and patterns
- Implement OnPush change detection strategy
- Use Angular's built-in pipes over methods in templates
- Implement proper lazy loading for modules
- Use Angular CDK for advanced components

## File Organization

### Cursor Rules Structure
```
.cursorrules                    # Main rules file
cursor-rules/                   # Modular rules directory
├── angular-general.mdc         # General Angular component rules
├── accessibility-guidelines.mdc # WCAG compliance rules
├── performance-optimization.mdc # Performance best practices
├── angular-template-hints.mdc  # Template-specific rules
└── general-reasoning.mdc       # Reasoning and accuracy rules
```

### Configuration Files
- `.eslintrc.json` - ESLint configuration for TypeScript/Angular
- `.prettierrc` - Code formatting rules
- `.htmlhintrc` - HTML template validation
- `.editorconfig` - Editor consistency settings

## Development Workflow

### 1. Code Quality Checks
All code must pass:
- ESLint validation
- Prettier formatting
- HTMLHint template validation
- TypeScript compilation
- Jest test coverage (80%+)

### 2. Performance Guidelines
- Use OnPush change detection
- Implement code splitting
- Optimize bundle size
- Use Angular's built-in optimizations
- Monitor Core Web Vitals

### 3. Accessibility Requirements
- Semantic HTML elements
- Proper ARIA attributes
- Keyboard navigation support
- Color contrast compliance (4.5:1 minimum)
- Screen reader compatibility

## Testing Standards

### Jest Configuration
- Unit tests for all components
- Integration tests for services
- E2E tests for critical user flows
- Mock external dependencies
- Test coverage reporting

### Test Structure
```typescript
describe('ComponentName', () => {
  let component: ComponentName;
  let fixture: ComponentFixture<ComponentName>;

  beforeEach(() => {
    // Setup
  });

  it('should create', () => {
    // Test implementation
  });
});
```

## Code Examples

### Component Structure
```typescript
import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-example',
  templateUrl: './example.component.html',
  styleUrls: ['./example.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ExampleComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  constructor() {}

  ngOnInit(): void {
    // Initialization logic
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
```

### Service Structure
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ExampleService {
  constructor(private http: HttpClient) {}

  getData(): Observable<any> {
    return this.http.get('/api/data');
  }
}
```

## Performance Optimization

### Change Detection
- Use OnPush strategy for components
- Implement manual change detection when needed
- Use trackBy functions for *ngFor loops

### Bundle Optimization
- Implement lazy loading for routes
- Use code splitting for large modules
- Optimize images and assets
- Use production builds for deployment

### Memory Management
- Unsubscribe from observables
- Use takeUntil pattern for cleanup
- Implement proper error handling
- Use OnDestroy lifecycle hook

## Accessibility Guidelines

### HTML Structure
```html
<main role="main">
  <h1>Page Title</h1>
  <nav aria-label="Main navigation">
    <ul>
      <li><a href="/home" aria-current="page">Home</a></li>
    </ul>
  </nav>
</main>
```

### Form Accessibility
```html
<form>
  <label for="email">Email Address</label>
  <input
    type="email"
    id="email"
    name="email"
    aria-describedby="email-error"
    required
  >
  <div id="email-error" role="alert" aria-live="polite">
    <!-- Error messages -->
  </div>
</form>
```

## Integration with Cursor AI

The Cursor rules are automatically applied when:
- Working with `.ts` files (Angular components)
- Working with `.html` files (templates)
- Working with `.scss` files (styles)
- Any file in the `src/` directory

### Rule Activation
- **General rules**: Apply to all TypeScript files
- **Template rules**: Apply to HTML template files
- **Accessibility rules**: Apply to all source files
- **Performance rules**: Apply to all source files

## Maintenance

### Regular Updates
- Review and update rules quarterly
- Keep Angular and TypeScript versions current
- Update testing frameworks as needed
- Monitor performance metrics

### Rule Customization
- Modify `.cursorrules` for project-specific needs
- Update modular rules in `cursor-rules/` directory
- Adjust configuration files as requirements change
- Document any custom rules or exceptions

## Resources

- [Angular Documentation](https://angular.io/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [ESLint Angular Rules](https://github.com/angular-eslint/angular-eslint)

## Support

For questions about these guidelines or Angular development:
- Check the [Angular Documentation](https://angular.io/docs)
- Review the [awesome-cursorrules repository](https://github.com/PatrickJS/awesome-cursorrules)
- Consult the project's development team
- Create an issue in the project repository
