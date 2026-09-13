import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as Model

// Date/time label for the bar, and the host for the calendar popup.
//
// Left click reveals the calendar — asking "what is the date?" is what a
// click on a clock means — right click walks the common label formats, and
// middle click opens the timezone picker.
BarWidget {
  id: root
  moduleName: "omarchy.clock"

  property date displayDate: clock.date

  readonly property string configuredFormat: vertical
    ? setting("verticalFormat", "HH\n—\nmm")
    : setting("format", "dddd HH:mm")
  readonly property string configuredAltFormat: vertical
    ? setting("verticalFormatAlt", "dd\nMMM\n'W'ww\n''yy")
    : setting("formatAlt", "d MMMM 'W'ww yyyy")

  readonly property var formatRing: Model.clockFormatRing(configuredFormat, configuredAltFormat, Model.clockFormats(vertical))

  // What the bar shows is what shell.json stores, so a cycled format is the
  // format from then on rather than something that reverts on restart.
  readonly property string activeFormat: configuredFormat
  readonly property string displayText: formatted(displayDate)
  readonly property var verticalLines: displayText.split("\n")

  readonly property int badgeMinutes: Number(setting("badgeMinutes", 60))
  property var eventsData: null
  property string countdownBadge: ""

  readonly property string fullLabel: countdownBadge !== ""
    ? displayText + " • " + countdownBadge
    : displayText

  readonly property string omarchyPath: Quickshell.env("OMARCHY_PATH") || ""
  readonly property var pyEnv: ["HOME", "TZ", "LANG", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"]
  readonly property var notifyEnv: ["HOME", "XDG_RUNTIME_DIR", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "OMARCHY_PATH"]

  readonly property alias manageProc: manageProc

  Launch {
    id: fetchProc
    exe: "/usr/bin/python3"
    args: [Model.helperPath("fetch-events.py")]
    envKeys: root.pyEnv
    deadlineMs: 60000
  }

  Launch {
    id: manageProc
    exe: "/usr/bin/python3"
    envKeys: root.pyEnv
    deadlineMs: 20000
  }

  Launch {
    id: notifyProc
    exe: root.omarchyPath !== "" ? root.omarchyPath + "/bin/omarchy-notification-send" : ""
    envKeys: root.notifyEnv
    deadlineMs: 10000
  }

  function notify(title, message) {
    if (!root.omarchyPath || root.omarchyPath === "") return
    var truncTitle = String(title || "").slice(0, 200)
    var truncMsg = String(message || "").slice(0, 200)
    notifyProc.args = [truncTitle, truncMsg]
    notifyProc.launch()
  }

  function runFetch() {
    if (!fetchProc.running) {
      fetchProc.launch()
    }
  }

  FileView {
    id: calendarsConfig
    path: Quickshell.env("HOME") + "/.config/fred.clock/calendars.json"
    watchChanges: true
    printErrors: false
    onFileChanged: root.runFetch()
  }

  FileView {
    id: localIcsWatcher
    path: Quickshell.env("HOME") + "/.config/fred.clock/local.ics"
    watchChanges: true
    printErrors: false
    onFileChanged: root.runFetch()
  }

  FileView {
    id: eventsCache
    path: Quickshell.env("HOME") + "/.cache/fred.clock/events.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.handleCacheLoaded(text())
    onLoadFailed: root.handleCacheLoaded("")
  }

  function handleCacheLoaded(content) {
    if (!content || content.trim() === "") {
      eventsData = null
      recalculateBadge()
      return
    }
    try {
      eventsData = JSON.parse(content)
    } catch (e) {
      eventsData = null
    }
    recalculateBadge()
  }

  function recalculateBadge() {
    if (badgeMinutes <= 0 || !eventsData) {
      countdownBadge = ""
      return
    }
    var nowSec = Math.floor(displayDate.getTime() / 1000)
    var evs = eventsData.events || []
    var candidate = null
    var minDiff = 999999
    var inProg = false

    for (var i = 0; i < evs.length; i++) {
      var ev = evs[i]
      if (ev.allDay) continue
      var start = ev.startTs
      var end = ev.endTs
      if (start <= nowSec && nowSec < end) {
        candidate = ev
        inProg = true
        break
      } else if (start > nowSec) {
        var diffMin = Math.floor((start - nowSec) / 60)
        if (diffMin <= badgeMinutes && diffMin < minDiff) {
          minDiff = diffMin
          candidate = ev
        }
      }
    }

    if (!candidate) {
      countdownBadge = ""
      return
    }

    var summary = candidate.summary || "Event"
    if (inProg) {
      countdownBadge = summary + " now"
    } else if (minDiff <= 0) {
      countdownBadge = summary + " now"
    } else {
      countdownBadge = summary + " in " + minDiff + "m"
    }
  }

  onDisplayDateChanged: recalculateBadge()

  Timer {
    id: fetchTimer
    interval: 15 * 60 * 1000
    running: true
    repeat: true
    onTriggered: root.runFetch()
  }

  Component.onCompleted: {
    runFetch()
  }

  function checkFetchOnOpen() {
    var nowSec = Math.floor(Date.now() / 1000)
    if (eventsData && eventsData.updatedAt && (nowSec - eventsData.updatedAt > 300)) {
      runFetch()
    } else if (!eventsData) {
      runFetch()
    }
  }

  function refresh() {
    displayDate = new Date()
    runFetch()
    if (panelLoader.item && panelLoader.item.refresh) panelLoader.item.refresh()
  }

  function cycleFormat() {
    var current = String(configuredFormat)
    var next = Model.nextClockFormat(formatRing, current)
    if (next === "" || next === current) return

    var entry = { id: root.moduleName }
    for (var key in root.settings) if (key !== "id") entry[key] = root.settings[key]
    entry[vertical ? "verticalFormat" : "format"] = next

    // Applied locally first so the label changes on the click itself; the
    // shell.json write comes back through the bar as the same value.
    root.settings = entry
    if (root.bar && root.bar.shell && typeof root.bar.shell.updateEntryInline === "function")
      root.bar.shell.updateEntryInline(root.moduleName, entry)
  }

  function formatted(date) {
    return Qt.formatDateTime(date, activeFormat.replace(/ww/g, Model.isoWeekLiteral(date.getFullYear(), date.getMonth(), date.getDate())))
  }

  // ---- Calendar popup. Shape contract for shell.summon/hide/toggle
  //      routing: Bar.findPanelWidget requires open/close/opened on the
  //      bar-widget root.
  readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false

  function open() {
    checkFetchOnOpen()
    if (panelLoader.item) panelLoader.item.open()
  }

  function close() {
    if (panelLoader.item) panelLoader.item.close()
  }

  function togglePanel() {
    checkFetchOnOpen()
    if (panelLoader.item) panelLoader.item.toggle()
  }

  function toggleWeekStart() {
    if (panelLoader.item) panelLoader.item.toggleWeekStart()
  }

  // The clock fills more slot than it paints a mark for, at both
  // orientations: horizontally it is a text label in a padded slot, so the
  // dot takes the label width; vertically it is a stack of icon-sized lines,
  // so the dot takes one line — the same mark every icon widget gets, rather
  // than a rule running the height of the whole stack.
  readonly property real openPanelIndicatorWidth: button.labelWidth
  readonly property real openPanelIndicatorHeight: Math.max(Style.space(10), Math.round(Style.bar.iconSlot * 0.55))

  // Forwarded so this widget can stand in for the panel as the bar's popout
  // identity: Bar.requestPopout prefers closeForPopoutSwitch over close, and
  // KeyboardPanel reads popoutSwitchClosing back off its owner.
  readonly property bool popoutSwitchClosing: panelLoader.item ? panelLoader.item.popoutSwitchClosing === true : false

  function closeForPopoutSwitch() {
    if (panelLoader.item) panelLoader.item.closeForPopoutSwitch()
  }

  function injectPanel() {
    var target = panelLoader.item
    if (!target) return
    if ("bar" in target) target.bar = root.bar
    if ("settings" in target) target.settings = root.settings
    if ("anchorItem" in target) target.anchorItem = button
    if ("hostWidget" in target) target.hostWidget = root
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  onBarChanged: injectPanel()
  onSettingsChanged: injectPanel()

  SystemClock {
    id: clock
    precision: SystemClock.Minutes
    onDateChanged: root.displayDate = date
  }

  Loader {
    id: panelLoader
    active: true
    source: Qt.resolvedUrl("Panel.qml")
    visible: false
    onLoaded: {
      root.injectPanel()
      Qt.callLater(root.injectPanel)
    }
  }

  IpcHandler {
    target: "omarchy.clock"

    function refresh(): void { root.broadcast("refresh") }
    function cycleFormat(): void { root.cycleFormat() }
    function toggleWeekStart(): void { root.toggleWeekStart() }
    function open(): void { root.open() }
    function close(): void { root.close() }
    function show(): void { root.open() }
    function hide(): void { root.close() }
    function toggle(): void { root.togglePanel() }
    function selectDate(key: string): void {
      if (panelLoader.item && panelLoader.item.selectDateString) {
        panelLoader.item.selectDateString(key)
        root.open()
      }
    }
    function copyAgenda(): void {
      if (panelLoader.item && panelLoader.item.copyDayMarkdown) {
        panelLoader.item.copyDayMarkdown()
      }
    }
    function openAddEvent(): void {
      root.open()
      if (panelLoader.item && panelLoader.item.openAddEvent) {
        panelLoader.item.openAddEvent()
      }
    }
    function closeAddEvent(): void {
      if (panelLoader.item && panelLoader.item.closeAddEvent) {
        panelLoader.item.closeAddEvent()
      }
    }
    function filterAccount(account: string): void {
      if (panelLoader.item) {
        panelLoader.item.selectedAccount = account
      }
    }
    function createEvent(summary: string, date: string, allDay: string, startTime: string, endTime: string, location: string): void {
      if (manageProc.running) {
        root.notify("Calendar Busy", "Another calendar update is in progress")
        return
      }
      var isAllDay = (allDay === "true" || allDay === "1" || allDay === "yes")
      var script = Model.helperPath("manage-event.py")
      var args = [script, "add", "--date", date, "--summary", summary]
      if (isAllDay) {
        args.push("--all-day")
      } else {
        args.push("--start-time", startTime || "09:00")
        args.push("--end-time", endTime || "10:00")
      }
      if (location && location.trim() !== "") {
        args.push("--location", location.trim())
      }
      manageProc.args = args
      manageProc.launch()
      root.notify("Event Added", summary + " (" + date + ")")
    }
    function deleteEvent(uid: string): void {
      if (manageProc.running) {
        root.notify("Calendar Busy", "Another calendar update is in progress")
        return
      }
      var script = Model.helperPath("manage-event.py")
      manageProc.args = [script, "delete", "--uid", uid]
      manageProc.launch()
      root.notify("Event Deleted", "Local event removed")
    }
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.vertical ? "" : root.fullLabel
    tooltipText: root.countdownBadge !== "" ? root.countdownBadge : ""
    labelVisible: !root.vertical
    hasVisualContent: root.vertical ? root.verticalLines.length > 0 : text !== ""
    fixedHeight: root.vertical ? root.verticalLines.length * Style.bar.iconSlot : -1
    horizontalMargin: 8.75
    verticalPadding: 8.75

    onPressed: function(b) {
      if (b === Qt.RightButton) root.cycleFormat()
      else if (b === Qt.MiddleButton) { if (root.bar) root.bar.run("omarchy-menu-timezone") }
      else root.togglePanel()
    }

    Column {
      visible: root.vertical
      anchors.fill: parent

      Repeater {
        model: root.verticalLines

        OpticalGlyph {
          required property string modelData
          width: button.width
          height: Style.bar.iconSlot
          text: modelData
          fontFamily: button.fontFamily
          fontSize: modelData.length > 3
            ? button.fontSize * 0.9
            : button.fontSize
          color: button.foreground
        }
      }
    }
  }
}
