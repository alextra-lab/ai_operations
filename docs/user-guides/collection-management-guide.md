# Collection Management User Guide

**Version:** 1.0
**Audience:** Corpus Administrators, Administrators
**Date:** October 27, 2025
**Status:** Implemented

---

## Overview

Collections are isolated namespaces for documents that share the same embedding model. This guide explains how to create, manage, and use collections effectively in AI Operations Platform.

**What You'll Learn:**
- How to create collections with the right embedding model
- Understanding embedding model choices (built-in vs. remote)
- Multi-collection search constraints
- Best practices for collection organization

---

## Quick Start

### 1. Create Your First Collection

1. Navigate to **Collections** from the main menu
2. Click **"Create Collection"** button (top-right)
3. Fill in the form:
   - **Name:** `threat_intelligence` (lowercase, alphanumeric, hyphens, underscores)
   - **Description:** "Threat intelligence reports and IOC data"
   - **Embedding Model:** Select from dropdown (e.g., `all-MiniLM-L6-v2`)
4. Review the selected model details card
5. Click **"Create Collection"**

**Result:** Collection created and ready for document upload

---

## Embedding Models

### Understanding Embedding Models

Embedding models convert text into numerical vectors for semantic search. Each collection is permanently bound to one embedding model.

**Why This Matters:**
- Different models produce different vector dimensions
- Vector spaces from different models are incompatible
- **Once created, a collection's embedding model CANNOT be changed**

### Built-in Model: all-MiniLM-L6-v2

**Always available** - No API keys required

**Specifications:**
- **Provider:** Local (sentence-transformers)
- **Dimensions:** 384D
- **Context:** 256 tokens
- **Cost:** $0 (runs locally)
- **Performance:** Fast, suitable for most use cases
- **Availability:** 100% (always available, even air-gapped)

**When to Use:**
- ✅ Air-gapped deployments
- ✅ Cost-sensitive projects (no API fees)
- ✅ Fast local processing
- ✅ General cybersecurity content
- ✅ When you need guaranteed availability

**Badge:** Shows **"BUILT-IN"** in green in the dropdown

### Remote Models (OpenAI, etc.)

**Requires API keys and internet connectivity**

**Example Models:**
- `text-embedding-3-small` (OpenAI, 1536D)
- `text-embedding-3-large` (OpenAI, 3072D)
- Provider-specific models as configured

**When to Use:**
- ✅ Higher quality embeddings needed
- ✅ Larger embedding dimensions for complex queries
- ✅ Internet connectivity available
- ✅ API costs acceptable

**When NOT to Use:**
- ❌ Air-gapped environments
- ❌ Cost constraints
- ❌ API quota limits
- ❌ Model availability uncertain

**Note:** If a remote model becomes unavailable (API key expired, service down), the collection becomes unusable until the model is restored. Built-in models avoid this risk.

---

## Creating Collections

### Step-by-Step: Create Collection Dialog

**1. Open Dialog**
- Click **"Create Collection"** button on Collections page
- Dialog opens with three sections: Basic Info, Embedding Model, Information

**2. Enter Basic Information**
- **Collection Name:**
  - Minimum 3 characters, maximum 255
  - Lowercase only
  - Alphanumeric with underscores and hyphens
  - Must be unique
  - Example: `threat_intelligence`, `malware_analysis`, `phishing_reports`
  - Reserved names: `system`, `default`, `test`, `admin`, `public`, `private`
- **Description (Optional):**
  - Clear explanation of collection purpose
  - Example: "Threat intelligence reports from external feeds"

**3. Select Embedding Model**
- Dropdown shows all available models
- Built-in models show **"BUILT-IN"** badge in green
- Each option shows:
  - Model name
  - Provider badge (local/openai/other)
  - Dimensions badge (384D, 1536D, etc.)
  - Warning icon if unavailable (disabled)
- Default selection: System Configuration default (usually `all-MiniLM-L6-v2`)
- **Selected Model Card** displays full details below dropdown

**4. Review Information**
- Yellow information banner explains:
  - ⚠️ Embedding model is **immutable** after creation
  - ⚠️ Use Cases can search multiple collections only if they share the same model
- **Think carefully** before creating - you cannot change the model later

**5. Create**
- Click **"Create"**
- Success: Redirects to Collections list
- Error: Shows error message (e.g., "Model not available")

---

## Multi-Collection Search Constraint

### The Same-Model Rule

**Rule:** Use Cases can search multiple collections ONLY if they share the same embedding model.

**Why?**
- Similarity scores differ between embedding models
- Merging results from different models produces inconsistent rankings
- No reliable way to normalize scores across models (deferred to future)

**Examples:**

