const {app, BrowserWindow, Menu, ipcMain} = require("electron");
const path = require("path");

let mainWindow

function createWindow(){
    mainWindow = new BrowserWindow({
        width: 1000,
        height: 700, 
        frame: false,
        webPreferences: {
            preload: path.join(__dirname, "preload.js")
        }
    });

    Menu.setApplicationMenu(null)
    mainWindow.loadFile("index.html");
}

ipcMain.on("window:minimize", () => {
  mainWindow.minimize()
})

ipcMain.on("window:maximize", () => {
  if (mainWindow.isMaximized()) {
    mainWindow.unmaximize()
  } else {
    mainWindow.maximize()
  }
})

ipcMain.on("window:close", () => {
  mainWindow.close()
})

app.whenReady().then(() => {
    createWindow()

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow()
    })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})