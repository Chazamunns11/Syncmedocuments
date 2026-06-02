.PHONY: help test test-quiet doctor status scan backtest sweep deps clean

help:
	@echo "Targets:"
	@echo "  make test       - run the full test suite (offline, no deps)"
	@echo "  make doctor     - preflight checks"
	@echo "  make backtest   - backtest on synthetic data (demo)"
	@echo "  make sweep      - parameter sweep on synthetic data"
	@echo "  make deps       - install live-mode dependencies"
	@echo "  make clean      - remove local bets.db/bets.csv and caches"

test:
	python3 -m unittest discover -s tests -v

test-quiet:
	python3 -m unittest discover -s tests

doctor:
	python3 run.py doctor

status:
	python3 run.py status

scan:
	python3 run.py scan

backtest:
	python3 run.py backtest --synthetic 5000 --stake 10

sweep:
	python3 run.py backtest --synthetic 3000 --sweep

deps:
	pip install -r requirements.txt

clean:
	rm -f bets.db bets.csv
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache
