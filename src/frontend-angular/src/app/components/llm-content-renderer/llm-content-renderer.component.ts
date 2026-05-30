/**
 * LLM Content Renderer Component
 *
 * Custom implementation for rendering LLM-generated content with:
 * - Markdown formatting (custom parser)
 * - Mermaid diagrams (lazy-loaded on-demand - P3-PERF-01)
 * - KaTeX mathematical notation (lazy-loaded on-demand - P3-PERF-01)
 * - Structured output with visualizations (P3-F5)
 *
 * Performance optimization: Heavy libraries loaded only when content requires them
 */

import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  OnChanges,
  OnInit,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { FormattedOutput } from '../../models/output-format.model';
import { LibraryLoaderService } from '../../services/library-loader.service';
import { OutputFormattingService } from '../../services/output-formatting.service';
import { TemplateRegistryService } from '../../services/template-registry.service';
import { ChartVisualizerComponent } from '../visualizers/chart-visualizer/chart-visualizer.component';
import { GaugeVisualizerComponent } from '../visualizers/gauge-visualizer/gauge-visualizer.component';
import { TableVisualizerComponent } from '../visualizers/table-visualizer/table-visualizer.component';
import { TimelineVisualizerComponent } from '../visualizers/timeline-visualizer/timeline-visualizer.component';

