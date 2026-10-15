CLASS ltcl_test DEFINITION FINAL FOR TESTING
  DURATION SHORT RISK LEVEL HARMLESS.
  PRIVATE SECTION.
    METHODS normal_reading FOR TESTING RAISING zcx_utilities_input.
    METHODS zero_consumption FOR TESTING RAISING zcx_utilities_input.
    METHODS tolerance_boundary FOR TESTING RAISING zcx_utilities_input.
    METHODS jump_falls_back FOR TESTING RAISING zcx_utilities_input.
    METHODS negative_falls_back FOR TESTING RAISING zcx_utilities_input.
    METHODS missing_falls_back FOR TESTING RAISING zcx_utilities_input.
    METHODS missing_no_history FOR TESTING RAISING zcx_utilities_input.
    METHODS negative_no_history FOR TESTING RAISING zcx_utilities_input.
    METHODS first_history_absent FOR TESTING RAISING zcx_utilities_input.
    METHODS rollover_one_unit FOR TESTING RAISING zcx_utilities_input.
    METHODS rollover_twenty_units FOR TESTING RAISING zcx_utilities_input.
    METHODS rollover_jump FOR TESTING RAISING zcx_utilities_input.
    METHODS rollover_not_assumed FOR TESTING RAISING zcx_utilities_input.
    METHODS fractional_reading FOR TESTING RAISING zcx_utilities_input.
    METHODS zero_history_jump FOR TESTING RAISING zcx_utilities_input.
    METHODS daily_baseline FOR TESTING RAISING zcx_utilities_input.
    METHODS negative_register FOR TESTING RAISING zcx_utilities_input.
    METHODS previous_overflow FOR TESTING RAISING zcx_utilities_input.
    METHODS current_overflow FOR TESTING RAISING zcx_utilities_input.
    METHODS digits_zero FOR TESTING RAISING zcx_utilities_input.
    METHODS digits_too_large FOR TESTING RAISING zcx_utilities_input.
    METHODS invalid_tolerance FOR TESTING RAISING zcx_utilities_input.
    METHODS zero_interval FOR TESTING RAISING zcx_utilities_input.

ENDCLASS.

