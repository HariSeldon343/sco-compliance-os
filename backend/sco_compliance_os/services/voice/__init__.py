"""Voice services SCO Compliance OS — STT (Whisper.cpp) + TTS (Piper).

Privacy hard requirement: tutto on-device, nessun cloud STT/TTS.

Modelli e binari sono auto-scaricati al primo utilizzo in
~/.sco-compliance-os/voice-models/ e ~/.sco-compliance-os/voice-bin/.

Hidden imports candidates per PyInstaller (Conv. 44 lesson 3):
- email_validator (gia' coperto da onboarding)
- nessuna nuova dep Python: whisper.cpp e piper sono binari nativi
  invocati via subprocess (no bindings Python che PyInstaller debba
  hint-import). I path dei binari sono risolti runtime con fallback
  a download al primo use.
"""

from __future__ import annotations

__all__ = ["stt", "tts"]
