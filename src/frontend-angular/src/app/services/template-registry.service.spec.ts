/**
 * Unit Tests for Template Registry Service
 *
 * ADR-066: Templates use structural names.
 */

import { TestBed } from '@angular/core/testing';
import {
  OutputFormatTemplate,
} from '../models/output-format.model';
import {
  TemplateRegistryService,
} from './template-registry.service';

describe('TemplateRegistryService', () => {
  let service: TemplateRegistryService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TemplateRegistryService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should have 8 built-in templates registered', () => {
    const templates = service.list();
    expect(templates.length).toBe(8);
  });

  it('should retrieve score-table-timeline template', () => {
    const tpl = service.get('score-table-timeline');
    expect(tpl).toBeDefined();
    expect(tpl?.name).toBe('Score + Table + Timeline');
    expect(tpl?.layout.sections.length).toBe(3);
  });

  it('should retrieve filterable-table template', () => {
    const tpl = service.get('filterable-table');
    expect(tpl).toBeDefined();
    expect(tpl?.name).toBe('Filterable Data Table');
  });

  it('should retrieve score-timeline template', () => {
    const tpl = service.get('score-timeline');
    expect(tpl).toBeDefined();
    expect(tpl?.name).toBe('Score + Timeline');
  });

  it('should retrieve auto-table template', () => {
    const tpl = service.get('auto-table');
    expect(tpl).toBeDefined();
    expect(tpl?.name).toBe('Auto-Column Table');
  });

  it('should retrieve bar-chart template', () => {
    const tpl = service.get('bar-chart');
    expect(tpl).toBeDefined();
    expect(tpl?.name).toBe('Bar Chart');
  });

  it('should retrieve kv-summary template (new)', () => {
    const tpl = service.get('kv-summary');
    expect(tpl).toBeDefined();
    expect(tpl?.name).toBe('Key-Value Summary');
  });

  it('should retrieve multi-table template (new)', () => {
    const tpl = service.get('multi-table');
    expect(tpl).toBeDefined();
    expect(tpl?.name).toBe('Multi-Table View');
    expect(tpl?.layout.type).toBe('tabs');
  });

  it('should retrieve comparison-grid template (new)', () => {
    const tpl = service.get('comparison-grid');
    expect(tpl).toBeDefined();
    expect(tpl?.name).toBe('Comparison Grid');
    expect(tpl?.layout.sections.length).toBe(2);
  });

  it('should return undefined for non-existent template', () => {
    expect(service.get('non-existent')).toBeUndefined();
  });

  it('should return undefined for old template IDs', () => {
    expect(service.get('threat-triage-dashboard'))
      .toBeUndefined();
    expect(service.get('ioc-extraction-table'))
      .toBeUndefined();
    expect(service.get('incident-summary'))
      .toBeUndefined();
    expect(service.get('simple-table'))
      .toBeUndefined();
    expect(service.get('metrics-dashboard'))
      .toBeUndefined();
  });

  it('should check if template exists', () => {
    expect(service.has('score-table-timeline'))
      .toBe(true);
    expect(service.has('non-existent')).toBe(false);
  });

  it('should register new template', () => {
    const newTemplate: OutputFormatTemplate = {
      template_id: 'test-template',
      name: 'Test Template',
      description: 'Test',
      data_schema: { type: 'object' },
      layout: { type: 'single', sections: [] },
      export_formats: [],
    };

    service.register(newTemplate);
    expect(service.has('test-template')).toBe(true);

    const retrieved = service.get('test-template');
    expect(retrieved?.name).toBe('Test Template');
  });

  it('should unregister template', () => {
    service.unregister('score-table-timeline');
    expect(service.has('score-table-timeline'))
      .toBe(false);
  });

  it('should clear all templates', () => {
    service.clearAll();
    expect(service.list().length).toBe(0);
  });
});
