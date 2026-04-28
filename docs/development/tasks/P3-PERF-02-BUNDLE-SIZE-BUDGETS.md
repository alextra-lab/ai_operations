# P3-PERF-02: Enforce Bundle Size Budgets

**Status:** 📋 DEFERRED (Phase 6)
**Updated:** 2025-10-25
**Phase Assignment:** Phase 6 - Performance & Production
**Sequence:** After P3-PERF-01 completes in Phase 4
**Priority:** 🟠 HIGH
**Estimated Effort:** 2-3 hours
**Created:** 2025-10-13
**Target Completion:** Week 1

---

## Problem Statement

Current bundle size budgets in `angular.json` are too permissive:

```json
"budgets": [
  {
    "type": "initial",
    "maximumWarning": "2MB",    // TOO HIGH
    "maximumError": "5MB"        // WAY TOO HIGH
  }
]
```

This allows the application to grow unchecked, leading to:
- **Current bundle size:** 1.5MB (approaching warning threshold)
- **No build-time enforcement** of performance standards
- **Gradual performance degradation** over time
- **Difficult to identify** which changes introduce bloat

---

## Success Criteria

- [ ] Strict bundle size budgets enforced at build time
- [ ] CI/CD pipeline fails if budgets are exceeded
- [ ] Budgets aligned with industry best practices
- [ ] Clear error messages when budgets are exceeded
- [ ] Documentation for developers on staying within budgets

---

## Technical Approach

### 1. Update Angular Build Budgets

**File:** `src/frontend-angular/angular.json`

**Current (Lines 63-81):**
```json
"budgets": [
  {
    "type": "initial",
    "maximumWarning": "2MB",
    "maximumError": "5MB"
  },
  {
    "type": "anyComponentStyle",
    "maximumWarning": "6kB",
    "maximumError": "12kB"
  },
  {
    "type": "bundle",
    "name": "styles",
    "baseline": "90kB",
    "maximumWarning": "100kB",
    "maximumError": "120kB"
  }
]
```

**Change to:**
```json
"budgets": [
  {
    "type": "initial",
    "maximumWarning": "500kB",
    "maximumError": "750kB"
  },
  {
    "type": "anyComponentStyle",
    "maximumWarning": "4kB",
    "maximumError": "8kB"
  },
  {
    "type": "bundle",
    "name": "styles",
    "baseline": "80kB",
    "maximumWarning": "90kB",
    "maximumError": "100kB"
  },
  {
    "type": "bundle",
    "name": "main",
    "baseline": "100kB",
    "maximumWarning": "150kB",
    "maximumError": "200kB"
  },
  {
    "type": "bundle",
    "name": "polyfills",
    "baseline": "30kB",
    "maximumWarning": "40kB",
    "maximumError": "50kB"
  },
  {
    "type": "anyScript",
    "maximumWarning": "150kB",
    "maximumError": "200kB"
  }
]
```

### 2. Add Bundle Analysis to Build Process

**File:** `src/frontend-angular/package.json`

**Add scripts:**
```json
{
  "scripts": {
    "build": "ng build",
    "build:analyze": "ng build --stats-json",
    "analyze": "npm run build:analyze && webpack-bundle-analyzer dist/aio-ui/browser/stats.json",
    "build:prod": "ng build --configuration production",
    "build:prod:analyze": "ng build --configuration production --stats-json && webpack-bundle-analyzer dist/aio-ui/browser/stats.json"
  }
}
```

**Install webpack-bundle-analyzer:**
```bash
npm install --save-dev webpack-bundle-analyzer
```

### 3. Create Budget Report Script

**New File:** `src/frontend-angular/ops/check-bundle-size.js`

