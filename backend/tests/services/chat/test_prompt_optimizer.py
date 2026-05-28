"""Test per il prompt optimizer silenzioso (Feature 4 componente A, v0.15.0)."""

from __future__ import annotations

from sco_compliance_os.services.chat.prompt_optimizer import (
    optimize_prompt,
    should_optimize,
)


def test_optimize_substantial_message() -> None:
    msg = "Come faccio una gap analysis NIS2 per un ospedale?"
    out, was_optimized = optimize_prompt(msg)
    assert was_optimized is True
    assert msg in out  # il messaggio originale e' preservato
    assert "Elaborazione" in out  # il meta-wrapper e' stato aggiunto


def test_skip_short_message() -> None:
    out, was_optimized = optimize_prompt("ok")
    assert was_optimized is False
    assert out == "ok"


def test_skip_slash_command() -> None:
    out, was_optimized = optimize_prompt("/audit-iso-27001 esegui un audit completo")
    assert was_optimized is False
    assert out == "/audit-iso-27001 esegui un audit completo"


def test_skip_when_disabled() -> None:
    msg = "Una domanda sostanziale abbastanza lunga da superare la soglia"
    out, was_optimized = optimize_prompt(msg, enabled=False)
    assert was_optimized is False
    assert out == msg


def test_skip_structured_message() -> None:
    msg = "Fammi questo lavoro:\n- punto uno\n- punto due"
    _out, was_optimized = optimize_prompt(msg)
    assert was_optimized is False


def test_skip_monosyllabic_confirmation() -> None:
    for word in ("procedi", "continua", "grazie"):
        _, was_optimized = optimize_prompt(word)
        assert was_optimized is False, f"'{word}' non doveva essere ottimizzato"


def test_should_optimize_predicate() -> None:
    assert should_optimize("Spiegami come strutturare un DVR per una RSA") is True
    assert should_optimize("/skill") is False
    assert should_optimize("si") is False
