import asyncio
import os
import shutil
import time
import unittest
import uuid
from pathlib import Path
from datetime import datetime, timezone

from langchain_core.runnables import RunnableConfig

from enhanced_memory_manager_with_recovery import EnhancedMemoryManagerWithRecovery
from langgraph.checkpoint.base import Checkpoint

# A base class to share setup, teardown, and helper methods
class CheckpointerTestBase:
    test_dir_name = ""

    def setUp(self):
        """Set up a temporary directory for testing."""
        # Use a unique directory for each test class to avoid conflicts
        self.test_dir = Path(self.test_dir_name)
        self.test_dir.mkdir(exist_ok=True, parents=True)
        self.backup_dir = self.test_dir / "backups"
        self.checkpoint_dir = self.test_dir / "checkpoints"
        
        self.memory_manager = EnhancedMemoryManagerWithRecovery(
            backup_dir=str(self.backup_dir),
            checkpoint_dir=str(self.checkpoint_dir)
        )
        
        self.thread_id = f"test_thread_{uuid.uuid4()}"
        self.config: RunnableConfig = {"configurable": {"thread_id": self.thread_id}}

    def tearDown(self):
        """Clean up the temporary directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_dummy_checkpoint(self, i: int) -> Checkpoint:
        """Helper to create a dummy checkpoint dictionary."""
        ts = datetime.now(timezone.utc)
        return Checkpoint(
            v=1,
            id=str(int(ts.timestamp() * 1_000_000)),
            ts=ts.isoformat().replace("+00:00", "Z"),
            channel_values={"messages": [f"message_{i}"]},
            channel_versions={},
            versions_seen={},
        )

class TestSyncCheckpointer(CheckpointerTestBase, unittest.TestCase):
    """
    Test suite for the synchronous BaseCheckpointSaver implementation.
    """
    test_dir_name = "./test_temp_sync"

    def test_put_and_get_tuple(self):
        """Test saving and retrieving a checkpoint."""
        checkpoint1 = self._create_dummy_checkpoint(1)
        put_config = self.memory_manager.put(self.config, checkpoint1, {})
        
        self.assertIn("thread_ts", put_config["configurable"])
        self.assertEqual(put_config["configurable"]["thread_id"], self.thread_id)
        
        retrieved_tuple = self.memory_manager.get_tuple(self.config)
        self.assertIsNotNone(retrieved_tuple)
        self.assertEqual(retrieved_tuple.checkpoint["id"], checkpoint1["id"])
        
        get_specific_config: RunnableConfig = {
            "configurable": {
                "thread_id": self.thread_id,
                "thread_ts": retrieved_tuple.config["configurable"]["thread_ts"]
            }
        }
        retrieved_specific_tuple = self.memory_manager.get_tuple(get_specific_config)
        self.assertIsNotNone(retrieved_specific_tuple)
        self.assertEqual(retrieved_specific_tuple.checkpoint["id"], checkpoint1["id"])

    def test_list_checkpoints(self):
        """Test listing checkpoints for a thread."""
        checkpoint1 = self._create_dummy_checkpoint(1)
        config1 = self.memory_manager.put(self.config, checkpoint1, {})
        time.sleep(0.01)

        checkpoint2 = self._create_dummy_checkpoint(2)
        config2 = self.memory_manager.put(config1, checkpoint2, {})

        all_checkpoints_list = list(self.memory_manager.list(self.config))
        self.assertEqual(len(all_checkpoints_list), 2)
        
        self.assertEqual(all_checkpoints_list[0].checkpoint["id"], checkpoint2["id"])
        self.assertEqual(all_checkpoints_list[1].checkpoint["id"], checkpoint1["id"])

        limited_checkpoints = list(self.memory_manager.list(self.config, limit=1))
        self.assertEqual(len(limited_checkpoints), 1)
        self.assertEqual(limited_checkpoints[0].checkpoint["id"], checkpoint2["id"])
        
        before_checkpoints = list(self.memory_manager.list(self.config, before=config2))
        self.assertEqual(len(before_checkpoints), 1)
        self.assertEqual(before_checkpoints[0].checkpoint["id"], checkpoint1["id"])

    def test_delete_thread(self):
        """Test deleting all checkpoints for a thread."""
        checkpoint = self._create_dummy_checkpoint(1)
        self.memory_manager.put(self.config, checkpoint, {})
        
        self.assertTrue(any(self.checkpoint_dir.iterdir()))
        self.memory_manager.delete_thread(self.config)

        final_checkpoints = list(self.memory_manager.list(self.config))
        self.assertEqual(len(final_checkpoints), 0)

class TestAsyncCheckpointer(CheckpointerTestBase, unittest.IsolatedAsyncioTestCase):
    """
    Test suite for the asynchronous BaseCheckpointSaver implementation.
    """
    test_dir_name = "./test_temp_async"

    async def test_all_async_methods(self):
        """Test the asynchronous versions of the checkpointer methods."""
        # aput and aget_tuple
        checkpoint1 = self._create_dummy_checkpoint(1)
        put_config = await self.memory_manager.aput(self.config, checkpoint1, {})
        
        retrieved_tuple = await self.memory_manager.aget_tuple(self.config)
        self.assertIsNotNone(retrieved_tuple)
        self.assertEqual(retrieved_tuple.checkpoint["id"], checkpoint1["id"])
        
        # alist
        time.sleep(0.01)
        checkpoint2 = self._create_dummy_checkpoint(2)
        await self.memory_manager.aput(put_config, checkpoint2, {})
        
        all_checkpoints = [c async for c in self.memory_manager.alist(self.config)]
        self.assertEqual(len(all_checkpoints), 2)
        self.assertEqual(all_checkpoints[0].checkpoint["id"], checkpoint2["id"])
        
        # adelete_thread
        await self.memory_manager.adelete_thread(self.config)
        final_checkpoints = [c async for c in self.memory_manager.alist(self.config)]
        self.assertEqual(len(final_checkpoints), 0)

if __name__ == '__main__':
    unittest.main() 