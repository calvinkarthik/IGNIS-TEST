.PHONY: bootstrap backend frontend simulator test test-backend test-frontend test-cpp run-demo clean

bootstrap:
	powershell -ExecutionPolicy Bypass -File scripts/bootstrap-windows.ps1

backend:
	cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

simulator:
	cd simulator && ../backend/.venv/Scripts/python -m ignis_simulator.cli --scenario confirmed_fire

test: test-backend test-frontend test-cpp

test-backend:
	cd backend && .venv/Scripts/python -m pytest

test-frontend:
	cd frontend && npm test -- --run && npm run build

test-cpp:
	$(MAKE) -C qnx portable-test

run-demo:
	powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1

clean:
	powershell -ExecutionPolicy Bypass -File scripts/clean.ps1

