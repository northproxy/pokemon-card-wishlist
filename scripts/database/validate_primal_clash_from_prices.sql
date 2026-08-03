-- Script: validate_primal_clash_from_prices.sql
--
-- Purpose:
--     Validate the production Cardmarket price snapshot state for the controlled
--     Primal Clash vertical slice and prove the runtime canonical-card "From"
--     price rule defined by ADR-011 and FR-12.
--
-- Lifecycle:
--     Permanent project validation utility.
--
-- Removal:
--     Keep this script while Primal Clash remains the validated vertical slice.
--     It may be replaced only by automated integration tests or a generalized
--     runtime pricing validator that preserves equivalent scope, eligibility,
--     snapshot-selection, aggregation, and audit guarantees.

BEGIN;

DO $validation$
DECLARE
    v_snapshot_count integer;
    v_duplicate_snapshot_identities integer;
    v_unsuccessful_run_snapshots integer;
    v_inactive_product_snapshots integer;
    v_invalid_currency_snapshots integer;
    v_negative_price_snapshots integer;
    v_null_price_snapshots integer;
    v_active_mapping_count integer;
    v_active_mapping_without_snapshot integer;
    v_priced_canonical_cards integer;
    v_duplicate_runtime_rows integer;
BEGIN
    SELECT COUNT(*)
    INTO v_snapshot_count
    FROM market_price_snapshots AS snapshots
    JOIN market_products AS products
      ON products.market_product_id = snapshots.market_product_id
    WHERE products.source_system = 'cardmarket'
      AND products.source_expansion_id = '1585';

    IF v_snapshot_count <> 173 THEN
        RAISE EXCEPTION
            'Expected 173 Primal Clash Cardmarket price snapshots, found %.',
            v_snapshot_count;
    END IF;

    SELECT COUNT(*)
    INTO v_duplicate_snapshot_identities
    FROM (
        SELECT
            market_product_id,
            source_snapshot_at
        FROM market_price_snapshots
        GROUP BY
            market_product_id,
            source_snapshot_at
        HAVING COUNT(*) > 1
    ) AS duplicates;

    IF v_duplicate_snapshot_identities <> 0 THEN
        RAISE EXCEPTION
            'Found % duplicate market price snapshot identities.',
            v_duplicate_snapshot_identities;
    END IF;

    SELECT COUNT(*)
    INTO v_unsuccessful_run_snapshots
    FROM market_price_snapshots AS snapshots
    JOIN import_runs AS runs
      ON runs.import_run_id = snapshots.import_run_id
    WHERE runs.status <> 'succeeded';

    IF v_unsuccessful_run_snapshots <> 0 THEN
        RAISE EXCEPTION
            'Found % price snapshots linked to non-succeeded import runs.',
            v_unsuccessful_run_snapshots;
    END IF;

    SELECT COUNT(*)
    INTO v_inactive_product_snapshots
    FROM market_price_snapshots AS snapshots
    JOIN market_products AS products
      ON products.market_product_id = snapshots.market_product_id
    WHERE products.is_active IS NOT TRUE;

    IF v_inactive_product_snapshots <> 0 THEN
        RAISE EXCEPTION
            'Found % price snapshots linked to inactive market products.',
            v_inactive_product_snapshots;
    END IF;

    SELECT COUNT(*)
    INTO v_invalid_currency_snapshots
    FROM market_price_snapshots
    WHERE currency_code <> 'EUR';

    IF v_invalid_currency_snapshots <> 0 THEN
        RAISE EXCEPTION
            'Found % non-EUR market price snapshots.',
            v_invalid_currency_snapshots;
    END IF;

    SELECT COUNT(*)
    INTO v_negative_price_snapshots
    FROM market_price_snapshots
    WHERE avg30 < 0
       OR avg30_holo < 0;

    IF v_negative_price_snapshots <> 0 THEN
        RAISE EXCEPTION
            'Found % market price snapshots with negative values.',
            v_negative_price_snapshots;
    END IF;

    SELECT COUNT(*)
    INTO v_null_price_snapshots
    FROM market_price_snapshots
    WHERE avg30 IS NULL
      AND avg30_holo IS NULL;

    IF v_null_price_snapshots <> 0 THEN
        RAISE EXCEPTION
            'Found % market price snapshots without avg30 or avg30_holo.',
            v_null_price_snapshots;
    END IF;

    SELECT COUNT(*)
    INTO v_active_mapping_count
    FROM card_market_product_mappings AS mappings
    JOIN market_products AS products
      ON products.market_product_id = mappings.market_product_id
    WHERE mappings.is_active IS TRUE
      AND products.is_active IS TRUE
      AND products.source_system = 'cardmarket'
      AND products.source_expansion_id = '1585'
      AND mappings.card_id IS NOT NULL;

    IF v_active_mapping_count <> 165 THEN
        RAISE EXCEPTION
            'Expected 165 active canonical-card mappings, found %.',
            v_active_mapping_count;
    END IF;

    WITH latest_successful_snapshots AS (
        SELECT DISTINCT ON (snapshots.market_product_id)
            snapshots.market_product_id,
            snapshots.market_price_snapshot_id,
            snapshots.source_snapshot_at,
            snapshots.currency_code,
            snapshots.avg30,
            snapshots.avg30_holo
        FROM market_price_snapshots AS snapshots
        JOIN import_runs AS runs
          ON runs.import_run_id = snapshots.import_run_id
        WHERE runs.status = 'succeeded'
        ORDER BY
            snapshots.market_product_id,
            snapshots.source_snapshot_at DESC,
            snapshots.market_price_snapshot_id DESC
    )
    SELECT COUNT(*)
    INTO v_active_mapping_without_snapshot
    FROM card_market_product_mappings AS mappings
    JOIN market_products AS products
      ON products.market_product_id = mappings.market_product_id
    LEFT JOIN latest_successful_snapshots AS snapshots
      ON snapshots.market_product_id = mappings.market_product_id
    WHERE mappings.is_active IS TRUE
      AND products.is_active IS TRUE
      AND products.source_system = 'cardmarket'
      AND products.source_expansion_id = '1585'
      AND mappings.card_id IS NOT NULL
      AND snapshots.market_product_id IS NULL;

    IF v_active_mapping_without_snapshot <> 0 THEN
        RAISE EXCEPTION
            'Found % active mapped market products without a successful price snapshot.',
            v_active_mapping_without_snapshot;
    END IF;

    WITH latest_successful_snapshots AS (
        SELECT DISTINCT ON (snapshots.market_product_id)
            snapshots.market_product_id,
            snapshots.market_price_snapshot_id,
            snapshots.source_snapshot_at,
            snapshots.currency_code,
            snapshots.avg30
        FROM market_price_snapshots AS snapshots
        JOIN import_runs AS runs
          ON runs.import_run_id = snapshots.import_run_id
        WHERE runs.status = 'succeeded'
        ORDER BY
            snapshots.market_product_id,
            snapshots.source_snapshot_at DESC,
            snapshots.market_price_snapshot_id DESC
    ),
    runtime_prices AS (
        SELECT
            mappings.card_id,
            MIN(snapshots.avg30) AS from_avg30
        FROM card_market_product_mappings AS mappings
        JOIN market_products AS products
          ON products.market_product_id = mappings.market_product_id
        JOIN latest_successful_snapshots AS snapshots
          ON snapshots.market_product_id = products.market_product_id
        WHERE mappings.is_active IS TRUE
          AND products.is_active IS TRUE
          AND products.source_system = 'cardmarket'
          AND products.source_expansion_id = '1585'
          AND mappings.card_id IS NOT NULL
          AND snapshots.currency_code = 'EUR'
          AND snapshots.avg30 IS NOT NULL
        GROUP BY mappings.card_id
    )
    SELECT COUNT(*)
    INTO v_priced_canonical_cards
    FROM runtime_prices;

    IF v_priced_canonical_cards <> 164 THEN
        RAISE EXCEPTION
            'Expected 164 canonical cards with runtime From prices, found %.',
            v_priced_canonical_cards;
    END IF;

    WITH latest_successful_snapshots AS (
        SELECT DISTINCT ON (snapshots.market_product_id)
            snapshots.market_product_id,
            snapshots.market_price_snapshot_id,
            snapshots.source_snapshot_at,
            snapshots.currency_code,
            snapshots.avg30
        FROM market_price_snapshots AS snapshots
        JOIN import_runs AS runs
          ON runs.import_run_id = snapshots.import_run_id
        WHERE runs.status = 'succeeded'
        ORDER BY
            snapshots.market_product_id,
            snapshots.source_snapshot_at DESC,
            snapshots.market_price_snapshot_id DESC
    ),
    runtime_prices AS (
        SELECT
            mappings.card_id,
            MIN(snapshots.avg30) AS from_avg30
        FROM card_market_product_mappings AS mappings
        JOIN market_products AS products
          ON products.market_product_id = mappings.market_product_id
        JOIN latest_successful_snapshots AS snapshots
          ON snapshots.market_product_id = products.market_product_id
        WHERE mappings.is_active IS TRUE
          AND products.is_active IS TRUE
          AND products.source_system = 'cardmarket'
          AND products.source_expansion_id = '1585'
          AND mappings.card_id IS NOT NULL
          AND snapshots.currency_code = 'EUR'
          AND snapshots.avg30 IS NOT NULL
        GROUP BY mappings.card_id
    )
    SELECT COUNT(*)
    INTO v_duplicate_runtime_rows
    FROM (
        SELECT card_id
        FROM runtime_prices
        GROUP BY card_id
        HAVING COUNT(*) > 1
    ) AS duplicates;

    IF v_duplicate_runtime_rows <> 0 THEN
        RAISE EXCEPTION
            'Found % duplicate canonical-card runtime price rows.',
            v_duplicate_runtime_rows;
    END IF;

    RAISE NOTICE 'Primal Clash runtime From price validation passed';
    RAISE NOTICE 'Price snapshots: %', v_snapshot_count;
    RAISE NOTICE 'Active mapped market products: %', v_active_mapping_count;
    RAISE NOTICE 'Canonical cards with From prices: %', v_priced_canonical_cards;
