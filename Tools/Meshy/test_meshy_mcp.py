"""Safety gates must reject before launching a server or spending credits."""
import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('meshy_mcp', Path(__file__).with_name('meshy_mcp.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RequestGates(unittest.IsolatedAsyncioTestCase):
    async def reject(self, tool, allow=False, existing=False):
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / 'request.json'
            output = Path(directory) / 'response.json'
            request.write_text(json.dumps({'tool': tool, 'arguments': {}}))
            if existing:
                output.write_text('retained task receipt')
            args = argparse.Namespace(action='call', request=str(request), output=str(output), allow_create=allow)
            with patch.object(module, 'stdio_client') as launch:
                with self.assertRaises(ValueError):
                    await module.run(args)
                launch.assert_not_called()
            if existing:
                self.assertEqual(output.read_text(), 'retained task receipt')

    async def test_paid_request_requires_explicit_create_flag(self):
        await self.reject('meshy_image_to_3d')

    async def test_task_deletion_is_not_a_pipeline_retry(self):
        await self.reject('meshy_cancel_task', allow=True)

    async def test_existing_task_receipt_is_preserved(self):
        await self.reject('meshy_image_to_3d', allow=True, existing=True)

if __name__ == '__main__':
    unittest.main()
