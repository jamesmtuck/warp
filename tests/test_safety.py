"""Tests for safety module."""
import pytest
from warp.safety import RISK_HIGH, RISK_LOW, RISK_MODERATE, analyze_command_risk


def test_low_risk_ls():
    risk, warnings, safer = analyze_command_risk("ls -la")
    assert risk == RISK_LOW
    assert warnings == []
    assert safer is None


def test_high_risk_rm_rf():
    risk, warnings, safer = analyze_command_risk("rm -rf /tmp/junk")
    assert risk == RISK_HIGH
    assert len(warnings) > 0
    assert "rm -rf" in warnings[0].lower() or "recursive" in warnings[0].lower() or "permanently" in warnings[0].lower()


def test_high_risk_find_delete():
    risk, warnings, safer = analyze_command_risk('find . -name "*.log" -delete')
    assert risk == RISK_HIGH
    assert safer is not None
    assert "-print" in safer
    assert "-delete" not in safer


def test_high_risk_dd():
    risk, warnings, safer = analyze_command_risk("dd if=/dev/zero of=/dev/sda")
    assert risk == RISK_HIGH


def test_high_risk_mkfs():
    risk, warnings, safer = analyze_command_risk("mkfs.ext4 /dev/sdb1")
    assert risk == RISK_HIGH


def test_moderate_risk_rm():
    risk, warnings, safer = analyze_command_risk("rm myfile.txt")
    assert risk == RISK_MODERATE
    assert len(warnings) > 0


def test_moderate_risk_sudo():
    risk, warnings, safer = analyze_command_risk("sudo apt-get install vim")
    assert risk == RISK_MODERATE
    assert any("sudo" in w.lower() or "elevated" in w.lower() for w in warnings)


def test_moderate_risk_kill_9():
    risk, warnings, safer = analyze_command_risk("kill -9 1234")
    assert risk == RISK_MODERATE


def test_wildcard_rm_high_risk():
    risk, warnings, safer = analyze_command_risk("rm *.tmp")
    assert risk == RISK_HIGH
    assert safer is not None


def test_empty_command():
    risk, warnings, safer = analyze_command_risk("")
    assert risk == RISK_LOW
    assert warnings == []
    assert safer is None
