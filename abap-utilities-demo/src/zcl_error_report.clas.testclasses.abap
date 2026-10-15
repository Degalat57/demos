CLASS ltcl_test DEFINITION FINAL FOR TESTING
  DURATION SHORT RISK LEVEL HARMLESS.
  PRIVATE SECTION.
    METHODS empty_worklist FOR TESTING RAISING zcx_utilities_input.
    METHODS clean_reading FOR TESTING RAISING zcx_utilities_input.
    METHODS missing_reading FOR TESTING RAISING zcx_utilities_input.
    METHODS mismatched_device FOR TESTING RAISING zcx_utilities_input.
    METHODS duplicate_reading FOR TESTING RAISING zcx_utilities_input.
    METHODS three_duplicates FOR TESTING RAISING zcx_utilities_input.
    METHODS different_registers FOR TESTING RAISING zcx_utilities_input.
    METHODS different_dates FOR TESTING RAISING zcx_utilities_input.
    METHODS different_installations FOR TESTING RAISING zcx_utilities_input.
    METHODS multiple_reasons FOR TESTING RAISING zcx_utilities_input.
    METHODS preserves_source_row FOR TESTING RAISING zcx_utilities_input.

ENDCLASS.

CLASS ltcl_test IMPLEMENTATION.
  METHOD empty_worklist.
    DATA(actual) = NEW zcl_error_report( )->build( readings = VALUE #(  ) ).
    cl_abap_unit_assert=>assert_equals( act = lines( actual ) exp = 0 ).
  ENDMETHOD.

  METHOD clean_reading.
    DATA(actual) = NEW zcl_error_report( )->build( readings = VALUE #( ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' ) ) ).
    cl_abap_unit_assert=>assert_equals( act = lines( actual ) exp = 0 ).
  ENDMETHOD.

  METHOD missing_reading.
    DATA(actual) = NEW zcl_error_report( )->build( readings = VALUE #( ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' missing = abap_true ) ) ).
    cl_abap_unit_assert=>assert_equals( act = lines( actual ) exp = 1 ).
    cl_abap_unit_assert=>assert_equals( act = actual[ 1 ]-reason exp = 'READING_MISSING' ).
  ENDMETHOD.

  METHOD mismatched_device.
    DATA(actual) = NEW zcl_error_report( )->build( readings = VALUE #( ( installation = 'I1' device = 'D2' expected_device = 'D1' ) ) ).
    cl_abap_unit_assert=>assert_equals( act = lines( actual ) exp = 1 ).
    cl_abap_unit_assert=>assert_equals( act = actual[ 1 ]-reason exp = 'DEVICE_MISMATCH' ).
  ENDMETHOD.

  METHOD duplicate_reading.
    DATA(actual) = NEW zcl_error_report( )->build( readings = VALUE #( ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' ) ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' ) ) ).
    cl_abap_unit_assert=>assert_equals( act = lines( actual ) exp = 1 ).
    cl_abap_unit_assert=>assert_equals( act = actual[ 1 ]-reason exp = 'DUPLICATE_READING' ).
  ENDMETHOD.

  METHOD three_duplicates.
    DATA(actual) = NEW zcl_error_report( )->build( readings = VALUE #( ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' ) ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' ) ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' ) ) ).
    cl_abap_unit_assert=>assert_equals( act = lines( actual ) exp = 2 ).
    cl_abap_unit_assert=>assert_equals( act = actual[ 1 ]-reason exp = 'DUPLICATE_READING' ).
    cl_abap_unit_assert=>assert_equals( act = actual[ 2 ]-reason exp = 'DUPLICATE_READING' ).
  ENDMETHOD.

  METHOD different_registers.
    DATA(actual) = NEW zcl_error_report( )->build( readings = VALUE #( ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' ) ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '002' reading_date = '20260430' ) ) ).
    cl_abap_unit_assert=>assert_equals( act = lines( actual ) exp = 0 ).
  ENDMETHOD.

  METHOD different_dates.
    DATA(actual) = NEW zcl_error_report( )->build( readings = VALUE #( ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' ) ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260531' ) ) ).
    cl_abap_unit_assert=>assert_equals( act = lines( actual ) exp = 0 ).
  ENDMETHOD.

  METHOD different_installations.
    DATA(actual) = NEW zcl_error_report( )->build( readings = VALUE #( ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' ) ( installation = 'I2' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' ) ) ).
    cl_abap_unit_assert=>assert_equals( act = lines( actual ) exp = 0 ).
  ENDMETHOD.

  METHOD multiple_reasons.
    DATA(actual) = NEW zcl_error_report( )->build( readings = VALUE #( ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' ) ( installation = 'I1' device = 'D2' expected_device = 'D1' register_id = '001' reading_date = '20260430' missing = abap_true ) ) ).
    cl_abap_unit_assert=>assert_equals( act = lines( actual ) exp = 2 ).
    cl_abap_unit_assert=>assert_equals( act = actual[ 1 ]-reason exp = 'READING_MISSING' ).
    cl_abap_unit_assert=>assert_equals( act = actual[ 2 ]-reason exp = 'DEVICE_MISMATCH' ).
  ENDMETHOD.

  METHOD preserves_source_row.
    DATA(actual) = NEW zcl_error_report( )->build(
      readings = VALUE #( ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' ) ( installation = 'I1' device = 'D1' expected_device = 'D1' register_id = '001' reading_date = '20260430' missing = abap_true ) ) ).
    cl_abap_unit_assert=>assert_equals( act = actual[ 1 ]-row_number exp = 2 ).
    cl_abap_unit_assert=>assert_equals( act = actual[ 2 ]-priority exp = 2 ).
    cl_abap_unit_assert=>assert_equals( act = actual[ 2 ]-installation exp = 'I1' ).
  ENDMETHOD.

ENDCLASS.
