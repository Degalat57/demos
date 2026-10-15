CLASS zcx_utilities_input DEFINITION PUBLIC INHERITING FROM cx_static_check
  FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    METHODS constructor IMPORTING code TYPE string DEFAULT 'INVALID_INPUT'.
    METHODS get_code RETURNING VALUE(code) TYPE string.
  PRIVATE SECTION.
    DATA reason_code TYPE string.
ENDCLASS.

CLASS zcx_utilities_input IMPLEMENTATION.
  METHOD constructor.
    super->constructor( ).
    reason_code = code.
  ENDMETHOD.

  METHOD get_code.
    code = reason_code.
  ENDMETHOD.
ENDCLASS.
