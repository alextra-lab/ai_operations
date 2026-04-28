import { Injectable, SecurityContext } from '@angular/core';
import {
  DomSanitizer,
  SafeHtml,
  SafeResourceUrl,
  SafeScript,
  SafeStyle,
  SafeUrl,
} from '@angular/platform-browser';

/**
 * Service for XSS protection and input sanitization.
 * Provides comprehensive protection against cross-site scripting attacks.
 */
@Injectable({ providedIn: 'root' })
export class XSSProtectionService {
  private readonly dangerousPatterns = [
    /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
    /<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi,
    /<object\b[^<]*(?:(?!<\/object>)<[^<]*)*<\/object>/gi,
    /<embed\b[^<]*(?:(?!<\/embed>)<[^<]*)*<\/embed>/gi,
    /<link\b[^<]*(?:(?!<\/link>)<[^<]*)*<\/link>/gi,
    /<meta\b[^<]*(?:(?!<\/meta>)<[^<]*)*<\/meta>/gi,
    /javascript:/gi,
    /vbscript:/gi,
    /data:text\/html/gi,
    /on\w+\s*=/gi, // Event handlers like onclick, onload, etc.
  ];

  private readonly allowedTags = new Set([
    'p',
    'br',
    'strong',
    'em',
    'u',
    'i',
    'b',
    'span',
    'div',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'ul',
    'ol',
    'li',
    'blockquote',
    'pre',
    'code',
    'a',
    'img',
    'table',
    'tr',
    'td',
    'th',
    'thead',
    'tbody',
  ]);

  private readonly allowedAttributes = new Set([
    'href',
    'src',
    'alt',
    'title',
    'class',
    'id',
    'style',
    'width',
    'height',
    'colspan',
    'rowspan',
  ]);

  constructor(private sanitizer: DomSanitizer) {}

  /**
   * Sanitizes HTML content to prevent XSS attacks.
   */
  sanitizeHtml(html: string): SafeHtml {
    if (!html) return this.sanitizer.bypassSecurityTrustHtml('');

    const cleaned = this.cleanHtml(html);
    return this.sanitizer.sanitize(SecurityContext.HTML, cleaned) as SafeHtml;
  }

  /**
   * Sanitizes URL to prevent javascript: and data: schemes.
   */
  sanitizeUrl(url: string): SafeUrl {
    if (!url) return this.sanitizer.bypassSecurityTrustUrl('');

    const cleaned = this.cleanUrl(url);
    return this.sanitizer.sanitize(SecurityContext.URL, cleaned) as SafeUrl;
  }

  /**
   * Sanitizes script content.
   */
  sanitizeScript(script: string): SafeScript {
    if (!script) return this.sanitizer.bypassSecurityTrustScript('');

    const cleaned = this.cleanScript(script);
    return this.sanitizer.sanitize(
      SecurityContext.SCRIPT,
      cleaned
    ) as SafeScript;
  }

  /**
   * Sanitizes CSS style content.
   */
  sanitizeStyle(style: string): SafeStyle {
    if (!style) return this.sanitizer.bypassSecurityTrustStyle('');

    const cleaned = this.cleanStyle(style);
    return this.sanitizer.sanitize(SecurityContext.STYLE, cleaned) as SafeStyle;
  }

  /**
   * Sanitizes resource URL for iframe src, etc.
   */
  sanitizeResourceUrl(url: string): SafeResourceUrl {
    if (!url) return this.sanitizer.bypassSecurityTrustResourceUrl('');

    const cleaned = this.cleanUrl(url);
    return this.sanitizer.sanitize(
      SecurityContext.RESOURCE_URL,
      cleaned
    ) as SafeResourceUrl;
  }

  /**
   * Validates input for XSS patterns.
   */
  validateInput(input: string): InputValidation {
    const violations: string[] = [];
    let isSafe = true;

    if (!input) {
      return { isSafe: true, violations: [], riskLevel: 'none' };
    }

    // Check for dangerous patterns
    this.dangerousPatterns.forEach((pattern, index) => {
      if (pattern.test(input)) {
        violations.push(
          `Dangerous pattern detected: ${this.getPatternDescription(index)}`
        );
        isSafe = false;
      }
    });

    // Check for suspicious character sequences
    if (this.containsSuspiciousSequences(input)) {
      violations.push('Suspicious character sequences detected');
      isSafe = false;
    }

    // Check for encoded payloads
    if (this.containsEncodedPayloads(input)) {
      violations.push('Encoded payload detected');
      isSafe = false;
    }

    const riskLevel = this.calculateRiskLevel(violations.length, input.length);

    return {
      isSafe,
      violations,
      riskLevel,
      sanitizedInput: isSafe ? input : this.cleanHtml(input),
    };
  }

