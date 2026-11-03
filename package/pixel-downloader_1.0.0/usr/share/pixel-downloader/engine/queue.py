import asyncio
from engine.downloader import ChunkDownloader
from engine.database import update_download, get_all_downloads

class DownloadQueue:
    def __init__(self, max_concurrent=3, progress_callback=None):
        self.max_concurrent = max_concurrent
        self.progress_callback = progress_callback
        self.queue = asyncio.Queue()
        self.active = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.running = False
        self._loop = None

    async def _run_download(self, downloader: ChunkDownloader):
        async with self.semaphore:
            try:
                self.active[downloader.download_id] = downloader
                await downloader.start()
            except Exception as e:
                print(f"[Queue] Download failed: {e}")
            finally:
                self.active.pop(downloader.download_id, None)

    async def _worker(self):
        self.running = True
        while self.running:
            try:
                downloader = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                asyncio.create_task(self._run_download(downloader))
                self.queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[Queue] Worker error: {e}")

    def add(self, url, filename=None, save_path=None, segments=8):
        downloader = ChunkDownloader(
            url=url,
            filename=filename,
            save_path=save_path,
            segments=segments,
            progress_callback=self.progress_callback
        )
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self.queue.put_nowait, downloader)
        else:
            self.queue.put_nowait(downloader)
        return downloader

    def pause(self, download_id):
        if download_id in self.active:
            self.active[download_id].pause()

    def resume(self, download_id):
        if download_id in self.active:
            self.active[download_id].resume()

    def cancel(self, download_id):
        if download_id in self.active:
            self.active[download_id].cancel()

    def set_max_concurrent(self, n):
        self.max_concurrent = n
        self.semaphore = asyncio.Semaphore(n)

    async def start(self):
        self._loop = asyncio.get_event_loop()
        await self._worker()

    def stop(self):
        self.running = False

    def get_active_ids(self):
        return list(self.active.keys())

    def queue_size(self):
        return self.queue.qsize()
