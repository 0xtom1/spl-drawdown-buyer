from dataclasses import dataclass


@dataclass
class ExitStrategy:
    amount_remaining_percent_gt: float
    amount_remaining_percent_lte: float
    stop_price_per_token_percent_change: float
    profit_price_per_token_percent_change: float
    profit_sell_amount_percent: float

    def __str__(self):
        return (
            f"ExitStrategy:\n"
            f"\tAmount Remaining >: {self.amount_remaining_percent_gt*100:.2f}%\n"
            f"\tAmount Remaining ≤: {self.amount_remaining_percent_lte*100:.2f}%\n"
            f"\tStop Price Change: {self.stop_price_per_token_percent_change*100:.2f}%\n"
            f"\tProfit Price Change: {self.profit_price_per_token_percent_change*100:.2f}%\n"
            f"\tProfit Sell Amount: {self.profit_sell_amount_percent*100:.2f}%"
        )
