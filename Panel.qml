import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as Model

// The clock's calendar popup: a month grid with ISO week numbers, built to
// sit beside the weather panel — same hero-over-detail composition, same
// spacing scale, same small-caps labels.
//
// The grid is a read-out rather than a picker: today is the only marked
// day, and the only thing that moves is which month is on screen —
// chevrons, the scroll wheel, and the arrow keys all step it.
//
// BarWidget.qml owns the bar label and hands this panel the button to
// anchor against.
Panel {
  id: root
  moduleName: "omarchy.clock"
  ipcTarget: "omarchy.clock"
  manageIpc: false

  property var anchorItem: null

  // The bar tracks the widget mounted in its slot — BarWidget.qml — not this
  // nested panel. Everything the bar identifies a panel by has to be that
  // widget: the popout coordinator (and with it the open-panel dot under the
  // pill) compares against `slot.activeItem`, and switchPanelFrom looks the
  // slot up the same way.
  property var hostWidget: null
  readonly property var barIdentity: hostWidget || root

  // ---- Today. SystemClock keeps this honest across midnight so the
  //      highlight rolls over without the panel being reopened.
  property date today: new Date()
  readonly property string todayKey: Model.keyForDate(today)

  // Selected date for agenda display (defaults to today)
  property date selectedDate: today
  property string selectedDateKey: Model.keyForDate(selectedDate)

  property var eventsData: null
  property var eventsByDate: ({})
  property var accountList: ["All"]
  property string selectedAccount: "All"
  readonly property var dayFilteredEvents: root.getEventsForDate(selectedDateKey, selectedAccount)

  // The month on screen. Stepping moves this and nothing else: the grid is
  // a read-out, not a picker, so there is no per-day cursor to keep in sync.
  property int viewYear: today.getFullYear()
  property int viewMonth: today.getMonth()

  readonly property date viewDate: new Date(viewYear, viewMonth, 1)
  readonly property bool viewingCurrentMonth: viewYear === today.getFullYear() && viewMonth === today.getMonth()

  // Pinned to today, not to the month being browsed — stepping through the
  // calendar does not change how much of the year is gone.
  readonly property real yearDone: Model.yearProgress(today.getFullYear(), today.getMonth(), today.getDate())
  readonly property int yearDonePercent: Model.yearProgressPercent(today.getFullYear(), today.getMonth(), today.getDate())

  // Memento mori, for anyone who goes looking: double-tapping the year bar
  // asks for a birth year and a life expectancy, and a second bar tracks one
  // against the other. A birth year rather than an age, so it keeps counting
  // on its own. Without one the bar stays hidden.
  readonly property int birthYear: Model.parseBirthYear(setting("birthYear", 0), today.getFullYear())
  readonly property int age: Model.ageFromBirthYear(birthYear, today.getFullYear())
  readonly property int lifeExpectancy: Model.parseLifeExpectancy(setting("lifeExpectancy", 0))
  readonly property real lifeDone: Model.lifeProgress(age, lifeExpectancy)
  readonly property int lifeDonePercent: Model.lifeProgressPercent(age, lifeExpectancy)
  property bool editingLife: false

  // Unset falls through to the locale's own first day, so a fresh install
  // starts out matching the rest of the desktop rather than a hardcoded
  // convention. Clicking the grid's "W" heading writes the choice back to
  // shell.json.
  readonly property int weekStart: Model.normalizedWeekStart(setting("weekStartDay", null), Qt.locale().firstDayOfWeek)
  // The interface is English throughout, so day names are not taken from the
  // system locale. Where the week starts still is: that is a regional
  // convention rather than a translation, and it stays overridable above.
  readonly property var labelLocale: Qt.locale("en_US")
  readonly property string nextWeekStartLabel: labelLocale.dayName(Model.toggledWeekStart(weekStart), Locale.LongFormat)
  readonly property var weekdays: Model.weekdayOrder(weekStart)
  readonly property var weeks: Model.monthGrid(viewYear, viewMonth, weekStart, todayKey)


  // Guarded so the widget renders before the bar is injected (the bar-widget
  // contract instantiates it bare).
  readonly property color contentForeground: bar ? bar.foreground : Color.foreground
  readonly property string contentFontFamily: bar ? bar.fontFamily : Style.font.family

  readonly property int cellWidth: Style.space(52)
  readonly property int cellHeight: Style.space(34)
  readonly property int cellSpacing: Style.space(2)
  readonly property int weekColumnWidth: Style.space(32)
  readonly property int gutterWidth: Style.space(14)

  function open() {
    root.today = new Date()
    if (eventsCache) eventsCache.reload()
    root.controller.show()
    Qt.callLater(function() {
      if (root.opened) setCenterHoverRevealSuppressed(true)
    })
  }

  function close() {
    setCenterHoverRevealSuppressed(false)
    // Dismissing the panel mid-edit would otherwise leave the inputs up,
    // waiting behind a closed popup for the next time it opens.
    if (root.editingLife) root.cancelEditingLife()
    root.controller.hide()
  }

  function toggle() {
    if (root.opened) root.close()
    else root.open()
  }

  function switchPanel(direction) {
    if (root.bar && typeof root.bar.switchPanelFrom === "function")
      return root.bar.switchPanelFrom(root.barIdentity, direction)
    return false
  }

  // Summoning by hotkey moves no pointer, so a hover the bar was still
  // holding must not keep the center indicators revealed behind the panel.
  function setCenterHoverRevealSuppressed(value) {
    if (root.bar && typeof root.bar.setCenterHoverRevealSuppressed === "function")
      root.bar.setCenterHoverRevealSuppressed(value)
    else if (root.bar && "centerHoverRevealSuppressed" in root.bar)
      root.bar.centerHoverRevealSuppressed = value
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
      root.eventsData = null
      root.eventsByDate = {}
      root.accountList = ["All"]
      return
    }
    try {
      var parsed = JSON.parse(content)
      root.eventsData = parsed
      var index = root.buildEventsIndex(parsed.events || [])
      root.eventsByDate = index.byDate
      root.accountList = index.accounts
    } catch (e) {
      root.eventsData = null
      root.eventsByDate = {}
      root.accountList = ["All"]
    }
  }

  function buildEventsIndex(events) {
    var byDate = {}
    var accounts = {}
    if (!events) return { byDate: byDate, accounts: ["All"] }

    for (var i = 0; i < events.length; i++) {
      var ev = events[i]
      if (ev.account) accounts[ev.account] = true
      var startKey = ev.dateKey
      var endKey = ev.endDateKey || startKey

      var sParts = startKey.split("-").map(Number)
      var eParts = endKey.split("-").map(Number)
      var cur = new Date(sParts[0], sParts[1] - 1, sParts[2])
      var end = new Date(eParts[0], eParts[1] - 1, eParts[2])

      var count = 0
      while (cur <= end && count < 366) {
        var k = Model.keyForDate(cur)
        if (!byDate[k]) byDate[k] = []
        byDate[k].push(ev)
        cur.setDate(cur.getDate() + 1)
        count++
      }
    }
    var accList = ["All"]
    for (var acc in accounts) {
      accList.push(acc)
    }
    return { byDate: byDate, accounts: accList }
  }

  function getEventsForDate(dateKey, accountFilter) {
    var list = (root.eventsByDate && root.eventsByDate[dateKey]) || []
    if (!accountFilter || accountFilter === "All") return list
    var filtered = []
    for (var i = 0; i < list.length; i++) {
      if (list[i].account === accountFilter) {
        filtered.push(list[i])
      }
    }
    return filtered
  }

  function dotColors(events) {
    if (!events || events.length === 0) return []
    var colors = []
    for (var i = 0; i < events.length; i++) {
      var c = events[i].color || "#4285f4"
      if (colors.indexOf(c) === -1) {
        colors.push(c)
        if (colors.length >= 4) break
      }
    }
    return colors
  }

  function selectDateKey(key, year, month, day) {
    root.selectedDateKey = key
    root.selectedDate = new Date(year, month, day)
    if (year !== root.viewYear || month !== root.viewMonth) {
      root.viewYear = year
      root.viewMonth = month
    }
  }

  function selectDateString(key) {
    if (!key || typeof key !== "string") return
    var parts = key.split("-").map(Number)
    if (parts.length === 3) {
      selectDateKey(key, parts[0], parts[1] - 1, parts[2])
      if (!root.opened) {
        root.controller.show()
      }
    }
  }

  function openMeetingUrl(url) {
    if (!url || typeof url !== "string") return
    var trimmed = url.trim()
    if (!/^https?:\/\/[^\s<>'"]+$/i.test(trimmed)) return
    Quickshell.execDetached(["xdg-open", trimmed])
  }

  function copyDayMarkdown() {
    var evs = root.dayFilteredEvents
    var dateTitle = Qt.formatDate(root.selectedDate, "dddd, MMMM d, yyyy")
    var md = "### " + dateTitle + "\n\n"
    if (!evs || evs.length === 0) {
      md += "_No events scheduled._\n"
    } else {
      for (var i = 0; i < evs.length; i++) {
        var ev = evs[i]
        var timePart = ev.timeStr || (ev.allDay ? "All Day" : "")
        var line = "- **" + timePart + "**: " + (ev.summary || "Event")
        if (ev.meetingUrl) {
          line += " ([Join](" + ev.meetingUrl + "))"
        }
        if (ev.location && ev.location !== ev.meetingUrl) {
          line += " — " + ev.location
        }
        md += line + "\n"
      }
    }

    Quickshell.execDetached(["bash", "-c", "printf %s " + Util.shellQuote(md) + " | wl-copy"])
    Quickshell.execDetached(["omarchy-notification-send", "Agenda Copied", dateTitle + " agenda copied to clipboard"])
  }

  property bool addEventOpen: false
  readonly property string manageScript: Quickshell.env("HOME") + "/.config/omarchy/plugins/fred.clock/manage-event.py"

  function toggleAddEvent() {
    root.addEventOpen = !root.addEventOpen
  }

  function openAddEvent() {
    root.addEventOpen = true
  }

  function closeAddEvent() {
    root.addEventOpen = false
  }

  function submitNewEvent(title, allDay, startTime, endTime, location, targetDate) {
    if (!title || !title.trim()) return
    var finalDate = targetDate || root.selectedDateKey || root.todayKey
    var args = [
      "python3",
      root.manageScript,
      "add",
      "--date", finalDate,
      "--summary", title.trim()
    ]
    if (allDay === true || allDay === "true") {
      args.push("--all-day")
    } else {
      args.push("--start-time", startTime || "09:00")
      args.push("--end-time", endTime || "10:00")
    }
    if (location && location.trim()) {
      args.push("--location", location.trim())
    }
    Quickshell.execDetached(args)
    Quickshell.execDetached(["omarchy-notification-send", "Event Added", title.trim() + " (" + finalDate + ")"])
    root.closeAddEvent()
  }

  function deleteLocalEvent(eventUid) {
    if (!eventUid) return
    var args = [
      "python3",
      root.manageScript,
      "delete",
      "--uid", eventUid
    ]
    Quickshell.execDetached(args)
    Quickshell.execDetached(["omarchy-notification-send", "Event Deleted", "Local event removed"])
  }

  function refresh() {
    root.today = new Date()
    root.goToToday()
    if (eventsCache) eventsCache.reload()
  }

  function goToToday() {
    root.viewYear = today.getFullYear()
    root.viewMonth = today.getMonth()
    root.selectedDate = root.today
    root.selectedDateKey = root.todayKey
  }

  function moveMonth(delta) {
    var next = Model.stepMonth(viewYear, viewMonth, delta)
    root.viewYear = next.year
    root.viewMonth = next.month
  }

  function moveYear(delta) {
    moveMonth(delta * 12)
  }

  // Applied locally first so the panel redraws on the click itself; the
  // shell.json write comes back through the bar as the same value. With no
  // writable entry (the widget is not in the layout) it stays a session-only
  // preference rather than doing nothing. The host widget builds its own
  // entry when the label format is cycled, so it has to be kept in step or
  // it would write this key straight back out from a stale copy.
  function persistSettings(values) {
    var entry = { id: root.moduleName }
    for (var existing in root.settings) if (existing !== "id") entry[existing] = root.settings[existing]
    for (var key in values) entry[key] = values[key]

    root.settings = entry
    if (root.hostWidget && "settings" in root.hostWidget) root.hostWidget.settings = entry
    if (root.bar && root.bar.shell && typeof root.bar.shell.updateEntryInline === "function")
      root.bar.shell.updateEntryInline(root.moduleName, entry)
  }

  function setWeekStart(day) {
    var next = Model.normalizedWeekStart(day, root.weekStart)
    if (next === root.weekStart) return
    persistSettings({ weekStartDay: Model.weekStartSettingName(next) })
  }

  function startEditingLife() {
    root.editingLife = true
    Qt.callLater(function() {
      bornField.text = root.birthYear > 0 ? String(root.birthYear) : ""
      expectancyField.text = String(root.lifeExpectancy)
      bornField.selectAll()
      bornField.forceActiveFocus()
    })
  }

  function cancelEditingLife() {
    root.editingLife = false
    Qt.callLater(function() { if (keyCatcher) keyCatcher.forceActiveFocus() })
  }

  // Shared by both fields: Tab hops to the other one, Enter commits the pair,
  // Escape drops the lot.
  function handleLifeKey(event, other) {
    if (event.key === Qt.Key_Escape) {
      root.cancelEditingLife()
      event.accepted = true
    } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
      root.commitLife()
      event.accepted = true
    } else if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
      other.selectAll()
      other.forceActiveFocus()
      event.accepted = true
    }
  }

  // Double-tapping the life bar puts it away again. The expectancy stays in
  // the config so setting a birth year again brings your own number back
  // rather than the default.
  function clearLife() {
    if (root.birthYear <= 0) return
    persistSettings({ birthYear: 0 })
  }

  function commitLife() {
    var born = Model.parseBirthYear(bornField.text, today.getFullYear())
    var span = Model.parseLifeExpectancy(expectancyField.text)
    if (born !== root.birthYear || span !== root.lifeExpectancy)
      persistSettings({ birthYear: born, lifeExpectancy: span })
    cancelEditingLife()
  }

  function toggleWeekStart() {
    setWeekStart(Model.toggledWeekStart(root.weekStart))
  }

  // English short day names, matching the rest of the interface.
  function weekdayLabel(weekday) {
    return String(labelLocale.dayName(weekday, Locale.ShortFormat)).toUpperCase()
  }

  SystemClock {
    id: clock
    precision: SystemClock.Minutes
    onDateChanged: {
      if (Model.keyForDate(clock.date) === String(root.todayKey)) return
      var followToday = root.viewingCurrentMonth
      var wasOnToday = root.selectedDateKey === root.todayKey
      root.today = clock.date
      if (followToday) root.goToToday()
      else if (wasOnToday) {
        root.selectedDate = root.today
        root.selectedDateKey = root.todayKey
      }
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.barIdentity
    bar: root.bar
    open: root.opened
    centerOnBar: true
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(560))
    contentHeight: panel.fittedContentHeight(calendarColumn.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      blocked: root.editingLife
      onMoveRequested: function(dx, dy) {
        if (dx !== 0) root.moveMonth(dx)
        if (dy !== 0) root.moveYear(dy)
      }
      onActivateRequested: root.goToToday()
      onCloseRequested: {
        if (root.addEventOpen) {
          root.closeAddEvent()
        } else {
          root.close()
        }
      }
      onTabRequested: function(direction) { root.switchPanel(direction) }
      onTextKey: function(t) {
        if (t === "[") root.moveMonth(-1)
        else if (t === "]") root.moveMonth(1)
        else if (t === "{") root.moveYear(-1)
        else if (t === "}") root.moveYear(1)
        else if (t === "t" || t === "T") root.goToToday()
        else if (t === "w" || t === "W") root.toggleWeekStart()
        else if (t === "y" || t === "Y") root.copyDayMarkdown()
        else if (t === "n" || t === "N" || t === "a" || t === "A") root.openAddEvent()
      }

      Flickable {
        id: calendarScroll
        anchors.fill: parent
        contentWidth: calendarColumn.width
        contentHeight: calendarColumn.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height || contentWidth > width

        Column {
          id: calendarColumn
          // Never narrower than the grid. The popup width is capped to what
          // the screen allows, and a fixed seven-column grid would otherwise
          // lose its last days off the edge instead of scrolling.
          width: Math.max(calendarScroll.width, gridColumn.width)
          spacing: Style.space(8)

          // ---- Hero: today, centered. Once the view has stepped back
          //      it is also the way home — clicking the date you are
          //      looking for beats hunting for a reset button.
          Item {
            width: parent.width
            height: heroRow.height

            Row {
              id: heroRow
              anchors.horizontalCenter: parent.horizontalCenter
              spacing: Style.space(22)

              Text {
                // Baseline-aligned, not center-aligned: "July 26" carries a
                // descender, so centering the two boxes leaves the icon
                // sitting visibly low against the digits.
                anchors.baseline: heroDate.baseline
                text: "󰃭"
                color: heroMouse.containsMouse
                  ? Style.hoverStateColor(root.contentForeground, Color.accent)
                  : root.contentForeground
                font.family: root.contentFontFamily
                // Decorative, and deliberately outside the Style.font.*
                // scale. Sized so the glyph reads at the cap height of the
                // date beside it rather than towering over it.
                font.pixelSize: 48
              }

              Text {
                id: heroDate
                textFormat: Text.PlainText
                anchors.verticalCenter: parent.verticalCenter
                text: Qt.formatDate(root.today, "MMMM d")
                color: heroMouse.containsMouse
                  ? Style.hoverStateColor(root.contentForeground, Color.accent)
                  : root.contentForeground
                font.family: root.contentFontFamily
                font.pixelSize: 52
                font.bold: true
              }
            }

            MouseArea {
              id: heroMouse
              x: heroRow.x
              y: heroRow.y
              width: heroRow.width
              height: heroRow.height
              enabled: !root.viewingCurrentMonth
              hoverEnabled: enabled
              cursorShape: Qt.PointingHandCursor
              onClicked: root.goToToday()

              PanelToolTip {
                visible: heroMouse.containsMouse
                text: "Back to today"
                fontFamily: root.contentFontFamily
              }
            }
          }

          // ---- Year progress, doubling as the rule under the hero:
          //      a plain hairline said nothing, and whole days done
          //      over days in the year says the same thing louder.
          Item {
            width: parent.width
            height: yearBlock.y + yearBlock.height

            Item {
              id: yearBlock
              y: Style.space(6)
              anchors.horizontalCenter: parent.horizontalCenter
              width: gridColumn.width
              height: Math.max(yearLabel.implicitHeight, Style.space(10))

              TapHandler {
                enabled: !root.editingLife
                onDoubleTapped: root.startEditingLife()
              }

              Row {
                visible: root.editingLife
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                spacing: Style.space(10)

                Text {
                  anchors.verticalCenter: parent.verticalCenter
                  text: "BORN"
                  color: Qt.darker(root.contentForeground, 1.5)
                  font.family: root.contentFontFamily
                  font.pixelSize: Style.font.bodySmall
                  font.letterSpacing: 1
                }

                TextField {
                  id: bornField
                  width: Style.space(70)
                  anchors.verticalCenter: parent.verticalCenter
                  placeholderText: "year"
                  foreground: root.contentForeground
                  font.family: root.contentFontFamily
                  inputMethodHints: Qt.ImhDigitsOnly

                  Keys.onPressed: function(event) { root.handleLifeKey(event, expectancyField) }
                }

                Text {
                  anchors.verticalCenter: parent.verticalCenter
                  anchors.verticalCenterOffset: 0
                  leftPadding: Style.space(6)
                  text: "LIVE TO"
                  color: Qt.darker(root.contentForeground, 1.5)
                  font.family: root.contentFontFamily
                  font.pixelSize: Style.font.bodySmall
                  font.letterSpacing: 1
                }

                TextField {
                  id: expectancyField
                  width: Style.space(60)
                  anchors.verticalCenter: parent.verticalCenter
                  placeholderText: "90"
                  foreground: root.contentForeground
                  font.family: root.contentFontFamily
                  inputMethodHints: Qt.ImhDigitsOnly

                  Keys.onPressed: function(event) { root.handleLifeKey(event, bornField) }
                }
              }

              Text {
                id: yearLabel
                textFormat: Text.PlainText
                visible: !root.editingLife
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: root.today.getFullYear()
                color: Qt.darker(root.contentForeground, 1.5)
                font.family: root.contentFontFamily
                font.pixelSize: Style.font.bodySmall
                font.letterSpacing: 1
              }

              Text {
                id: yearPercent
                textFormat: Text.PlainText
                visible: !root.editingLife
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: root.yearDonePercent + "%"
                color: root.contentForeground
                font.family: root.contentFontFamily
                font.pixelSize: Style.font.bodySmall
              }

              Rectangle {
                id: yearTrack
                visible: !root.editingLife
                anchors.left: yearLabel.right
                anchors.right: yearPercent.left
                anchors.leftMargin: Style.space(12)
                anchors.rightMargin: Style.space(12)
                anchors.verticalCenter: parent.verticalCenter
                height: Style.space(6)
                radius: Style.cornerRadius > 0 ? height / 2 : 0
                color: Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.12)

                Rectangle {
                  width: Math.round(parent.width * root.yearDone)
                  height: parent.height
                  radius: parent.radius
                  color: Style.selectedStateColor(root.contentForeground, Color.accent)

                  Behavior on width { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                }
              }
            }
          }

          // ---- Memento mori. Only here once someone has gone looking and
          //      given an age; the same rail as the year above it, measured
          //      against a nominal lifetime.
          Item {
            visible: root.birthYear > 0
            width: parent.width
            height: visible ? lifeBlock.height : 0

            Item {
              id: lifeBlock
              anchors.horizontalCenter: parent.horizontalCenter
              width: gridColumn.width
              height: Math.max(lifeLabel.implicitHeight, Style.space(10))

              Text {
                id: lifeLabel
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "LIFE"
                color: Qt.darker(root.contentForeground, 1.5)
                font.family: root.contentFontFamily
                font.pixelSize: Style.font.bodySmall
                font.letterSpacing: 1
              }

              Text {
                id: lifePercent
                textFormat: Text.PlainText
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: root.lifeDonePercent + "%"
                color: root.contentForeground
                font.family: root.contentFontFamily
                font.pixelSize: Style.font.bodySmall
              }

              Rectangle {
                anchors.left: lifeLabel.right
                anchors.right: lifePercent.left
                anchors.leftMargin: Style.space(12)
                anchors.rightMargin: Style.space(12)
                anchors.verticalCenter: parent.verticalCenter
                height: Style.space(6)
                radius: Style.cornerRadius > 0 ? height / 2 : 0
                color: Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.12)

                Rectangle {
                  width: Math.round(parent.width * root.lifeDone)
                  height: parent.height
                  radius: parent.radius
                  color: Style.selectedStateColor(root.contentForeground, Color.accent)

                  Behavior on width { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                }
              }

              TapHandler {
                onDoubleTapped: root.clearLife()
              }

              MouseArea {
                id: lifeMouse
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.NoButton

                PanelToolTip {
                  visible: lifeMouse.containsMouse
                  text: "Memento Mori"
                  fontFamily: root.contentFontFamily
                }
              }
            }
          }

          // ---- Month grid: week numbers down a gutter on the left, then
          //      the seven day columns. Always six rows, so the popup is
          //      exactly as tall in February as it is in August.
          Item {
            width: parent.width
            height: gridColumn.y + gridColumn.height

            WheelHandler {
              onWheel: function(event) {
                // Horizontal wheels and touchpad side-scrolls report y === 0;
                // without this they would every one read as "next month".
                if (event.angleDelta.y === 0) return
                root.moveMonth(event.angleDelta.y > 0 ? -1 : 1)
              }
            }

            Column {
              id: gridColumn
              // The meter above is a solid rule; the grid needs room to
              // read as its own block rather than hanging off it.
              y: Style.space(18)
              anchors.horizontalCenter: parent.horizontalCenter
              spacing: Style.space(3)

              Row {
                id: headerRow
                spacing: root.cellSpacing

                // The week-number heading doubles as the week-start toggle.
                // It is the one control in the panel whose meaning is not
                // self-evident, so it carries a tooltip naming the day the
                // click will switch to.
                Rectangle {
                  width: root.weekColumnWidth
                  height: Style.space(16)
                  radius: Style.cornerRadius
                  color: weekStartMouse.containsMouse
                    ? Style.hoverFillFor(root.contentForeground, Color.accent)
                    : "transparent"

                  Text {
                    anchors.centerIn: parent
                    text: "W"
                    color: weekStartMouse.containsMouse
                      ? Style.hoverStateColor(root.contentForeground, Color.accent)
                      : Qt.darker(root.contentForeground, 1.9)
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.caption
                    font.letterSpacing: 1
                    font.bold: true
                  }

                  MouseArea {
                    id: weekStartMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.toggleWeekStart()
                  }

                  PanelToolTip {
                    visible: weekStartMouse.containsMouse
                    text: "Start weeks on " + root.nextWeekStartLabel
                    fontFamily: root.contentFontFamily
                  }
                }

                Item {
                  width: root.gutterWidth
                  height: Style.space(16)
                }

                Repeater {
                  model: root.weekdays

                  Text {
                    textFormat: Text.PlainText
                    required property var modelData
                    width: root.cellWidth
                    height: Style.space(16)
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    text: root.weekdayLabel(modelData)
                    color: Qt.darker(root.contentForeground, 1.5)
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.caption
                    font.letterSpacing: 1
                    font.bold: true
                  }
                }
              }

              Repeater {
                model: root.weeks

                Row {
                  required property var modelData
                  spacing: root.cellSpacing

                  Text {
                    textFormat: Text.PlainText
                    width: root.weekColumnWidth
                    height: root.cellHeight
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    text: modelData.week
                    color: Qt.darker(root.contentForeground, 1.9)
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.caption
                  }

                  Item {
                    width: root.gutterWidth
                    height: root.cellHeight
                  }

                  Repeater {
                    model: modelData.days

                    Rectangle {
                      required property var modelData

                      readonly property bool isSelected: modelData.key === root.selectedDateKey
                      readonly property var dayEvents: (root.eventsByDate && root.eventsByDate[modelData.key]) || []

                      width: root.cellWidth
                      height: root.cellHeight
                      radius: Style.cornerRadius
                      color: isSelected
                        ? Style.selectedFillFor(root.contentForeground, Color.accent)
                        : (cellMouse.containsMouse ? Style.hoverFillFor(root.contentForeground, Color.accent) : "transparent")
                      border.width: modelData.today ? Style.spacing.hairline : (isSelected ? Style.spacing.hairline : 0)
                      border.color: modelData.today
                        ? Style.normalBorderFor(root.contentForeground, Color.accent)
                        : (isSelected ? Style.selectedStateColor(root.contentForeground, Color.accent) : "transparent")

                      Text {
                        textFormat: Text.PlainText
                        anchors.centerIn: parent
                        anchors.verticalCenterOffset: dayEvents.length > 0 ? -Style.space(3) : 0
                        text: modelData.day
                        color: isSelected
                          ? Style.selectedStateColor(root.contentForeground, Color.accent)
                          : (modelData.inMonth
                              ? (modelData.weekend ? Qt.darker(root.contentForeground, 1.45) : root.contentForeground)
                              : Qt.darker(root.contentForeground, 2.2))
                        font.family: root.contentFontFamily
                        font.pixelSize: Style.font.body
                        font.bold: modelData.today || isSelected
                      }

                      Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: Style.space(3)
                        spacing: Style.space(2)
                        visible: dayEvents.length > 0

                        Repeater {
                          model: root.dotColors(dayEvents)
                          Rectangle {
                            required property string modelData
                            width: Style.space(4)
                            height: Style.space(4)
                            radius: width / 2
                            color: modelData
                          }
                        }
                      }

                      MouseArea {
                        id: cellMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.selectDateKey(modelData.key, modelData.year, modelData.month, modelData.day)
                      }
                    }
                  }
                }
              }
            }

            // Hairline down the week-number gutter, drawn only beside the
            // day rows so it does not cut through the header band.
            Rectangle {
              x: gridColumn.x + root.weekColumnWidth + root.cellSpacing + Math.round((root.gutterWidth - width) / 2)
              y: gridColumn.y + headerRow.height + gridColumn.spacing
              width: Style.spacing.hairline
              height: gridColumn.height - headerRow.height - gridColumn.spacing
              color: root.contentForeground
              opacity: 0.1
            }
          }

          // ---- Month stepping, spanning the grid it drives. The chevrons
          //      sit on the grid's outer bounds, the same edges the year
          //      rail above uses, so the row reads as the panel's other
          //      full-width rail instead of a cluster floating in space.
          //      The label is centered and fixed-width, so it holds still
          //      from "MAY" to "SEPTEMBER".
          Item {
            width: parent.width
            height: monthNav.height

            Item {
              id: monthNav
              anchors.horizontalCenter: parent.horizontalCenter
              width: gridColumn.width
              height: monthLabel.implicitHeight + Style.space(10)

              Text {
                id: monthLabel
                textFormat: Text.PlainText
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                // Fixed width so the chevrons hold still between a
                // "MAY 2026" and a "SEPTEMBER 2026".
                width: Style.space(130)
                horizontalAlignment: Text.AlignHCenter
                text: Qt.formatDate(root.viewDate, "MMMM yyyy").toUpperCase()
                color: Qt.darker(root.contentForeground, 1.4)
                font.family: root.contentFontFamily
                font.pixelSize: Style.font.body
                font.letterSpacing: 1
              }

              PanelActionButton {
                // Pulled out by the button's own padding so the glyph, not
                // its hit box, lines up with the "2026" on the year rail.
                anchors.left: parent.left
                anchors.leftMargin: -Style.space(8)
                anchors.verticalCenter: parent.verticalCenter
                iconText: "󰅁"
                tooltipText: "Previous month"
                foreground: root.contentForeground
                fontFamily: root.contentFontFamily
                onClicked: root.moveMonth(-1)
              }

              PanelActionButton {
                anchors.right: parent.right
                anchors.rightMargin: -Style.space(8)
                anchors.verticalCenter: parent.verticalCenter
                iconText: "󰅂"
                tooltipText: "Next month"
                foreground: root.contentForeground
                fontFamily: root.contentFontFamily
                onClicked: root.moveMonth(1)
              }
            }
          }

          // ---- Agenda Section ----
          Item {
            width: parent.width
            height: agendaColumn.implicitHeight + Style.space(12)

            Column {
              id: agendaColumn
              anchors.horizontalCenter: parent.horizontalCenter
              width: gridColumn.width
              spacing: Style.space(8)

              PanelSeparator {
                strength: 0.15
                width: parent.width
              }

              // Header: Selected date title + Today pill + Copy button
              Item {
                width: parent.width
                height: Math.max(agendaDateRow.implicitHeight, agendaCopyBtn.height)

                Row {
                  id: agendaDateRow
                  anchors.left: parent.left
                  anchors.verticalCenter: parent.verticalCenter
                  spacing: Style.space(8)

                  Text {
                    id: agendaDateLabel
                    textFormat: Text.PlainText
                    anchors.verticalCenter: parent.verticalCenter
                    text: Qt.formatDate(root.selectedDate, "dddd, MMMM d").toUpperCase()
                    color: Qt.darker(root.contentForeground, 1.3)
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.caption
                    font.letterSpacing: 1
                    font.bold: true
                  }

                  Rectangle {
                    visible: root.selectedDateKey === root.todayKey
                    anchors.verticalCenter: parent.verticalCenter
                    width: todayText.implicitWidth + Style.space(10)
                    height: Style.space(16)
                    radius: Style.cornerRadius > 0 ? height / 2 : 0
                    color: Style.selectedFillFor(root.contentForeground, Color.accent)
                    border.width: Style.spacing.hairline
                    border.color: Style.selectedStateColor(root.contentForeground, Color.accent)

                    Text {
                      id: todayText
                      anchors.centerIn: parent
                      text: "TODAY"
                      color: Style.selectedStateColor(root.contentForeground, Color.accent)
                      font.family: root.contentFontFamily
                      font.pixelSize: Style.font.caption
                      font.letterSpacing: 1
                      font.bold: true
                    }
                  }
                }

                Row {
                  anchors.right: parent.right
                  anchors.verticalCenter: parent.verticalCenter
                  spacing: Style.space(4)

                  PanelActionButton {
                    id: agendaAddBtn
                    iconText: "󰐕"
                    tooltipText: "Add local event (n)"
                    foreground: root.contentForeground
                    fontFamily: root.contentFontFamily
                    onClicked: root.toggleAddEvent()
                  }

                  PanelActionButton {
                    id: agendaCopyBtn
                    iconText: "󰆏"
                    tooltipText: "Copy agenda as Markdown (y)"
                    foreground: root.contentForeground
                    fontFamily: root.contentFontFamily
                    onClicked: root.copyDayMarkdown()
                  }
                }
              }

              // Account filter chips (shown if multiple accounts exist)
              Item {
                visible: root.accountList.length > 2
                width: parent.width
                height: visible ? filterRow.height : 0

                Row {
                  id: filterRow
                  spacing: Style.space(6)

                  Repeater {
                    model: root.accountList

                    Rectangle {
                      required property string modelData
                      readonly property bool isActive: root.selectedAccount === modelData
                      width: chipText.implicitWidth + Style.space(16)
                      height: Style.space(22)
                      radius: Style.cornerRadius > 0 ? height / 2 : 0
                      color: isActive
                        ? Style.selectedFillFor(root.contentForeground, Color.accent)
                        : (chipMouse.containsMouse
                            ? Style.hoverFillFor(root.contentForeground, Color.accent)
                            : "transparent")
                      border.width: Style.spacing.hairline
                      border.color: isActive
                        ? Style.selectedStateColor(root.contentForeground, Color.accent)
                        : Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.15)

                      Text {
                        id: chipText
                        anchors.centerIn: parent
                        text: modelData
                        color: isActive
                          ? Style.selectedStateColor(root.contentForeground, Color.accent)
                          : Qt.darker(root.contentForeground, 1.4)
                        font.family: root.contentFontFamily
                        font.pixelSize: Style.font.caption
                        font.bold: isActive
                      }

                      MouseArea {
                        id: chipMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.selectedAccount = modelData
                      }
                    }
                  }
                }
              }

              // Inline Add Event Form
              Rectangle {
                id: addEventCard
                visible: root.addEventOpen
                width: parent.width
                implicitHeight: addEventCol.implicitHeight + Style.space(16)
                radius: Style.cornerRadius
                color: Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.05)
                border.width: Style.spacing.hairline
                border.color: Style.selectedStateColor(root.contentForeground, Color.accent)

                Column {
                  id: addEventCol
                  width: parent.width - Style.space(20)
                  anchors.centerIn: parent
                  spacing: Style.space(8)

                  Item {
                    width: parent.width
                    height: cancelAddBtn.height

                    Text {
                      anchors.left: parent.left
                      anchors.verticalCenter: parent.verticalCenter
                      text: "NEW LOCAL EVENT"
                      color: Style.selectedStateColor(root.contentForeground, Color.accent)
                      font.family: root.contentFontFamily
                      font.pixelSize: Style.font.caption
                      font.bold: true
                      font.letterSpacing: 1
                    }

                    PanelActionButton {
                      id: cancelAddBtn
                      anchors.right: parent.right
                      anchors.verticalCenter: parent.verticalCenter
                      iconText: "✕"
                      tooltipText: "Cancel (Esc)"
                      foreground: root.contentForeground
                      fontFamily: root.contentFontFamily
                      onClicked: root.closeAddEvent()
                    }
                  }

                  TextField {
                    id: newEventTitle
                    width: parent.width
                    placeholderText: "Event title"
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.bodySmall
                    focus: root.addEventOpen
                    onAccepted: root.submitNewEvent(
                      newEventTitle.text,
                      allDayBoxMouse.allDay,
                      newStartTime.text,
                      newEndTime.text,
                      newEventLocation.text
                    )
                  }

                  Row {
                    spacing: Style.space(12)

                    Row {
                      spacing: Style.space(6)
                      anchors.verticalCenter: parent.verticalCenter

                      Rectangle {
                        width: Style.space(16)
                        height: Style.space(16)
                        radius: Style.cornerRadius > 0 ? 3 : 0
                        color: allDayBoxMouse.allDay
                          ? Style.selectedStateColor(root.contentForeground, Color.accent)
                          : "transparent"
                        border.width: Style.spacing.hairline
                        border.color: allDayBoxMouse.allDay
                          ? Style.selectedStateColor(root.contentForeground, Color.accent)
                          : Qt.darker(root.contentForeground, 1.8)

                        Text {
                          visible: allDayBoxMouse.allDay
                          anchors.centerIn: parent
                          text: "✓"
                          color: Color.background
                          font.pixelSize: Style.font.caption - 1
                          font.bold: true
                        }

                        MouseArea {
                          id: allDayBoxMouse
                          property bool allDay: true
                          anchors.fill: parent
                          cursorShape: Qt.PointingHandCursor
                          onClicked: allDay = !allDay
                        }
                      }

                      Text {
                        text: "All Day"
                        color: root.contentForeground
                        font.family: root.contentFontFamily
                        font.pixelSize: Style.font.caption
                        anchors.verticalCenter: parent.verticalCenter

                        MouseArea {
                          anchors.fill: parent
                          cursorShape: Qt.PointingHandCursor
                          onClicked: allDayBoxMouse.allDay = !allDayBoxMouse.allDay
                        }
                      }
                    }

                    Row {
                      visible: !allDayBoxMouse.allDay
                      spacing: Style.space(4)
                      anchors.verticalCenter: parent.verticalCenter

                      TextField {
                        id: newStartTime
                        width: Style.space(56)
                        text: "09:00"
                        font.family: root.contentFontFamily
                        font.pixelSize: Style.font.caption
                        horizontalAlignment: TextInput.AlignHCenter
                        onAccepted: root.submitNewEvent(
                          newEventTitle.text,
                          allDayBoxMouse.allDay,
                          newStartTime.text,
                          newEndTime.text,
                          newEventLocation.text
                        )
                      }

                      Text {
                        text: "–"
                        color: Qt.darker(root.contentForeground, 1.5)
                        font.pixelSize: Style.font.caption
                        anchors.verticalCenter: parent.verticalCenter
                      }

                      TextField {
                        id: newEndTime
                        width: Style.space(56)
                        text: "10:00"
                        font.family: root.contentFontFamily
                        font.pixelSize: Style.font.caption
                        horizontalAlignment: TextInput.AlignHCenter
                        onAccepted: root.submitNewEvent(
                          newEventTitle.text,
                          allDayBoxMouse.allDay,
                          newStartTime.text,
                          newEndTime.text,
                          newEventLocation.text
                        )
                      }
                    }
                  }

                  TextField {
                    id: newEventLocation
                    width: parent.width
                    placeholderText: "Location (optional)"
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.bodySmall
                    onAccepted: root.submitNewEvent(
                      newEventTitle.text,
                      allDayBoxMouse.allDay,
                      newStartTime.text,
                      newEndTime.text,
                      newEventLocation.text
                    )
                  }

                  Row {
                    spacing: Style.space(8)

                    Button {
                      text: "Save Event"
                      accent: Color.accent
                      bordered: true
                      onClicked: root.submitNewEvent(
                        newEventTitle.text,
                        allDayBoxMouse.allDay,
                        newStartTime.text,
                        newEndTime.text,
                        newEventLocation.text
                      )
                    }

                    Button {
                      text: "Cancel"
                      onClicked: root.closeAddEvent()
                    }
                  }
                }
              }

              // Empty state
              Rectangle {
                visible: root.dayFilteredEvents.length === 0
                width: parent.width
                height: Style.space(48)
                radius: Style.cornerRadius
                color: Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.04)
                border.width: Style.spacing.hairline
                border.color: Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.08)

                Row {
                  anchors.centerIn: parent
                  spacing: Style.space(8)

                  Text {
                    text: "󰃭"
                    color: Qt.darker(root.contentForeground, 1.8)
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.body
                    anchors.verticalCenter: parent.verticalCenter
                  }

                  Text {
                    text: "No events scheduled"
                    color: Qt.darker(root.contentForeground, 1.6)
                    font.family: root.contentFontFamily
                    font.pixelSize: Style.font.bodySmall
                    anchors.verticalCenter: parent.verticalCenter
                  }
                }
              }

              // Event cards list
              Repeater {
                model: root.dayFilteredEvents

                Rectangle {
                  required property var modelData
                  width: parent.width
                  height: Math.max(cardContentCol.implicitHeight + Style.space(16), Style.space(48))
                  radius: Style.cornerRadius
                  color: cardMouse.containsMouse
                    ? Style.hoverFillFor(root.contentForeground, Color.accent)
                    : Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.04)
                  border.width: Style.spacing.hairline
                  border.color: Qt.rgba(root.contentForeground.r, root.contentForeground.g, root.contentForeground.b, 0.1)

                  // Left edge color strip
                  Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.margins: Style.space(4)
                    width: Style.space(3)
                    radius: width / 2
                    color: modelData.color || "#4285f4"
                  }

                  // Content column
                  Column {
                    id: cardContentCol
                    anchors.left: parent.left
                    anchors.leftMargin: Style.space(16)
                    anchors.right: joinBtn.visible ? joinBtn.left : (deleteLocalBtn.visible ? deleteLocalBtn.left : parent.right)
                    anchors.rightMargin: Style.space(10)
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Style.space(2)

                    Row {
                      spacing: Style.space(8)

                      Text {
                        textFormat: Text.PlainText
                        text: modelData.timeStr || (modelData.allDay ? "All Day" : "")
                        color: Qt.darker(root.contentForeground, 1.3)
                        font.family: root.contentFontFamily
                        font.pixelSize: Style.font.caption
                        font.bold: true
                      }

                      Text {
                        textFormat: Text.PlainText
                        visible: !!modelData.account
                        text: "• " + modelData.account
                        color: Qt.darker(root.contentForeground, 1.8)
                        font.family: root.contentFontFamily
                        font.pixelSize: Style.font.caption
                      }
                    }

                    Text {
                      textFormat: Text.PlainText
                      width: parent.width
                      text: modelData.summary || "Event"
                      color: root.contentForeground
                      font.family: root.contentFontFamily
                      font.pixelSize: Style.font.bodySmall
                      font.bold: true
                      elide: Text.ElideRight
                    }

                    Text {
                      textFormat: Text.PlainText
                      visible: !!modelData.location && !modelData.location.startsWith("http")
                      width: parent.width
                      text: "󰍎 " + modelData.location
                      color: Qt.darker(root.contentForeground, 1.7)
                      font.family: root.contentFontFamily
                      font.pixelSize: Style.font.caption
                      elide: Text.ElideRight
                    }
                  }

                  // Join button (if meeting URL exists)
                  Rectangle {
                    id: joinBtn
                    visible: !!modelData.meetingUrl && modelData.meetingUrl !== ""
                    anchors.right: parent.right
                    anchors.rightMargin: Style.space(10)
                    anchors.verticalCenter: parent.verticalCenter
                    width: joinRow.width + Style.space(16)
                    height: Style.space(26)
                    radius: Style.cornerRadius > 0 ? height / 2 : 0
                    color: joinMouse.containsMouse
                      ? Style.selectedStateColor(root.contentForeground, Color.accent)
                      : Style.selectedFillFor(root.contentForeground, Color.accent)
                    border.width: Style.spacing.hairline
                    border.color: Style.selectedStateColor(root.contentForeground, Color.accent)

                    Row {
                      id: joinRow
                      anchors.centerIn: parent
                      spacing: Style.space(4)

                      Text {
                        text: "󰅟"
                        color: joinMouse.containsMouse ? Color.background : root.contentForeground
                        font.family: root.contentFontFamily
                        font.pixelSize: Style.font.caption
                        anchors.verticalCenter: parent.verticalCenter
                      }

                      Text {
                        text: "Join"
                        color: joinMouse.containsMouse ? Color.background : root.contentForeground
                        font.family: root.contentFontFamily
                        font.pixelSize: Style.font.caption
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter
                      }
                    }

                    MouseArea {
                      id: joinMouse
                      anchors.fill: parent
                      hoverEnabled: true
                      cursorShape: Qt.PointingHandCursor
                      onClicked: root.openMeetingUrl(modelData.meetingUrl)
                    }

                    PanelToolTip {
                      visible: joinMouse.containsMouse
                      text: modelData.meetingUrl
                      fontFamily: root.contentFontFamily
                    }
                  }

                  // Delete button for local events
                  Rectangle {
                    id: deleteLocalBtn
                    visible: !!modelData.isLocal
                    anchors.right: parent.right
                    anchors.rightMargin: Style.space(10)
                    anchors.verticalCenter: parent.verticalCenter
                    width: Style.space(26)
                    height: Style.space(26)
                    radius: Style.cornerRadius > 0 ? height / 2 : 0
                    color: deleteMouse.containsMouse
                      ? Style.selectedFillFor(root.contentForeground, Color.accent)
                      : "transparent"
                    border.width: Style.spacing.hairline
                    border.color: deleteMouse.containsMouse
                      ? Style.selectedStateColor(root.contentForeground, Color.accent)
                      : "transparent"

                    Text {
                      anchors.centerIn: parent
                      text: "󰆴"
                      color: deleteMouse.containsMouse ? Color.accent : Qt.darker(root.contentForeground, 1.8)
                      font.family: root.contentFontFamily
                      font.pixelSize: Style.font.bodySmall
                    }

                    MouseArea {
                      id: deleteMouse
                      anchors.fill: parent
                      hoverEnabled: true
                      cursorShape: Qt.PointingHandCursor
                      onClicked: root.deleteLocalEvent(modelData.id)
                    }

                    PanelToolTip {
                      visible: deleteMouse.containsMouse
                      text: "Delete event"
                      fontFamily: root.contentFontFamily
                    }
                  }

                  MouseArea {
                    id: cardMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