@Component({
  selector: 'app-llm-content-renderer',
  standalone: true,
  imports: [
    CommonModule,
    TableVisualizerComponent,
    ChartVisualizerComponent,
    GaugeVisualizerComponent,
    TimelineVisualizerComponent,
  ],
  template: `
    <div class="llm-content-container">
      <!-- Structured output visualization -->
      <div *ngIf="formattedOutput" class="structured-output">
        <div
          *ngFor="let section of formattedOutput.rendered_sections"
          class="output-section"
          [ngClass]="'width-' + (section.width || 'full')"
        >
          <!-- Table visualizer -->
          <app-table-visualizer
            *ngIf="section.component_type === 'table'"
            [data]="$any(section.data)"
            [config]="$any(section.config)"
            [title]="section.title"
          >
          </app-table-visualizer>

          <!-- Chart visualizer -->
          <app-chart-visualizer
            *ngIf="section.component_type === 'chart'"
            [data]="$any(section.data)"
            [config]="$any(section.config)"
            [title]="section.title"
          >
          </app-chart-visualizer>

          <!-- Gauge visualizer -->
          <app-gauge-visualizer
            *ngIf="section.component_type === 'gauge'"
            [value]="$any(section.data)"
            [config]="$any(section.config)"
            [title]="section.title"
          >
          </app-gauge-visualizer>

          <!-- Timeline visualizer -->
          <app-timeline-visualizer
            *ngIf="section.component_type === 'timeline'"
            [events]="$any(section.data)"
            [config]="$any(section.config)"
            [title]="section.title"
          >
          </app-timeline-visualizer>

          <!-- Fallback: text/markdown -->
          <div *ngIf="section.component_type === 'text'" class="text-section">
            <h3>{{ section.title }}</h3>
            <pre>{{ section.data | json }}</pre>
          </div>
        </div>
      </div>

      <!-- Traditional markdown/mermaid/katex rendering -->
      <div #contentContainer class="content-output"></div>
    </div>
  `,
  styles: [
    `
      .llm-content-container {
        width: 100%;
        line-height: 1.6;
      }

      .structured-output {
        display: grid;
        grid-template-columns: repeat(12, 1fr);
        gap: 24px;
        margin-bottom: 24px;
      }

      .output-section {
        grid-column: span 12;
      }

      .output-section.width-half {
        grid-column: span 6;
      }

      .output-section.width-third {
        grid-column: span 4;
      }

      .output-section.width-two-thirds {
        grid-column: span 8;
      }

      .text-section {
        padding: 16px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

        h3 {
          margin: 0 0 12px 0;
          font-size: 1.25rem;
          font-weight: 500;
        }

        pre {
          margin: 0;
          padding: 12px;
          background: #f5f5f5;
          border-radius: 4px;
          overflow-x: auto;
        }
      }

      @media (max-width: 768px) {
        .output-section,
        .output-section.width-half,
        .output-section.width-third,
        .output-section.width-two-thirds {
          grid-column: span 12;
        }
      }

      .content-output {
        min-height: auto;
        max-height: none;
        overflow: visible;
      }

      .content-output p {
        margin: 8px 0;
        line-height: 1.5;
      }

      .content-output h1,
      .content-output h2,
      .content-output h3 {
        margin-top: 16px;
        margin-bottom: 8px;
        font-weight: 600;
      }

      .content-output h1 {
        font-size: 1.5em;
        border-bottom: 1px solid #eee;
        padding-bottom: 4px;
      }
      .content-output h2 {
        font-size: 1.3em;
      }
      .content-output h3 {
        font-size: 1.1em;
      }

      .content-output code {
        background-color: #f5f5f5;
        border-radius: 3px;
        padding: 2px 6px;
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
        color: #d63384;
      }

      .content-output pre {
        background-color: #282c34;
        color: #abb2bf;
        border-radius: 4px;
        padding: 12px;
        overflow-x: auto;
        margin: 12px 0;
        border: 1px solid #ddd;
      }

      .content-output pre code {
        background: none;
        padding: 0;
        color: inherit;
      }

      .content-output ul,
      .content-output ol {
        margin: 8px 0;
        padding-left: 24px;
      }

      .content-output li {
        margin: 4px 0;
      }

      .content-output blockquote {
        border-left: 4px solid #ddd;
        margin: 12px 0;
        padding-left: 16px;
        color: #666;
        font-style: italic;
      }

      .content-output strong {
        font-weight: 600;
      }

      .content-output em {
        font-style: italic;
      }

      .content-output a {
        color: #0366d6;
        text-decoration: none;
      }

      .content-output a:hover {
        text-decoration: underline;
      }

      .mermaid-container {
        margin: 16px 0;
        padding: 16px;
        background: #f9f9f9;
        border-radius: 8px;
        border: 1px solid #ddd;
        overflow-x: auto;
        min-height: 100px;
        display: flex;
        justify-content: center;
        align-items: center;
      }

      .mermaid-container svg {
        max-width: 100%;
        height: auto;
      }

      .katex-display {
        margin: 16px 0;
        overflow-x: auto;
        text-align: center;
      }

      .markdown-table {
        border-collapse: collapse;
        margin: 16px 0;
        width: 100%;
        max-width: 100%;
        overflow-x: auto;
        display: block;
        white-space: nowrap;
      }

      .markdown-table th,
      .markdown-table td {
        border: 1px solid #ddd;
        padding: 8px 12px;
        text-align: left;
        white-space: normal;
      }

      .markdown-table th {
        background-color: #f5f5f5;
        font-weight: 600;
        border-bottom: 2px solid #ddd;
      }

      .markdown-table tbody tr:nth-child(even) {
        background-color: #f9f9f9;
      }

      .markdown-table tbody tr:hover {
        background-color: #f0f0f0;
      }

      .render-error {
        background-color: #fff9f9;
        border-left: 3px solid #e57373;
        border-radius: 3px;
        margin: 8px 0;
        padding: 6px 8px;
        font-size: 0.85em;
        line-height: 1.3;
        border-top: 1px solid #e0e0e0;
        border-bottom: 1px solid #e0e0e0;
      }

      .render-error-inline {
        display: inline;
        margin: 0;
        padding: 0;
      }

      .render-error-header {
        color: #d32f2f;
        font-weight: 600;
        font-size: 0.85em;
        display: inline;
        margin-right: 6px;
      }

      .render-error-message {
        color: #757575;
        font-family: monospace;
        font-size: 0.75em;
        display: inline;
        margin-right: 6px;
      }

      .render-error-code {
        display: block;
        margin: 4px 0 0 0;
        background-color: #f5f5f5;
        color: #424242;
        border-radius: 2px;
        padding: 4px 6px;
        overflow-x: auto;
        font-family: 'Courier New', monospace;
        font-size: 0.75em;
        max-height: 100px;
        border: 1px solid #e0e0e0;
      }
    `,
  ],
})
export class LLMContentRendererComponent
  implements OnInit, OnChanges, AfterViewInit
{
  @Input() content = '';
  @Input() structuredData?: unknown;
  @Input() templateId?: string;

  @ViewChild('contentContainer', { static: false })
  contentContainer?: ElementRef;

  formattedOutput?: FormattedOutput;

  private viewInitialized = false;
  private hasCodeBlocks = false;
  private hasMathContent = false;
  private hasDiagrams = false;

  constructor(
    private outputFormattingService: OutputFormattingService,
    private templateRegistryService: TemplateRegistryService,
    private libraryLoader: LibraryLoaderService
  ) {}

  async ngOnInit(): Promise<void> {
    // Format structured output if template ID provided
    if (this.structuredData && this.templateId) {
      await this.formatStructuredOutput();
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Re-format structured output if inputs change
    if (
      (changes['structuredData'] || changes['templateId']) &&
      this.structuredData &&
      this.templateId
    ) {
      void this.formatStructuredOutput();
    }

    // Re-render markdown content if changed
    if (changes['content'] && this.content && this.viewInitialized) {
      void this.renderContent();
    }
  }

  ngAfterViewInit(): void {
    this.viewInitialized = true;

    if (this.content) {
      void this.renderContent();
    }
  }

  /**
   * Format structured output using template
   */
  private async formatStructuredOutput(): Promise<void> {
    if (!this.structuredData || !this.templateId) {
      this.formattedOutput = undefined;
      return;
    }

    // Get template from registry
    const template = this.templateRegistryService.get(this.templateId);
    if (!template) {
      console.warn(`Template not found: ${this.templateId}`);
      this.formattedOutput = undefined;
      return;
    }

    try {
      // Format response with template
      this.formattedOutput = await this.outputFormattingService.formatResponse(
        {
          answer: this.content,
          structured_data: this.structuredData,
        },
        template
      );
    } catch (error) {
      console.error('Error formatting structured output:', error);
      this.formattedOutput = undefined;
    }
  }

  private async renderContent(): Promise<void> {
    try {
      if (!this.contentContainer) {
        return;
      }

      // P3-PERF-01: Detect and lazy load required libraries
      await this.detectAndLoadLibraries();

      // Normalize LLM-wrapped Mermaid/code blocks
      let processedContent = this.normalizeLLMMarkdown(this.content);

      // Step 1: Extract Mermaid blocks with placeholders
      const mermaidBlocks: string[] = [];
      processedContent = processedContent.replace(
        /```mermaid\n([\s\S]*?)```/g,
        (_match, diagram) => {
          mermaidBlocks.push(diagram.trim());
          return `\n\n{{MERMAID${mermaidBlocks.length - 1}}}\n\n`;
        }
      );

      // Step 2: Extract KaTeX expressions with placeholders (before HTML escaping)
      const katexExpressions: { html: string; isBlock: boolean }[] = [];

      // Only process math if KaTeX is loaded
      if (this.hasMathContent && (window as any).katex) {
        const katexLib = (window as any).katex;

        // Extract block math: $$...$$ or \[...\]
        processedContent = processedContent.replace(
          /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]/g,
          (match, dollars, brackets) => {
            const formula = dollars || brackets;
            try {
              const html = katexLib.renderToString(formula.trim(), {
                displayMode: true,
                throwOnError: false,
              });
              katexExpressions.push({ html, isBlock: true });
              return `{{KATEX${katexExpressions.length - 1}}}`;
            } catch {
              return match;
            }
          }
        );

        // Extract inline math: $...$ or \(...\)
        processedContent = processedContent.replace(
          /\$([^$\n]+?)\$|\\\((.*?)\\\)/g,
          (match, dollars, parens) => {
            const formula = dollars || parens;
            try {
              const html = katexLib.renderToString(formula.trim(), {
                displayMode: false,
                throwOnError: false,
              });
              katexExpressions.push({ html, isBlock: false });
              return `{{KATEX${katexExpressions.length - 1}}}`;
            } catch {
              return match;
            }
          }
        );
      }

      // Step 3: Process Markdown (this will escape HTML)
      processedContent = this.simpleMarkdownToHtml(processedContent);

      // Step 4: Replace Mermaid placeholders
      processedContent = processedContent.replace(
        /\{\{MERMAID(\d+)\}\}/g,
        (_, index) =>
          `<div class="mermaid-container" data-mermaid-index="${index}"></div>`
      );

      // Step 5: Replace KaTeX placeholders
      processedContent = processedContent.replace(
        /\{\{KATEX(\d+)\}\}/g,
        (_, index) => katexExpressions[parseInt(index)]?.html || ''
      );

      // Step 6: Set content
      this.contentContainer.nativeElement.innerHTML = processedContent;

      // Step 7: Render Mermaid diagrams
      if (mermaidBlocks.length > 0) {
        setTimeout(() => void this.renderMermaidDiagrams(mermaidBlocks), 100);
      }
    } catch (error) {
      console.error('Error rendering content:', error);
      if (this.contentContainer) {
        this.contentContainer.nativeElement.textContent = this.content;
      }
    }
  }

  /**
   * Detect content types and lazy load required libraries
   * P3-PERF-01: Loads only what's needed for the current content
   */
  private async detectAndLoadLibraries(): Promise<void> {
    const content = this.content || '';

    // Detect code blocks
    this.hasCodeBlocks =
      /```[\s\S]*?```/.test(content) || /<code/.test(content);

    // Detect math content
    this.hasMathContent =
      /\$\$[\s\S]*?\$\$/.test(content) ||
      /\\\([\s\S]*?\\\)/.test(content) ||
      /\$[^$\n]+?\$/.test(content);

    // Detect diagrams
    this.hasDiagrams = /```mermaid[\s\S]*?```/.test(content);

    // Load libraries in parallel only if needed
    const loadPromises: Promise<void>[] = [];

    if (this.hasCodeBlocks) {
      loadPromises.push(
        this.libraryLoader.loadPrism([
          'typescript',
          'javascript',
          'python',
          'json',
          'bash',
        ])
      );
    }

    if (this.hasMathContent) {
      loadPromises.push(this.libraryLoader.loadKaTeX());
    }

    if (this.hasDiagrams) {
      loadPromises.push(this.libraryLoader.loadMermaid());
    }

    if (loadPromises.length > 0) {
      await Promise.all(loadPromises);
    }
  }

  private normalizeLLMMarkdown(md: string): string {
    // Unwrap ```markdown blocks that contain ```mermaid or other code fences
    // This handles LLMs that helpfully wrap examples in markdown code blocks
    md = md.replace(/```markdown\s*(```mermaid[\s\S]*?```)\s*```/g, '$1');

    // Also handle other nested code blocks
    md = md.replace(/```markdown\s*(```\w+[\s\S]*?```)\s*```/g, '$1');

    return md;
  }

  private simpleMarkdownToHtml(text: string): string {
    let html = text;

    // Escape HTML first
    html = html
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Code blocks (```language\ncode\n```) - process before inline code
    html = html.replace(
      /```(?:\w+)?\n([\s\S]*?)```/g,
      '<pre><code>$1</code></pre>'
    );

    // Inline code (`code`)
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold (**text** or __text__)
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');

    // Italic (*text* or _text_)
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/_([^_]+)_/g, '<em>$1</em>');

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Lists
    html = html.replace(/^\* (.+)$/gm, '<li>$1</li>');
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>[\s\S]+?<\/li>)/g, '<ul>$1</ul>');

    // Tables - handle before line breaks
    html = this.parseMarkdownTables(html);

    // Links [text](url)
    html = html.replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );

    // Line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    // Wrap in paragraph
    if (!html.match(/^<(h[1-6]|ul|ol|pre|div)/)) {
      html = '<p>' + html + '</p>';
    }

    return html;
  }

  private parseMarkdownTables(text: string): string {
    // Match markdown tables with optional leading/trailing whitespace
    return text.replace(
      /^\s*\|(.+)\|\s*\n\s*\|[-\s|]+\|\s*\n((?:\s*\|.+\|\s*\n?)*)/gm,
      (match, header, rows) => {
        // Parse header row
        const headerCells = header
          .split('|')
          .map((cell: string) => `<th>${cell.trim()}</th>`)
          .join('');

        // Parse data rows
        const dataRows = rows
          .trim()
          .split('\n')
          .map((row: string) => {
            const cells = row
              .split('|')
              .map((cell: string) => `<td>${cell.trim()}</td>`)
              .join('');
            return `<tr>${cells}</tr>`;
          })
          .join('');

        return `<table class="markdown-table"><thead><tr>${headerCells}</tr></thead><tbody>${dataRows}</tbody></table>`;
      }
    );
  }

  private async renderMermaidDiagrams(diagrams: string[]): Promise<void> {
    try {
      const containers = this.contentContainer?.nativeElement.querySelectorAll(
        '.mermaid-container[data-mermaid-index]'
      );

      if (!containers) return;

      // Use lazy-loaded mermaid
      const mermaidLib = (window as any).mermaid;
      if (!mermaidLib) {
        console.warn('Mermaid not loaded');
        return;
      }

      for (const container of Array.from(containers)) {
        const element = container as HTMLElement;
        const index = element.getAttribute('data-mermaid-index');

        if (index !== null && diagrams[parseInt(index)]) {
          try {
            const { svg } = await mermaidLib.render(
              `mermaid-${Date.now()}-${index}`,
              diagrams[parseInt(index)]
            );
            element.innerHTML = svg;
          } catch (e) {
            console.error('Mermaid render error:', e);
            const errorSnippet = this.extractErrorSnippet(e);
            const rawDiagram = diagrams[parseInt(index)];
            element.innerHTML = this.buildErrorDisplay(
              rawDiagram,
              errorSnippet
            );
          }
        }
      }
    } catch (error) {
      console.error('Error rendering Mermaid diagrams:', error);
    }
  }

  /**
   * Extract meaningful error snippet from Mermaid error
   */
  private extractErrorSnippet(error: unknown): string {
    if (!error) return 'Unknown error';

    const errorStr = error instanceof Error ? error.message : String(error);

    // Extract just the main error message, before verbose details
    // Look for "Expecting" keyword which starts verbose output
    const expectingIndex = errorStr.indexOf('Expecting');
    let snippet =
      expectingIndex > 0
        ? errorStr.substring(0, expectingIndex).trim()
        : errorStr;

    // Further limit to 100 characters for compact display
    if (snippet.length > 100) {
      snippet = snippet.substring(0, 100) + '...';
    }

    return snippet;
  }

  /**
   * Build HTML for error display with raw code and error message
   */
  private buildErrorDisplay(rawCode: string, errorMsg: string): string {
    const escapedCode = rawCode
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    const escapedError = errorMsg
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    return `<div class="render-error"><span class="render-error-header">⚠️ Diagram Error:</span> <span class="render-error-message">${escapedError}</span><div class="render-error-code">${escapedCode}</div></div>`;
  }
}
