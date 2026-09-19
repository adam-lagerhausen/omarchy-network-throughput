import QtQuick
import QtQuick.Window

Window {
  id: win
  width: 980
  height: 420
  visible: true
  color: "#0f1115"
  title: "Network Throughput bar rates"

  readonly property int slotWidth: 80
  readonly property int slotHeight: 30
  readonly property int rateFontSize: 11
  readonly property int rateDisplayWidth: 7
  readonly property string fontFamily: "CaskaydiaMono Nerd Font"

  function displayRate(value) {
    var text = String(value || "0.0MB")
    if (text === "--") text = "0.0MB"
    while (text.length < rateDisplayWidth)
      text = " " + text
    return text
  }

  function evidenceDir() {
    var args = Qt.application.arguments
    for (var i = 0; i < args.length - 1; i++) {
      if (args[i] === "--")
        return args[i + 1]
    }
    if (args.length > 1)
      return args[args.length - 1]
    return "."
  }

  function quote(value) {
    return '"' + String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"'
  }

  function collectMetrics() {
    var items = [
      idle.uploadLabel, idle.downloadLabel,
      small.uploadLabel, small.downloadLabel,
      mid.uploadLabel, mid.downloadLabel,
      gig.uploadLabel, gig.downloadLabel,
      zoom.uploadLabel, zoom.downloadLabel
    ]
    var sizes = []
    var modes = []
    var labels = []
    var arrowsRight = []
    for (var i = 0; i < items.length; i++) {
      var item = items[i]
      sizes.push(item.font.pixelSize)
      modes.push(item.fontSizeMode)
      labels.push(item.text)
      arrowsRight.push(item.arrowOnRight === true)
    }
    var unique = []
    for (var s = 0; s < sizes.length; s++) {
      if (unique.indexOf(sizes[s]) === -1)
        unique.push(sizes[s])
    }
    var json = '{"pixelSizes":[' + sizes.join(",") +
      '],"uniquePixelSizes":[' + unique.join(",") +
      '],"fontSizeModes":[' + modes.join(",") +
      '],"arrowsRight":[' + arrowsRight.join(",") +
      '],"labels":['
    for (var l = 0; l < labels.length; l++) {
      json += quote(labels[l])
      if (l + 1 < labels.length) json += ","
    }
    json += "]}"
    return json
  }

  Column {
    anchors.fill: parent
    anchors.margins: 24
    spacing: 18

    Text {
      text: "Bar slot: always megabytes, arrow after the number, one font size"
      color: "#e6e8ee"
      font.pixelSize: 18
      font.family: win.fontFamily
    }

    Text {
      text: "Default 80px slot · upload on top · download below · 0.0MB when idle"
      color: "#9aa3b2"
      font.pixelSize: 13
      font.family: win.fontFamily
    }

    Rectangle {
      width: parent.width
      height: 56
      color: "#16181d"
      radius: 6

      Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: 16
        spacing: 18

        RateSlot { id: idle; upload: "0.0MB"; download: "0.0MB"; caption: "idle" }
        RateSlot { id: small; upload: "0.8MB"; download: "0.0MB"; caption: "tiny" }
        RateSlot { id: mid; upload: "12.4MB"; download: "0.8MB"; caption: "typical" }
        RateSlot { id: gig; upload: "125.0MB"; download: "12.4MB"; caption: "gigabit" }
      }
    }

    Row {
      spacing: 28

      Column {
        spacing: 10

        Text {
          text: "Zoomed typical slot (12.4MB ↑ / 0.8MB ↓)"
          color: "#9aa3b2"
          font.pixelSize: 13
          font.family: win.fontFamily
        }

        RateSlot {
          id: zoom
          upload: "12.4MB"
          download: "0.8MB"
          scaleFactor: 4
        }
      }

      Column {
        spacing: 8

        Text {
          text: "Padded strings stay 7 characters through 125.0MB"
          color: "#9aa3b2"
          font.pixelSize: 13
          font.family: win.fontFamily
        }

        Repeater {
          model: ["0.0MB", "0.8MB", "12.4MB", "125.0MB"]
          delegate: Text {
            font.family: win.fontFamily
            font.pixelSize: 20
            font.features: { "tnum": 1 }
            color: "#e6e8ee"
            text: "\"" + win.displayRate(modelData) + "\"  len=" + win.displayRate(modelData).length
          }
        }
      }
    }
  }

  component RateSlot: Item {
    id: slot
    property string upload: "0.0MB"
    property string download: "0.0MB"
    property string caption: ""
    property real scaleFactor: 1
    property alias uploadLabel: uploadText
    property alias downloadLabel: downloadText

    width: win.slotWidth * scaleFactor
    height: win.slotHeight * scaleFactor + (caption.length ? 18 : 0)

    Column {
      anchors.top: parent.top
      spacing: 4

      Rectangle {
        width: win.slotWidth * slot.scaleFactor
        height: win.slotHeight * slot.scaleFactor
        color: "#111317"
        border.color: "#3a3f4b"
        border.width: 1
        radius: 3

        Column {
          id: rates
          anchors.fill: parent
          anchors.leftMargin: 4 * slot.scaleFactor
          anchors.rightMargin: 4 * slot.scaleFactor
          anchors.topMargin: 2 * slot.scaleFactor
          anchors.bottomMargin: 2 * slot.scaleFactor

          Item {
            width: rates.width
            height: rates.height / 2

            Text {
              id: uploadArrow
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              width: 10 * slot.scaleFactor
              text: "↑"
              color: "#d7dbe4"
              font.family: win.fontFamily
              font.pixelSize: win.rateFontSize * slot.scaleFactor
              horizontalAlignment: Text.AlignHCenter
            }

            Text {
              id: uploadText
              property bool arrowOnRight: true
              anchors.left: parent.left
              anchors.right: uploadArrow.left
              anchors.verticalCenter: parent.verticalCenter
              text: win.displayRate(slot.upload)
              color: "#d7dbe4"
              font.family: win.fontFamily
              font.pixelSize: win.rateFontSize * slot.scaleFactor
              font.features: { "tnum": 1 }
              horizontalAlignment: Text.AlignRight
              clip: true
            }
          }

          Item {
            width: rates.width
            height: rates.height / 2

            Text {
              id: downloadArrow
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              width: 10 * slot.scaleFactor
              text: "↓"
              color: "#d7dbe4"
              font.family: win.fontFamily
              font.pixelSize: win.rateFontSize * slot.scaleFactor
              horizontalAlignment: Text.AlignHCenter
            }

            Text {
              id: downloadText
              property bool arrowOnRight: true
              anchors.left: parent.left
              anchors.right: downloadArrow.left
              anchors.verticalCenter: parent.verticalCenter
              text: win.displayRate(slot.download)
              color: "#d7dbe4"
              font.family: win.fontFamily
              font.pixelSize: win.rateFontSize * slot.scaleFactor
              font.features: { "tnum": 1 }
              horizontalAlignment: Text.AlignRight
              clip: true
            }
          }
        }
      }

      Text {
        visible: slot.caption.length > 0
        text: slot.caption
        color: "#7b8494"
        font.pixelSize: 11
        font.family: win.fontFamily
        width: win.slotWidth * slot.scaleFactor
        horizontalAlignment: Text.AlignHCenter
      }
    }
  }

  Timer {
    interval: 300
    running: true
    repeat: false
    onTriggered: {
      var dir = win.evidenceDir()
      console.log("METRICS " + win.collectMetrics())
      console.log("IMAGE " + dir + "/bar-rate-layout.png")
      contentItem.grabToImage(function(result) {
        var ok = result.saveToFile(dir + "/bar-rate-layout.png")
        console.log("SAVED " + ok)
        Qt.quit()
      }, Qt.size(win.width * 2, win.height * 2))
    }
  }
}
