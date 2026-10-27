from __future__ import annotations

from crupest_chatbot_core import faces


def test_known_face() -> None:
    assert faces.face_id("微笑") == "14"
    assert faces.face_id("/微笑") == "14"


def test_new_face_text_is_present() -> None:
    assert faces.face_id("/敲敲") == "351"
    assert faces.face_id("敲敲") == "351"
    assert faces.face_id("汪汪") == "277"
    assert faces.face_text("277") == "汪汪"


def test_table_is_complete_and_uses_face_text() -> None:
    assert len(faces.FACE_TEXTS) > 300
    assert all(not text.startswith("/") for text in faces.FACE_TEXTS.values())


def test_name_is_trimmed() -> None:
    assert faces.face_id("  微笑  ") == "14"


def test_unknown_face_returns_none() -> None:
    assert faces.face_id("没有这个表情") is None


def test_table_ids_are_digits() -> None:
    assert all(face_id.isdigit() for face_id in faces.FACE_IDS.values())


def test_table_names_are_unique() -> None:
    assert len(faces.FACE_IDS) == len(set(faces.FACE_IDS))


def test_face_ids_round_trip() -> None:
    for text, face_id in faces.FACE_IDS.items():
        assert faces.face_text(face_id) == text
