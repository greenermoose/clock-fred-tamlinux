import QtQuick
import Quickshell
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
  environment: Model.pickEnv(envKeys, { PATH: "/usr/bin" }, function (name) { return Quickshell.env(name) })
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
  // Process has no default property, so the watchdog timers cannot be
  // declared as children; they live in object-valued properties instead.
  readonly property Timer termTimer: Timer {
    interval: proc.deadlineMs
    onTriggered: {
      proc.signal(15)
      proc.killTimer.restart()
    }
  }
  readonly property Timer killTimer: Timer {
    interval: 3000
    onTriggered: proc.signal(9)
  }
}