✅ **Valid Multi-Collection Search:**
```
Collection A: all-MiniLM-L6-v2 (384D)
Collection B: all-MiniLM-L6-v2 (384D)
Collection C: all-MiniLM-L6-v2 (384D)
→ Use Case can search A + B + C together
```

❌ **Invalid Multi-Collection Search:**
```
Collection A: all-MiniLM-L6-v2 (384D)
Collection B: text-embedding-3-small (1536D)
→ Use Case CANNOT search A + B together
→ Error: "Collections use different embedding models"
```

### Use Case Wizard Behavior

When configuring RAG settings in the Use Case Wizard:

**Before First Selection:**
- All collections shown in dropdown

**After First Selection:**
- Dropdown filters to show ONLY collections with the same model
- Other collections disabled/hidden
- If you accidentally selected wrong model, clear all selections to reset

**Validation:**
- Inline error if mixed models detected
- Save blocked until same-model constraint satisfied
- Backend enforces constraint with 400 error if frontend bypassed

---

## Managing Collections

### Update Collection

**What You Can Change:**
- ✅ Description
- ✅ Active status (`is_active`)

**What You CANNOT Change:**
- ❌ Name
- ❌ Embedding model
- ❌ Embedding provider
- ❌ Embedding dimensions
- ❌ Qdrant collection name

**How to Update:**
1. Navigate to Collections page
2. Click on collection card or use Actions menu
3. Edit description or toggle active status
4. Click **"Save"**

### Delete Collection

**Requirements:**
- Collection must have **zero documents**
- Collection must NOT be system-managed
- Confirmation required

**How to Delete:**
1. Ensure all documents are deleted or moved to another collection
2. Click **"Delete"** in Actions menu
3. Confirm deletion
4. Collection and Qdrant vectors are removed

**Protection:**
- System-managed collections (e.g., default) cannot be deleted
- Collections with documents cannot be deleted (delete/move documents first)
- Permanent action - cannot be undone

### View Statistics

**Available Metrics:**
- Total document count
- Total chunk count
- Storage size (bytes)
- Last updated timestamp
- Embedding model details

**How to View:**
1. Click on collection name in list
2. View details panel
3. Statistics auto-refresh

---

## System Configuration Integration

### Default Embedding Model

**Location:** Admin → System Configuration → Corpus Settings → Default Embedding Model

**Purpose:**
- Pre-selects model in Collection Create Dialog
- Convenience feature for consistent collection creation
- **NOT a global enforcement** - each collection chooses independently

**Health Indicator:**
- Red banner shown if default model becomes unavailable
- Message: "Default embedding model 'X' is not available. New collections cannot be created."
- **Action:** Update to an available model (e.g., `all-MiniLM-L6-v2`)

**How to Update:**
1. Navigate to Admin → System Configuration
2. Scroll to "Corpus Settings"
3. Find "Default Embedding Model" dropdown
4. Select an available model (green check icon)
5. Click **"Save All"**
6. Health banner disappears if successful

---

## Best Practices

### 1. Choose the Right Model

**For Most Use Cases → Use `all-MiniLM-L6-v2`:**
- ✅ Always available
- ✅ No API costs
- ✅ Fast local processing
- ✅ 384D suitable for semantic search
- ✅ Air-gapped friendly

**For Advanced Use Cases → Use Remote Models:**
- Larger knowledge bases (10,000+ documents)
- Complex multi-lingual content
- Higher precision requirements
- When API costs are acceptable

### 2. Plan Collection Organization

**Group by Embedding Model:**
- Decide your primary model (built-in vs. remote)
- Create all related collections with the same model
- Enables multi-collection searches across all collections

**Example Organization:**

**Strategy A - All Built-in (Recommended):**
```
all-MiniLM-L6-v2:
  ├── threat_intelligence
  ├── malware_reports
  ├── incident_postmortems
  └── security_advisories
```

**Strategy B - Hybrid (Advanced):**
```
all-MiniLM-L6-v2:
  ├── general_security_docs
  └── daily_alerts

text-embedding-3-small:
  ├── strategic_analysis
  └── executive_briefings
```

**Note:** With Strategy B, Use Cases cannot search across both groups.

### 3. Name Collections Descriptively

**Good Names:**
- `threat_intelligence`
- `malware_analysis`
- `phishing_reports`
- `incident_postmortems`

**Bad Names:**
- `collection1`
- `test`
- `docs`
- `misc`

### 4. Document Collection Purposes

Always add clear descriptions:
- What types of documents are stored
- Intended use cases
- Update frequency
- Data sources

Example: "Threat intelligence reports from OSINT feeds, updated daily, used for IOC extraction and threat correlation"

