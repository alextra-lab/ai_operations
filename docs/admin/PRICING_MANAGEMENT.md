# Pricing Management Guide

This guide provides instructions for administrators on managing LLMaaS pricing tiers and model configurations through the AI Operations Platform admin interface.

## Overview

The pricing management system allows administrators to:
- Create, update, and delete pricing tiers
- Configure model-to-tier associations
- Monitor token usage and rate limits
- View audit trails for all pricing changes
- Generate utilization reports

## Access Requirements

**Admin Role Required**
- Only users with `admin` role can access pricing management
- Located at: `/admin/pricing` (when implemented)
- Requires authentication and proper permissions

## Pricing Tier Management

### Creating New Pricing Tiers

1. **Navigate to Pricing Management**
   - Access: `/admin/pricing/tiers`
   - Click "Create New Tier" button

2. **Fill Required Fields**
   ```
   Tier Key: XS|Large (auto-generated from plan + model)
   Tier Name: Extra Small - Mistral Large
   Plan Size: XS, S, M, L, XL
   Model Class: Large, Small, Codestral/Llama
   Input Rate (per 1M tokens): 1.10
   Output Rate (per 1M tokens): 0.30
   Rate Limit (TPM): 2000
   Description: Optional description
   ```

3. **Validation Rules**
   - Tier Key must be unique
   - Plan Size + Model Class combination must be unique
   - Rates must be ≥ 0
   - Rate Limit must be ≥ 1

4. **Save Changes**
   - System automatically creates audit entry
   - New tier becomes available immediately

### Updating Existing Tiers

1. **Select Tier to Update**
   - Navigate to pricing tiers list
   - Click "Edit" button for desired tier

2. **Modify Fields**
   - Update rates, limits, or description
   - Tier Key cannot be changed after creation
   - Plan Size and Model Class cannot be changed

3. **Provide Change Reason**
   - **Required**: Enter reason for the change
   - Used for audit trail and compliance
   - Examples: "Price adjustment", "Rate limit increase", "Model update"

4. **Save Changes**
   - Old and new values recorded in audit log
   - Changes take effect immediately

### Deleting Pricing Tiers

1. **Check Usage**
   - System shows if tier is used by any models
   - If in use: tier is deactivated (soft delete)
   - If not in use: tier is permanently deleted

2. **Provide Deletion Reason**
   - **Required**: Enter reason for deletion
   - Examples: "Tier no longer needed", "Replaced by new tier"

3. **Confirm Deletion**
   - Review impact on associated models
   - Confirm deletion action

## Model Configuration Management

### Adding New Models

1. **Navigate to Model Configs**
   - Access: `/admin/pricing/models`
   - Click "Create New Model" button

2. **Configure Model Settings**
   ```
   Model ID: mistral-large-v2 (unique identifier)
   Model Name: Mistral Large v2 (display name)
   Provider: mistral, openai, meta, microsoft, foundation
   Tokenizer Type: tiktoken, sentencepiece, huggingface
   Encoding Name: mistral-large-v2 (for tiktoken)
   Default Pricing Tier: Select from dropdown
   Max Context Tokens: 8192
   Supports Streaming: Yes/No
   ```

3. **Tokenizer Configuration**
   - For air-gapped deployment: specify tokenizer file path
   - For standard deployment: use encoding name
   - Verify tokenizer works with test requests

4. **Save Configuration**
   - Model becomes available for use
   - Pricing tier association established

### Updating Model Configurations

1. **Select Model to Update**
   - Navigate to model configs list
   - Click "Edit" button for desired model

2. **Modify Settings**
   - Update pricing tier association
   - Change tokenizer settings
   - Adjust context limits or capabilities

3. **Save Changes**
   - Changes take effect immediately
   - No audit trail required for model configs

### Managing Model Availability

1. **Activate/Deactivate Models**
   - Toggle "Active" status
   - Inactive models cannot be used for new requests
   - Existing requests continue processing

2. **Health Check Status**
   - System monitors model availability
   - "Available" status indicates model is responding
   - Inactive models show as unavailable

## Rate Limit Monitoring

### Current Usage Dashboard

1. **Access Rate Limits**
   - Navigate to `/analytics/tokens/rate-limits/current`
   - View real-time token usage per model

2. **Key Metrics**
   ```
   Model: mistral-large
   Tokens In/Out per Minute: 1500 / 800
   Total TPM: 2300
   Rate Limit: 2000
   Utilization: 115%
   Status: CRITICAL
   Recommendation: UPGRADE_TIER
   ```

3. **Status Indicators**
   - **OK**: < 70% utilization
   - **MONITOR**: 70-80% utilization
   - **THROTTLE**: 80-90% utilization
   - **UPGRADE_TIER**: > 90% utilization