END
$validation$;

WITH latest_successful_snapshots AS (
    SELECT DISTINCT ON (snapshots.market_product_id)
        snapshots.market_product_id,
        snapshots.market_price_snapshot_id,
        snapshots.import_run_id,
        snapshots.source_snapshot_at,
        snapshots.currency_code,
        snapshots.avg30,
        snapshots.avg30_holo
    FROM market_price_snapshots AS snapshots
    JOIN import_runs AS runs
      ON runs.import_run_id = snapshots.import_run_id
    WHERE runs.status = 'succeeded'
    ORDER BY
        snapshots.market_product_id,
        snapshots.source_snapshot_at DESC,
        snapshots.market_price_snapshot_id DESC
),
eligible_prices AS (
    SELECT
        mappings.card_id,
        cards.source_card_id,
        cards.collector_number,
        cards.name AS card_name,
        products.market_product_id,
        products.source_product_id,
        products.raw_name AS market_product_name,
        snapshots.source_snapshot_at,
        snapshots.currency_code,
        snapshots.avg30
    FROM card_market_product_mappings AS mappings
    JOIN cards
      ON cards.card_id = mappings.card_id
    JOIN market_products AS products
      ON products.market_product_id = mappings.market_product_id
    JOIN latest_successful_snapshots AS snapshots
      ON snapshots.market_product_id = products.market_product_id
    WHERE mappings.is_active IS TRUE
      AND cards.is_active IS TRUE
      AND products.is_active IS TRUE
      AND products.source_system = 'cardmarket'
      AND products.source_expansion_id = '1585'
      AND snapshots.currency_code = 'EUR'
      AND snapshots.avg30 IS NOT NULL
),
runtime_from_prices AS (
    SELECT
        card_id,
        source_card_id,
        collector_number,
        card_name,
        currency_code,
        MIN(avg30) AS from_avg30,
        COUNT(*) AS eligible_product_count,
        MAX(source_snapshot_at) AS latest_source_snapshot_at
    FROM eligible_prices
    GROUP BY
        card_id,
        source_card_id,
        collector_number,
        card_name,
        currency_code
)
SELECT
    source_card_id,
    collector_number,
    card_name,
    eligible_product_count,
    currency_code,
    from_avg30,
    latest_source_snapshot_at,
    'From' AS display_prefix,
    '30-day average' AS display_label
FROM runtime_from_prices
ORDER BY
    CASE
        WHEN collector_number ~ '^[0-9]+$'
            THEN collector_number::integer
        ELSE NULL
    END,
    collector_number,
    source_card_id;

ROLLBACK;