```javascript
#!/usr/bin/env node

/**
 * Check bundle sizes against budgets and generate report
 * Run: node ops/check-bundle-size.js
 */

const fs = require('fs');
const path = require('path');

const DIST_DIR = path.join(__dirname, '../dist/aio-ui/browser');
const BUDGETS_FILE = path.join(__dirname, '../angular.json');

// Read budgets from angular.json
const angularConfig = JSON.parse(fs.readFileSync(BUDGETS_FILE, 'utf8'));
const budgets = angularConfig.projects['aio-ui']
  .architect.build.configurations.production.budgets;

// Scan dist directory for bundle sizes
function getFileSizes(dir) {
  const files = {};

  if (!fs.existsSync(dir)) {
    console.error(`Directory not found: ${dir}`);
    console.error('Run "npm run build" first');
    process.exit(1);
  }

  fs.readdirSync(dir).forEach(file => {
    const filePath = path.join(dir, file);
    const stats = fs.statSync(filePath);

    if (stats.isFile() && (file.endsWith('.js') || file.endsWith('.css'))) {
      files[file] = stats.size;
    }
  });

  return files;
}

// Format bytes to human-readable
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Check file against budget
function checkBudget(fileName, size, budget) {
  const warningThreshold = parseSize(budget.maximumWarning);
  const errorThreshold = parseSize(budget.maximumError);

  if (size > errorThreshold) {
    return { status: 'ERROR', message: `Exceeds error threshold (${formatBytes(errorThreshold)})` };
  } else if (size > warningThreshold) {
    return { status: 'WARNING', message: `Exceeds warning threshold (${formatBytes(warningThreshold)})` };
  } else {
    return { status: 'OK', message: 'Within budget' };
  }
}

// Parse size string (e.g., "500kB") to bytes
function parseSize(sizeStr) {
  const match = sizeStr.match(/^(\d+(?:\.\d+)?)(B|kB|MB)$/);
  if (!match) return 0;

  const [, value, unit] = match;
  const multipliers = { B: 1, kB: 1024, MB: 1024 * 1024 };
  return parseFloat(value) * multipliers[unit];
}

// Main execution
console.log('🔍 Checking bundle sizes...\n');

const files = getFileSizes(DIST_DIR);
const results = [];

// Calculate totals
let totalJsSize = 0;
let totalCssSize = 0;

Object.entries(files).forEach(([file, size]) => {
  if (file.endsWith('.js')) totalJsSize += size;
  if (file.endsWith('.css')) totalCssSize += size;
});

console.log('📊 Summary:');
console.log(`  Total JavaScript: ${formatBytes(totalJsSize)}`);
console.log(`  Total CSS: ${formatBytes(totalCssSize)}`);
console.log(`  Total Assets: ${formatBytes(totalJsSize + totalCssSize)}\n`);

// Check against budgets
let hasErrors = false;
let hasWarnings = false;

// Check initial budget (main + polyfills)
const mainFiles = Object.entries(files).filter(([name]) =>
  name.startsWith('main-') || name.startsWith('polyfills-')
);
const initialSize = mainFiles.reduce((sum, [, size]) => sum + size, 0);

const initialBudget = budgets.find(b => b.type === 'initial');
if (initialBudget) {
  const result = checkBudget('Initial Bundle', initialSize, initialBudget);
  console.log(`Initial Bundle: ${formatBytes(initialSize)} - ${result.status}`);
  if (result.status === 'ERROR') hasErrors = true;
  if (result.status === 'WARNING') hasWarnings = true;
}

console.log('\n📦 Individual Bundles:');

// Sort files by size (largest first)
Object.entries(files)
  .sort(([, a], [, b]) => b - a)
  .slice(0, 10) // Show top 10
  .forEach(([file, size]) => {
    console.log(`  ${file.padEnd(40)} ${formatBytes(size).padStart(10)}`);
  });

// Exit with appropriate code
if (hasErrors) {
  console.log('\n❌ Bundle size check FAILED - exceeds error thresholds');
  process.exit(1);
} else if (hasWarnings) {
  console.log('\n⚠️  Bundle size check passed with WARNINGS');
  process.exit(0);
} else {
  console.log('\n✅ Bundle size check PASSED');
  process.exit(0);
}
```

Make executable:
```bash
chmod +x src/frontend-angular/ops/check-bundle-size.js
```

### 4. Update CI/CD Pipeline

**File:** `.github/workflows/frontend-build.yml` (or similar)

Add bundle size check step:

```yaml
- name: Build Angular App
  run: |
    cd src/frontend-angular
    npm ci
    npm run build:prod

- name: Check Bundle Sizes
  run: |
    cd src/frontend-angular
    node ops/check-bundle-size.js

- name: Generate Bundle Report
  if: always()
  run: |
    cd src/frontend-angular
    npm run build:prod:analyze
```

