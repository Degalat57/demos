CLASS ltcl_test DEFINITION FINAL FOR TESTING
  DURATION SHORT RISK LEVEL HARMLESS.
  PRIVATE SECTION.
    METHODS invalid_february FOR TESTING RAISING zcx_utilities_input.
    METHODS invalid_april FOR TESTING RAISING zcx_utilities_input.
    METHODS century_not_leap FOR TESTING RAISING zcx_utilities_input.
    METHODS invalid_month FOR TESTING RAISING zcx_utilities_input.

    METHODS mean_consumption FOR TESTING RAISING zcx_utilities_input.
    METHODS last_one_latest FOR TESTING RAISING zcx_utilities_input.
    METHODS sorts_input FOR TESTING RAISING zcx_utilities_input.
    METHODS daily_normalisation FOR TESTING RAISING zcx_utilities_input.
    METHODS seasonal_adjustment FOR TESTING RAISING zcx_utilities_input.
    METHODS short_estimate FOR TESTING RAISING zcx_utilities_input.
    METHODS more_n_than_history FOR TESTING RAISING zcx_utilities_input.
    METHODS zero_history_valid FOR TESTING RAISING zcx_utilities_input.
    METHODS empty_history FOR TESTING RAISING zcx_utilities_input.
    METHODS negative_history FOR TESTING RAISING zcx_utilities_input.
    METHODS zero_history_days FOR TESTING RAISING zcx_utilities_input.
    METHODS duplicate_periods FOR TESTING RAISING zcx_utilities_input.
    METHODS invalid_n FOR TESTING RAISING zcx_utilities_input.
    METHODS invalid_season FOR TESTING RAISING zcx_utilities_input.
    METHODS two_tier_invoice FOR TESTING RAISING zcx_utilities_input.
    METHODS zero_usage_base_only FOR TESTING RAISING zcx_utilities_input.
    METHODS exact_tier_boundary FOR TESTING RAISING zcx_utilities_input.
    METHODS partial_period FOR TESTING RAISING zcx_utilities_input.
    METHODS leap_year_full FOR TESTING RAISING zcx_utilities_input.
    METHODS leap_year_partial FOR TESTING RAISING zcx_utilities_input.
    METHODS non_leap_february FOR TESTING RAISING zcx_utilities_input.
    METHODS single_day_proration FOR TESTING RAISING zcx_utilities_input.
    METHODS money_rounding FOR TESTING RAISING zcx_utilities_input.
    METHODS estimate_reason FOR TESTING RAISING zcx_utilities_input.
    METHODS negative_consumption FOR TESTING RAISING zcx_utilities_input.
    METHODS negative_base FOR TESTING RAISING zcx_utilities_input.
    METHODS negative_tax FOR TESTING RAISING zcx_utilities_input.
    METHODS tax_over_one FOR TESTING RAISING zcx_utilities_input.
    METHODS reverse_dates FOR TESTING RAISING zcx_utilities_input.
    METHODS zero_full_days FOR TESTING RAISING zcx_utilities_input.
    METHODS period_exceeds_full FOR TESTING RAISING zcx_utilities_input.
    METHODS empty_tiers FOR TESTING RAISING zcx_utilities_input.
    METHODS negative_tier_price FOR TESTING RAISING zcx_utilities_input.
    METHODS negative_tier_limit FOR TESTING RAISING zcx_utilities_input.
    METHODS descending_tiers FOR TESTING RAISING zcx_utilities_input.
    METHODS no_unlimited_tier FOR TESTING RAISING zcx_utilities_input.
    METHODS unlimited_not_last FOR TESTING RAISING zcx_utilities_input.
    METHODS duplicate_tier_limits FOR TESTING RAISING zcx_utilities_input.

ENDCLASS.

