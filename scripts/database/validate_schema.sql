\set ON_ERROR_STOP on

BEGIN;

DO $validation$
DECLARE
    actual_project_tables integer;
    actual_migrations integer;
    violation_count bigint;
BEGIN
    SELECT count(*)
    INTO actual_project_tables
    FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename <> 'schema_migrations';

    IF actual_project_tables <> 21 THEN
        RAISE EXCEPTION
            'Expected 21 project tables, found %',
            actual_project_tables;
    END IF;

    SELECT count(*)
    INTO actual_migrations
    FROM public.schema_migrations;

    IF actual_migrations <> 17 THEN
        RAISE EXCEPTION
            'Expected 17 applied migrations, found %',
            actual_migrations;
    END IF;

    SELECT count(*)
    INTO violation_count
    FROM (
        SELECT source_system, source_card_id
        FROM public.cards
        GROUP BY source_system, source_card_id
        HAVING count(*) > 1
    ) AS duplicate_cards;

    IF violation_count <> 0 THEN
        RAISE EXCEPTION
            'Duplicate source-scoped card identities: %',
            violation_count;
    END IF;

    SELECT count(*)
    INTO violation_count
    FROM (
        SELECT source_system, source_product_id
        FROM public.market_products
        GROUP BY source_system, source_product_id
        HAVING count(*) > 1
    ) AS duplicate_products;

    IF violation_count <> 0 THEN
        RAISE EXCEPTION
            'Duplicate source-scoped market-product identities: %',
            violation_count;
    END IF;

    SELECT count(*)
    INTO violation_count
    FROM (
        SELECT market_product_id
        FROM public.card_market_mapping_cases
        GROUP BY market_product_id
        HAVING count(*) > 1
    ) AS duplicate_cases;

    IF violation_count <> 0 THEN
        RAISE EXCEPTION
            'Market products with multiple mapping cases: %',
            violation_count;
    END IF;

    SELECT count(*)
    INTO violation_count
    FROM public.card_market_mapping_cases AS mapping_case
    LEFT JOIN public.card_market_product_mappings AS mapping
        ON mapping.mapping_case_id = mapping_case.mapping_case_id
       AND mapping.market_product_id = mapping_case.market_product_id
       AND mapping.is_active = true
    WHERE mapping_case.current_status = 'confirmed'
    GROUP BY mapping_case.mapping_case_id
    HAVING count(mapping.card_market_product_mapping_id) <> 1;

    IF violation_count <> 0 THEN
        RAISE EXCEPTION
            'Confirmed cases without exactly one active mapping: %',
            violation_count;
    END IF;

    SELECT count(*)
    INTO violation_count
    FROM public.card_market_mapping_cases AS mapping_case
    JOIN public.card_market_product_mappings AS mapping
        ON mapping.mapping_case_id = mapping_case.mapping_case_id
       AND mapping.is_active = true
    WHERE mapping_case.current_status <> 'confirmed';

    IF violation_count <> 0 THEN
        RAISE EXCEPTION
            'Non-confirmed cases with active mappings: %',
            violation_count;
    END IF;

    SELECT count(*)
    INTO violation_count
    FROM public.card_market_product_mappings AS mapping
    JOIN public.card_market_mapping_cases AS mapping_case
        ON mapping_case.mapping_case_id = mapping.mapping_case_id
    WHERE mapping.is_active = true
      AND (
          mapping.market_product_id
              IS DISTINCT FROM mapping_case.market_product_id
          OR mapping.confirmation_scope
              IS DISTINCT FROM mapping_case.current_confirmation_scope
          OR mapping.card_id
              IS DISTINCT FROM mapping_case.current_card_id
          OR mapping.card_edition_id
              IS DISTINCT FROM mapping_case.current_card_edition_id
          OR mapping.card_variant_id
              IS DISTINCT FROM mapping_case.current_card_variant_id
      );

    IF violation_count <> 0 THEN
        RAISE EXCEPTION
            'Active mapping and current case projection drift: %',
            violation_count;
    END IF;

    SELECT count(*)
    INTO violation_count
    FROM (
        SELECT market_product_id
        FROM public.card_market_product_mappings
        WHERE is_active = true
        GROUP BY market_product_id
        HAVING count(*) > 1
    ) AS duplicate_active_mappings;

    IF violation_count <> 0 THEN
        RAISE EXCEPTION
            'Products with multiple active mappings: %',
            violation_count;
    END IF;

    SELECT count(*)
    INTO violation_count
    FROM public.card_market_product_mappings AS mapping
    JOIN public.card_editions AS edition
        ON edition.card_edition_id = mapping.card_edition_id
    WHERE mapping.card_edition_id IS NOT NULL
      AND edition.card_id <> mapping.card_id;

    IF violation_count <> 0 THEN
        RAISE EXCEPTION
            'Mapping editions belonging to another card: %',
            violation_count;
    END IF;

    SELECT count(*)
    INTO violation_count
    FROM public.card_market_product_mappings AS mapping
    JOIN public.card_variants AS variant
        ON variant.card_variant_id = mapping.card_variant_id
    WHERE mapping.card_variant_id IS NOT NULL
      AND variant.card_edition_id <> mapping.card_edition_id;

    IF violation_count <> 0 THEN
        RAISE EXCEPTION
            'Mapping variants belonging to another edition: %',
            violation_count;
    END IF;

    SELECT count(*)
    INTO violation_count
    FROM (
        SELECT market_product_id, source_snapshot_at
        FROM public.market_price_snapshots
        GROUP BY market_product_id, source_snapshot_at
        HAVING count(*) > 1
    ) AS duplicate_snapshots;

    IF violation_count <> 0 THEN
        RAISE EXCEPTION
            'Duplicate product price snapshots: %',
            violation_count;
    END IF;

    SELECT count(*)
    INTO violation_count
    FROM public.market_price_snapshots AS snapshot
    JOIN public.import_runs AS import_run
        ON import_run.import_run_id = snapshot.import_run_id
    WHERE import_run.run_kind <> 'market_prices'
       OR import_run.source_system <> 'cardmarket'
       OR import_run.source_entity_type <> 'market_price'
       OR import_run.status <> 'succeeded';

    IF violation_count <> 0 THEN
        RAISE EXCEPTION
            'Price snapshots attached to incompatible runs: %',
            violation_count;
    END IF;

    SELECT count(*)
    INTO violation_count
    FROM public.market_price_snapshots
    WHERE currency_code <> 'EUR'
       OR avg30 < 0
       OR avg30_holo < 0
       OR (
           avg30 IS NULL
           AND avg30_holo IS NULL
       );

    IF violation_count <> 0 THEN
        RAISE EXCEPTION
            'Invalid production price snapshots: %',
            violation_count;
    END IF;

    SELECT count(*)
    INTO violation_count
    FROM public.wishlist_items AS wishlist
    LEFT JOIN public.cards AS card
        ON card.card_id = wishlist.card_id
    WHERE card.card_id IS NULL
       OR wishlist.quantity < 1;

    IF violation_count <> 0 THEN
        RAISE EXCEPTION
            'Invalid wishlist rows: %',
            violation_count;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'wishlist_items'
          AND column_name IN (
              'market_product_id',
              'card_edition_id',
              'card_variant_id',
              'language_code',
              'finish_code',
              'avg30',
              'avg30_holo'
          )
    ) THEN
        RAISE EXCEPTION
            'Wishlist contains forbidden catalogue or market columns';
    END IF;
END
$validation$;

ROLLBACK;

SELECT
    'schema validation passed' AS result;
