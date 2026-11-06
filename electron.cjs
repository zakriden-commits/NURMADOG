const { app, BrowserWindow, Menu } = require('electron');
app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  const win = new BrowserWindow({ width: 1440, height: 1040, minWidth: 460, minHeight: 640, backgroundColor: '#0b0c10', icon: require('path').join(__dirname, 'assets/logo.png'), title: 'САСНЫЙ — Битва чата', webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true } });
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-navigate', e => e.preventDefault());
  win.loadFile('index.html');
});
app.on('window-all-closed', () => app.quit());