CLASS ltcl_test IMPLEMENTATION.
  METHOD mean_consumption.
    DATA(actual) = NEW zcl_billing_estimator( )->estimate(
      history = VALUE #( ( end_date = '20260131' consumption = 60 days = 30 ) ( end_date = '20260228' consumption = 120 days = 30 ) ) last_n = 3 days = 30 seasonal_factor = '1' ).
    cl_abap_unit_assert=>assert_equals( act = actual exp = CONV decfloat34( '90' ) ).
  ENDMETHOD.

  METHOD last_one_latest.
    DATA(actual) = NEW zcl_billing_estimator( )->estimate(
      history = VALUE #( ( end_date = '20260131' consumption = 60 days = 30 ) ( end_date = '20260228' consumption = 120 days = 30 ) ) last_n = 1 days = 30 seasonal_factor = '1' ).
    cl_abap_unit_assert=>assert_equals( act = actual exp = CONV decfloat34( '120' ) ).
  ENDMETHOD.

  METHOD sorts_input.
    DATA(actual) = NEW zcl_billing_estimator( )->estimate(
      history = VALUE #( ( end_date = '20260228' consumption = 120 days = 30 ) ( end_date = '20260131' consumption = 60 days = 30 ) ) last_n = 1 days = 30 seasonal_factor = '1' ).
    cl_abap_unit_assert=>assert_equals( act = actual exp = CONV decfloat34( '120' ) ).
  ENDMETHOD.

  METHOD daily_normalisation.
    DATA(actual) = NEW zcl_billing_estimator( )->estimate(
      history = VALUE #( ( end_date = '20260131' consumption = 62 days = 31 ) ( end_date = '20260228' consumption = 56 days = 28 ) ) last_n = 3 days = 30 seasonal_factor = '1' ).
    cl_abap_unit_assert=>assert_equals( act = actual exp = CONV decfloat34( '60' ) ).
  ENDMETHOD.

  METHOD seasonal_adjustment.
    DATA(actual) = NEW zcl_billing_estimator( )->estimate(
      history = VALUE #( ( end_date = '20260131' consumption = 60 days = 30 ) ( end_date = '20260228' consumption = 120 days = 30 ) ) last_n = 3 days = 30 seasonal_factor = '1.5' ).
    cl_abap_unit_assert=>assert_equals( act = actual exp = CONV decfloat34( '135' ) ).
  ENDMETHOD.

  METHOD short_estimate.
    DATA(actual) = NEW zcl_billing_estimator( )->estimate(
      history = VALUE #( ( end_date = '20260131' consumption = 60 days = 30 ) ( end_date = '20260228' consumption = 120 days = 30 ) ) last_n = 3 days = 15 seasonal_factor = '1' ).
    cl_abap_unit_assert=>assert_equals( act = actual exp = CONV decfloat34( '45' ) ).
  ENDMETHOD.

  METHOD more_n_than_history.
    DATA(actual) = NEW zcl_billing_estimator( )->estimate(
      history = VALUE #( ( end_date = '20260131' consumption = 60 days = 30 ) ( end_date = '20260228' consumption = 120 days = 30 ) ) last_n = 20 days = 30 seasonal_factor = '1' ).
    cl_abap_unit_assert=>assert_equals( act = actual exp = CONV decfloat34( '90' ) ).
  ENDMETHOD.

  METHOD zero_history_valid.
    DATA(actual) = NEW zcl_billing_estimator( )->estimate(
      history = VALUE #( ( end_date = '20260131' consumption = 0 days = 31 ) ) last_n = 3 days = 30 seasonal_factor = '1' ).
    cl_abap_unit_assert=>assert_equals( act = actual exp = CONV decfloat34( '0' ) ).
  ENDMETHOD.

  METHOD empty_history.
    TRY.
        NEW zcl_billing_estimator( )->estimate(
          history = VALUE #( ) last_n = 3 days = 30 seasonal_factor = '1' ).
        cl_abap_unit_assert=>fail( msg = 'Invalid history accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD negative_history.
    TRY.
        NEW zcl_billing_estimator( )->estimate(
          history = VALUE #( ( end_date = '20260131' consumption = -1 days = 30 ) ) last_n = 3 days = 30 seasonal_factor = '1' ).
        cl_abap_unit_assert=>fail( msg = 'Invalid history accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD zero_history_days.
    TRY.
        NEW zcl_billing_estimator( )->estimate(
          history = VALUE #( ( end_date = '20260131' consumption = 1 days = 0 ) ) last_n = 3 days = 30 seasonal_factor = '1' ).
        cl_abap_unit_assert=>fail( msg = 'Invalid history accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD duplicate_periods.
    TRY.
        NEW zcl_billing_estimator( )->estimate(
          history = VALUE #( ( end_date = '20260131' consumption = 1 days = 30 ) ( end_date = '20260131' consumption = 2 days = 30 ) ) last_n = 3 days = 30 seasonal_factor = '1' ).
        cl_abap_unit_assert=>fail( msg = 'Invalid history accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD invalid_n.
    TRY.
        NEW zcl_billing_estimator( )->estimate(
          history = VALUE #( ( end_date = '20260131' consumption = 60 days = 30 ) ( end_date = '20260228' consumption = 120 days = 30 ) ) last_n = 0 days = 30 seasonal_factor = '1' ).
        cl_abap_unit_assert=>fail( msg = 'Invalid history accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD invalid_season.
    TRY.
        NEW zcl_billing_estimator( )->estimate(
          history = VALUE #( ( end_date = '20260131' consumption = 60 days = 30 ) ( end_date = '20260228' consumption = 120 days = 30 ) ) last_n = 3 days = 30 seasonal_factor = '0' ).
        cl_abap_unit_assert=>fail( msg = 'Invalid history accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD two_tier_invoice.
    DATA(actual) = NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = actual-net exp = CONV zcl_billing_estimator=>ty_money( '45' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-tax exp = CONV zcl_billing_estimator=>ty_money( '8.55' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-gross exp = CONV zcl_billing_estimator=>ty_money( '53.55' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-reason exp = 'ACTUAL' ).
  ENDMETHOD.

  METHOD zero_usage_base_only.
    DATA(actual) = NEW zcl_billing_estimator( )->bill(
          consumption = '0' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = actual-net exp = CONV zcl_billing_estimator=>ty_money( '10' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-tax exp = CONV zcl_billing_estimator=>ty_money( '1.90' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-gross exp = CONV zcl_billing_estimator=>ty_money( '11.90' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-reason exp = 'ACTUAL' ).
  ENDMETHOD.

  METHOD exact_tier_boundary.
    DATA(actual) = NEW zcl_billing_estimator( )->bill(
          consumption = '100' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = actual-net exp = CONV zcl_billing_estimator=>ty_money( '30' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-tax exp = CONV zcl_billing_estimator=>ty_money( '5.70' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-gross exp = CONV zcl_billing_estimator=>ty_money( '35.70' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-reason exp = 'ACTUAL' ).
  ENDMETHOD.

  METHOD partial_period.
    DATA(actual) = NEW zcl_billing_estimator( )->bill(
          consumption = '75' date_from = '20260401' date_to = '20260415' full_days = 30
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = actual-net exp = CONV zcl_billing_estimator=>ty_money( '22.50' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-tax exp = CONV zcl_billing_estimator=>ty_money( '4.28' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-gross exp = CONV zcl_billing_estimator=>ty_money( '26.78' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-reason exp = 'ACTUAL' ).
  ENDMETHOD.

  METHOD leap_year_full.
    DATA(actual) = NEW zcl_billing_estimator( )->bill(
          consumption = '100' date_from = '20240201' date_to = '20240229' full_days = 29
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = actual-net exp = CONV zcl_billing_estimator=>ty_money( '30' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-tax exp = CONV zcl_billing_estimator=>ty_money( '5.70' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-gross exp = CONV zcl_billing_estimator=>ty_money( '35.70' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-reason exp = 'ACTUAL' ).
  ENDMETHOD.

  METHOD leap_year_partial.
    DATA(actual) = NEW zcl_billing_estimator( )->bill(
          consumption = '100' date_from = '20240215' date_to = '20240229' full_days = 29
          tiers = VALUE #( ( upper_limit = 0 price = '0.20' ) ) base_fee = '29' tax_rate = '0' estimated = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = actual-net exp = CONV zcl_billing_estimator=>ty_money( '35' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-tax exp = CONV zcl_billing_estimator=>ty_money( '0' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-gross exp = CONV zcl_billing_estimator=>ty_money( '35' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-reason exp = 'ACTUAL' ).
  ENDMETHOD.

  METHOD non_leap_february.
    DATA(actual) = NEW zcl_billing_estimator( )->bill(
          consumption = '100' date_from = '20230201' date_to = '20230228' full_days = 28
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = actual-net exp = CONV zcl_billing_estimator=>ty_money( '30' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-tax exp = CONV zcl_billing_estimator=>ty_money( '5.70' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-gross exp = CONV zcl_billing_estimator=>ty_money( '35.70' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-reason exp = 'ACTUAL' ).
  ENDMETHOD.

  METHOD single_day_proration.
    DATA(actual) = NEW zcl_billing_estimator( )->bill(
          consumption = '1' date_from = '20260430' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 0 price = '0.20' ) ) base_fee = '30' tax_rate = '0' estimated = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = actual-net exp = CONV zcl_billing_estimator=>ty_money( '1.20' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-tax exp = CONV zcl_billing_estimator=>ty_money( '0' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-gross exp = CONV zcl_billing_estimator=>ty_money( '1.20' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-reason exp = 'ACTUAL' ).
  ENDMETHOD.

  METHOD money_rounding.
    DATA(actual) = NEW zcl_billing_estimator( )->bill(
          consumption = '3' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 0 price = '0.335' ) ) base_fee = '0' tax_rate = '0.19' estimated = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = actual-net exp = CONV zcl_billing_estimator=>ty_money( '1.01' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-tax exp = CONV zcl_billing_estimator=>ty_money( '0.19' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-gross exp = CONV zcl_billing_estimator=>ty_money( '1.20' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-reason exp = 'ACTUAL' ).
  ENDMETHOD.

  METHOD estimate_reason.
    DATA(actual) = NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_true ).
    cl_abap_unit_assert=>assert_equals( act = actual-net exp = CONV zcl_billing_estimator=>ty_money( '45' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-tax exp = CONV zcl_billing_estimator=>ty_money( '8.55' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-gross exp = CONV zcl_billing_estimator=>ty_money( '53.55' ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-reason exp = 'ESTIMATED' ).
  ENDMETHOD.

  METHOD negative_consumption.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '-1' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD negative_base.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '-1' tax_rate = '0.19' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD negative_tax.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '10' tax_rate = '-1' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD tax_over_one.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '10' tax_rate = '2' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD reverse_dates.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260501' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD zero_full_days.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 0
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD period_exceeds_full.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 29
          tiers = VALUE #( ( upper_limit = 100 price = '0.20' ) ( upper_limit = 0 price = '0.30' ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD empty_tiers.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD negative_tier_price.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 0 price = '-0.1' ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD negative_tier_limit.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = -1 price = '0.1' ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD descending_tiers.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 100 price = 1 ) ( upper_limit = 50 price = 1 ) ( upper_limit = 0 price = 1 ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD no_unlimited_tier.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 100 price = 1 ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD unlimited_not_last.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 0 price = 1 ) ( upper_limit = 100 price = 1 ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD duplicate_tier_limits.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = '150' date_from = '20260401' date_to = '20260430' full_days = 30
          tiers = VALUE #( ( upper_limit = 100 price = 1 ) ( upper_limit = 100 price = 2 ) ( upper_limit = 0 price = 3 ) ) base_fee = '10' tax_rate = '0.19' estimated = abap_false ).
        cl_abap_unit_assert=>fail( msg = 'Invalid billing input accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD invalid_february.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = 1 date_from = '20230229' date_to = '20230229' full_days = 30
          tiers = VALUE #( ( upper_limit = 0 price = 1 ) ) base_fee = 0 tax_rate = 0 ).
        cl_abap_unit_assert=>fail( msg = 'Invalid calendar date accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD invalid_april.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = 1 date_from = '20260431' date_to = '20260431' full_days = 30
          tiers = VALUE #( ( upper_limit = 0 price = 1 ) ) base_fee = 0 tax_rate = 0 ).
        cl_abap_unit_assert=>fail( msg = 'Invalid calendar date accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD century_not_leap.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = 1 date_from = '19000229' date_to = '19000229' full_days = 30
          tiers = VALUE #( ( upper_limit = 0 price = 1 ) ) base_fee = 0 tax_rate = 0 ).
        cl_abap_unit_assert=>fail( msg = 'Invalid calendar date accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD invalid_month.
    TRY.
        NEW zcl_billing_estimator( )->bill(
          consumption = 1 date_from = '20261301' date_to = '20261301' full_days = 30
          tiers = VALUE #( ( upper_limit = 0 price = 1 ) ) base_fee = 0 tax_rate = 0 ).
        cl_abap_unit_assert=>fail( msg = 'Invalid calendar date accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

ENDCLASS.
