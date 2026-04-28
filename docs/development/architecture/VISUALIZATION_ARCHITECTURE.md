# Visualization Architecture

**Version:** 1.0
**Date:** October 10, 2025
**Status:** ✅ Implemented (P2-F5)

## Overview

This document defines the visualization architecture for AI Operations Platform, a security operations application that requires multiple visualization types for analytics, graph relationships, and LLM-generated content.

## Visualization Requirements

### 1. Security Analytics
- Usage statistics and trends
- Performance metrics over time
- Document access patterns
- Security event monitoring

### 2. Graph Relationships
- Threat actor relationships
- Indicator of Compromise (IOC) connections
- Attack path visualizations
- Knowledge graph representations
- Future Neo4j integration support

### 3. LLM-Generated Visualizations
- Flowcharts and process diagrams
- Sequence diagrams
- Network relationship diagrams
- Mathematical notation
- Attack flow representations

## Technology Stack

### Standard Analytics Charts: **Chart.js** (ng2-charts)
- **Purpose:** Time-series data, bar charts, pie charts, line graphs
- **License:** MIT (enterprise-friendly)
- **Use Cases:**
  - Usage analytics dashboards
  - Performance metrics over time
  - Document access trends
  - Security event counts

**Rationale:** Already installed, lightweight, excellent for standard analytics

### Graph/Relationship Diagrams: **ngx-graph** (Swimlane)
- **Purpose:** Interactive network and relationship visualizations
- **License:** MIT (enterprise-friendly)
- **Use Cases:**
  - Threat actor relationships
  - IOC connection graphs
  - Attack path visualizations
  - Knowledge graph representations
  - Future Neo4j data visualization

**Rationale:** Purpose-built for Angular, excellent for graph databases, interactive

### LLM Diagram Rendering: **Mermaid.js**
- **Purpose:** Text-to-diagram rendering for LLM outputs
- **License:** MIT (enterprise-friendly)
- **Use Cases:**
  - Flowcharts from LLM descriptions
  - Sequence diagrams for attack flows
  - State diagrams for security processes
  - Entity relationship diagrams
  - Gantt charts for incident timelines

**Rationale:** LLMs can generate Mermaid syntax easily, widely supported

### Mathematical Notation: **KaTeX**
- **Purpose:** Fast mathematical typography
- **License:** MIT (enterprise-friendly)
- **Use Cases:**
  - Security formulas and calculations
  - Risk score calculations
  - Statistical analysis notation
  - Cryptographic notation

**Rationale:** Fast, lightweight, compatible with LLM output

### Markdown Parsing: **marked**
- **Purpose:** Convert markdown to HTML with proper sanitization
- **License:** MIT (enterprise-friendly)
- **Use Cases:**
  - LLM response formatting
  - Rich text rendering
  - Code syntax highlighting integration

**Rationale:** Industry standard, secure, extensible

## Architecture Components

### 1. Analytics Service (`analytics.service.ts`)
```typescript
- getHotDocuments(): Observable<HotDocumentsResponse>
- getUsageStats(): Observable<UsageStatsResponse>
- getSecurityMetrics(): Observable<SecurityMetricsResponse>
```

### 2. Graph Visualization Service (`graph-visualization.service.ts`)
```typescript
- createThreatGraph(data: ThreatRelationships): GraphData
- createIOCGraph(data: IOCRelationships): GraphData
- createAttackPath(data: AttackSequence): GraphData
- exportToNeo4j(graph: GraphData): Cypher
```

### 3. LLM Content Renderer (`llm-content-renderer.component.ts`)
```typescript
- renderMarkdown(content: string): SafeHtml
- renderMermaid(diagramDef: string): void
- renderKaTeX(formula: string): SafeHtml
- detectAndRenderVisualization(content: string): void
```

### 4. Analytics Components
- `usage-analytics.component.ts` - Chart.js dashboards
- `performance-metrics.component.ts` - Performance visualizations
- `security-audit.component.ts` - Security metrics

