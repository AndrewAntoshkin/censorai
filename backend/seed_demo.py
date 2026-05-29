"""Курирование демо-данных для «фреймчек».

Создаёт чистый проект «Демо — видеоконтент» с 5 разными показательными примерами
(уже проанализированными), переносит всё остальное в «Архив» и удаляет пустые проекты.
Скрипт идемпотентный и НЕ удаляет анализы/сцены — только перекладывает файлы по проектам.

Запуск:  python seed_demo.py
"""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis import Analysis  # noqa: F401 — регистрация модели
from app.models.project import Project, VideoFile

DEMO_PROJECT_NAME = "Демо — видеоконтент"
ARCHIVE_PROJECT_NAME = "Архив"

# keyword (в нижнем регистре) -> презентабельное имя файла.
# Порядок = порядок показа в демо.
DEMO_EXAMPLES: list[tuple[str, str]] = [
    ("убойная сила", "Убойная сила — серия 1"),
    ("4 сезо", "Трудные подростки — трейлер 4 сезона"),
    ("кухня", "Кухня — нарезка сцен"),
    ("любовь и прочие", "«Любовь и прочие…» — трейлер"),
    ("ресторан", "Рекламный ролик — ресторан и спа"),
]


def get_or_create_project(session: Session, name: str) -> Project:
    project = session.scalar(select(Project).where(Project.name == name))
    if project is None:
        project = Project(name=name)
        session.add(project)
        session.flush()
    return project


def main() -> None:
    engine = create_engine(settings.DATABASE_URL_SYNC)
    with Session(engine) as session:
        demo = get_or_create_project(session, DEMO_PROJECT_NAME)
        archive = get_or_create_project(session, ARCHIVE_PROJECT_NAME)

        analyses = session.scalars(select(Analysis)).all()
        chosen_file_ids: set[str] = set()

        print("Подбираю 5 примеров для демо:")
        for keyword, nice_name in DEMO_EXAMPLES:
            match = next(
                (a for a in analyses if a.video_title and keyword in a.video_title.lower()),
                None,
            )
            if match is None:
                print(f"  ⚠ не найден анализ по ключу «{keyword}» — пропуск")
                continue
            vf = session.scalar(
                select(VideoFile).where(VideoFile.analysis_id == match.id)
            )
            if vf is None:
                print(f"  ⚠ нет файла для анализа «{match.video_title}» — пропуск")
                continue
            vf.project_id = demo.id
            vf.folder_id = None
            vf.name = nice_name
            chosen_file_ids.add(vf.id)
            print(f"  ✓ {nice_name}")

        # Всё остальное — в «Архив», чтобы кабинет демо был чистым.
        others = session.scalars(
            select(VideoFile).where(VideoFile.id.notin_(chosen_file_ids or {""}))
        ).all()
        moved = 0
        for vf in others:
            if vf.project_id != archive.id:
                vf.project_id = archive.id
                vf.folder_id = None
                moved += 1
        print(f"Перенесено в «Архив»: {moved} файл(ов)")

        session.flush()

        # Удаляем пустые проекты (кроме Демо и Архив) — ORM-каскад уберёт папки.
        all_projects = session.scalars(select(Project)).all()
        removed = 0
        for p in all_projects:
            if p.id in {demo.id, archive.id}:
                continue
            count = session.scalar(
                select(VideoFile).where(VideoFile.project_id == p.id).limit(1)
            )
            if count is None:
                session.delete(p)
                removed += 1
        print(f"Удалено пустых проектов: {removed}")

        session.commit()

        demo_files = session.scalar(
            select(VideoFile).where(VideoFile.project_id == demo.id).limit(1)
        )
        total_demo = len(
            session.scalars(
                select(VideoFile).where(VideoFile.project_id == demo.id)
            ).all()
        )
        print(
            f"\nГотово. В проекте «{DEMO_PROJECT_NAME}»: {total_demo} файл(ов)."
            + ("" if demo_files else " (пусто — проверьте данные)")
        )


if __name__ == "__main__":
    main()
