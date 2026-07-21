import { useEffect, useMemo, useState } from 'react'
import './App.css'

const humanId = 'human-1'

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
  const [tradeTarget, setTradeTarget] = useState('ai-1')
  const [tradeOfferCash, setTradeOfferCash] = useState(100)
  const [aiCount, setAiCount] = useState(1)
  const [aiPrompt, setAiPrompt] = useState('')
  const [coachPrompt, setCoachPrompt] = useState('')
  const [isAiThinking, setIsAiThinking] = useState(false)

  const players = useMemo(() => state?.players || [], [state])
  const aiPlayers = useMemo(() => players.filter((player) => !player.is_human), [players])

  useEffect(() => {
    if (!aiPlayers.length) return
    if (!aiPlayers.find((player) => player.id === tradeTarget)) {
      setTradeTarget(aiPlayers[0].id)
    }
  }, [aiPlayers, tradeTarget])

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
    const selectedAiCount = Math.max(1, Number(aiCount) || 1)
    const configuredPlayers = [
      { id: humanId, name: 'You', is_human: true, skill_level: 0.5 },
      ...Array.from({ length: selectedAiCount }, (_, idx) => ({
        id: `ai-${idx + 1}`,
        name: `AI ${idx + 1}`,
        is_human: false,
        skill_level: Math.min(0.95, 0.6 + idx * 0.1),
      })),
    ]
    const response = await fetch('/games', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        game_type: selectedGame,
        players: configuredPlayers,
        ai_prompt: aiPrompt.trim() || undefined,
        coach_prompt: coachPrompt.trim() || undefined,
      }),
    })
    const payload = await response.json()
    if (!response.ok) {
      setStatus(payload.detail || 'Failed to create game')
      return
    }
    setGameId(payload.game_id)
    setState(payload.state)
    setAiPrompt(payload.state?.metadata?.ai_prompt || aiPrompt)
    setCoachPrompt(payload.state?.metadata?.coach_prompt || coachPrompt)
    setStatus('Game created')
    await refreshMoves(payload.game_id, payload.state)
  }

  async function refreshMoves(id = gameId, nextState = state) {
    if (!id || !nextState) return
    const current = nextState.current_player_id
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

  async function doAiMove(playerId = state?.current_player_id) {
    if (!gameId || !playerId || playerId === humanId) return
    setIsAiThinking(true)
    setStatus(`AI ${playerId} is thinking...`)
    const response = await fetch(`/games/${gameId}/ai-move?player_id=${playerId}`, { method: 'POST' })
    const body = await response.json()
    if (!response.ok) {
      setIsAiThinking(false)
      setStatus(body.detail || 'AI move failed')
      return
    }
    setState(body.state)
    setStatus(`AI played: ${body.move.action}`)
    setIsAiThinking(false)
    await refreshMoves(gameId, body.state)
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

  async function updatePrompts() {
    if (!gameId) return
    const response = await fetch(`/games/${gameId}/prompts`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ai_prompt: aiPrompt,
        coach_prompt: coachPrompt,
      }),
    })
    const payload = await response.json()
    if (!response.ok) {
      setStatus(payload.detail || 'Unable to update prompts')
      return
    }
    setState(payload.state)
    setStatus('Prompts updated for current game')
  }

  useEffect(() => {
    if (!state || !gameId || isAiThinking) return
    const current = state.current_player_id
    if (current && current !== humanId) {
      void doAiMove(current)
    }
  }, [state?.current_player_id, gameId, isAiThinking])

  const boardTiles = state?.board?.tiles || []
  const positions = state?.board?.positions || {}
  const currentPlayerId = state?.current_player_id
  const currentTileIndex = currentPlayerId ? Number(positions[currentPlayerId] ?? 0) : null
  const currentTile = currentTileIndex === null ? null : boardTiles.find((tile) => tile.index === currentTileIndex)
  const currentTileOwnership = currentTile ? state?.board?.ownership?.[String(currentTile.index)] : null
  const currentTileOwnerName = currentTileOwnership
    ? players.find((player) => player.id === currentTileOwnership)?.name || currentTileOwnership
    : null

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
        <label>
          AI opponents
          <select value={aiCount} onChange={(e) => setAiCount(Number(e.target.value))}>
            <option value={1}>1</option>
            <option value={2}>2</option>
            <option value={3}>3</option>
          </select>
        </label>
        <label>
          AI move prompt (per game)
          <textarea value={aiPrompt} onChange={(e) => setAiPrompt(e.target.value)} rows={6} />
        </label>
        <label>
          Coach prompt (per game)
          <textarea value={coachPrompt} onChange={(e) => setCoachPrompt(e.target.value)} rows={3} />
        </label>
        <button onClick={loadGameTypes}>Refresh Game List</button>
        <button onClick={createGame} disabled={!games.find((g) => g.key === selectedGame)?.enabled}>
          Start Game
        </button>
        <button onClick={updatePrompts} disabled={!gameId}>
          Save Prompt Changes
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
                  className={`tile tile-${tile.type}${tile.color_group ? ` tile-group-${String(tile.color_group).replaceAll('_', '-')}` : ''}`}
                  style={{ gridRow: row + 1, gridColumn: col + 1 }}
                  title={`${tile.name} (${tile.type})`}
                >
                  <span className="tile-index">{tile.index}</span>
                  <span className="tile-name">{tile.name}</span>
                  <span className="tile-price">
                    {tile.price ? `$${tile.price}` : tile.amount ? `Tax $${tile.amount}` : ''}
                  </span>
                </div>
              )
            })}
            <div className="board-center">
              <strong>{currentTile?.name || 'Monopoly'}</strong>
              <p className="center-subtitle">{currentTile ? `Tile #${currentTile.index} • ${currentTile.type}` : 'Start a game to view tile details'}</p>
              {currentTile?.price ? <p>Cost: ${currentTile.price}</p> : null}
              {currentTile?.house_cost ? <p>House cost: ${currentTile.house_cost}</p> : null}
              {currentTile?.rent_tiers ? <p>Rent tiers: {currentTile.rent_tiers.join(' / ')}</p> : null}
              {currentTileOwnerName ? <p>Owned by: {currentTileOwnerName}</p> : null}
              {currentTile?.rule_text ? <p>Rule: {currentTile.rule_text}</p> : null}
              {currentTile?.outcomes?.length ? <p>Possible outcomes: {currentTile.outcomes.join(' • ')}</p> : null}
            </div>
            {Object.entries(positions).map(([playerId, tileIndex], idx) => (
              <div
                key={playerId}
                className={`token ${playerId === humanId ? 'human' : 'ai'}`}
                style={positionToPercent(Number(tileIndex), idx)}
              >
                {playerId === humanId ? 'H' : playerId.replace('ai-', 'A')}
              </div>
            ))}
          </div>
        </section>

        <section className="controls">
          <h3>Turn Controls</h3>
          {isAiThinking ? <p className="ai-runner">🤖 AI is making a move...</p> : null}
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
                      {aiPlayers.map((player) => (
                        <option key={player.id} value={player.id}>
                          {player.name}
                        </option>
                      ))}
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
            <button onClick={() => doAiMove(state?.current_player_id)} disabled={!state?.current_player_id || state?.current_player_id === humanId || isAiThinking}>
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
