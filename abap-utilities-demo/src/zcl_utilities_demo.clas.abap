CLASS zcl_utilities_demo DEFINITION PUBLIC FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    TYPES: BEGIN OF ty_output,
             reading TYPE zif_reading_check=>ty_result,
             bill TYPE zcl_billing_estimator=>ty_bill,
             ready_for_billing TYPE abap_bool,
           END OF ty_output.
    CLASS-METHODS run RETURNING VALUE(output) TYPE ty_output
      RAISING zcx_utilities_input.
ENDCLASS.

CLASS zcl_utilities_demo IMPLEMENTATION.
  METHOD run.
    DATA checker TYPE REF TO zif_reading_check.
    checker = NEW zcl_meter_reading_validator( ).
    output-reading = checker->check(
      request = VALUE #( previous = 12300 current = 12420 register_digits = 5
                         days = 30 tolerance = 2 )
      history = VALUE #( ( end_date = '20260131' consumption = 100 days = 31 )
                         ( end_date = '20260228' consumption = 110 days = 28 ) ) ).
    IF output-reading-accepted = abap_true.
      output-bill = NEW zcl_billing_estimator( )->bill(
        consumption = output-reading-consumption
        date_from = '20260401' date_to = '20260430' full_days = 30
        tiers = VALUE #( ( upper_limit = 100 price = '0.20' )
                         ( upper_limit = 0 price = '0.30' ) )
        base_fee = 10 tax_rate = '0.19' ).
      output-ready_for_billing = abap_true.
    ENDIF.
  ENDMETHOD.
ENDCLASS.
