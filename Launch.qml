import QtQuick
import Quickshell.Io
import "Model.js" as Model

// Every process the plugin starts goes through here: absolute executable,
// closed environment built from an allowlist, and a watchdog that TERMs
// then KILLs. All process launches are supervised through this component.
Process {
  id: proc
  property string exe                // absolute path, checked by caller
  property var args: []
  property var envKeys: []           // names copied from the shell's env if non-empty
  property int deadlineMs: 10000
  property string stdinText: ""
  command: exe !== "" ? [exe].concat(args) : []
  clearEnvironment: true
  environment: Model.pickEnv(envKeys, { PATH: "/usr/bin" })
  stdinEnabled: stdinText !== ""
  function launch() {
    if (!running && exe !== "") {
      stdinEnabled = (stdinText !== "")
      running = true
    }
  }
  onStarted: {
    if (stdinText !== "") {
      write(stdinText)
      stdinEnabled = false
    }
    termTimer.restart()
  }
  onExited: {
    termTimer.stop()
    killTimer.stop()
  }
  Timer {
    id: termTimer
    interval: proc.deadlineMs
    onTriggered: {
      proc.signal(15)
      killTimer.restart()
    }
  }
  Timer {
    id: killTimer
    interval: 3000
    onTriggered: proc.signal(9)
  }
}
