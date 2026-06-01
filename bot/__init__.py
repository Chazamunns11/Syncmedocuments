"""Value betting bot.

Identifies +EV ("value") sportsbook bets, sizes them with fractional Kelly,
places them through a pluggable executor (paper by default, Betfair Exchange
for real money), and logs every identified and placed bet.
"""

__version__ = "0.1.0"
