import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import { UseCase } from '../../api/models/use-case.models';
import { UseCaseService } from '../../api/services/use-case.service';
import { UseCaseMenuComponent } from './use-case-menu.component';

describe('UseCaseMenuComponent', () => {
  let component: UseCaseMenuComponent;
  let fixture: ComponentFixture<UseCaseMenuComponent>;
  let useCaseServiceSpy: {
    getAvailableUseCases: jest.Mock;
    getCategories: jest.Mock;
    clearCache: jest.Mock;
    getUseCasesStream: any;
    getCategoriesStream: any;
  };
  let routerSpy: {
    navigate: jest.Mock;
  };

  const mockUseCases: UseCase[] = [
    {
      id: '1',
      use_case_id: 'threat-analysis',
      name: 'Threat Analysis',
      description: 'Analyze security threats',
      category: 'threat_analysis',
      intent_type: 'analysis',
      tags: ['security', 'threats'],
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
      created_by: 'admin',
      is_active: true,
    },
    {
      id: '2',
      use_case_id: 'incident-response',
      name: 'Incident Response',
      description: 'Handle security incidents',
      category: 'incident_response',
      intent_type: 'response',
      tags: ['security', 'incidents'],
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
      created_by: 'admin',
      is_active: true,
    },
  ];

  beforeEach(async () => {
    const useCaseServiceSpyObj = {
      getAvailableUseCases: jest.fn(),
      getCategories: jest.fn(),
      clearCache: jest.fn(),
      getUseCasesStream: jest.fn().mockReturnValue(of([])),
      getCategoriesStream: jest.fn().mockReturnValue(of([])),
    };

    const routerSpyObj = {
      navigate: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [
        UseCaseMenuComponent,
        ReactiveFormsModule,
        NoopAnimationsModule,
      ],
      providers: [
        FormBuilder,
        { provide: UseCaseService, useValue: useCaseServiceSpyObj },
        { provide: Router, useValue: routerSpyObj },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UseCaseMenuComponent);
    component = fixture.componentInstance;
    useCaseServiceSpy = TestBed.inject(
      UseCaseService
    ) as typeof useCaseServiceSpyObj;
    routerSpy = TestBed.inject(Router) as typeof routerSpyObj;
  });

  beforeEach(() => {
    useCaseServiceSpy.getAvailableUseCases.mockReturnValue(of(mockUseCases));
    useCaseServiceSpy.getCategories.mockReturnValue(
      of(['threat_analysis', 'incident_response'])
    );
    useCaseServiceSpy.getUseCasesStream.mockReturnValue(of(mockUseCases));
    useCaseServiceSpy.getCategoriesStream.mockReturnValue(
      of(['threat_analysis', 'incident_response'])
    );
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize form and load use cases on init', () => {
    fixture.detectChanges();

    expect(component.searchForm).toBeDefined();
    expect(useCaseServiceSpy.getAvailableUseCases).toHaveBeenCalled();
    expect(component.filteredUseCases).toEqual(mockUseCases);
    expect(component.isLoading).toBe(false);
  });

  it('should handle error when loading use cases', () => {
    const error = new Error('Failed to load use cases');
    useCaseServiceSpy.getAvailableUseCases.mockReturnValue(
      throwError(() => error)
    );

    fixture.detectChanges();

    expect(component.error).toBe('Failed to load use cases. Please try again.');
    expect(component.isLoading).toBe(false);
  });

  it('should filter use cases by search query', async () => {
    fixture.detectChanges();

    // Set searchQuery directly since form has 300ms debounce
    component.searchQuery = 'threat';
    component['applyFilters']();

    expect(component.paginatedUseCases.length).toBe(1);
    expect(component.paginatedUseCases[0].name).toBe('Threat Analysis');
  });

  it('should filter use cases by category', () => {
    fixture.detectChanges();

    // Set selectedCategory directly for immediate filter
    component.selectedCategory = 'threat_analysis';
    component['applyFilters']();

    expect(component.paginatedUseCases.length).toBe(1);
    expect(component.paginatedUseCases[0].category).toBe('threat_analysis');
  });

  it('should sort use cases by name', () => {
    fixture.detectChanges();

    // Set sort properties directly for immediate effect
    component.sortBy = 'name';
    component.sortOrder = 'asc';
    component['applyFilters']();

    expect(component.paginatedUseCases[0].name).toBe('Incident Response');
    expect(component.paginatedUseCases[1].name).toBe('Threat Analysis');
  });

  it('should open use case when clicked', () => {
    fixture.detectChanges();

    const useCase = mockUseCases[0];
    component.openUseCase(useCase);

    // Component navigates with UUID (id), not string use_case_id
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/use-cases', useCase.id]);
  });

  it('should refresh use cases', () => {
    fixture.detectChanges();

    component.refresh();

    expect(useCaseServiceSpy.clearCache).toHaveBeenCalled();
    expect(useCaseServiceSpy.getAvailableUseCases).toHaveBeenCalledTimes(2);
  });

  it('should change view mode', () => {
    component.onViewModeChange('list');
    expect(component.viewMode).toBe('list');

    component.onViewModeChange('grid');
    expect(component.viewMode).toBe('grid');
  });

  it('should change page', () => {
    fixture.detectChanges();
    component.itemsPerPage = 1;

    component.onPageChange(2);

    expect(component.currentPage).toBe(2);
  });

  it('should change items per page', () => {
    fixture.detectChanges();

    component.onItemsPerPageChange(6);

    expect(component.itemsPerPage).toBe(6);
    expect(component.currentPage).toBe(1);
  });

  it('should get category display name', () => {
    const displayName = component.getCategoryDisplayName('threat_analysis');
    expect(displayName).toBe('Threat Analysis');
  });

  it('should get use case icon', () => {
    const icon = component.getUseCaseIcon('threat_analysis');
    expect(icon).toBe('shield');
  });

  it('should get use case color', () => {
    const color = component.getUseCaseColor('threat_analysis');
    expect(color).toBe('var(--cat-threat)');
  });

  it('should calculate total pages correctly', () => {
    component.totalItems = 25;
    component.itemsPerPage = 10;

    expect(component.getTotalPages()).toBe(3);
  });

  it('should get page numbers correctly', () => {
    component.totalItems = 100;
    component.itemsPerPage = 10;
    component.currentPage = 5;

    const pageNumbers = component.getPageNumbers();
    expect(pageNumbers).toEqual([3, 4, 5, 6, 7]);
  });

  it('should detect hasUseCases correctly', () => {
    component.paginatedUseCases = [];
    expect(component.hasUseCases).toBe(false);

    component.paginatedUseCases = mockUseCases;
    expect(component.hasUseCases).toBe(true);
  });

  it('should detect hasFilters correctly', () => {
    component.searchQuery = '';
    component.selectedCategory = 'all';
    expect(component.hasFilters).toBe(false);

    component.searchQuery = 'test';
    expect(component.hasFilters).toBe(true);

    component.searchQuery = '';
    component.selectedCategory = 'threat_analysis';
    expect(component.hasFilters).toBe(true);
  });

  it('should detect isEmpty correctly', () => {
    component.isLoading = false;
    component.paginatedUseCases = [];
    expect(component.isEmpty).toBe(true);

    component.paginatedUseCases = mockUseCases;
    expect(component.isEmpty).toBe(false);
  });

  it('should detect showPagination correctly', () => {
    component.totalItems = 5;
    component.itemsPerPage = 10;
    expect(component.showPagination).toBe(false);

    component.totalItems = 25;
    expect(component.showPagination).toBe(true);
  });

  it('should cleanup on destroy', () => {
    jest.spyOn(component['destroy$'], 'next');
    jest.spyOn(component['destroy$'], 'complete');

    component.ngOnDestroy();

    expect(component['destroy$'].next).toHaveBeenCalled();
    expect(component['destroy$'].complete).toHaveBeenCalled();
  });
});
