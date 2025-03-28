IDENTIFICATION DIVISION.
PROGRAM-ID. DEPOSIT.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-ACCOUNT-NUM PIC 9(5).
01 WS-AMOUNT      PIC 9(9)V99.
01 WS-BALANCE     PIC 9(9)V99 VALUE 0.

PROCEDURE DIVISION USING WS-ACCOUNT-NUM WS-AMOUNT.
    DISPLAY "Enter deposit amount for Account Number ", WS-ACCOUNT-NUM, ": ".
    ACCEPT WS-AMOUNT.
    ADD WS-AMOUNT TO WS-BALANCE.
    DISPLAY "New Balance for Account Number ", WS-ACCOUNT-NUM, " is: ", WS-BALANCE.
    STOP RUN.
