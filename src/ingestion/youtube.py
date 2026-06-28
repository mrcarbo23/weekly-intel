"""YouTube transcript ingestion."""
import logging
import re
from datetime import datetime
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import yt_dlp

logger = logging.getLogger(__name__)


def fetch_channel_videos(channel_url: str, max_videos: int = 10) -> list[dict]:
    """Fetch recent videos and transcripts from a YouTube channel or playlist."""
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "playlistend": max_videos,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)

    entries = info.get("entries", []) if info else []
    videos = []

    for entry in entries:
        video_id = entry.get("id") or entry.get("url", "").split("v=")[-1]
        if not video_id:
            continue

        transcript = _get_transcript(video_id)
        if not transcript:
            logger.warning(f"No transcript for video {video_id}")
            continue

        videos.append({
            "title": entry.get("title", ""),
            "author": info.get("uploader", entry.get("uploader", "")),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "publish_date": _parse_upload_date(entry.get("upload_date")),
            "raw_content": transcript,
            "video_id": video_id,
        })

    return videos


def fetch_single_video(url: str) -> Optional[dict]:
    """Fetch transcript for a single YouTube video URL."""
    video_id = _extract_video_id(url)
    if not video_id:
        return None

    ydl_opts = {"quiet": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error(f"Failed to fetch video info: {e}")
            return None

    transcript = _get_transcript(video_id)
    if not transcript:
        return None

    return {
        "title": info.get("title", ""),
        "author": info.get("uploader", ""),
        "url": url,
        "publish_date": _parse_upload_date(info.get("upload_date")),
        "raw_content": transcript,
        "video_id": video_id,
    }


def _get_transcript(video_id: str) -> Optional[str]:
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(item["text"] for item in transcript_list)
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception as e:
        logger.error(f"Transcript error for {video_id}: {e}")
        return None


def _extract_video_id(url: str) -> Optional[str]:
    patterns = [
        r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"shorts/([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def _parse_upload_date(date_str: Optional[str]) -> datetime:
    if date_str and len(date_str) == 8:
        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            pass
    return datetime.utcnow()
