-- ============================================================================
-- Seed Data: Pricing Tiers
-- ============================================================================
-- Description: Populates LLMaaS pricing tier data
-- Prerequisites: 000_complete_init.sql, 001_seed_users.sql
--
-- Pricing Tiers:
--   - XS, S, M, L, XL plans
--   - Large, Small, Codestral/Llama model classes
--   - Rate limits and token pricing
--
-- Usage:
--   PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
--     -h $POSTGRES_HOST -p $POSTGRES_PORT \
--     -U $POSTGRES_USER -d $POSTGRES_DB \
--     -f scripts/database/seed/004_seed_pricing.sql
-- ============================================================================

BEGIN;

-- Insert pricing tiers from LLMaaS pricing table
INSERT INTO pricing_tiers (tier_key, tier_name, plan_size, model_class, input_rate_per_1m, output_rate_per_1m, rate_limit_tpm, is_active, description, created_by)
VALUES
    -- Extra Small (XS) Plans
    ('XS|Large', 'Extra Small - Mistral Large', 'XS', 'Large', 1.10, 0.30, 2000, TRUE, 'Extra Small plan with Mistral Large model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),
    ('XS|Small', 'Extra Small - Mistral Small', 'XS', 'Small', 1.60, 0.40, 3000, TRUE, 'Extra Small plan with Mistral Small model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),
    ('XS|Codestral/Llama', 'Extra Small - Codestral/Llama', 'XS', 'Codestral/Llama', 3.70, 0.90, 6900, TRUE, 'Extra Small plan with Codestral/Llama model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),

    -- Small (S) Plans
    ('S|Large', 'Small - Mistral Large', 'S', 'Large', 2.20, 0.60, 4000, TRUE, 'Small plan with Mistral Large model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),
    ('S|Small', 'Small - Mistral Small', 'S', 'Small', 3.20, 0.80, 6000, TRUE, 'Small plan with Mistral Small model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),
    ('S|Codestral/Llama', 'Small - Codestral/Llama', 'S', 'Codestral/Llama', 7.40, 1.80, 13800, TRUE, 'Small plan with Codestral/Llama model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),

    -- Medium (M) Plans
    ('M|Large', 'Medium - Mistral Large', 'M', 'Large', 8.90, 2.20, 16500, TRUE, 'Medium plan with Mistral Large model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),
    ('M|Small', 'Medium - Mistral Small', 'M', 'Small', 12.80, 3.20, 23600, TRUE, 'Medium plan with Mistral Small model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),
    ('M|Codestral/Llama', 'Medium - Codestral/Llama', 'M', 'Codestral/Llama', 29.80, 7.40, 55140, TRUE, 'Medium plan with Codestral/Llama model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),

    -- Large (L) Plans
    ('L|Large', 'Large - Mistral Large', 'L', 'Large', 17.90, 4.50, 33000, TRUE, 'Large plan with Mistral Large model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),
    ('L|Small', 'Large - Mistral Small', 'L', 'Small', 25.50, 6.40, 47200, TRUE, 'Large plan with Mistral Small model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),
    ('L|Codestral/Llama', 'Large - Codestral/Llama', 'L', 'Codestral/Llama', 59.60, 14.80, 110280, TRUE, 'Large plan with Codestral/Llama model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),

    -- Extra Large (XL) Plans
    ('XL|Large', 'Extra Large - Mistral Large', 'XL', 'Large', 44.70, 11.20, 83000, TRUE, 'Extra Large plan with Mistral Large model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),
    ('XL|Small', 'Extra Large - Mistral Small', 'XL', 'Small', 63.80, 16.00, 118000, TRUE, 'Extra Large plan with Mistral Small model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1)),
    ('XL|Codestral/Llama', 'Extra Large - Codestral/Llama', 'XL', 'Codestral/Llama', 148.90, 37.20, 275700, TRUE, 'Extra Large plan with Codestral/Llama model', (SELECT id FROM users WHERE username = 'admin' LIMIT 1))
ON CONFLICT (tier_key) DO NOTHING;

-- Set default pricing tier (M|Large)
UPDATE pricing_tiers
SET is_default = TRUE
WHERE tier_key = 'M|Large';

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    tier_count INTEGER;
    default_tier VARCHAR(50);
BEGIN
    SELECT COUNT(*) INTO tier_count FROM pricing_tiers;
    SELECT tier_key INTO default_tier FROM pricing_tiers WHERE is_default = TRUE;

    RAISE NOTICE '✅ Pricing tiers seeded successfully!';
    RAISE NOTICE '   - Total tiers: %', tier_count;
    RAISE NOTICE '   - Default tier: %', default_tier;
    RAISE NOTICE '';
    RAISE NOTICE '💰 Pricing Tiers (per 1M tokens):';
    RAISE NOTICE '   - XS Plans: 1.10-3.70 KEUR input, 0.30-0.90 KEUR output';
    RAISE NOTICE '   - S Plans: 2.20-7.40 KEUR input, 0.60-1.80 KEUR output';
    RAISE NOTICE '   - M Plans: 8.90-29.80 KEUR input, 2.20-7.40 KEUR output';
    RAISE NOTICE '   - L Plans: 17.90-59.60 KEUR input, 4.50-14.80 KEUR output';
    RAISE NOTICE '   - XL Plans: 44.70-148.90 KEUR input, 11.20-37.20 KEUR output';
    RAISE NOTICE '';
    RAISE NOTICE '🚀 Rate Limits:';
    RAISE NOTICE '   - XS: 2,000-6,900 TPM';
    RAISE NOTICE '   - S: 4,000-13,800 TPM';
    RAISE NOTICE '   - M: 16,500-55,140 TPM';
    RAISE NOTICE '   - L: 33,000-110,280 TPM';
    RAISE NOTICE '   - XL: 83,000-275,700 TPM';
END $$;

-- Display pricing tiers by plan size
SELECT
    plan_size,
    model_class,
    input_rate_per_1m || ' KEUR' as input_rate,
    output_rate_per_1m || ' KEUR' as output_rate,
    rate_limit_tpm || ' TPM' as rate_limit,
    is_default
FROM pricing_tiers
ORDER BY
    CASE plan_size
        WHEN 'XS' THEN 1
        WHEN 'S' THEN 2
        WHEN 'M' THEN 3
        WHEN 'L' THEN 4
        WHEN 'XL' THEN 5
    END,
    model_class;
