import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import {
  SchemaEditorComponent,
  SchemaPreset,
  SchemaValidationResult,
} from './schema-editor.component';

describe('SchemaEditorComponent', () => {
  let component: SchemaEditorComponent;
  let fixture: ComponentFixture<SchemaEditorComponent>;

  const validSchema = `{
  "type": "object",
  "required": ["id"],
  "properties": {
    "id": { "type": "string" }
  }
}`;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SchemaEditorComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(SchemaEditorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should validate valid JSON and emit valid result', () => {
    const emitSpy = jest.spyOn(component.validationChange, 'emit');
    component.onSchemaInput(validSchema);
    expect(emitSpy).toHaveBeenCalled();
    const result = emitSpy.mock.calls[0][0] as SchemaValidationResult;
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('should validate invalid JSON and emit syntax error', () => {
    const emitSpy = jest.spyOn(component.validationChange, 'emit');
    component.onSchemaInput('{ invalid }');
    expect(emitSpy).toHaveBeenCalled();
    const result = emitSpy.mock.calls[0][0] as SchemaValidationResult;
    expect(result.valid).toBe(false);
    expect(result.errors[0].level).toBe('syntax');
  });

  it('should emit schema on input', () => {
    const emitSpy = jest.spyOn(component.schemaChange, 'emit');
    component.onSchemaInput(validSchema);
    expect(emitSpy).toHaveBeenCalledWith(validSchema);
  });

  it('should format schema and emit', () => {
    component.schema = '{"type":"object"}';
    const emitSpy = jest.spyOn(component.schemaChange, 'emit');
    component.formatSchema();
    expect(emitSpy).toHaveBeenCalled();
    expect(component.schema).toContain('\n');
  });

  it('should clear schema and emit', () => {
    component.schema = validSchema;
    const emitSpy = jest.spyOn(component.schemaChange, 'emit');
    component.clearSchema();
    expect(emitSpy).toHaveBeenCalledWith('');
    expect(component.schema).toBe('');
  });

  it('should generate schema from example JSON', () => {
    const example = '{"name": "test", "count": 1}';
    component.exampleJson = example;
    const emitSpy = jest.spyOn(component.schemaChange, 'emit');
    component.generateFromExample();
    expect(emitSpy).toHaveBeenCalled();
    expect(component.schema).toContain('"type": "object"');
    expect(component.schema).toContain('"name"');
    expect(component.schema).toContain('"count"');
  });

  it('should apply preset and emit schema', () => {
    const preset: SchemaPreset = {
      id: 'test',
      label: 'Test',
      schema: validSchema,
    };
    const emitSpy = jest.spyOn(component.schemaChange, 'emit');
    component.applyPreset(preset);
    expect(emitSpy).toHaveBeenCalled();
    expect(component.schema).toContain('"type": "object"');
    expect(component.schema).toContain('"id"');
  });
});
