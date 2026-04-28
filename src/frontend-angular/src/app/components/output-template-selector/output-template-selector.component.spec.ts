import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { OutputFormatTemplate } from '../../models/output-format.model';
import { TemplateRegistryService } from '../../services/template-registry.service';
import { OutputTemplateSelectorComponent } from './output-template-selector.component';

describe('OutputTemplateSelectorComponent', () => {
  let component: OutputTemplateSelectorComponent;
  let fixture: ComponentFixture<OutputTemplateSelectorComponent>;
  let mockRegistry: { list: jest.Mock };

  const mockTemplates: OutputFormatTemplate[] = [
    {
      template_id: 'auto-table',
      name: 'Auto-Column Table',
      description: 'Generic table with auto-detected columns',
      data_schema: { type: 'object' },
      layout: { type: 'single', sections: [] },
      export_formats: ['json'],
    },
  ];

  beforeEach(async () => {
    mockRegistry = { list: jest.fn(() => mockTemplates) };
    await TestBed.configureTestingModule({
      imports: [OutputTemplateSelectorComponent, NoopAnimationsModule],
      providers: [
        {
          provide: TemplateRegistryService,
          useValue: mockRegistry,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(OutputTemplateSelectorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load templates from registry', () => {
    expect(mockRegistry.list).toHaveBeenCalled();
    expect(component.templates).toEqual(mockTemplates);
  });

  it('should emit template id on selection', () => {
    const emitSpy = jest.spyOn(component.templateChange, 'emit');
    component.onSelectionChange('auto-table');
    expect(emitSpy).toHaveBeenCalledWith('auto-table');
  });

  it('should emit null when empty string selected', () => {
    const emitSpy = jest.spyOn(component.templateChange, 'emit');
    component.onSelectionChange('');
    expect(emitSpy).toHaveBeenCalledWith(null);
  });
});