### 5. Graph Components
- `threat-graph.component.ts` - Threat actor relationships
- `ioc-network.component.ts` - IOC connections
- `attack-path.component.ts` - Attack flow visualization

## Component Integration Points

### Use Case Execution Results
```typescript
// Result rendering with multiple visualization types
<app-llm-content-renderer
    [content]="executionResult.response"
    [enableMermaid]="true"
    [enableKaTeX]="true">
</app-llm-content-renderer>
```

### RAG Q&A Responses
```typescript
// Answer display with rich formatting
<app-llm-content-renderer
    [content]="answer.text"
    [enableMermaid]="true"
    [enableKaTeX]="true">
</app-llm-content-renderer>
```

### Thread Conversations
```typescript
// Message bubbles with visualization support
<app-llm-content-renderer
    [content]="message.content"
    [enableMermaid]="message.role === 'assistant'"
    [enableKaTeX]="true">
</app-llm-content-renderer>
```

## LLM Integration Patterns

### Mermaid Diagram Generation
LLMs can generate Mermaid syntax in code blocks:

\`\`\`mermaid
graph TD
    A[Reconnaissance] --> B[Initial Access]
    B --> C[Execution]
    C --> D[Persistence]
    D --> E[Privilege Escalation]
\`\`\`

### LaTeX/KaTeX Mathematical Notation
Inline: $E = mc^2$
Block: $$\text{Risk Score} = P \times I \times V$$

### Relationship Graphs
The LLM can output JSON that we render with ngx-graph:

```json
{
  "nodes": [
    {"id": "actor1", "label": "APT29"},
    {"id": "malware1", "label": "Cobalt Strike"}
  ],
  "edges": [
    {"source": "actor1", "target": "malware1", "label": "uses"}
  ]
}
```

## Future Enhancements

### Phase 3 Considerations
1. **ngx-echarts** - For advanced force-directed graphs and 3D visualizations
2. **D3.js custom visualizations** - For specialized security visualizations
3. **Neo4j Browser integration** - Direct graph database visualization
4. **Cytoscape.js** - Alternative for very large graphs (10K+ nodes)

### Performance Optimization
- Virtual scrolling for large datasets
- Canvas rendering for 1000+ node graphs
- WebGL acceleration for 3D visualizations
- Lazy loading of visualization libraries

## Security Considerations

### Content Sanitization
All LLM-generated content must be sanitized:
- Use DomSanitizer for HTML
- Validate Mermaid syntax before rendering
- Escape user input in KaTeX formulas
- Content Security Policy (CSP) compliance

### Data Privacy
- No external CDNs (air-gapped deployment)
- All libraries bundled in application
- No telemetry or analytics tracking

## Testing Strategy

### Unit Tests
- Chart data transformation logic
- Graph data structure validation
- Mermaid syntax detection
- KaTeX formula parsing

### Integration Tests
- Chart rendering with real data
- Graph interaction (zoom, pan, select)
- Mermaid diagram generation
- Mixed content rendering

### E2E Tests
- Analytics dashboard workflows
- Graph exploration scenarios
- LLM response with diagrams
- Performance under load

## Implementation Status

- ✅ Chart.js analytics (P2-F5)
- ✅ Analytics service and models (P2-F5)
- ✅ Usage Analytics component (P2-F5)
- ✅ ngx-graph installed (P2-F5)
- ✅ Mermaid.js installed (P2-F5)
- ✅ KaTeX installed (P2-F5)
- 🔄 LLM content renderer (P2-F5 in progress)
- ⏳ Graph visualization service (P3)
- ⏳ Threat graph components (P3)
- ⏳ Neo4j integration (P3)

## References

- [ngx-graph Documentation](https://swimlane.gitbook.io/ngx-graph/)
- [Mermaid.js Documentation](https://mermaid.js.org/)
- [KaTeX Documentation](https://katex.org/)
- [Chart.js Documentation](https://www.chartjs.org/)
- [Neo4j Visualization Best Practices](https://neo4j.com/developer/graph-visualization/)