  /**
   * Strips all HTML tags from input.
   */
  stripHtml(input: string): string {
    if (!input) return '';

    return input
      .replace(/<[^>]*>/g, '') // Remove HTML tags
      .replace(/&[^;]+;/g, '') // Remove HTML entities
      .trim();
  }

  /**
   * Escapes HTML special characters.
   */
  escapeHtml(input: string): string {
    if (!input) return '';

    return input
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;')
      .replace(/\//g, '&#x2F;');
  }

  private cleanHtml(html: string): string {
    let cleaned = html;

    // Remove dangerous patterns
    this.dangerousPatterns.forEach((pattern) => {
      cleaned = cleaned.replace(pattern, '');
    });

    // Remove dangerous attributes
    cleaned = this.removeDangerousAttributes(cleaned);

    // Remove dangerous tags
    cleaned = this.removeDangerousTags(cleaned);

    return cleaned;
  }

  private cleanUrl(url: string): string {
    // Remove javascript: and data: schemes
    if (
      url.toLowerCase().startsWith('javascript:') ||
      url.toLowerCase().startsWith('vbscript:') ||
      url.toLowerCase().startsWith('data:text/html')
    ) {
      return '#';
    }

    // Validate URL format
    try {
      new URL(url);
      return url;
    } catch {
      return '#';
    }
  }

  private cleanScript(script: string): string {
    // Remove dangerous patterns from script content
    let cleaned = script;
    this.dangerousPatterns.forEach((pattern) => {
      cleaned = cleaned.replace(pattern, '');
    });
    return cleaned;
  }

  private cleanStyle(style: string): string {
    // Remove dangerous CSS patterns
    let cleaned = style;

    // Remove expression() and javascript: in CSS
    cleaned = cleaned.replace(/expression\s*\(/gi, '');
    cleaned = cleaned.replace(/javascript:/gi, '');
    cleaned = cleaned.replace(/vbscript:/gi, '');

    return cleaned;
  }

  private removeDangerousAttributes(html: string): string {
    // Remove event handlers and dangerous attributes
    return html
      .replace(/\s*on\w+\s*=\s*["'][^"']*["']/gi, '')
      .replace(/\s*style\s*=\s*["'][^"']*javascript[^"']*["']/gi, '')
      .replace(/\s*href\s*=\s*["']javascript:[^"']*["']/gi, '');
  }

  private removeDangerousTags(html: string): string {
    // Remove script, iframe, object, embed tags
    return html.replace(
      /<\/?(script|iframe|object|embed|link|meta)[^>]*>/gi,
      ''
    );
  }

  private containsSuspiciousSequences(input: string): boolean {
    const suspicious = [
      'eval(',
      'Function(',
      'setTimeout(',
      'setInterval(',
      'document.cookie',
      'document.write',
      'innerHTML',
      'outerHTML',
      'document.location',
      'window.location',
    ];

    return suspicious.some((seq) => input.toLowerCase().includes(seq));
  }

  private containsEncodedPayloads(input: string): boolean {
    // Check for common encoding patterns used in XSS
    const encodedPatterns = [
      /%3Cscript/gi,
      /%3Ciframe/gi,
      /&#x3C;script/gi,
      /&#60;script/gi,
      /&lt;script/gi,
      /\\x3Cscript/gi,
      /\\u003Cscript/gi,
    ];

    return encodedPatterns.some((pattern) => pattern.test(input));
  }

  private calculateRiskLevel(
    violationCount: number,
    inputLength: number
  ): 'none' | 'low' | 'medium' | 'high' | 'critical' {
    if (violationCount === 0) return 'none';
    if (violationCount === 1 && inputLength < 100) return 'low';
    if (violationCount <= 2 && inputLength < 500) return 'medium';
    if (violationCount <= 4) return 'high';
    return 'critical';
  }

  private getPatternDescription(index: number): string {
    const descriptions = [
      'Script tag',
      'Iframe tag',
      'Object tag',
      'Embed tag',
      'Link tag',
      'Meta tag',
      'JavaScript protocol',
      'VBScript protocol',
      'Data URI with HTML',
      'Event handler attribute',
    ];
    return descriptions[index] || 'Unknown pattern';
  }
}

export interface InputValidation {
  isSafe: boolean;
  violations: string[];
  riskLevel: 'none' | 'low' | 'medium' | 'high' | 'critical';
  sanitizedInput: string;
}
