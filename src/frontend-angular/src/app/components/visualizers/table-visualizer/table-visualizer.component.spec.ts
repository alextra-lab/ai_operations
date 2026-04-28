/**
 * Unit Tests for Table Visualizer Component
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TableConfig } from '../../../models/output-format.model';
import { TableVisualizerComponent } from './table-visualizer.component';

describe('TableVisualizerComponent', () => {
  let component: TableVisualizerComponent;
  let fixture: ComponentFixture<TableVisualizerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        TableVisualizerComponent,
        MatTableModule,
        MatPaginatorModule,
        MatSortModule,
        MatFormFieldModule,
        MatInputModule,
        MatIconModule,
        MatButtonModule,
        NoopAnimationsModule,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TableVisualizerComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render table with provided data', () => {
    const testData = [
      { id: 1, name: 'Test 1', value: 100 },
      { id: 2, name: 'Test 2', value: 200 },
    ];

    const testConfig: TableConfig = {
      columns: [
        { field: 'id', header: 'ID' },
        { field: 'name', header: 'Name' },
        { field: 'value', header: 'Value' },
      ],
    };

    component.data = testData;
    component.config = testConfig;
    component.ngOnInit();
    fixture.detectChanges();

    expect(component.dataSource.data.length).toBe(2);
    expect(component.displayedColumns).toEqual(['id', 'name', 'value']);
  });

  it('should auto-generate columns when not provided', () => {
    const testData = [{ id: 1, name: 'Test', value: 100 }];

    component.data = testData;
    component.config = { columns: [] };
    component.ngOnInit();

    expect(component.config.columns.length).toBe(3);
    expect(component.config.columns[0].field).toBe('id');
  });

  it('should export data as CSV', () => {
    const testData = [
      { id: 1, name: 'Test 1' },
      { id: 2, name: 'Test 2' },
    ];

    const testConfig: TableConfig = {
      columns: [
        { field: 'id', header: 'ID' },
        { field: 'name', header: 'Name' },
      ],
    };

    component.data = testData;
    component.config = testConfig;
    component.ngOnInit();

    const csv = component['convertToCSV'](testData);
    expect(csv).toContain('ID,Name');
    expect(csv).toContain('1,Test 1');
  });

  it('should handle empty data gracefully', () => {
    component.data = [];
    component.config = { columns: [] };
    component.ngOnInit();
    fixture.detectChanges();

    expect(component.dataSource.data.length).toBe(0);
  });
});
