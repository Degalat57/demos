INTERFACE zif_reading_check PUBLIC.
  TYPES ty_quantity TYPE decfloat34.
  TYPES: BEGIN OF ty_period,
           end_date    TYPE d,
           consumption TYPE ty_quantity,
           days        TYPE i,
         END OF ty_period,
         ty_history TYPE STANDARD TABLE OF ty_period WITH EMPTY KEY.
  TYPES: BEGIN OF ty_request,
           previous       TYPE ty_quantity,
           current        TYPE ty_quantity,
           register_digits TYPE i,
           days           TYPE i,
           tolerance      TYPE ty_quantity,
           allow_rollover TYPE abap_bool,
           missing        TYPE abap_bool,
         END OF ty_request.
  TYPES: BEGIN OF ty_result,
           consumption TYPE ty_quantity,
           accepted    TYPE abap_bool,
           estimated   TYPE abap_bool,
           reason      TYPE string,
         END OF ty_result.
  METHODS check
    IMPORTING request TYPE ty_request history TYPE ty_history
    RETURNING VALUE(result) TYPE ty_result
    RAISING zcx_utilities_input.
ENDINTERFACE.
