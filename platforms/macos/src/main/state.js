// Shared mutable state — imported by reference so all modules see the same object.
const state = {
  mainWindow: null,
  flaskProcess: null,
  startupError: null,
  waitingForLocation: false,
};

module.exports = state;
