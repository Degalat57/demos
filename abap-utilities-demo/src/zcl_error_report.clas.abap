CLASS zcl_error_report DEFINITION PUBLIC FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    TYPES: BEGIN OF ty_reading,
             installation TYPE c LENGTH 10,
             device       TYPE c LENGTH 18,
             expected_device TYPE c LENGTH 18,
             register_id  TYPE c LENGTH 3,
             reading_date TYPE d,
             missing      TYPE abap_bool,
           END OF ty_reading,
           ty_readings TYPE STANDARD TABLE OF ty_reading WITH EMPTY KEY.
    TYPES: BEGIN OF ty_item,
             row_number   TYPE i,
             installation TYPE c LENGTH 10,
             device       TYPE c LENGTH 18,
             register_id  TYPE c LENGTH 3,
             reading_date TYPE d,
             reason       TYPE string,
             priority     TYPE i,
           END OF ty_item,
           ty_worklist TYPE STANDARD TABLE OF ty_item WITH EMPTY KEY.
    METHODS build IMPORTING readings TYPE ty_readings
                  RETURNING VALUE(worklist) TYPE ty_worklist.
ENDCLASS.

CLASS zcl_error_report IMPLEMENTATION.
  METHOD build.
    TYPES: BEGIN OF ty_key,
             installation TYPE c LENGTH 10,
             device TYPE c LENGTH 18,
             register_id TYPE c LENGTH 3,
             reading_date TYPE d,
           END OF ty_key.
    DATA seen TYPE HASHED TABLE OF ty_key
      WITH UNIQUE KEY installation device register_id reading_date.
    LOOP AT readings INTO DATA(reading).
      DATA(row_number) = sy-tabix.
      DATA(item) = CORRESPONDING ty_item( reading ).
      item-row_number = row_number.
      item-priority = 1.
      IF reading-missing = abap_true.
        item-reason = 'READING_MISSING'.
        APPEND item TO worklist.
      ENDIF.
      IF reading-device <> reading-expected_device.
        item-reason = 'DEVICE_MISMATCH'.
        APPEND item TO worklist.
      ENDIF.
      DATA(key) = CORRESPONDING ty_key( reading ).
      INSERT key INTO TABLE seen.
      IF sy-subrc <> 0.
        item-reason = 'DUPLICATE_READING'.
        item-priority = 2.
        APPEND item TO worklist.
      ENDIF.
    ENDLOOP.
  ENDMETHOD.
ENDCLASS.
