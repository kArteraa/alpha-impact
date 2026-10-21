export interface Loan {
  id: string;
  product: string;
  amount: number;
  rate: string;
  maturity: string;
}

export const LOANS: Loan[] = [
  { id: "loan-1", product: "Кредитная линия", amount: 120_000_000, rate: "ключевая + 2,5%", maturity: "2027-06-30" },
  { id: "loan-2", product: "Лизинг транспорта", amount: 38_400_000, rate: "17,9% фикс.", maturity: "2028-03-31" },
  { id: "loan-3", product: "Овердрафт", amount: 15_000_000, rate: "ключевая + 3%", maturity: "2026-12-31" },
];

export const LOANS_TOTAL = LOANS.reduce((sum, loan) => sum + loan.amount, 0);
