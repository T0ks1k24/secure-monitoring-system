import "./TitleBar.scss"

export default function TitleBar() {
  return (
    <div id="titlebar">
      <div className="title">Security System</div>
      <div className="buttons">
        <button onClick={() => window.windowAPI.minimize()}>—</button>
        <button onClick={() => window.windowAPI.maximize()}>☐</button>
        <button onClick={() => window.windowAPI.close()}>✕</button>
      </div>
    </div>
  )
}