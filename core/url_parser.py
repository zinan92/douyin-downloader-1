import re
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.pipeline import LOCAL_MEDIA_EXTENSIONS
from utils.validators import parse_url_type
from utils.logger import setup_logger

logger = setup_logger('URLParser')


class URLParser:
    @staticmethod
    def parse(url: str) -> Optional[Dict[str, Any]]:
        # Check if it's a local file path
        local_result = URLParser._parse_local_path(url)
        if local_result:
            return local_result

        url_type = parse_url_type(url)
        if not url_type:
            logger.error("Unsupported URL type: %s", url)
            return None

        result = {
            'original_url': url,
            'type': url_type,
        }

        if url_type == 'video':
            aweme_id = URLParser._extract_video_id(url)
            if aweme_id:
                result['aweme_id'] = aweme_id

        elif url_type == 'user':
            sec_uid = URLParser._extract_user_id(url)
            if sec_uid:
                result['sec_uid'] = sec_uid

        elif url_type == 'collection':
            mix_id = URLParser._extract_mix_id(url)
            if mix_id:
                result['mix_id'] = mix_id

        elif url_type == 'gallery':
            note_id = URLParser._extract_note_id(url)
            if note_id:
                result['note_id'] = note_id
                result['aweme_id'] = note_id

        elif url_type == 'music':
            music_id = URLParser._extract_music_id(url)
            if music_id:
                result['music_id'] = music_id

        return result

    @staticmethod
    def _parse_local_path(path_str: str) -> Optional[Dict[str, Any]]:
        """Check if input is a local media file or directory of media files."""
        p = Path(path_str)

        if p.is_file() and p.suffix.lower() in LOCAL_MEDIA_EXTENSIONS:
            return {
                'original_url': path_str,
                'type': 'local_file',
                'file_path': str(p.resolve()),
                'files': [str(p.resolve())],
            }

        if p.is_dir():
            media_files = sorted(
                str(f.resolve())
                for f in p.iterdir()
                if f.is_file() and f.suffix.lower() in LOCAL_MEDIA_EXTENSIONS
            )
            if media_files:
                return {
                    'original_url': path_str,
                    'type': 'local_dir',
                    'dir_path': str(p.resolve()),
                    'files': media_files,
                }

        return None

    @staticmethod
    def _extract_video_id(url: str) -> Optional[str]:
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)

        match = re.search(r'modal_id=(\d+)', url)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def _extract_user_id(url: str) -> Optional[str]:
        match = re.search(r'/user/([A-Za-z0-9_-]+)', url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _extract_mix_id(url: str) -> Optional[str]:
        match = re.search(r'/collection/(\d+)', url)
        if not match:
            match = re.search(r'/mix/(\d+)', url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _extract_note_id(url: str) -> Optional[str]:
        match = re.search(r'/(?:note|gallery)/(\d+)', url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _extract_music_id(url: str) -> Optional[str]:
        match = re.search(r'/music/(\d+)', url)
        if match:
            return match.group(1)
        return None