---

## Implementation Steps

### Phase 1: Update Budgets (30 minutes)
1. [ ] Update `angular.json` with new budget values
2. [ ] Run build locally to see current budget violations
3. [ ] Document any violations that need to be addressed

### Phase 2: Add Analysis Tools (1 hour)
4. [ ] Install webpack-bundle-analyzer
5. [ ] Add analysis scripts to package.json
6. [ ] Create check-bundle-size.js script
7. [ ] Test bundle analysis locally

### Phase 3: CI/CD Integration (1 hour)
8. [ ] Update CI/CD pipeline configuration
9. [ ] Test pipeline with budget checks
10. [ ] Configure notifications for budget violations

### Phase 4: Documentation (30 minutes)
11. [ ] Create developer guide for bundle management
12. [ ] Document how to analyze and reduce bundle sizes
13. [ ] Add troubleshooting guide for budget violations

---

## Budget Rationale

### Initial Bundle: 500kB Warning, 750kB Error

**Rationale:**
- Google recommends < 200kB for initial bundle
- After P3-PERF-01 (lazy loading), we expect ~400-500kB
- 500kB warning gives headroom for new features
- 750kB error is absolute maximum

### Component Styles: 4kB Warning, 8kB Error

**Rationale:**
- Most components should have minimal styles
- Large component styles indicate overly complex components
- Forces developers to use shared styles

### Main Bundle: 100kB Baseline, 200kB Error

**Rationale:**
- Core application logic should be lean
- Encourages feature modules and lazy loading
- Prevents "everything in main" antipattern

### Any Script: 150kB Warning, 200kB Error

**Rationale:**
- Prevents single massive chunks
- Encourages proper code splitting
- Ensures lazy-loaded routes are reasonably sized

---

## Testing Checklist

### Build Tests
- [ ] Production build completes successfully
- [ ] Budget warnings appear for oversized bundles
- [ ] Budget errors fail the build when exceeded
- [ ] Bundle analysis script runs without errors

### CI/CD Tests
- [ ] Pipeline runs budget checks
- [ ] Pipeline fails when budgets are exceeded
- [ ] Bundle reports are generated and accessible

### Developer Experience
- [ ] Clear error messages when budgets exceeded
- [ ] Bundle analyzer provides actionable insights
- [ ] Documentation helps developers fix budget violations

---

## Performance Impact

### Before
- **No enforcement:** Budgets are advisory only
- **Gradual bloat:** No protection against bundle growth
- **Reactive:** Issues found after deployment

### After
- **Proactive enforcement:** Budgets prevent bloat at build time
- **Continuous monitoring:** Every build checks bundle sizes
- **Clear accountability:** Developers see impact of changes

---

## Developer Guide (To be created)

**File:** `src/frontend-angular/docs/BUNDLE_SIZE_MANAGEMENT.md`

Contents should include:
- How to analyze bundle sizes
- How to identify large dependencies
- Strategies for reducing bundle size
- Common causes of budget violations
- When to request budget increases

---

## Rollback Plan

If budgets cause build failures that can't be immediately fixed:

1. **Temporarily increase budgets:**
   ```json
   "maximumWarning": "1MB",
   "maximumError": "1.5MB"
   ```

2. **Create task** to address root cause
3. **Gradually decrease** budgets as improvements are made

---

## Related Tasks

- **Prerequisite:** P3-PERF-01 (Lazy load libraries - must complete first)
- **Blocks:** Future development (enforces bundle discipline)
- **Related:** P3-PERF-03 (OnPush change detection)

---

## Notes

- After P3-PERF-01 is complete, re-evaluate budget values
- Monitor bundle analyzer reports weekly
- Consider adding bundle size reporting to PR comments
- Track bundle size trends over time

---

## Acceptance Criteria

- ✅ Bundle budgets configured and enforced
- ✅ Build fails when budgets are exceeded
- ✅ Bundle analysis tools integrated
- ✅ CI/CD pipeline includes budget checks
- ✅ Developer documentation created
- ✅ All current builds pass budget checks (after P3-PERF-01)
- ✅ Team trained on bundle management

---

**Assignee:** TBD
**Reviewer:** TBD
**Dependencies:** P3-PERF-01
