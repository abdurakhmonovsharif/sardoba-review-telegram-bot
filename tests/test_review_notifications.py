import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")

from app.config import _env_bool  # noqa: E402
from app.db import crud  # noqa: E402


class ReviewNotificationTests(unittest.TestCase):
    def run_async(self, coroutine):
        return asyncio.run(coroutine)

    def test_env_bool_accepts_common_values(self):
        for value in ("1", "true", "YES", "on"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"TEST_FLAG": value}):
                    self.assertTrue(_env_bool("TEST_FLAG"))

        for value in ("0", "false", "NO", "off"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"TEST_FLAG": value}):
                    self.assertFalse(_env_bool("TEST_FLAG"))

    def test_sparse_mode_skips_the_first_ten_reviews(self):
        session = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar=lambda: 10)),
        )
        review = SimpleNamespace(id=10, group_notified=False)

        with patch.object(crud.settings, "REVIEW_GROUP_BATCH_ENABLED", True), \
                patch.object(crud.settings, "REVIEW_GROUP_BATCH_SIZE", 10), \
                patch.object(crud, "get_admin_group", new=AsyncMock(return_value=123)), \
                patch.object(crud, "get_review_with_relations", new=AsyncMock(return_value=review)), \
                patch.object(crud, "_send_review_to_group", new=AsyncMock()) as send:
            self.run_async(crud.notify_superadmin_group(None, session, 1, review))

        send.assert_not_awaited()
        session.execute.assert_awaited_once()

    def test_sparse_mode_sends_only_the_eleventh_review(self):
        review = SimpleNamespace(id=11, group_notified=False)
        session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

        with patch.object(crud.settings, "REVIEW_GROUP_BATCH_ENABLED", True), \
                patch.object(crud.settings, "REVIEW_GROUP_BATCH_SIZE", 10), \
                patch.object(crud, "get_admin_group", new=AsyncMock(return_value=123)), \
                patch.object(crud, "get_review_with_relations", new=AsyncMock(return_value=review)), \
                patch.object(crud, "_send_review_to_group", new=AsyncMock(return_value=True)) as send:
            session.execute = AsyncMock(return_value=SimpleNamespace(scalar=lambda: 11))
            self.run_async(crud.notify_superadmin_group(None, session, 1, review))

        self.assertTrue(review.group_notified)
        send.assert_awaited_once()
        session.commit.assert_awaited_once()

    def test_disabled_mode_keeps_immediate_notification(self):
        review = SimpleNamespace(id=1, group_notified=False)
        session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

        with patch.object(crud.settings, "REVIEW_GROUP_BATCH_ENABLED", False), \
                patch.object(crud, "get_admin_group", new=AsyncMock(return_value=123)), \
                patch.object(crud, "get_review_with_relations", new=AsyncMock(return_value=review)), \
                patch.object(crud, "_send_review_to_group", new=AsyncMock(return_value=True)) as send:
            self.run_async(crud.notify_superadmin_group(None, session, 1, review))

        send.assert_awaited_once()
        self.assertTrue(review.group_notified)
        session.commit.assert_awaited_once()

if __name__ == "__main__":
    unittest.main()
