"""Worker Whisper (exemple).

Ce module illustre un worker de transcription audio. Dans un vrai contexte,
on brancherait un backend comme whisper.cpp ou openai-whisper. Ici on
simule juste le succès si le fichier existe.
"""

from typing import Optional


def transcribe(audio_path: str, model: str = "base") -> Optional[str]:
    """Transcrit un fichier audio fictivement.

    Args:
        audio_path: chemin du fichier audio.
        model: nom du modèle (ex: base, small, medium, large).

    Returns:
        Une chaîne de transcription factice, ou None si le fichier est absent.
    """
    # Simule une transcription
    try:
        with open(audio_path, "rb") as _:
            pass
        return f"Transcription factice de {audio_path} avec le modèle {model}"
    except FileNotFoundError:
        return None

