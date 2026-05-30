import { Injectable, SecurityContext } from '@angular/core';
import {
  DomSanitizer,
  SafeHtml,
  SafeResourceUrl,
  SafeScript,
  SafeStyle,
  SafeUrl,
} from '@angular/platform-browser';
import DOMPurify from 'dompurify';

const ALLOWED_URL_PROTOCOLS = new Set([
  'http:',
  'https:',
  'mailto:',
  'tel:',
]);

/**
 * Service for XSS protection and input sanitization.
 * Uses DOMPurify plus Angular DomSanitizer for defense in depth.
 */
@Injectable({ providedIn: 'root' })
export class XSSProtectionService {
  constructor(private sanitizer: DomSanitizer) {}

  /** Sanitizes HTML content to prevent XSS attacks. */
  sanitizeHtml(html: string): SafeHtml {
    if (!html) {
      return this.sanitizer.bypassSecurityTrustHtml('');
    }

    const cleaned = DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
    return this.sanitizer.sanitize(
      SecurityContext.HTML,
      cleaned
    ) as SafeHtml;
  }

  /** Sanitizes URL to prevent dangerous schemes. */
  sanitizeUrl(url: string): SafeUrl {
    if (!url) {
      return this.sanitizer.bypassSecurityTrustUrl('');
    }

    const cleaned = this.normalizeUrl(url);
    return this.sanitizer.sanitize(
      SecurityContext.URL,
      cleaned
    ) as SafeUrl;
  }

  /** Sanitizes script content (always stripped). */
  sanitizeScript(script: string): SafeScript {
    const cleaned = DOMPurify.sanitize(script, {
      ALLOWED_TAGS: [],
      ALLOWED_ATTR: [],
    });
    return this.sanitizer.sanitize(
      SecurityContext.SCRIPT,
      cleaned
    ) as SafeScript;
  }

  /** Sanitizes CSS style content. */
  sanitizeStyle(style: string): SafeStyle {
    const cleaned = DOMPurify.sanitize(style, {
      ALLOWED_TAGS: [],
      ALLOWED_ATTR: [],
    });
    return this.sanitizer.sanitize(
      SecurityContext.STYLE,
      cleaned
    ) as SafeStyle;
  }

  /** Sanitizes resource URL for iframe src, etc. */
  sanitizeResourceUrl(url: string): SafeResourceUrl {
    if (!url) {
      return this.sanitizer.bypassSecurityTrustResourceUrl('');
    }

    const cleaned = this.normalizeUrl(url);
    return this.sanitizer.sanitize(
      SecurityContext.RESOURCE_URL,
      cleaned
    ) as SafeResourceUrl;
  }

  /** Validates input for XSS patterns. */
  validateInput(input: string): InputValidation {
    if (!input) {
      return {
        isSafe: true,
        violations: [],
        riskLevel: 'none',
        sanitizedInput: '',
      };
    }

    const sanitized = DOMPurify.sanitize(input, { USE_PROFILES: { html: true } });
    const violations: string[] = [];

    if (sanitized !== input) {
      violations.push('HTML sanitization modified input');
    }

    if (this.containsSuspiciousSequences(input)) {
      violations.push('Suspicious JavaScript sequence detected');
    }

    const isSafe = violations.length === 0;
    const riskLevel = this.calculateRiskLevel(violations.length, input.length);

    return {
      isSafe,
      violations,
      riskLevel,
      sanitizedInput: isSafe ? input : sanitized,
    };
  }

  /** Strips all HTML tags from input. */
  stripHtml(input: string): string {
    if (!input) {
      return '';
    }

    return DOMPurify.sanitize(input, {
      ALLOWED_TAGS: [],
      ALLOWED_ATTR: [],
    }).trim();
  }

  /** Escapes HTML special characters. */
  escapeHtml(input: string): string {
    if (!input) {
      return '';
    }

    return input
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;')
      .replace(/\//g, '&#x2F;');
  }

  private normalizeUrl(url: string): string {
    const trimmed = url.trim();
    if (!trimmed || trimmed.startsWith('#') || trimmed.startsWith('/')) {
      return trimmed;
    }

    try {
      const parsed = new URL(trimmed, window.location.origin);
      if (!ALLOWED_URL_PROTOCOLS.has(parsed.protocol)) {
        return '#';
      }
      return parsed.toString();
    } catch {
      return '#';
    }
  }

  private containsSuspiciousSequences(input: string): boolean {
    const suspicious = [
      'eval(',
      'function(',
      'settimeout(',
      'setinterval(',
      'document.cookie',
      'document.write',
      'innerhtml',
      'outerhtml',
    ];

    const lower = input.toLowerCase();
    return suspicious.some((seq) => lower.includes(seq));
  }

  private calculateRiskLevel(
    violationCount: number,
    inputLength: number
  ): 'none' | 'low' | 'medium' | 'high' | 'critical' {
    if (violationCount === 0) {
      return 'none';
    }
    if (violationCount === 1 && inputLength < 100) {
      return 'low';
    }
    if (violationCount <= 2 && inputLength < 500) {
      return 'medium';
    }
    if (violationCount <= 4) {
      return 'high';
    }
    return 'critical';
  }
}

export interface InputValidation {
  isSafe: boolean;
  violations: string[];
  riskLevel: 'none' | 'low' | 'medium' | 'high' | 'critical';
  sanitizedInput: string;
}
