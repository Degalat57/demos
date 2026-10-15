CLASS ltcl_test DEFINITION FINAL FOR TESTING
  DURATION SHORT RISK LEVEL HARMLESS.
  PRIVATE SECTION.
    METHODS report_example FOR TESTING RAISING zcx_utilities_input.

ENDCLASS.

CLASS ltcl_test IMPLEMENTATION.
  METHOD report_example.
    DATA(actual) = zcl_utilities_demo=>run( ).
    cl_abap_unit_assert=>assert_equals( act = actual-reading-consumption exp = CONV decfloat34( 120 ) ).
    cl_abap_unit_assert=>assert_equals( act = actual-bill-gross exp = CONV zcl_billing_estimator=>ty_money( '42.84' ) ).
    cl_abap_unit_assert=>assert_true( act = actual-ready_for_billing ).
  ENDMETHOD.

ENDCLASS.
