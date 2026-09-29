"""Firmware & USB -> Stop: ending the build or installation that is running (app 0.4.24).

The ESPHome CLI is the stand-in of test_firmware_download, held busy with FAKE_SLEEP. Stopping has to end that process
itself, not only the job the app shows, and the page has to be told what happened without waiting for its next poll.
"""
import asyncio
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'screen_manager/app'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from firmware import Firmware  # noqa: E402
from test_firmware_download import PROFILE, fake_cli  # noqa: E402

HAS_AIOHTTP = importlib.util.find_spec('aiohttp') is not None
if HAS_AIOHTTP:
    from aiohttp.test_utils import TestClient, TestServer
    from server import Manager, create_app
    from test_screen_owned_settings import fake_ha


async def waiting(firmware):
    """Wait until the job's task has the ESPHome CLI running, so a stop really interrupts something."""
    for _ in range(500):
        if firmware.process:
            return firmware.process.pid
        await asyncio.sleep(0.01)
    raise AssertionError('the stand-in ESPHome never started')


def gone(pid):
    """Whether the process is no longer there. The job's child is a group leader (start_new_session), so a stop that
    only cancelled the task in the app would leave it compiling here."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


class StopTheJob(unittest.IsolatedAsyncioTestCase):
    async def test_nothing_running_is_said_and_not_silently_fine(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, fake_cli(tmp)):
            f = Firmware(Path(tmp) / 'esphome', Path(tmp) / 'data')
            f.create(PROFILE)
            with self.assertRaisesRegex(ValueError, 'No build or installation is running'):
                await f.cancel()
            f.start({'file': 'kitchen.yaml', 'action': 'build'})
            await f.task
            self.assertEqual(f.job['state'], 'success')
            with self.assertRaisesRegex(ValueError, 'No build or installation is running'):
                await f.cancel()
            self.assertEqual(f.job['state'], 'success', 'a finished job stays as it was')

    async def test_a_running_build_is_ended_with_its_esphome_process(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {**fake_cli(tmp), 'FAKE_SLEEP': '30'}):
            f = Firmware(Path(tmp) / 'esphome', Path(tmp) / 'data')
            f.create(PROFILE)
            f.start({'file': 'kitchen.yaml', 'action': 'build'})
            pid = await waiting(f)
            self.assertFalse(gone(pid))
            status = await f.cancel()
            self.assertEqual(status['job']['state'], 'interrupted')
            self.assertIn('Stopped: build', status['logs'])
            self.assertIsNone(f.process)
            self.assertTrue(gone(pid), 'the ESPHome process is gone, not left compiling')
            self.assertIn('finished', f.job)
            self.assertEqual(status['downloads'], [], 'a stopped build offers no image to download')
            # The next job is allowed straight away: the stop waited for the one before it to let go.
            f.start({'file': 'kitchen.yaml', 'action': 'validate'})
            self.assertEqual((await f.cancel())['job']['state'], 'interrupted')

    async def test_a_job_stopped_before_it_started_is_over_too(self):
        """Stopped in the moment between start() and the first step of its task: the task never runs, so nothing in it
        can say the job ended. It must still be over, or the page would show a build that runs for ever."""
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {**fake_cli(tmp), 'FAKE_SLEEP': '30'}):
            f = Firmware(Path(tmp) / 'esphome', Path(tmp) / 'data')
            f.create(PROFILE)
            f.start({'file': 'kitchen.yaml', 'action': 'build'})
            self.assertIsNone(f.process, 'stopped before the CLI was started')
            status = await f.cancel()
            self.assertEqual(status['job']['state'], 'interrupted')
            self.assertIn('Stopped: build', status['logs'])
            self.assertIn('finished', status['job'])

    async def test_a_stopped_installation_never_counts_as_flashed(self):
        """An installation stopped while it compiles (the stage before the upload): the screen still runs what it ran,
        so the screen list must not start nudging the owner to pair it."""
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {**fake_cli(tmp), 'FAKE_SLEEP': '30'}):
            f = Firmware(Path(tmp) / 'esphome', Path(tmp) / 'data')
            f.create(PROFILE)
            with patch.object(Firmware, 'ports', return_value=['/dev/ttyUSB0']):
                f.start({'file': 'kitchen.yaml', 'action': 'install', 'target': '/dev/ttyUSB0'})
                await waiting(f)
                self.assertEqual(f.job['stage'], 'compile')
                status = await f.cancel()
            self.assertEqual(status['job']['state'], 'interrupted')
            self.assertEqual(f.installed, set(), 'a stopped installation never counts as flashed')
            self.assertEqual(status['downloads'], [])


@unittest.skipUnless(HAS_AIOHTTP, 'Run using .venv-portal/bin/python for server tests')
class StopRoute(unittest.IsolatedAsyncioTestCase):
    async def test_the_page_stops_the_job_and_is_answered_with_the_status(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {**fake_cli(tmp), 'FAKE_SLEEP': '30',
                                                                           'ESPHOME_CONFIG': str(Path(tmp) / 'esphome')}):
            m = Manager(fake_ha(), Path(tmp) / 'screens.json')
            async with TestClient(TestServer(create_app(m, True))) as client:
                inventory = await (await client.get('/api/inventory')).json()
                headers = {'X-Screen-CSRF': inventory['csrf']}
                m.firmware.create(PROFILE)
                started = await client.post('/api/firmware/jobs', headers=headers,
                                            json={'file': 'kitchen.yaml', 'action': 'build'})
                self.assertEqual(started.status, 200)
                self.assertEqual((await started.json())['state'], 'running')
                refused = await client.post('/api/firmware/jobs/cancel')
                self.assertEqual(refused.status, 403, 'CSRF like every other change')
                self.assertEqual((await (await client.get('/api/firmware')).json())['job']['state'], 'running')
                stopped = await client.post('/api/firmware/jobs/cancel', headers=headers)
                self.assertEqual(stopped.status, 200)
                answer = await stopped.json()
                self.assertEqual(answer['job']['state'], 'interrupted')
                self.assertIn('Stopped: build', answer['logs'])
                self.assertIn('taken', answer, 'the same shape as /api/firmware')
                again = await client.post('/api/firmware/jobs/cancel', headers=headers)
                self.assertEqual(again.status, 400)
                self.assertIn('No build or installation is running', (await again.json())['error'])


if __name__ == '__main__':
    unittest.main()
