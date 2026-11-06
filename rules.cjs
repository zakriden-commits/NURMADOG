/* Shared, deterministic match rules for browser and tests. */
(function (root) {
  const TARGET = 100;
  function createMatch() { return { benoit: 0, khabib: 0, winner: null }; }
  function vote(state, fighter) {
    if (state.winner || !['benoit', 'khabib'].includes(fighter)) return state;
    const next = { ...state, [fighter]: Math.min(TARGET, state[fighter] + 1) };
    if (next[fighter] === TARGET) next.winner = fighter;
    return next;
  }
  const api = { TARGET, createMatch, vote };
  if (typeof module !== 'undefined') module.exports = api;
  else root.BattleRules = api;
})(typeof window !== 'undefined' ? window : globalThis);
