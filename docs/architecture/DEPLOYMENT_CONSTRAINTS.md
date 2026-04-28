# Deployment Constraints

This document outlines the deployment constraints and requirements for AI Operations Platform, particularly for air-gapped enterprise environments.

## Air-Gapped Deployment Requirements

### Network Isolation Constraints

**No External Internet Access**
- Production environments cannot access HuggingFace or external tokenizer registries
- No cloud services or external APIs during runtime
- All dependencies must be bundled or pre-installed

**Internal Network Requirements**
- PostgreSQL database connectivity
- Qdrant vector store connectivity
- Inter-service communication (backend, frontend, LLM-Guard)
- WebSocket connections for real-time features

### Tokenizer Constraints

**Offline Tokenizer Requirement**
- All model tokenizers must be bundled in the deployment
- No runtime downloads of BPE vocabulary files
- Fallback to character approximation if tokenizers unavailable
- Supported models: Foundation-sec, Phi-4 mini, Mistral Large/Small, GPT-oss, Llama 3.3

**Tokenizer Storage**
- ~50MB additional storage for 6 model tokenizers
- Read-only access to tokenizer files
- Integrity verification on deployment

### LLMaaS Pricing Tier Constraints

**Dynamic Pricing Management**
- Pricing tiers must be configurable without code changes
- Database-backed pricing configuration
- Admin UI for pricing tier CRUD operations
- Full audit trail for pricing changes

**Rate Limit SLA Requirements**
- Token usage monitoring with 1-minute granularity
- Real-time rate limit calculations
- Tier upgrade recommendations
- Utilization percentage tracking

### Security Constraints

**Access Control**
- Admin-only access to pricing management UI
- Role-based access control (analyst, admin)
- Audit logging for all administrative actions
- Change reason requirements for pricing updates

**Data Protection**
- No external data exfiltration
- All sensitive data remains local
- Encryption for data at rest and in transit
- Compliance with enterprise security standards

## Performance Constraints

### Token Counting Accuracy
- ±2% accuracy with proper tokenizers
- ±20% accuracy with character approximation (fallback)
- Rate limit calculations must be within 5% of actual usage

### Rate Limit Monitoring
- 1-minute rolling window for TPM calculations
- Real-time dashboard updates
- Alert thresholds: 80% (warning), 90% (critical)

### Database Performance
- Pricing tier queries must complete within 100ms
- Token usage aggregation within 500ms
- Audit log queries within 200ms

## Compliance Constraints

### Audit Requirements
- All pricing changes must include change reason
- User attribution for all administrative actions
- Immutable audit trail
- Compliance reporting capabilities

### Data Governance
- Data classification and handling
- Retention policies for audit logs
- Backup and recovery procedures
- Change management processes

## Operational Constraints

### Deployment Procedures
- Secure file transfer for tokenizer bundles
- Integrity verification for all transferred files
- Zero-downtime deployment capability
- Rollback procedures for failed deployments

### Monitoring Requirements
- Health checks for all services
- Token usage monitoring
- Rate limit violation alerts
- Performance metrics collection

### Maintenance Windows
- Scheduled maintenance procedures
- Update procedures for tokenizers
- Database migration procedures
- Configuration update procedures

## Technology Constraints

### Container Requirements
- Docker containerization for all services
- No privileged containers
- Resource limits and quotas
- Security scanning compliance

### Database Constraints
- PostgreSQL 13+ required
- UUID-based schema
- Transaction isolation requirements
- Backup and recovery procedures

### Frontend Constraints
- Angular 21+ framework
- Progressive Web App (PWA) capabilities
- Offline functionality where applicable
- Accessibility compliance (WCAG 2.1)

## Integration Constraints

### Enterprise Systems
- Single Sign-On (SSO) integration
- LDAP/Active Directory integration
- Enterprise key management systems
- SIEM integration capabilities

### External Dependencies
- No runtime external API calls
- Pre-configured model endpoints
- Offline documentation and help
- Self-contained diagnostic tools

## Scalability Constraints

### Horizontal Scaling
- Stateless service design
- Load balancer compatibility
- Database connection pooling
- Session management requirements

### Vertical Scaling
- Memory requirements for tokenizers
- CPU requirements for token counting
- Storage requirements for audit logs
- Network bandwidth for real-time updates

## Disaster Recovery Constraints

### Backup Requirements
- Daily database backups
- Configuration backup procedures
- Tokenizer file backup
- Audit log retention

### Recovery Procedures
- Point-in-time recovery capability
- Service restart procedures
- Configuration restoration
- Data integrity verification

## References

- [ADR-019: Offline Tokenizer Strategy](../development/adrs/ADR-019-Offline-Tokenizer-Strategy.md)
- [Air-Gapped Deployment Guide](../operations/AIR_GAPPED_DEPLOYMENT.md)
- [UI Development Plan](../development/plans/UI_DEVELOPMENT_PLAN.md)
- [Pricing Management Guide](../admin/PRICING_MANAGEMENT.md)
