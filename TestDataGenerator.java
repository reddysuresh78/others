package com.wf.tempest.testdata.gen;

import java.util.Random;

public class TestDataGenerator {

	private static final char FIELD_SEPARATOR = ',';
	private static final char RECORD_SEPARATOR = '\n';
	private static Random rand = new Random();
	
	public static void main(String[] args) {
		
		int max = 70000;
		int min = 10000;
		
		for(int i=1;i<=2;i++) {
			createEntries(i, max, min);
		 
		}
	}
	
	private static String createEntries(int i, int max, int min) {
		StringBuilder dbBuffer = new StringBuilder();
		
		String savingAcc = "123456" + i + 1;
		String checkingAcc = "123456" + i + 2;
		
		int savingsBal = rand.nextInt((max - min) + 1) + min;
		int checkingBal = 80000 - savingsBal;
		
		
		dbBuffer.append(i).append(FIELD_SEPARATOR)
			.append(savingAcc).append(FIELD_SEPARATOR)
			.append(checkingAcc).append(FIELD_SEPARATOR)
			.append(String.format("%.2f", savingsBal*1.0)).append(FIELD_SEPARATOR)
			.append(String.format("%.2f", checkingBal*1.0)).append(RECORD_SEPARATOR);
		
		System.out.print (dbBuffer);
		
		StringBuilder mqBuffer = new StringBuilder();
		
		int tranMax = 100;
		int tranMin = 10;
		int curBal = savingsBal;
		for(int j=1; j<=10; j++) {
			int tranAmt = rand.nextInt((tranMax - tranMin) + 1) + tranMin;
			boolean debit = rand.nextBoolean();
			curBal = debit? curBal - tranAmt: curBal + tranAmt;
			mqBuffer.append(savingAcc).append(FIELD_SEPARATOR)
				.append(String.format("%.2f", tranAmt*1.0)).append(FIELD_SEPARATOR)
				.append(String.format("%.2f", curBal*1.0)).append(FIELD_SEPARATOR)
				.append(j+345678).append(FIELD_SEPARATOR)
				.append("Memo").append(debit?" Debit ": " Credit ").append("for savings account") 
				.append(RECORD_SEPARATOR);
		}
		curBal = checkingBal;
		for(int k=1; k<=10; k++) {
			int tranAmt = rand.nextInt((tranMax - tranMin) + 1) + tranMin;
			boolean debit = rand.nextBoolean();
			curBal = debit? curBal - tranAmt: curBal + tranAmt;
			mqBuffer.append(checkingAcc).append(FIELD_SEPARATOR)
				.append(String.format("%.2f", tranAmt*1.0)).append(FIELD_SEPARATOR)
				.append(String.format("%.2f", curBal*1.0)).append(FIELD_SEPARATOR)
				.append(k+234567).append(FIELD_SEPARATOR)
				.append("Memo").append(debit?" Debit ": " Credit ").append("for checkings account") 
				.append(RECORD_SEPARATOR);
		}
		
//		System.out.println(mqBuffer);
		
		return dbBuffer.toString();
	}
	 

}
