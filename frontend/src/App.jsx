import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'

const humanId = 'human-1'
const HUMAN_SKILL_LEVEL = 0.5
const BASE_AI_SKILL_LEVEL = 0.6
const AI_SKILL_INCREMENT = 0.1
const MAX_AI_SKILL_LEVEL = 0.95

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

function getTileClassName(tile) {
  const groupClass = tile.color_group ? ` tile-group-${String(tile.color_group).replace(/_/g, '-')}` : ''
  return `tile tile-${tile.type}${groupClass}`
}

const PLAYER_COLORS = ['#22d3ee', '#f59e0b', '#4ade80', '#f87171']

const GROUP_COLORS = {
  brown: '#8b5a2b',
  light_blue: '#86d3f7',
  pink: '#e879f9',
  orange: '#fb923c',
  red: '#f87171',
  yellow: '#fde047',
  green: '#4ade80',
  dark_blue: '#2563eb',
  railroad: '#94a3b8',
  utility: '#94a3b8',
}

function getPlayerColor(playerId, players) {
  const idx = players.findIndex((p) => p.id === playerId)
  return idx >= 0 ? (PLAYER_COLORS[idx] ?? '#94a3b8') : '#94a3b8'
}

function getPlayerInitial(playerId, players) {
  const player = players.find((p) => p.id === playerId)
  return player ? player.name.charAt(0).toUpperCase() : '?'
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
  const [tradeOfferCash, setTradeOfferCash] = useState(0)
  const [tradeRequestCash, setTradeRequestCash] = useState(0)
  const [tradeOfferProperty, setTradeOfferProperty] = useState('')
  const [tradeRequestProperty, setTradeRequestProperty] = useState('')
  const [mortgageTarget, setMortgageTarget] = useState('')
  const [unmortgageTarget, setUnmortgageTarget] = useState('')
  const [buyHouseTarget, setBuyHouseTarget] = useState('')
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
      { id: humanId, name: 'You', is_human: true, skill_level: HUMAN_SKILL_LEVEL },
      ...Array.from({ length: selectedAiCount }, (_, idx) => ({
        id: `ai-${idx + 1}`,
        name: `AI ${idx + 1}`,
        is_human: false,
        skill_level: Math.min(MAX_AI_SKILL_LEVEL, BASE_AI_SKILL_LEVEL + idx * AI_SKILL_INCREMENT),
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

  async function refreshMoves(id = gameId, gameState = state) {
    if (!id || !gameState) return
    const current = gameState.current_player_id
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

  const doAiMove = useCallback(async (playerId) => {
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
    if (body.state.current_player_id === humanId) {
      const movesResponse = await fetch(`/games/${gameId}/moves/${humanId}`)
      const movesPayload = await movesResponse.json()
      if (movesResponse.ok) {
        setMoves(movesPayload.moves)
      }
    } else {
      setMoves([])
    }
  }, [gameId])

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
      doAiMove(current)
    }
  }, [state, gameId, isAiThinking, doAiMove])

  const boardTiles = state?.board?.tiles || []
  const positions = state?.board?.positions || {}
  const ownership = state?.board?.ownership || {}
  const mortgages = state?.board?.mortgages || {}
  const houses = state?.board?.houses || {}
  const monopoliesByPlayer = state?.board?.monopolies_by_player || {}
  const propertiesByPlayer = state?.board?.properties_by_player || {}
  const currentPlayerId = state?.current_player_id
  const currentTileIndex = currentPlayerId == null ? null : Number(positions[currentPlayerId] ?? 0)
  const currentTile = currentTileIndex === null ? null : boardTiles.find((tile) => tile.index === currentTileIndex)
  const currentTileOwnership = currentTile ? ownership[String(currentTile.index)] : null
  const currentTileOwnerName = currentTileOwnership
    ? players.find((player) => player.id === currentTileOwnership)?.name || currentTileOwnership
    : null

  const tilesMap = useMemo(() => {
    const map = {}
    boardTiles.forEach((t) => { map[t.index] = t })
    return map
  }, [boardTiles])

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
            <div key={player.id} className="money-row" style={{ borderLeftColor: getPlayerColor(player.id, players) }}>
              <span>{player.name}</span>
              <span>${state?.board?.money?.[player.id] ?? 0}</span>
            </div>
          ))}
        </div>

        {players.length > 0 && (
          <div className="properties-box">
            <h3>Properties</h3>
            {players.map((player) => {
              const playerProps = propertiesByPlayer[player.id] || []
              const playerMonopolies = monopoliesByPlayer[player.id] || []
              const color = getPlayerColor(player.id, players)
              return (
                <div key={player.id} className="player-props">
                  <div className="player-props-header" style={{ borderLeftColor: color }}>
                    <span>{player.name}</span>
                    {playerMonopolies.length > 0 && (
                      <span className="monopoly-count" title={`Monopolies: ${playerMonopolies.join(', ')}`}>
                        ★ {playerMonopolies.length}
                      </span>
                    )}
                  </div>
                  {playerProps.length === 0 ? (
                    <p className="no-props">None</p>
                  ) : (
                    <ul className="prop-list">
                      {playerProps.map((idx) => {
                        const tile = tilesMap[idx]
                        if (!tile) return null
                        const isMortgaged = Boolean(mortgages[String(idx)])
                        const houseCount = Number(houses[String(idx)] || 0)
                        const group = tile.color_group
                        const isMonopoly = group && playerMonopolies.includes(group)
                        return (
                          <li key={idx} className={`prop-item${isMortgaged ? ' prop-mortgaged' : ''}`}>
                            {group && (
                              <span
                                className="prop-color-dot"
                                style={{ background: GROUP_COLORS[group] || '#888' }}
                                title={group.replace(/_/g, ' ')}
                              />
                            )}
                            <span className="prop-name">{tile.name}</span>
                            {isMonopoly && <span className="prop-monopoly" title="Monopoly">★</span>}
                            {isMortgaged && <span className="prop-badge prop-badge-m" title="Mortgaged">M</span>}
                            {houseCount > 0 && (
                              <span className="prop-badge prop-badge-h" title={houseCount === 5 ? 'Hotel' : `${houseCount} house(s)`}>
                                {houseCount === 5 ? '🏨' : `🏠×${houseCount}`}
                              </span>
                            )}
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </div>
              )
            })}
          </div>
        )}
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
              const ownerId = ownership[String(tile.index)]
              const ownerColor = ownerId ? getPlayerColor(ownerId, players) : null
              const ownerInitial = ownerId ? getPlayerInitial(ownerId, players) : null
              const ownerName = ownerId ? (players.find((p) => p.id === ownerId)?.name || ownerId) : null
              const isMortgaged = Boolean(mortgages[String(tile.index)])
              const houseCount = Number(houses[String(tile.index)] || 0)
              const tileTitle = `${tile.name} (${tile.type})${ownerName ? ' — owned by ' + ownerName : ''}${isMortgaged ? ' [Mortgaged]' : ''}`
              return (
                <div
                  key={tile.index}
                  className={getTileClassName(tile)}
                  style={{ gridRow: row + 1, gridColumn: col + 1 }}
                  title={tileTitle}
                >
                  <span className="tile-index">{tile.index}</span>
                  <span className="tile-name">{tile.name}</span>
                  <span className="tile-price">
                    {tile.price ? `$${tile.price}` : tile.amount ? `Tax $${tile.amount}` : ''}
                  </span>
                  <div className="tile-status-row">
                    {ownerColor && (
                      <span
                        className="tile-owner-badge"
                        style={{ background: ownerColor }}
                        title={`Owned by ${ownerName}`}
                      >
                        {ownerInitial}
                      </span>
                    )}
                    {isMortgaged && <span className="tile-mortgage-badge" title="Mortgaged">M</span>}
                    {houseCount > 0 && (
                      <span className="tile-house-count" title={houseCount === 5 ? 'Hotel' : `${houseCount} house${houseCount > 1 ? 's' : ''}`}>
                        {houseCount === 5 ? 'H' : houseCount}
                      </span>
                    )}
                  </div>
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
                    🎲 Roll Dice
                  </button>
                )
              }

              if (move.action === 'accept_trade') {
                const offer = move.offer || {}
                const fromName = players.find((p) => p.id === offer.from_player_id)?.name || offer.from_player_id
                const offerPropName = offer.offer_property != null ? tilesMap[offer.offer_property]?.name : null
                const reqPropName = offer.request_property != null ? tilesMap[offer.request_property]?.name : null
                return (
                  <div key="incoming_trade" className="incoming-trade">
                    <p className="trade-from"><strong>{fromName}</strong> offers a trade:</p>
                    <ul className="trade-details">
                      {offer.offer_cash > 0 && <li>Gives you: ${offer.offer_cash}</li>}
                      {offerPropName && <li>Gives you: {offerPropName}</li>}
                      {offer.request_cash > 0 && <li>Wants from you: ${offer.request_cash}</li>}
                      {reqPropName && <li>Wants from you: {reqPropName}</li>}
                    </ul>
                    <div className="trade-respond-row">
                      <button className="btn-accept" onClick={() => runMove('accept_trade', { offer_index: 0 })}>✓ Accept</button>
                      <button className="btn-decline" onClick={() => runMove('decline_trade', { offer_index: 0 })}>✕ Decline</button>
                    </div>
                  </div>
                )
              }

              if (move.action === 'decline_trade') {
                return null
              }

              if (move.action === 'offer_trade') {
                const humanProps = (propertiesByPlayer[humanId] || []).map((idx) => tilesMap[idx]).filter(Boolean)
                const targetProps = (propertiesByPlayer[tradeTarget] || []).map((idx) => tilesMap[idx]).filter(Boolean)
                return (
                  <div key="offer_trade" className="trade-form">
                    <div className="trade-row">
                      <label>Trade with</label>
                      <select value={tradeTarget} onChange={(e) => setTradeTarget(e.target.value)}>
                        {aiPlayers.map((player) => (
                          <option key={player.id} value={player.id}>{player.name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="trade-row">
                      <label>Offer cash</label>
                      <input type="number" min="0" value={tradeOfferCash} onChange={(e) => setTradeOfferCash(Number(e.target.value))} />
                    </div>
                    <div className="trade-row">
                      <label>Offer property</label>
                      <select value={tradeOfferProperty} onChange={(e) => setTradeOfferProperty(e.target.value)}>
                        <option value="">None</option>
                        {humanProps.map((tile) => (
                          <option key={tile.index} value={String(tile.index)}>{tile.name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="trade-row">
                      <label>Request cash</label>
                      <input type="number" min="0" value={tradeRequestCash} onChange={(e) => setTradeRequestCash(Number(e.target.value))} />
                    </div>
                    <div className="trade-row">
                      <label>Request property</label>
                      <select value={tradeRequestProperty} onChange={(e) => setTradeRequestProperty(e.target.value)}>
                        <option value="">None</option>
                        {targetProps.map((tile) => (
                          <option key={tile.index} value={String(tile.index)}>{tile.name}</option>
                        ))}
                      </select>
                    </div>
                    <button onClick={() => runMove('offer_trade', {
                      to_player_id: tradeTarget,
                      offer_cash: tradeOfferCash,
                      request_cash: tradeRequestCash,
                      offer_property: tradeOfferProperty !== '' ? Number(tradeOfferProperty) : undefined,
                      request_property: tradeRequestProperty !== '' ? Number(tradeRequestProperty) : undefined,
                    })}>
                      📤 Send Trade Offer
                    </button>
                  </div>
                )
              }

              if (move.action === 'mortgage_property') {
                const props = move.properties || []
                if (props.length === 0) return null
                const target = mortgageTarget || String(props[0].index)
                const targetIdx = Number(target)
                return (
                  <div key="mortgage" className="action-form">
                    <select value={target} onChange={(e) => setMortgageTarget(e.target.value)}>
                      {props.map((p) => (
                        <option key={p.index} value={String(p.index)}>
                          {p.name} (+${p.mortgage_value})
                        </option>
                      ))}
                    </select>
                    <button disabled={isNaN(targetIdx)} onClick={() => runMove('mortgage_property', { property_index: targetIdx })}>
                      Mortgage
                    </button>
                  </div>
                )
              }

              if (move.action === 'unmortgage_property') {
                const props = move.properties || []
                if (props.length === 0) return null
                const target = unmortgageTarget || String(props[0].index)
                const targetIdx = Number(target)
                return (
                  <div key="unmortgage" className="action-form">
                    <select value={target} onChange={(e) => setUnmortgageTarget(e.target.value)}>
                      {props.map((p) => (
                        <option key={p.index} value={String(p.index)}>
                          {p.name} (${p.cost})
                        </option>
                      ))}
                    </select>
                    <button disabled={isNaN(targetIdx)} onClick={() => runMove('unmortgage_property', { property_index: targetIdx })}>
                      Unmortgage
                    </button>
                  </div>
                )
              }

              if (move.action === 'buy_house') {
                const props = move.properties || []
                if (props.length === 0) return null
                const target = buyHouseTarget || String(props[0].index)
                const targetIdx = Number(target)
                return (
                  <div key="buy_house" className="action-form">
                    <select value={target} onChange={(e) => setBuyHouseTarget(e.target.value)}>
                      {props.map((p) => (
                        <option key={p.index} value={String(p.index)}>
                          {p.name} (${p.cost}, {p.current_houses} 🏠)
                        </option>
                      ))}
                    </select>
                    <button disabled={isNaN(targetIdx)} onClick={() => runMove('buy_house', { property_index: targetIdx })}>
                      🏠 Build
                    </button>
                  </div>
                )
              }

              return (
                <button key={move.action} onClick={() => runMove(move.action)}>
                  {move.action.replace(/_/g, ' ')}
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
