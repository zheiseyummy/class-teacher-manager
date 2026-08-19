from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select

from database.connection import get_session
from models.class_group import ClassGroup
from models.teacher_profile import TeacherProfile
from models.teaching_schedule import AcademicSemester
from utils.score_excel_import import DEFAULT_SUBJECTS


class TeacherProfileDataError(ValueError):
    """Raised when local teacher profile values are invalid."""


class TeacherProfileController:
    PROFILE_ID = 1
    COMMON_SUBJECTS = DEFAULT_SUBJECTS

    def get_profile(self) -> dict[str, Any]:
        with get_session() as session:
            profile = session.get(TeacherProfile, self.PROFILE_ID)
            return self._profile_dict(profile) if profile is not None else self._empty_profile()

    def get_form_options(self) -> dict[str, list[dict[str, Any]]]:
        with get_session() as session:
            classes = session.scalars(
                select(ClassGroup)
                .where(ClassGroup.is_deleted.is_(False))
                .order_by(ClassGroup.grade, ClassGroup.name)
            ).all()
            semesters = session.scalars(
                select(AcademicSemester)
                .where(AcademicSemester.is_deleted.is_(False))
                .order_by(
                    AcademicSemester.is_current.desc(),
                    AcademicSemester.start_date.desc(),
                    AcademicSemester.id.desc(),
                )
            ).all()
            return {
                "classes": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "grade": item.grade or "",
                        "school_year": item.school_year or "",
                    }
                    for item in classes
                ],
                "semesters": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "is_current": item.is_current,
                        "date_range_display": f"{item.start_date.isoformat()} 至 {item.end_date.isoformat()}",
                    }
                    for item in semesters
                ],
            }

    def save_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        teacher_name = self._text(data.get("teacher_name"), "教师姓名", 80, required=True)
        school_name = self._text(data.get("school_name"), "学校名称", 160)
        personal_mark = self._text(data.get("personal_mark"), "个人标记", 120)
        subjects = self._string_list(data.get("subjects"), "任教学科", 30, maximum_items=24)
        class_ids = self._integer_list(data.get("common_class_ids"), "常用班级")
        default_semester_id = self._optional_integer(data.get("default_semester_id"), "默认学期")

        with get_session() as session:
            active_class_ids = set(
                session.scalars(
                    select(ClassGroup.id).where(
                        ClassGroup.id.in_(class_ids or [-1]),
                        ClassGroup.is_deleted.is_(False),
                    )
                ).all()
            )
            if active_class_ids != set(class_ids):
                raise TeacherProfileDataError("常用班级中包含已删除或不存在的班级，请重新选择。")
            if default_semester_id is not None:
                semester_exists = session.scalar(
                    select(AcademicSemester.id).where(
                        AcademicSemester.id == default_semester_id,
                        AcademicSemester.is_deleted.is_(False),
                    )
                )
                if semester_exists is None:
                    raise TeacherProfileDataError("默认学期已不存在，请重新选择。")

            profile = session.get(TeacherProfile, self.PROFILE_ID)
            if profile is None:
                profile = TeacherProfile(id=self.PROFILE_ID)
                session.add(profile)
            profile.teacher_name = teacher_name
            profile.school_name = school_name
            profile.subjects_json = json.dumps(subjects, ensure_ascii=False)
            profile.common_class_ids_json = json.dumps(class_ids)
            profile.default_semester_id = default_semester_id
            profile.personal_mark = personal_mark
            profile.onboarding_completed = True
            session.flush()
            return self._profile_dict(profile)

    def dismiss_onboarding(self) -> dict[str, Any]:
        with get_session() as session:
            profile = session.get(TeacherProfile, self.PROFILE_ID)
            if profile is None:
                profile = TeacherProfile(id=self.PROFILE_ID)
                session.add(profile)
            profile.onboarding_completed = True
            session.flush()
            return self._profile_dict(profile)

    @classmethod
    def _profile_dict(cls, profile: TeacherProfile) -> dict[str, Any]:
        teacher_name = (profile.teacher_name or "").strip()
        teacher_display = cls.teacher_display_name(teacher_name)
        personal_mark = (profile.personal_mark or "").strip()
        if not personal_mark:
            personal_mark = (
                f"{teacher_display} · 个人教学工作台" if teacher_name else "个人教学工作台"
            )
        return {
            "id": profile.id,
            "teacher_name": teacher_name,
            "teacher_display_name": teacher_display,
            "school_name": (profile.school_name or "").strip(),
            "subjects": cls._decode_string_list(profile.subjects_json),
            "common_class_ids": cls._decode_integer_list(profile.common_class_ids_json),
            "default_semester_id": profile.default_semester_id,
            "personal_mark": (profile.personal_mark or "").strip(),
            "personal_mark_display": personal_mark,
            "greeting": f"您好，{teacher_display}！",
            "onboarding_completed": profile.onboarding_completed,
        }

    @classmethod
    def _empty_profile(cls) -> dict[str, Any]:
        return {
            "id": None,
            "teacher_name": "",
            "teacher_display_name": "老师",
            "school_name": "",
            "subjects": [],
            "common_class_ids": [],
            "default_semester_id": None,
            "personal_mark": "",
            "personal_mark_display": "个人教学工作台",
            "greeting": "您好，老师！",
            "onboarding_completed": False,
        }

    @staticmethod
    def teacher_display_name(value: str) -> str:
        name = value.strip()
        if not name:
            return "老师"
        return name if name.endswith("老师") else f"{name}老师"

    @staticmethod
    def _text(value: Any, label: str, maximum_length: int, required: bool = False) -> str:
        text = str(value or "").strip()
        if required and not text:
            raise TeacherProfileDataError(f"请填写{label}。")
        if len(text) > maximum_length:
            raise TeacherProfileDataError(f"{label}不能超过 {maximum_length} 个字符。")
        return text

    @classmethod
    def _string_list(
        cls,
        value: Any,
        label: str,
        maximum_length: int,
        *,
        maximum_items: int,
    ) -> list[str]:
        if value is None:
            raw_items: Iterable[Any] = []
        elif isinstance(value, str):
            raw_items = re.split(r"[,，、;；]", value)
        elif isinstance(value, Iterable):
            raw_items = value
        else:
            raise TeacherProfileDataError(f"{label}格式不正确。")
        items: list[str] = []
        seen: set[str] = set()
        for raw_item in raw_items:
            item = str(raw_item or "").strip()
            if not item or item in seen:
                continue
            if len(item) > maximum_length:
                raise TeacherProfileDataError(f"{label}中的“{item}”过长。")
            seen.add(item)
            items.append(item)
        if len(items) > maximum_items:
            raise TeacherProfileDataError(f"{label}最多选择 {maximum_items} 项。")
        return items

    @staticmethod
    def _integer_list(value: Any, label: str) -> list[int]:
        if value is None:
            return []
        if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
            raise TeacherProfileDataError(f"{label}格式不正确。")
        result: list[int] = []
        for raw_item in value:
            try:
                item = int(raw_item)
            except (TypeError, ValueError) as exc:
                raise TeacherProfileDataError(f"{label}格式不正确。") from exc
            if item > 0 and item not in result:
                result.append(item)
        return result

    @staticmethod
    def _optional_integer(value: Any, label: str) -> int | None:
        if value in (None, ""):
            return None
        try:
            result = int(value)
        except (TypeError, ValueError) as exc:
            raise TeacherProfileDataError(f"{label}格式不正确。") from exc
        return result if result > 0 else None

    @staticmethod
    def _decode_string_list(value: str) -> list[str]:
        try:
            decoded = json.loads(value or "[]")
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(decoded, list):
            return []
        return [str(item).strip() for item in decoded if str(item).strip()]

    @staticmethod
    def _decode_integer_list(value: str) -> list[int]:
        try:
            decoded = json.loads(value or "[]")
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(decoded, list):
            return []
        result: list[int] = []
        for item in decoded:
            try:
                parsed = int(item)
            except (TypeError, ValueError):
                continue
            if parsed > 0 and parsed not in result:
                result.append(parsed)
        return result
