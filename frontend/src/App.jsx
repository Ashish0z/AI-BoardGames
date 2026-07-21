import { useMemo, useState } from 'react'
import './App.css'

const humanId = 'human-1'
const aiId = 'ai-1'

function rollTwoDice() {
  return {
    die1: Math.floor(Math.random() * 6) + 1,
    die2: Math.floor(Math.random() * 6) + 1,
  }
}

function getTileCoordinate(index) {
  if (index === 0) return [10, 10]
  if (index > 0 && index < 10) return [10, 10 - index]
  if (index === 10) return [10, 0]
  if (index > 10 && index < 20) return [10 - (index - 10), 0]
  if (index === 20) return [0, 0]
  if (index > 20 && index < 30) return [0, index - 20]
  if (index === 30) return [0, 10]
  return [index - 30, 10]
}

function positionToPercent(index, offset = 0) {
  const [row, col] = getTileCoordinate(index)
  const step = 100 / 10
  const x = col * step + step / 2 + (offset % 2) * 1.5
  const y = row * step + step / 2 + Math.floor(offset / 2) * 1.5
  return { left: `${x}%`, top: `${y}%` }
}

function App() {
  const [games, setGames] = useState([
    { key: 'monopoly', label: 'Monopoly', enabled: true },
    { key: 'catan', label: 'Catan', enabled: false },
    { key: 'chess', label: 'Chess', enabled: false },
    { key: 'risk', label: 'Risk', enabled: false },
  ])
  const [selectedGame, setSelectedGame] = useState('monopoly')
  const [gameId, setGameId] = useState(null)
  const [state, setState] = useState(null)
  const [moves, setMoves] = useState([])
  const [chat, setChat] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [status, setStatus] = useState('Ready')
  const [tradeTarget, setTradeTarget] = useState(aiId)
  const [tradeOfferCash, setTradeOfferCash] = useState(100)

  const players = useMemo(() => state?.players || [], [state])

  async function loadGameTypes() {
    try {
      const response = await fetch('/games/types')
      const payload = await response.json()
      setGames(payload.games)
    } catch {
      setStatus('Unable to load game list')
    }
  }

  async function createGame() {
    setStatus('Creating game...')
    const response = await fetch('/games', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        game_type: selectedGame,
        players: [
          { id: humanId, name: 'You', is_human: true, skill_level: 0.5 },
          { id: aiId, name: 'AI', is_human: false, skill_level: 0.7 },
        ],
      }),
    })
    const payload = await response.json()
    if (!response.ok) {
      setStatus(payload.detail || 'Failed to create game')
      return
    }
    setGameId(payload.game_id)
    setState(payload.state)
    setStatus('Game created')
    await refreshMoves(payload.game_id)
  }

  async function refreshMoves(id = gameId) {
    if (!id || !state) return
    const current = state.current_player_id
    if (current !== humanId) {
      setMoves([])
      return
    }
    const response = await fetch(`/games/${id}/moves/${humanId}`)
    const payload = await response.json()
    if (response.ok) {
      setMoves(payload.moves)
      return
    }
    setStatus(payload.detail || 'Failed to load moves')
  }

  async function runMove(action, payload = {}) {
    if (!gameId) return
    const response = await fetch(`/games/${gameId}/move`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player_id: humanId, action, payload }),
    })
    const body = await response.json()
    if (!response.ok) {
      setStatus(body.detail || 'Move failed')
      return
    }
    setState(body.state)
    setStatus(`Move: ${action}`)
    if (body.state.current_player_id === humanId) {
      await refreshMoves(gameId)
    } else {
      setMoves([])
    }
  }

  async function doAiMove() {
    if (!gameId) return
    const response = await fetch(`/games/${gameId}/ai-move?player_id=${aiId}`, { method: 'POST' })
    const body = await response.json()
    if (!response.ok) {
      setStatus(body.detail || 'AI move failed')
      return
    }
    setState(body.state)
    setStatus(`AI played: ${body.move.action}`)
    await refreshMoves(gameId)
  }

  async function sendChat() {
    if (!gameId || !chatInput.trim()) return
    const userMessage = chatInput.trim()
    setChat((current) => [...current, { role: 'You', text: userMessage }])
    setChatInput('')

    const response = await fetch(`/games/${gameId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userMessage }),
    })
    const payload = await response.json()
    setChat((current) => [...current, { role: 'Coach', text: payload.answer || payload.detail || 'No response' }])
  }

  const boardTiles = state?.board?.tiles || []
  const positions = state?.board?.positions || {}

  return (
    <div className="app-shell">
      <aside className="sidebar panel">
        <h2>Settings</h2>
        <label>
          Selected game
          <select value={selectedGame} onChange={(e) => setSelectedGame(e.target.value)}>
            {games.map((game) => (
              <option key={game.key} value={game.key} disabled={!game.enabled}>
                {game.label}{game.enabled ? '' : ' (coming soon)'}
              </option>
            ))}
          </select>
        </label>
        <button onClick={loadGameTypes}>Refresh Game List</button>
        <button onClick={createGame} disabled={!games.find((g) => g.key === selectedGame)?.enabled}>
          Start Game
        </button>

        <div className="status-box">
          <h3>Status</h3>
          <p>{status}</p>
          <p>Game ID: {gameId || 'N/A'}</p>
          <p>Current turn: {state?.current_player_id || 'N/A'}</p>
          <p>Last event: {state?.board?.last_event || 'N/A'}</p>
        </div>

        <div className="money-box">
          <h3>Players</h3>
          {players.map((player) => (
            <div key={player.id} className="money-row">
              <span>{player.name}</span>
              <span>${state?.board?.money?.[player.id] ?? 0}</span>
            </div>
          ))}
        </div>
      </aside>

      <main className="main panel">
        <header className="main-header">
          <h1>AI Board Games</h1>
          <div className="game-tabs">
            {games.map((game) => (
              <button
                key={game.key}
                className={game.key === selectedGame ? 'active' : ''}
                onClick={() => setSelectedGame(game.key)}
                disabled={!game.enabled}
              >
                {game.label}
              </button>
            ))}
          </div>
        </header>

        <section className="board-wrapper">
          <div className="board-grid">
            {boardTiles.map((tile) => {
              const [row, col] = getTileCoordinate(tile.index)
              return (
                <div
                  key={tile.index}
                  className={`tile tile-${tile.type}`}
                  style={{ gridRow: row + 1, gridColumn: col + 1 }}
                  title={`${tile.name} (${tile.type})`}
                >
                  <span className="tile-index">{tile.index}</span>
                  <span className="tile-name">{tile.name}</span>
                </div>
              )
            })}
            <div className="board-center">
              <strong>Monopoly</strong>
              <p>Extensible engine + AI coach</p>
            </div>
            {Object.entries(positions).map(([playerId, tileIndex], idx) => (
              <div
                key={playerId}
                className={`token ${playerId === humanId ? 'human' : 'ai'}`}
                style={positionToPercent(Number(tileIndex), idx)}
              >
                {playerId === humanId ? 'H' : 'A'}
              </div>
            ))}
          </div>
        </section>

        <section className="controls">
          <h3>Turn Controls</h3>
          <div className="control-row">
            {moves.map((move) => {
              if (move.action === 'roll_dice') {
                return (
                  <button key={move.action} onClick={() => runMove('roll_dice', rollTwoDice())}>
                    Roll Dice
                  </button>
                )
              }
              if (move.action === 'offer_trade') {
                return (
                  <div key={move.action} className="trade-form">
                    <select value={tradeTarget} onChange={(e) => setTradeTarget(e.target.value)}>
                      <option value={aiId}>AI</option>
                    </select>
                    <input
                      type="number"
                      min="0"
                      value={tradeOfferCash}
                      onChange={(e) => setTradeOfferCash(Number(e.target.value))}
                    />
                    <button onClick={() => runMove('offer_trade', { to_player_id: tradeTarget, offer_cash: tradeOfferCash })}>
                      Offer Trade
                    </button>
                  </div>
                )
              }
              return (
                <button key={move.action} onClick={() => runMove(move.action)}>
                  {move.action}
                </button>
              )
            })}
            <button onClick={doAiMove} disabled={state?.current_player_id !== aiId}>
              Run AI Turn
            </button>
          </div>
        </section>
      </main>

      <aside className="chat panel">
        <h2>Strategy Chat</h2>
        <div className="chat-log">
          {chat.map((entry, idx) => (
            <p key={`${entry.role}-${idx}`}>
              <strong>{entry.role}:</strong> {entry.text}
            </p>
          ))}
        </div>
        <div className="chat-actions">
          <input
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="Ask for strategy or best move"
          />
          <button onClick={sendChat}>Send</button>
        </div>
      </aside>
    </div>
  )
}

export default App
