IDENTIFICATION DIVISION.
PROGRAM-ID. BALANCEINQUIRY.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-ACCOUNT-NUM PIC 9(5).
01 WS-BALANCE     PIC 9(9)V99 VALUE 0.

PROCEDURE DIVISION USING WS-ACCOUNT-NUM.
    DISPLAY "Balance for Account Number ", WS-ACCOUNT-NUM, " is: ", WS-BALANCE.
    STOP RUN.
