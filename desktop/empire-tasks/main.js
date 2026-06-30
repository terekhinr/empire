const { app, BrowserWindow, shell } = require("electron");

const APP_URL = process.env.EMPIRE_TASKS_URL || "https://neverretire.ru/tasks/";

function createWindow() {
  const win = new BrowserWindow({
    width: 480,
    height: 900,
    title: "Empire",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  win.loadURL(APP_URL);
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

app.whenReady().then(createWindow);
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