### Tier Status Overview

1. **Access Tier Status**
   - Navigate to `/analytics/tokens/tiers/status`
   - View all tiers with usage indicators

2. **Tier Information**
   ```
   Tier: XS|Large
   Models Using: 2
   Total Usage TPM: 1800
   Rate Limit: 2000
   Utilization: 90%
   Status: WARNING
   ```

3. **Recommendations**
   - System suggests tier upgrades when needed
   - Identifies underutilized tiers
   - Provides cost optimization suggestions

## Audit Trail Management

### Viewing Audit History

1. **Access Audit Logs**
   - Click "View Audit" button for any pricing tier
   - Shows complete change history

2. **Audit Entry Details**
   ```
   Action: UPDATE
   Changed By: admin@example.com
   Changed At: 2025-01-27 14:30:00 UTC
   Change Reason: Price adjustment for Q2 2025

   Old Values:
   - input_rate_per_1m: 1.00
   - rate_limit_tpm: 1500

   New Values:
   - input_rate_per_1m: 1.10
   - rate_limit_tpm: 2000
   ```

3. **Audit Actions**
   - **CREATE**: New tier created
   - **UPDATE**: Tier modified
   - **DELETE**: Tier permanently deleted
   - **ACTIVATE**: Tier activated
   - **DEACTIVATE**: Tier deactivated (soft delete)

### Compliance Reporting

1. **Export Audit Data**
   - Download audit logs as CSV/JSON
   - Filter by date range, user, or action type
   - Use for compliance reporting

2. **Change Documentation**
   - All changes require reason documentation
   - User attribution for accountability
   - Immutable audit trail

## Best Practices

### Pricing Tier Naming

1. **Consistent Naming Convention**
   - Format: `{PLAN_SIZE}|{MODEL_CLASS}`
   - Examples: `XS|Large`, `M|Codestral/Llama`
   - Avoid special characters or spaces

2. **Descriptive Names**
   - Use clear, descriptive tier names
   - Include model information
   - Keep names under 100 characters

### Change Management

1. **Impact Analysis**
   - Review model associations before changes
   - Consider rate limit implications
   - Plan for tier upgrades/downgrades

2. **Communication**
   - Notify users of pricing changes
   - Provide advance notice for significant changes
   - Document change rationale

3. **Testing**
   - Test new tiers with sample workloads
   - Verify rate limits work correctly
   - Monitor utilization after changes

### Monitoring and Alerts

1. **Regular Monitoring**
   - Check rate limit utilization daily
   - Review tier status weekly
   - Monitor for unusual usage patterns

2. **Alert Thresholds**
   - Set up alerts for > 80% utilization
   - Monitor for tier upgrade recommendations
   - Track model availability issues

3. **Performance Optimization**
   - Identify underutilized tiers
   - Optimize tier assignments
   - Balance cost vs. performance

## Troubleshooting

### Common Issues

1. **Tier Key Conflicts**
   - Error: "Pricing tier XS|Large already exists"
   - Solution: Use different plan size or model class

2. **Model Association Errors**
   - Error: "Specified pricing tier does not exist"
   - Solution: Create tier first, then associate model

3. **Rate Limit Issues**
   - High utilization warnings
   - Solution: Upgrade tier or optimize usage

### Support Procedures

1. **Log Collection**
   - Gather audit trail data
   - Collect utilization metrics
   - Document error messages

2. **Escalation**
   - Contact system administrator
   - Provide detailed error information
   - Include relevant audit entries

## API Reference

### Admin Pricing Endpoints

```
GET    /api/v1/admin/pricing/tiers
POST   /api/v1/admin/pricing/tiers
PUT    /api/v1/admin/pricing/tiers/{tier_id}
DELETE /api/v1/admin/pricing/tiers/{tier_id}
GET    /api/v1/admin/pricing/tiers/{tier_id}/audit

GET    /api/v1/admin/pricing/models
POST   /api/v1/admin/pricing/models
PUT    /api/v1/admin/pricing/models/{model_id}
DELETE /api/v1/admin/pricing/models/{model_id}
```

### Analytics Endpoints

```
GET    /api/v1/analytics/tokens/rate-limits/current
GET    /api/v1/analytics/tokens/usage/summary
GET    /api/v1/analytics/tokens/tiers/status
```

## References

- [ADR-019: Offline Tokenizer Strategy](../development/adrs/ADR-019-Offline-Tokenizer-Strategy.md)
- [Air-Gapped Deployment Guide](../operations/AIR_GAPPED_DEPLOYMENT.md)
- [Deployment Constraints](../architecture/DEPLOYMENT_CONSTRAINTS.md)
- [UI Development Plan](../development/plans/UI_DEVELOPMENT_PLAN.md)
