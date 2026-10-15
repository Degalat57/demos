CLASS zcl_meter_reading_validator DEFINITION PUBLIC FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    INTERFACES zif_reading_check.
ENDCLASS.

CLASS zcl_meter_reading_validator IMPLEMENTATION.
  METHOD zif_reading_check~check.
    IF request-register_digits < 1 OR request-register_digits > 12
        OR request-days <= 0 OR request-tolerance < 1
        OR request-previous < 0 OR request-current < 0
        OR ( request-missing <> abap_true AND request-missing <> abap_false )
        OR ( request-allow_rollover <> abap_true AND request-allow_rollover <> abap_false ).
      RAISE EXCEPTION TYPE zcx_utilities_input EXPORTING code = 'INVALID_READING_INPUT'.
    ENDIF.
    DATA(modulus) = CONV decfloat34( 10 ) ** request-register_digits.
    IF request-previous >= modulus OR request-current >= modulus.
      RAISE EXCEPTION TYPE zcx_utilities_input EXPORTING code = 'REGISTER_OVERFLOW'.
    ENDIF.
    DATA(estimator) = NEW zcl_billing_estimator( ).
    DATA(baseline) = CONV decfloat34( 0 ).
    IF history IS NOT INITIAL.
      baseline = estimator->estimate( history = history days = request-days ).
    ENDIF.
    result = VALUE #( consumption = request-current - request-previous
                      accepted = abap_true reason = 'ACTUAL' ).
    IF request-missing = abap_true.
      result-reason = 'MISSING'.
    ELSEIF result-consumption < 0.
      " Caller must confirm one physical wrap; never infer device exchange.
      IF request-allow_rollover = abap_true.
        result-consumption = result-consumption + modulus.
        result-reason = 'ROLLOVER'.
      ELSE.
        result-reason = 'NEGATIVE'.
      ENDIF.
    ENDIF.
    IF ( result-reason = 'ACTUAL' OR result-reason = 'ROLLOVER' )
        AND history IS NOT INITIAL
        AND result-consumption > baseline * request-tolerance.
      result-reason = 'JUMP'.
    ENDIF.
    IF result-reason = 'MISSING' OR result-reason = 'NEGATIVE' OR result-reason = 'JUMP'.
      " Fallback quantity is a review candidate, never automatic acceptance.
      result-accepted = abap_false.
      result-consumption = 0.
      IF history IS NOT INITIAL.
        result-consumption = baseline.
        result-estimated = abap_true.
      ENDIF.
    ENDIF.
  ENDMETHOD.
ENDCLASS.
