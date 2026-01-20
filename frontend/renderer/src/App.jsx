import "./styles/global.scss"
import TitleBar from './components/TitleBar/TitleBar'

export default function App() {
  return (
    <>
      <TitleBar />

      <div className="app-content">
        <div className="top-bar">
          <h1>Події безпеки</h1>

          <div className="risk">
            Рівень ризику:{" "}
            <span className="risk-low">LOW</span>
          </div>
        </div>

        <div className="container">
          {/* VIDEO */}
          <div className="video-wrapper">
            <img
              src="http://127.0.0.1:8000/video"
              alt="Video stream"
            />
          </div>

          {/* CONTROL PANEL */}
          <div className="control-panel">
            <h2>Керування</h2>

            <button className="start-btn">
              Почати моніторинг
            </button>

            <h3>Події</h3>
            <ul id="events">
              {/* сюди пізніше підключимо SSE */}
            </ul>
          </div>
        </div>
      </div>
    </>
  )
}