---

## Troubleshooting

### "Model not available" Error

**Symptom:** Cannot create collection, error message says model unavailable

**Causes:**
1. Remote model API key not configured
2. Remote model service down
3. Model removed from registry
4. Model marked as unavailable

**Solution:**
1. Check Model Registry: Admin → Models
2. Verify model `is_available=true`
3. For remote models: Check API key configuration
4. Alternative: Use built-in `all-MiniLM-L6-v2`

### "Cannot search multiple collections" Error

**Symptom:** Use Case execution fails with mixed embedding models error

**Cause:** Selected collections use different embedding models

**Solution:**
1. Check each collection's embedding model
2. Edit Use Case configuration
3. Select only collections with the same embedding model
4. Or create separate Use Cases for each model group

### Health Banner Won't Disappear

**Symptom:** Red health banner persists after selecting available model

**Causes:**
1. Save failed (check console for errors)
2. Model still unavailable in registry
3. Browser cache outdated

**Solution:**
1. Hard refresh page (Cmd+Shift+R / Ctrl+Shift+F5)
2. Verify model in Model Registry
3. Check backend logs for save errors
4. Verify container is running: `docker ps | grep orchestrator`

### Collection Creation Slow

**Symptom:** Loading spinner for >5 seconds

**Causes:**
1. Loading models from external API
2. Model Registry endpoint slow
3. Database query performance

**Solution:**
- Normal for remote models (API latency)
- Built-in models load instantly
- Check network connectivity for remote models

---

## Advanced Topics

### Changing Embedding Models

**Current Collection - No Migration:**
- Embedding model is immutable after creation
- To change model: Create new collection, re-upload documents
- Future (Phase 5): Admin migration tool with automatic re-embedding

**System Default - Easy Update:**
- Admin → System Configuration → Corpus Settings
- Change `default_embedding_model` dropdown
- Click "Save All"
- Only affects NEW collections (existing collections unchanged)

### Model Availability Monitoring

**Check Model Health:**
1. Navigate to Admin → Models (future feature)
2. Or query API: GET `/api/v1/models?model_type=embedding`
3. Verify `is_available=true` for your models

**Setup Alerts:**
- Monitor Model Registry health endpoint
- Alert if primary model becomes unavailable
- Fallback to built-in model in emergencies

### Air-Gapped Deployments

**Built-in Models Only:**
- Use `all-MiniLM-L6-v2` for all collections
- No external dependencies
- Guaranteed 100% availability
- Zero API costs

**Model Loading:**
- Built-in models download automatically on first use
- Cached locally in `data/models/`
- No internet required after initial download

---

## Related Guides

- **Document Upload:** How to add documents to collections
- **Use Case Configuration:** How to configure RAG with collections
- **System Configuration:** Admin settings for default models
- **Model Registry:** Managing available embedding models (Phase 5)

---

## FAQ

**Q: Can I change a collection's embedding model after creation?**
A: No. The embedding model is immutable. Create a new collection and re-upload documents, or wait for the Phase 5 migration tool.

**Q: What happens if my remote model API key expires?**
A: Collections using that model become unusable until the key is restored. This is why built-in models are recommended.

**Q: Can I search across collections with different embedding models?**
A: No. Use Cases enforce same-model constraint. Similarity scores differ between models and cannot be reliably merged.

**Q: How do I know which model to choose?**
A: Use `all-MiniLM-L6-v2` (built-in) for most cases. Only use remote models if you need higher quality embeddings and have API access/budget.

**Q: What if I select the wrong model during creation?**
A: You cannot change it. Delete the empty collection and create a new one with the correct model. This is why the UI shows a warning.

**Q: How many collections can I create?**
A: No hard limit. Organize by purpose, data source, or access control needs. Each collection is isolated.

**Q: Can I move documents between collections?**
A: Only between collections with the **same embedding model**. Different models require re-embedding (planned for Phase 5).

---

## Glossary

- **Collection:** Isolated namespace for documents sharing an embedding model
- **Embedding Model:** AI model that converts text to vectors for semantic search
- **Vector Dimensions:** Size of embedding vectors (384D, 1536D, etc.)
- **Built-in Model:** Locally-run model (all-MiniLM-L6-v2) with no API costs
- **Remote Model:** Cloud-based model (OpenAI, etc.) requiring API key
- **Immutable:** Cannot be changed after creation
- **Same-Model Constraint:** Requirement that multi-collection searches use one model

---

**Document Owner:** Alex
**Last Updated:** October 27, 2025
**Related:** [Collection Management API](../api/collection-management.md), [ADR-021 Addendum 3](../development/adrs/ADR-021-Collection-Based-Document-Management.md)