CLASS ltcl_test IMPLEMENTATION.
  METHOD normal_reading.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).

    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ( end_date = '20260131' consumption = 100 days = 30 ) ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '100' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'ACTUAL' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_true ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_false ).
  ENDMETHOD.

  METHOD zero_consumption.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-current = 100.
    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ( end_date = '20260131' consumption = 100 days = 30 ) ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '0' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'ACTUAL' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_true ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_false ).
  ENDMETHOD.

  METHOD tolerance_boundary.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-current = 300.
    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ( end_date = '20260131' consumption = 100 days = 30 ) ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '200' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'ACTUAL' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_true ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_false ).
  ENDMETHOD.

  METHOD jump_falls_back.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-current = 301.
    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ( end_date = '20260131' consumption = 100 days = 30 ) ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '100' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'JUMP' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_true ).
  ENDMETHOD.

  METHOD negative_falls_back.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-current = 99.
    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ( end_date = '20260131' consumption = 100 days = 30 ) ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '100' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'NEGATIVE' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_true ).
  ENDMETHOD.

  METHOD missing_falls_back.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-missing = abap_true.
    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ( end_date = '20260131' consumption = 100 days = 30 ) ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '100' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'MISSING' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_true ).
  ENDMETHOD.

  METHOD missing_no_history.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-missing = abap_true.
    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '0' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'MISSING' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_false ).
  ENDMETHOD.

  METHOD negative_no_history.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-current = 99.
    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '0' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'NEGATIVE' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_false ).
  ENDMETHOD.

  METHOD first_history_absent.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).

    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '100' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'ACTUAL' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_true ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_false ).
  ENDMETHOD.

  METHOD rollover_one_unit.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-previous = 99999.
    request-current = 0.
    request-allow_rollover = abap_true.
    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ( end_date = '20260131' consumption = 100 days = 30 ) ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '1' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'ROLLOVER' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_true ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_false ).
  ENDMETHOD.

  METHOD rollover_twenty_units.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-previous = 99990.
    request-current = 10.
    request-allow_rollover = abap_true.
    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ( end_date = '20260131' consumption = 100 days = 30 ) ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '20' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'ROLLOVER' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_true ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_false ).
  ENDMETHOD.

  METHOD rollover_jump.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-previous = 99000.
    request-current = 1000.
    request-allow_rollover = abap_true.
    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ( end_date = '20260131' consumption = 100 days = 30 ) ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '100' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'JUMP' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_true ).
  ENDMETHOD.

  METHOD rollover_not_assumed.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-previous = 99990.
    request-current = 10.
    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ( end_date = '20260131' consumption = 100 days = 30 ) ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '100' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'NEGATIVE' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_true ).
  ENDMETHOD.

  METHOD fractional_reading.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-current = '200.125'.
    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ( end_date = '20260131' consumption = 100 days = 30 ) ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '100.125' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'ACTUAL' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_true ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_false ).
  ENDMETHOD.

  METHOD zero_history_jump.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).

    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ( end_date = '20260131' consumption = 0 days = 30 ) ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '0' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'JUMP' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_true ).
  ENDMETHOD.

  METHOD daily_baseline.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-days = 15.
    request-missing = abap_true.
    DATA(result) = NEW zcl_meter_reading_validator( )->zif_reading_check~check(
      request = request history = VALUE #( ( end_date = '20260131' consumption = 100 days = 30 ) ) ).
    cl_abap_unit_assert=>assert_equals( act = result-consumption exp = CONV decfloat34( '50' ) ).
    cl_abap_unit_assert=>assert_equals( act = result-reason exp = 'MISSING' ).
    cl_abap_unit_assert=>assert_equals( act = result-accepted exp = abap_false ).
    cl_abap_unit_assert=>assert_equals( act = result-estimated exp = abap_true ).
  ENDMETHOD.

  METHOD negative_register.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-current = -1.
    TRY.
        NEW zcl_meter_reading_validator( )->zif_reading_check~check(
          request = request history = VALUE #( ) ).
        cl_abap_unit_assert=>fail( msg = 'Invalid reading configuration accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD previous_overflow.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-previous = 100000.
    TRY.
        NEW zcl_meter_reading_validator( )->zif_reading_check~check(
          request = request history = VALUE #( ) ).
        cl_abap_unit_assert=>fail( msg = 'Invalid reading configuration accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD current_overflow.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-current = 100000.
    TRY.
        NEW zcl_meter_reading_validator( )->zif_reading_check~check(
          request = request history = VALUE #( ) ).
        cl_abap_unit_assert=>fail( msg = 'Invalid reading configuration accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD digits_zero.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-register_digits = 0.
    TRY.
        NEW zcl_meter_reading_validator( )->zif_reading_check~check(
          request = request history = VALUE #( ) ).
        cl_abap_unit_assert=>fail( msg = 'Invalid reading configuration accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD digits_too_large.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-register_digits = 13.
    TRY.
        NEW zcl_meter_reading_validator( )->zif_reading_check~check(
          request = request history = VALUE #( ) ).
        cl_abap_unit_assert=>fail( msg = 'Invalid reading configuration accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD invalid_tolerance.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-tolerance = '0.5'.
    TRY.
        NEW zcl_meter_reading_validator( )->zif_reading_check~check(
          request = request history = VALUE #( ) ).
        cl_abap_unit_assert=>fail( msg = 'Invalid reading configuration accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

  METHOD zero_interval.
    DATA(request) = VALUE zif_reading_check=>ty_request(
      previous = 100 current = 200 register_digits = 5 days = 30 tolerance = 2 ).
    request-days = 0.
    TRY.
        NEW zcl_meter_reading_validator( )->zif_reading_check~check(
          request = request history = VALUE #( ) ).
        cl_abap_unit_assert=>fail( msg = 'Invalid reading configuration accepted' ).
      CATCH zcx_utilities_input.
        RETURN.
    ENDTRY.
  ENDMETHOD.

ENDCLASS.
