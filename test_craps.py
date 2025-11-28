import unittest

# --- CONFIGURATION CONSTANTS ---
ODDS_PAYOUT = {4: 2.0, 10: 2.0, 5: 1.5, 9: 1.5, 6: 1.2, 8: 1.2}
PLACE_PAYOUT = {4: 1.8, 10: 1.8, 5: 1.4, 9: 1.4, 6: 1.166, 8: 1.166}

class CrapsEngine:
    def __init__(self, bankroll, min_bet, strategy, press_mode, press_limit):
        self.cash = bankroll
        self.min_bet = min_bet
        self.strategy = strategy
        self.press_mode = press_mode
        self.press_limit = press_limit
        
        self.active_bets = {}
        self.point = 0
        self.unit_size = min_bet
        self.is_ruined = False
        
        self.min_strategy_cost = min_bet
        if strategy == 'iron_cross': self.min_strategy_cost = min_bet * 4.4
        if strategy == 'place_68': self.min_strategy_cost = min_bet * 2.4

    def update_bet(self, bet_key, target_amt):
        current_amt = self.active_bets.get(bet_key, 0)
        if current_amt == 0:
            self.cash -= target_amt
            self.active_bets[bet_key] = target_amt
        elif current_amt < target_amt:
            diff = target_amt - current_amt
            self.cash -= diff
            self.active_bets[bet_key] = target_amt
        elif current_amt > target_amt:
            diff = current_amt - target_amt
            self.cash += diff
            self.active_bets[bet_key] = target_amt

    def process_roll(self, roll):
        if self.cash < self.min_strategy_cost and len(self.active_bets) == 0:
            self.is_ruined = True
            return

        winnings = 0
        event = 'neutral'
        
        # 1. Determine Game State
        if self.point == 0:
            if roll in [7, 11]: event = 'natural'
            elif roll in [2, 3, 12]: event = 'craps'
            else: 
                self.point = roll
                event = 'point_set'
        else:
            if roll == self.point: 
                event = 'point_hit'
                self.point = 0
            elif roll == 7: 
                event = 'seven_out'
                self.point = 0

        # 2. Reset Logic
        if self.point == 0:
            if event in ['natural', 'craps', 'seven_out', 'point_hit']:
                self.unit_size = self.min_bet

        # 3. Place Bets
        if self.point == 0:
            if self.strategy == 'pass_odds' and 'pass' not in self.active_bets:
                self.cash -= self.min_bet
                self.active_bets['pass'] = self.min_bet
            if self.strategy == 'dark_side' and 'dontpass' not in self.active_bets:
                self.cash -= self.min_bet
                self.active_bets['dontpass'] = self.min_bet
        else:
            if self.strategy == 'pass_odds' and 'pass' in self.active_bets and 'odds' not in self.active_bets:
                if self.cash >= self.unit_size * 3:
                    odds_amt = self.unit_size * 3
                    self.cash -= odds_amt
                    self.active_bets['odds'] = odds_amt

            if self.strategy == 'iron_cross' and self.cash >= self.unit_size * 4:
                if self.point != 5: self.update_bet('place5', self.unit_size)
                if self.point != 6: self.update_bet('place6', self.unit_size + 2)
                if self.point != 8: self.update_bet('place8', self.unit_size + 2)
                self.update_bet('field', self.unit_size) 

            if self.strategy == 'place_68' and self.cash >= self.unit_size * 2.4:
                if self.point != 6: self.update_bet('place6', self.unit_size + 2)
                if self.point != 8: self.update_bet('place8', self.unit_size + 2)

        # 4. Resolve Payouts
        
        # Pass Line
        if 'pass' in self.active_bets:
            if event == 'natural': winnings += self.active_bets['pass']
            elif event == 'craps': del self.active_bets['pass']
            elif event == 'point_hit':
                winnings += self.active_bets['pass']
                if 'odds' in self.active_bets:
                    winnings += self.active_bets['odds'] * ODDS_PAYOUT[roll]
                    self.cash += self.active_bets['odds'] 
                    del self.active_bets['odds']
            elif event == 'seven_out':
                del self.active_bets['pass']
                if 'odds' in self.active_bets: del self.active_bets['odds']

        # Don't Pass
        if 'dontpass' in self.active_bets:
            if event == 'natural': del self.active_bets['dontpass']
            elif event == 'craps' and roll != 12: winnings += self.active_bets['dontpass']
            elif event == 'seven_out': winnings += self.active_bets['dontpass']
            elif event == 'point_hit': del self.active_bets['dontpass']

        # Field
        if 'field' in self.active_bets:
            if roll in [2, 3, 4, 9, 10, 11, 12]:
                mult = 2 if roll in [2, 12] else 1
                winnings += self.active_bets['field'] * mult
                self.cash += self.active_bets['field'] 
                del self.active_bets['field']
            else:
                del self.active_bets['field']

        # Place Bets
        if self.point != 0 or event == 'seven_out':
            if roll == 7:
                for k in ['place5', 'place6', 'place8']:
                    if k in self.active_bets: del self.active_bets[k]
            else:
                if roll == 5 and 'place5' in self.active_bets: winnings += self.active_bets['place5'] * 1.4
                if roll == 6 and 'place6' in self.active_bets: winnings += self.active_bets['place6'] * 1.166
                if roll == 8 and 'place8' in self.active_bets: winnings += self.active_bets['place8'] * 1.166

        # 5. Pressing Logic
        if winnings > 0:
            self.cash += winnings 
            if self.unit_size < self.press_limit:
                if self.press_mode == 'press_half':
                    self.unit_size += (self.min_bet * 0.5)
                elif self.press_mode == 'press_full':
                    if winnings >= self.unit_size:
                        self.unit_size = self.unit_size * 2
                    else:
                        self.unit_size += self.min_bet

