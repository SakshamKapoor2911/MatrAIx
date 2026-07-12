# Texas Hold'em API protocol

The heads-up poker game is available through a REST API sidecar named `holdem-web`, reachable from this container at `http://holdem-web:8000`.

## Endpoints

| Method | Path | Body / Query | Response |
|---|---|---|---|
| `GET` | `/health` | - | `{"status": "ok"}` |
| `GET` | `/` | - | HTML page with the game UI |
| `POST` | `/new-game` | (optional query `?seed=<int>`) | Game state with hole cards, blinds posted |
| `GET` | `/state` | - | Current game state |
| `POST` | `/action` | `{"action": "fold\|check\|call\|raise", "amount": 60}` | Updated game state after action + bot response |

## Browser-based play

Open `http://holdem-web:8000/` in the browser. The page will automatically start a new game. Use the buttons to act on each street. When the hand finishes, copy the Result JSON from the right panel.

## API-based play (alternative)

Instead of the browser, you may use `curl` to interact programmatically:

1. Start a new game: `curl -X POST http://holdem-web:8000/new-game?seed=42`
2. Check state: `curl http://holdem-web:8000/state`
3. Take action: `curl -X POST http://holdem-web:8000/action -H "Content-Type: application/json" -d '{"action": "raise"}'`

## Required output

Save the result JSON to `/app/output/holdem_result.json`. Include all fields described in `instruction.md`.
