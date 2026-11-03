import os
import asyncio
import aiohttp
import aiofiles
from engine.database import add_download, update_download

DOWNLOAD_DIR = os.path.expanduser("~/Downloads/PixelDownloader")

class ChunkDownloader:
    def __init__(self, url, filename=None, save_path=None, segments=8, progress_callback=None):
        self.url = url
        self.filename = filename or url.split("/")[-1].split("?")[0] or "download"
        self.save_path = save_path or os.path.join(DOWNLOAD_DIR, self.filename)
        self.segments = segments
        self.progress_callback = progress_callback
        self.total_size = 0
        self.downloaded = 0
        self.download_id = None
        self.cancelled = False
        self.paused = False

    async def get_file_info(self, session):
        async with session.head(self.url, allow_redirects=True) as resp:
            self.total_size = int(resp.headers.get("Content-Length", 0))
            accepts_ranges = resp.headers.get("Accept-Ranges", "none")
            return accepts_ranges != "none" and self.total_size > 0

    async def download_chunk(self, session, start, end, chunk_index, temp_dir):
        headers = {"Range": f"bytes={start}-{end}"}
        chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")
        async with session.get(self.url, headers=headers) as resp:
            async with aiofiles.open(chunk_path, "wb") as f:
                async for data in resp.content.iter_chunked(65536):
                    if self.cancelled:
                        return
                    while self.paused:
                        await asyncio.sleep(0.5)
                    await f.write(data)
                    self.downloaded += len(data)
                    if self.progress_callback:
                        progress = (self.downloaded / self.total_size) * 100 if self.total_size else 0
                        self.progress_callback(self.download_id, self.downloaded, self.total_size, progress)

    async def merge_chunks(self, temp_dir):
        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
        async with aiofiles.open(self.save_path, "wb") as outfile:
            for i in range(self.segments):
                chunk_path = os.path.join(temp_dir, f"chunk_{i}")
                async with aiofiles.open(chunk_path, "rb") as chunk:
                    while True:
                        data = await chunk.read(65536)
                        if not data:
                            break
                        await outfile.write(data)
                os.remove(chunk_path)

    async def download_single(self, session, temp_dir):
        chunk_path = os.path.join(temp_dir, "chunk_0")
        async with session.get(self.url) as resp:
            async with aiofiles.open(chunk_path, "wb") as f:
                async for data in resp.content.iter_chunked(65536):
                    if self.cancelled:
                        return
                    while self.paused:
                        await asyncio.sleep(0.5)
                    await f.write(data)
                    self.downloaded += len(data)
                    if self.progress_callback:
                        progress = (self.downloaded / self.total_size * 100) if self.total_size else 0
                        self.progress_callback(self.download_id, self.downloaded, self.total_size, progress)
        self.segments = 1

    async def start(self):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        self.download_id = add_download(
            self.url, self.filename, self.save_path, self.total_size, self.segments
        )
        update_download(self.download_id, status="downloading")

        temp_dir = os.path.join(DOWNLOAD_DIR, f".tmp_{self.download_id}")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            async with aiohttp.ClientSession() as session:
                supports_range = await self.get_file_info(session)

                if supports_range and self.total_size > 0:
                    chunk_size = self.total_size // self.segments
                    tasks = []
                    for i in range(self.segments):
                        start = i * chunk_size
                        end = (start + chunk_size - 1) if i < self.segments - 1 else self.total_size - 1
                        tasks.append(self.download_chunk(session, start, end, i, temp_dir))
                    await asyncio.gather(*tasks)
                else:
                    await self.download_single(session, temp_dir)

            if not self.cancelled:
                await self.merge_chunks(temp_dir)
                update_download(self.download_id, status="completed", downloaded=self.downloaded)
            else:
                update_download(self.download_id, status="cancelled")

        except Exception as e:
            update_download(self.download_id, status="failed")
            raise e
        finally:
            if os.path.exists(temp_dir):
                try:
                    os.rmdir(temp_dir)
                except:
                    pass

        return self.save_path

    def pause(self):
        self.paused = True
        if self.download_id:
            update_download(self.download_id, status="paused")

    def resume(self):
        self.paused = False
        if self.download_id:
            update_download(self.download_id, status="downloading")

    def cancel(self):
        self.cancelled = True
        if self.download_id:
            update_download(self.download_id, status="cancelled")
