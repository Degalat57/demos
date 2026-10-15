CLASS zcl_billing_estimator DEFINITION PUBLIC FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    TYPES ty_money TYPE p LENGTH 16 DECIMALS 2.
    TYPES: BEGIN OF ty_tier,
             upper_limit TYPE decfloat34,
             price       TYPE decfloat34,
           END OF ty_tier,
           ty_tiers TYPE STANDARD TABLE OF ty_tier WITH EMPTY KEY.
    TYPES: BEGIN OF ty_bill,
             consumption TYPE decfloat34,
             period_days TYPE i,
             fraction    TYPE decfloat34,
             net         TYPE ty_money,
             tax         TYPE ty_money,
             gross       TYPE ty_money,
             currency    TYPE c LENGTH 3,
             reason      TYPE string,
           END OF ty_bill.
    METHODS estimate
      IMPORTING history TYPE zif_reading_check=>ty_history
                last_n TYPE i DEFAULT 3
                days TYPE i DEFAULT 30
                seasonal_factor TYPE decfloat34 DEFAULT 1
      RETURNING VALUE(consumption) TYPE decfloat34
      RAISING zcx_utilities_input.
    METHODS bill
      IMPORTING consumption TYPE decfloat34
                date_from TYPE d date_to TYPE d full_days TYPE i
                tiers TYPE ty_tiers base_fee TYPE decfloat34
                tax_rate TYPE decfloat34
                estimated TYPE abap_bool DEFAULT abap_false
      RETURNING VALUE(result) TYPE ty_bill
      RAISING zcx_utilities_input.
  PRIVATE SECTION.
    CLASS-METHODS valid_date IMPORTING date TYPE d
      RETURNING VALUE(valid) TYPE abap_bool.
ENDCLASS.

CLASS zcl_billing_estimator IMPLEMENTATION.
  METHOD valid_date.
    IF date CN '0123456789'.
      RETURN.
    ENDIF.
    DATA(year) = CONV i( date(4) ).
    DATA(month) = CONV i( date+4(2) ).
    DATA(day) = CONV i( date+6(2) ).
    IF year < 1 OR month < 1 OR month > 12 OR day < 1.
      RETURN.
    ENDIF.
    DATA(max_day) = COND i( WHEN month = 2 THEN 28
      WHEN month = 4 OR month = 6 OR month = 9 OR month = 11 THEN 30 ELSE 31 ).
    IF month = 2 AND ( year MOD 400 = 0 OR ( year MOD 4 = 0 AND year MOD 100 <> 0 ) ).
      max_day = 29.
    ENDIF.
    valid = xsdbool( day <= max_day ).
  ENDMETHOD.

  METHOD estimate.
    IF last_n <= 0 OR days <= 0 OR seasonal_factor <= 0 OR history IS INITIAL.
      RAISE EXCEPTION TYPE zcx_utilities_input EXPORTING code = 'INVALID_ESTIMATE_INPUT'.
    ENDIF.
    DATA(sorted) = history.
    SORT sorted BY end_date DESCENDING.
    DATA selected TYPE zif_reading_check=>ty_history.
    DATA(count) = 0.
    DATA(previous_date) = CONV d( '00000000' ).
    LOOP AT sorted INTO DATA(period).
      IF period-days <= 0 OR period-consumption < 0
          OR valid_date( period-end_date ) = abap_false
          OR period-end_date = previous_date.
        RAISE EXCEPTION TYPE zcx_utilities_input EXPORTING code = 'INVALID_HISTORY'.
      ENDIF.
      previous_date = period-end_date.
      IF count < last_n.
        APPEND period TO selected.
        count = count + 1.
      ENDIF.
    ENDLOOP.
    " Equal weight per period after daily normalisation; newest N only.
    DATA(total) = REDUCE decfloat34( INIT sum = CONV decfloat34( 0 )
      FOR sample IN selected NEXT sum = sum + sample-consumption / sample-days ).
    " decfloat34 division is inexact (100/30*30 = 99.999...): round the estimate to 3 decimals of the unit.
    consumption = round( val = total / count * days * seasonal_factor dec = 3 ).
  ENDMETHOD.

  METHOD bill.
    IF consumption < 0 OR base_fee < 0 OR tax_rate < 0 OR tax_rate > 1
        OR full_days <= 0 OR valid_date( date_from ) = abap_false
        OR valid_date( date_to ) = abap_false
        OR date_to < date_from OR tiers IS INITIAL.
      RAISE EXCEPTION TYPE zcx_utilities_input EXPORTING code = 'INVALID_BILLING_INPUT'.
    ENDIF.
    DATA(actual_days) = date_to - date_from + 1.
    IF actual_days > full_days.
      RAISE EXCEPTION TYPE zcx_utilities_input EXPORTING code = 'PERIOD_TOO_LONG'.
    ENDIF.
    " Consumption already belongs to this interval: only fee and limits scale.
    DATA(fraction) = CONV decfloat34( actual_days ) / full_days.
    DATA(lower) = CONV decfloat34( 0 ).
    DATA(energy) = CONV decfloat34( 0 ).
    DATA(unlimited) = abap_false.
    LOOP AT tiers INTO DATA(tier).
      IF unlimited = abap_true OR tier-price < 0 OR tier-upper_limit < 0.
        RAISE EXCEPTION TYPE zcx_utilities_input EXPORTING code = 'INVALID_TIER'.
      ENDIF.
      IF tier-upper_limit = 0.
        unlimited = abap_true.
        DATA(quantity) = nmax( val1 = consumption - lower val2 = 0 ).
      ELSE.
        DATA(upper) = tier-upper_limit * fraction.
        IF upper <= lower.
          RAISE EXCEPTION TYPE zcx_utilities_input EXPORTING code = 'NON_INCREASING_TIER'.
        ENDIF.
        quantity = nmax( val1 = nmin( val1 = consumption val2 = upper ) - lower
                         val2 = 0 ).
        lower = upper.
      ENDIF.
      energy = energy + quantity * tier-price.
    ENDLOOP.
    IF unlimited = abap_false.
      RAISE EXCEPTION TYPE zcx_utilities_input EXPORTING code = 'MISSING_FINAL_TIER'.
    ENDIF.
    result = VALUE #( consumption = consumption period_days = actual_days
                      fraction = fraction currency = 'EUR'
                      reason = COND #( WHEN estimated = abap_true
                                       THEN 'ESTIMATED' ELSE 'ACTUAL' ) ).
    " Synthetic invoice policy: round net first, then calculate tax on that net.
    result-net = round( val = base_fee * fraction + energy dec = 2 ).
    result-tax = round( val = CONV decfloat34( result-net ) * tax_rate dec = 2 ).
    result-gross = result-net + result-tax.
  ENDMETHOD.
ENDCLASS.
