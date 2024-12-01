IDENTIFICATION DIVISION.
PROGRAM-ID. BANKMAIN.

ENVIRONMENT DIVISION.
CONFIGURATION SECTION.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-OPTION      PIC 9.
01 WS-ACCOUNT-NUM PIC 9(5).
01 WS-AMOUNT      PIC 9(9)V99.

PROCEDURE DIVISION.
    DISPLAY "=========================".
    DISPLAY " Simple Banking System ".
    DISPLAY "=========================".
    DISPLAY "1. Create Account".
    DISPLAY "2. Balance Inquiry".
    DISPLAY "3. Deposit Money".
    DISPLAY "4. Withdraw Money".
    DISPLAY "5. Exit".
    DISPLAY "Enter your option: ".
    ACCEPT WS-OPTION.

    EVALUATE WS-OPTION
        WHEN 1
            CALL 'CREATEACCOUNT' USING WS-ACCOUNT-NUM
        WHEN 2
            CALL 'BALANCEINQUIRY' USING WS-ACCOUNT-NUM
        WHEN 3
            CALL 'DEPOSIT' USING WS-ACCOUNT-NUM WS-AMOUNT
        WHEN 4
            CALL 'WITHDRAW' USING WS-ACCOUNT-NUM WS-AMOUNT
        WHEN 5
            DISPLAY "Thank you for using the Banking System!"
            STOP RUN
        WHEN OTHER
            DISPLAY "Invalid Option, try again!"
    END-EVALUATE.

    STOP RUN.
