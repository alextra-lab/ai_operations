import { CommonModule } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';

// Angular Material imports
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';

import { LucideAngularModule } from 'lucide-angular';
import { SourceMetadata } from '../../api/models/use-case.models';

@Component({
  selector: 'app-source-citation',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatChipsModule,
    MatTooltipModule,
    MatExpansionModule,
    MatMenuModule,
  ],
  templateUrl: './source-citation.component.html',
  styleUrls: ['./source-citation.component.scss'],
})
export class SourceCitationComponent implements OnInit {
  @Input() source!: SourceMetadata;

  // Computed properties
  confidenceLevel = 'medium';
  confidenceClass = '';
  relevanceScore = 0;
  documentTypeIcon = '';
  classificationColor = '';
  isExpanded = false;

  ngOnInit(): void {
    this.calculateRelevanceScore();
    this.updateConfidenceLevel();
    this.setDocumentTypeIcon();
    this.setClassificationColor();
  }

  // ============================================================================
  // Computed Properties
  // ============================================================================

  private calculateRelevanceScore(): void {
    // Calculate relevance score based on similarity score
    // Higher similarity = higher relevance
    this.relevanceScore = this.source.similarity_score ?? 0;
  }

  private updateConfidenceLevel(): void {
    const score = this.source.similarity_score ?? 0;

    if (score >= 0.8) {
      this.confidenceLevel = 'high';
      this.confidenceClass = 'high-confidence';
    } else if (score >= 0.6) {
      this.confidenceLevel = 'medium';
      this.confidenceClass = 'medium-confidence';
    } else {
      this.confidenceLevel = 'low';
      this.confidenceClass = 'low-confidence';
    }
  }

  private setDocumentTypeIcon(): void {
    if (!this.source.document_type) {
      this.documentTypeIcon = 'file';
      return;
    }

    const type = this.source.document_type.toLowerCase();

    if (type.includes('pdf')) {
      this.documentTypeIcon = 'file-text';
    } else if (type.includes('doc') || type.includes('docx')) {
      this.documentTypeIcon = 'file-text';
    } else if (type.includes('txt') || type.includes('text')) {
      this.documentTypeIcon = 'file-text';
    } else if (type.includes('html') || type.includes('htm')) {
      this.documentTypeIcon = 'globe';
    } else if (type.includes('md') || type.includes('markdown')) {
      this.documentTypeIcon = 'code';
    } else {
      this.documentTypeIcon = 'file';
    }
  }

  private setClassificationColor(): void {
    if (!this.source.classification) {
      this.classificationColor = '#666';
      return;
    }

    const classification = this.source.classification.toLowerCase();

    if (
      classification.includes('confidential') ||
      classification.includes('secret')
    ) {
      this.classificationColor = '#f44336';
    } else if (
      classification.includes('internal') ||
      classification.includes('restricted')
    ) {
      this.classificationColor = '#ff9800';
    } else if (
      classification.includes('public') ||
      classification.includes('unclassified')
    ) {
      this.classificationColor = '#4caf50';
    } else {
      this.classificationColor = '#2196f3';
    }
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  formatSimilarityScore(score: number | undefined | null): string {
    if (score == null || isNaN(score)) {
      return 'N/A';
    }
    return `${(score * 100).toFixed(1)}%`;
  }

  formatDate(dateString: string): string {
    try {
      const date = new Date(dateString);
      if (Number.isNaN(date.getTime())) {
        return dateString;
      }
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  }

  formatChunkText(text: string, maxLength = 200): string {
    if (text.length <= maxLength) {
      return text;
    }

    // Find a good break point (end of sentence or word)
    const truncated = text.substring(0, maxLength);
    const lastPeriod = truncated.lastIndexOf('.');
    const lastSpace = truncated.lastIndexOf(' ');

    const breakPoint = lastPeriod > lastSpace ? lastPeriod + 1 : lastSpace;

    return truncated.substring(0, breakPoint) + '...';
  }

  getTruncatedChunkText(): string {
    const chunkText = this.source.chunk_text || this.source.content || '';
    return this.formatChunkText(chunkText, 200);
  }

  getFullChunkText(): string {
    return this.source.chunk_text || this.source.content || '';
  }

  // ============================================================================
  // User Actions
  // ============================================================================

  toggleExpanded(): void {
    this.isExpanded = !this.isExpanded;
  }

  copyToClipboard(text: string): void {
    navigator.clipboard.writeText(text).catch((err) => {
      console.error('Failed to copy text: ', err);
    });
  }

  openDocument(): void {
    if (this.source.url) {
      window.open(this.source.url, '_blank');
    } else {
      // TODO: Navigate to document viewer or show document details.
    }
  }

  downloadDocument(): void {
    // TODO: Implement document download functionality
  }

  // ============================================================================
  // Template Helpers
  // ============================================================================

  get hasAuthor(): boolean {
    return !!this.source.author && this.source.author.length > 0;
  }

  get hasPageNumber(): boolean {
    return this.source.page_number !== undefined;
  }

  get hasClassification(): boolean {
    return (
      !!this.source.classification && this.source.classification.length > 0
    );
  }

  get hasUrl(): boolean {
    return !!this.source.url && this.source.url.length > 0;
  }

  get isHighRelevance(): boolean {
    return this.relevanceScore >= 0.8;
  }

  get isMediumRelevance(): boolean {
    return this.relevanceScore >= 0.6 && this.relevanceScore < 0.8;
  }

  get isLowRelevance(): boolean {
    return this.relevanceScore < 0.6;
  }

  get shouldTruncate(): boolean {
    const chunkText = this.source.chunk_text || this.source.content || '';
    return chunkText.length > 200;
  }

  get confidenceColor(): string {
    switch (this.confidenceLevel) {
      case 'high':
        return '#4caf50';
      case 'medium':
        return '#ff9800';
      case 'low':
        return '#f44336';
      default:
        return '#666';
    }
  }

  get relevanceColor(): string {
    if (this.isHighRelevance) return '#4caf50';
    if (this.isMediumRelevance) return '#ff9800';
    return '#f44336';
  }

  // ============================================================================
  // Classification Helpers
  // ============================================================================

  getClassificationIcon(): string {
    if (!this.source.classification) return 'shield';

    const classification = this.source.classification.toLowerCase();

    if (
      classification.includes('confidential') ||
      classification.includes('secret')
    ) {
      return 'lock';
    } else if (
      classification.includes('internal') ||
      classification.includes('restricted')
    ) {
      return 'building-2';
    } else if (
      classification.includes('public') ||
      classification.includes('unclassified')
    ) {
      return 'globe';
    } else {
      return 'shield';
    }
  }

  getClassificationLabel(): string {
    if (!this.source.classification) return 'Unclassified';
    return this.source.classification;
  }
}
