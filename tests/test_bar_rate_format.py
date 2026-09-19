#!/usr/bin/env python3
"""Exercise the bar-rate formatter and widget layout.

Runs the real network-throughput script (live + mocked sysfs), executes the
awk formatter from that script with known byte rates, and renders the
number-then-arrow bar slot with QML so font size and unit stay stable.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "network-throughput"
BAR_WIDGET = ROOT / "BarWidget.qml"
RENDER_QML = Path(__file__).resolve().parent / "render_bar_rates.qml"
EVIDENCE_DIR = Path(
    os.environ.get(
        "NM_EVIDENCE_DIR",
        "/home/adam/.no-mistakes/evidence/01M2VRFAWFWAPKR6A4983M50W0",
    )
)

LINE_RE = re.compile(r"^↓ (\d+\.\dMB)  ↑ (\d+\.\dMB)$")
FORBIDDEN = re.compile(r"(?:KB|GB|B/s|/s|\bB\b)")
MIB = 1048576


def extract_awk_program(script_text: str) -> str:
    marker = "awk -v rx="
    start = script_text.index(marker)
    quote = script_text.index("'", start)
    end = script_text.index("'\n", quote + 1)
    return script_text[quote + 1 : end]


def extract_qml_function(source: str, name: str) -> str:
    needle = f"function {name}("
    start = source.index(needle)
    brace = source.index("{", start)
    depth = 0
    for index, char in enumerate(source[brace:], brace):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"could not extract {name}")


def format_rates(rx_bytes_per_sec: float, tx_bytes_per_sec: float) -> str:
    program = extract_awk_program(SCRIPT.read_text())
    result = subprocess.run(
        [
            "awk",
            "-v",
            f"rx={rx_bytes_per_sec}",
            "-v",
            f"tx={tx_bytes_per_sec}",
            "-v",
            "elapsed=1000000000",
            program,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def run_script_with_deltas(rx_delta: int, tx_delta: int) -> str:
    runner = textwrap.dedent(
        f"""
        set -euo pipefail
        mkdir -p /tmp/nm-fakebin-$$
        cat > /tmp/nm-fakebin-$$/ip << 'EOF'
        #!/bin/bash
        echo "default via 192.0.2.1 dev testdev proto dhcp src 192.0.2.10 metric 100"
        EOF
        chmod +x /tmp/nm-fakebin-$$/ip
        export PATH="/tmp/nm-fakebin-$$:$PATH"
        mount -t tmpfs tmpfs /sys/class/net
        mkdir -p /sys/class/net/testdev/statistics
        echo 0 > /sys/class/net/testdev/statistics/rx_bytes
        echo 0 > /sys/class/net/testdev/statistics/tx_bytes
        python3 - << 'PY' &
        import time
        time.sleep(0.2)
        open("/sys/class/net/testdev/statistics/rx_bytes", "w").write("{rx_delta}\\n")
        open("/sys/class/net/testdev/statistics/tx_bytes", "w").write("{tx_delta}\\n")
        PY
        "{SCRIPT}"
        """
    )
    result = subprocess.run(
        ["unshare", "--user", "--map-root-user", "--mount", "bash", "-c", runner],
        check=True,
        capture_output=True,
        text=True,
        timeout=8,
    )
    return result.stdout.strip().splitlines()[-1]


def node_eval(script: str) -> str:
    result = subprocess.run(
        ["node", "--input-type=commonjs", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class BarRateFormatTests(unittest.TestCase):
    def assert_bar_line(self, line: str) -> tuple[str, str]:
        self.assertIsNone(FORBIDDEN.search(line), f"forbidden unit in {line!r}")
        match = LINE_RE.match(line)
        self.assertIsNotNone(match, f"expected ↓ X.XMB  ↑ Y.YMB, got {line!r}")
        assert match is not None
        return match.group(1), match.group(2)

    def test_live_script_stays_in_megabytes(self) -> None:
        line = subprocess.run(
            [str(SCRIPT)],
            check=True,
            capture_output=True,
            text=True,
            timeout=8,
        ).stdout.strip()
        download, upload = self.assert_bar_line(line)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        installed = Path.home() / ".config/omarchy/plugins/dev.egoist.network-throughput/scripts/network-throughput"
        installed_line = ""
        if installed.is_file():
            installed_line = subprocess.run(
                [str(installed)],
                check=True,
                capture_output=True,
                text=True,
                timeout=8,
            ).stdout.strip()
        (EVIDENCE_DIR / "live-script-output.txt").write_text(
            "\n".join(
                [
                    f"forked:    {line}",
                    f"installed: {installed_line}",
                    f"download={download}",
                    f"upload={upload}",
                    "expected_layout=12.4MB ↑ / 0.8MB ↓",
                    "",
                ]
            )
        )

    def test_idle_and_tiny_traffic_print_zero_mb(self) -> None:
        self.assertEqual(format_rates(0, 0), "↓ 0.0MB  ↑ 0.0MB")
        self.assertEqual(format_rates(1024, 512), "↓ 0.0MB  ↑ 0.0MB")
        self.assertEqual(format_rates(100 * 1024, 0), "↓ 0.1MB  ↑ 0.0MB")

    def test_typical_and_gigabit_rates_stay_mb(self) -> None:
        line = format_rates(12.4 * MIB, 0.8 * MIB)
        download, upload = self.assert_bar_line(line)
        self.assertEqual(download, "12.4MB")
        self.assertEqual(upload, "0.8MB")
        self.assertEqual(format_rates(125 * MIB, 12.4 * MIB), "↓ 125.0MB  ↑ 12.4MB")
        gigabyte = format_rates(1024 * MIB, 0)
        self.assertEqual(gigabyte, "↓ 1024.0MB  ↑ 0.0MB")
        self.assertNotIn("GB", gigabyte)

    def test_mocked_sysfs_script_keeps_mb_and_arrow_order(self) -> None:
        rx = int(12.4 * MIB * 0.75)
        tx = int(0.8 * MIB * 0.75)
        line = run_script_with_deltas(rx, tx)
        download, upload = self.assert_bar_line(line)
        self.assertTrue(download.endswith("MB"))
        self.assertTrue(upload.endswith("MB"))
        self.assertAlmostEqual(float(download[:-2]), 12.4, delta=1.0)
        self.assertAlmostEqual(float(upload[:-2]), 0.8, delta=0.3)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        (EVIDENCE_DIR / "mocked-script-output.txt").write_text(line + "\n")

    def test_qml_display_rate_and_parser(self) -> None:
        source = BAR_WIDGET.read_text()
        display_rate = extract_qml_function(source, "displayRate")
        update_rates = extract_qml_function(source, "updateRates")
        js = f"""
        var rateDisplayWidth = 7;
        var downloadText = "";
        var uploadText = "";
        {display_rate}
        {update_rates}
        const padded = ["0.0MB", "0.8MB", "12.4MB", "125.0MB"].map(displayRate);
        if (padded.some(text => text.length !== 7)) throw new Error("pad " + JSON.stringify(padded));
        if (displayRate("--") !== "  0.0MB") throw new Error("fallback " + displayRate("--"));
        updateRates("↓ 12.4MB  ↑ 0.8MB");
        if (downloadText !== "12.4MB" || uploadText !== "0.8MB") {{
          throw new Error("parse " + downloadText + " " + uploadText);
        }}
        updateRates("");
        if (downloadText !== "0.0MB" || uploadText !== "0.0MB") {{
          throw new Error("empty " + downloadText + " " + uploadText);
        }}
        console.log(JSON.stringify({{
          padded,
          typical: {{ downloadText: "12.4MB", uploadText: "0.8MB", layout: ["12.4MB ↑", "0.8MB ↓"] }}
        }}));
        """
        payload = json.loads(node_eval(js))
        self.assertEqual(
            payload["padded"],
            ["  0.0MB", "  0.8MB", " 12.4MB", "125.0MB"],
        )
        self.assertEqual(payload["typical"]["layout"], ["12.4MB ↑", "0.8MB ↓"])

    def test_render_bar_layout_one_font_size(self) -> None:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        image = EVIDENCE_DIR / "bar-rate-layout.png"
        if image.exists():
            image.unlink()
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["QT_QUICK_BACKEND"] = "software"
        result = subprocess.run(
            ["qml6", str(RENDER_QML), "--", str(EVIDENCE_DIR)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
            env=env,
        )
        combined = result.stdout + "\n" + result.stderr
        (EVIDENCE_DIR / "qml-render.log").write_text(combined)
        self.assertEqual(result.returncode, 0, combined)
        self.assertTrue(image.is_file(), f"missing screenshot {image}\n{combined}")
        self.assertGreater(image.stat().st_size, 20_000)
        probe = subprocess.run(
            ["file", str(image)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertIn("PNG image data", probe)
        self.assertRegex(probe, r"1960 x 840")


if __name__ == "__main__":
    unittest.main(verbosity=2)