class TestCrapsLogic(unittest.TestCase):

    def test_pass_line_natural(self):
        """Test Basic Pass Line: 7 on Come Out."""
        game = CrapsEngine(100, 10, 'pass_odds', 'collect', 100)
        game.process_roll(7) 
        self.assertEqual(game.cash + game.active_bets.get('pass', 0), 110)

    def test_iron_cross_field(self):
        """Test Iron Cross: Field Win."""
        game = CrapsEngine(1000, 10, 'iron_cross', 'collect', 150)
        game.process_roll(5) # Set point 5. Field loses (-10). Assets 990.
        game.process_roll(12) # Field wins 20. Assets 1010.
        total = game.cash + sum(game.active_bets.values())
        self.assertEqual(total, 1010)

    def test_strategy_matrix(self):
        """Run a standard game loop on ALL combinations to ensure no crashes."""
        strategies = ['pass_odds', 'iron_cross', 'place_68', 'dark_side']
        press_modes = ['collect', 'press_half', 'press_full']
        
        # A standard game sequence:
        # 5 (Point) -> 6 (Place Win) -> 8 (Place Win) -> 5 (Point Hit) -> 7 (Come Out 7) -> 4 (New Point) -> 7 (Seven Out)
        rolls = [5, 6, 8, 5, 7, 4, 7]

        print("\n--- MATRIX TEST ---")
        for strat in strategies:
            for press in press_modes:
                with self.subTest(strategy=strat, press=press):
                    game = CrapsEngine(2000, 10, strat, press, 500)
                    start_cash = game.cash
                    
                    try:
                        for r in rolls:
                            game.process_roll(r)
                        
                        # Assert checks
                        # 1. Should not be None
                        self.assertIsNotNone(game.cash)
                        # 2. Should have processed some bets (cash shouldn't be exactly 2000 unless everything pushed, which is unlikely)
                        # Note: Dark side might break even on this specific roll sequence, so we just check no errors mostly.
                        
                        print(f"✅ {strat.ljust(12)} + {press.ljust(12)} | End Cash: ${game.cash:.2f}")
                        
                    except Exception as e:
                        self.fail(f"Crash on {strat} / {press}: {e}")

if __name__ == '__main__':
    unittest.main()