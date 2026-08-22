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

    def test_batch_mode_waits_until_a_complete_batch_exists(self):
        session = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar=lambda: 4)),
        )
        review = SimpleNamespace(id=5)

        with patch.object(crud.settings, "REVIEW_GROUP_BATCH_ENABLED", True), \
                patch.object(crud.settings, "REVIEW_GROUP_BATCH_SIZE", 10), \
                patch.object(crud, "get_admin_group", new=AsyncMock(return_value=123)), \
                patch.object(crud, "_get_pending_review_batch", new=AsyncMock(return_value=[])), \
                patch.object(crud, "_send_review_to_group", new=AsyncMock()) as send:
            self.run_async(crud.notify_superadmin_group(None, session, 1, review))

        send.assert_not_awaited()
        session.execute.assert_awaited_once()

    def test_batch_mode_sends_and_marks_all_reviews_in_the_batch(self):
        reviews = [SimpleNamespace(id=index, group_notified=False) for index in range(1, 11)]
        session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

        with patch.object(crud.settings, "REVIEW_GROUP_BATCH_ENABLED", True), \
                patch.object(crud.settings, "REVIEW_GROUP_BATCH_SIZE", 10), \
                patch.object(crud, "get_admin_group", new=AsyncMock(return_value=123)), \
                patch.object(crud, "_get_pending_review_batch", new=AsyncMock(return_value=reviews)), \
                patch.object(crud, "_send_review_to_group", new=AsyncMock(return_value=True)) as send:
            self.run_async(crud.notify_superadmin_group(None, session, 1, SimpleNamespace(id=10)))

        self.assertTrue(all(review.group_notified for review in reviews))
        self.assertEqual(send.await_count, 10)
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

    def test_batch_mode_keeps_successful_items_marked_when_a_later_send_fails(self):
        reviews = [SimpleNamespace(id=index, group_notified=False) for index in range(1, 4)]
        session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

        async def send_review(_bot, _group_id, review):
            return review.id != 2

        with patch.object(crud.settings, "REVIEW_GROUP_BATCH_ENABLED", True), \
                patch.object(crud.settings, "REVIEW_GROUP_BATCH_SIZE", 3), \
                patch.object(crud, "get_admin_group", new=AsyncMock(return_value=123)), \
                patch.object(crud, "_get_pending_review_batch", new=AsyncMock(return_value=reviews)), \
                patch.object(crud, "_send_review_to_group", side_effect=send_review):
            self.run_async(crud.notify_superadmin_group(None, session, 1, SimpleNamespace(id=3)))

        self.assertTrue(reviews[0].group_notified)
        self.assertFalse(reviews[1].group_notified)
        self.assertFalse(reviews[2].group_notified)
        session.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
