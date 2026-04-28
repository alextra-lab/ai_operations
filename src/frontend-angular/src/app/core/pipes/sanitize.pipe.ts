import { Pipe, PipeTransform } from '@angular/core';
import {
  DomSanitizer,
  SafeHtml,
  SafeResourceUrl,
  SafeScript,
  SafeStyle,
  SafeUrl,
} from '@angular/platform-browser';
import { XSSProtectionService } from '../security/xss-protection.service';

/**
 * Pipe for sanitizing content to prevent XSS attacks.
 * Provides safe rendering of HTML, URLs, scripts, and styles.
 */
@Pipe({
  name: 'sanitize',
  pure: true,
})
export class SanitizePipe implements PipeTransform {
  constructor(
    private sanitizer: DomSanitizer,
    private xssProtection: XSSProtectionService
  ) {}

  /**
   * Sanitizes content based on the specified type.
   */
  transform(
    value: string | null | undefined,
    type:
      | 'html'
      | 'url'
      | 'script'
      | 'style'
      | 'resourceUrl'
      | 'strip'
      | 'escape' = 'html'
  ): SafeHtml | SafeUrl | SafeScript | SafeStyle | SafeResourceUrl | string {
    if (!value) {
      return this.getEmptyValue(type);
    }

    // First validate the input for XSS patterns
    const validation = this.xssProtection.validateInput(value);

    if (!validation.isSafe) {
      console.warn('SanitizePipe: Potentially unsafe content detected', {
        violations: validation.violations,
        riskLevel: validation.riskLevel,
        content: value.substring(0, 100) + '...',
      });
    }

    switch (type) {
      case 'html':
        return this.xssProtection.sanitizeHtml(validation.sanitizedInput);

      case 'url':
        return this.xssProtection.sanitizeUrl(validation.sanitizedInput);

      case 'script':
        return this.xssProtection.sanitizeScript(validation.sanitizedInput);

      case 'style':
        return this.xssProtection.sanitizeStyle(validation.sanitizedInput);

      case 'resourceUrl':
        return this.xssProtection.sanitizeResourceUrl(
          validation.sanitizedInput
        );

      case 'strip':
        return this.xssProtection.stripHtml(validation.sanitizedInput);

      case 'escape':
        return this.xssProtection.escapeHtml(validation.sanitizedInput);

      default:
        return this.xssProtection.sanitizeHtml(validation.sanitizedInput);
    }
  }

  private getEmptyValue(
    type: string
  ): SafeHtml | SafeUrl | SafeScript | SafeStyle | SafeResourceUrl | string {
    switch (type) {
      case 'html':
        return this.sanitizer.bypassSecurityTrustHtml('');
      case 'url':
        return this.sanitizer.bypassSecurityTrustUrl('');
      case 'script':
        return this.sanitizer.bypassSecurityTrustScript('');
      case 'style':
        return this.sanitizer.bypassSecurityTrustStyle('');
      case 'resourceUrl':
        return this.sanitizer.bypassSecurityTrustResourceUrl('');
      case 'strip':
      case 'escape':
        return '';
      default:
        return this.sanitizer.bypassSecurityTrustHtml('');
    }
  }
}

/**
 * Pipe for sanitizing HTML content with additional security checks.
 * This is a more restrictive version that strips all HTML tags.
 */
@Pipe({
  name: 'sanitizeText',
  pure: true,
})
export class SanitizeTextPipe implements PipeTransform {
  constructor(private xssProtection: XSSProtectionService) {}

  transform(value: string | null | undefined): string {
    if (!value) return '';

    const validation = this.xssProtection.validateInput(value);

    if (!validation.isSafe) {
      console.warn('SanitizeTextPipe: Potentially unsafe content detected', {
        violations: validation.violations,
        riskLevel: validation.riskLevel,
      });
    }

    return this.xssProtection.stripHtml(validation.sanitizedInput);
  }
}

/**
 * Pipe for sanitizing URLs with strict validation.
 */
@Pipe({
  name: 'sanitizeUrl',
  pure: true,
})
export class SanitizeUrlPipe implements PipeTransform {
  constructor(private xssProtection: XSSProtectionService) {}

  transform(value: string | null | undefined): string {
    if (!value) return '#';

    const validation = this.xssProtection.validateInput(value);

    if (!validation.isSafe) {
      console.warn('SanitizeUrlPipe: Potentially unsafe URL detected', {
        violations: validation.violations,
        riskLevel: validation.riskLevel,
      });
      return '#';
    }

    const sanitized = this.xssProtection.sanitizeUrl(validation.sanitizedInput);

    // Convert SafeUrl to string for template usage
    if (typeof sanitized === 'string') {
      return sanitized;
    }

    // If it's a SafeUrl object, we need to extract the value
    // This is a workaround since we can't directly access the internal value
    try {
      return (sanitized as any).changingThisBreaksApplicationSecurity || '#';
    } catch {
      return '#';
    }
  }
}
