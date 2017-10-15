Setup:
Requires Python 3.6+
pip install -r requirements.txt
Edit config/engine.json to point to Stockfish (or your engine of choice)

Run:
1. Put PGN files into the pgn/ folder.
2. Run interactive.py and follow the prompts.
3. Read reports from the reports/ folder.

Terminology:
Working set - A set games to pre-process or analyze
Pre-process - Use an engine over the games in the working set. Results are persisted in db/data.sqlite3, so pre-processing can be killed and restarted at any time
Analysis - Use an algorithm to aggregate the results into some useful metrics
