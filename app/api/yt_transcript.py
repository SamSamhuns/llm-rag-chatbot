"""
Get a YouTube video transcript

pip install youtube-transcript-api
"""
import re
from typing import List

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

# regex to verify if URL is from a YouTube video
YT_REGEX = r'(?:https?:\/\/)?(?:www\.)?youtu(?:\.be\/|be\.com\/(?:watch\?v=|embed\/|v\/|user\/(?:\S+\/)?(?:UC)?))?([^&=\n%\?\/ ]{11})'


def get_text_transcript_from_yt_video(
        url: str,
        langs: List[str] = None,
        cookies_path: str = None) -> str:
    """
    Returns the transcript for a youtube video if available
    Arguments:
        url: str = youtube video url
        langs: List[str] = List of langs to use, "en" by default
        cookies_path: str = path to cookies.txt to get subtitles from age restricted video

    Warning: YouTubeTranscriptApi uses an undocumented part of the YouTube API which could be discontinued
    Note: another option is extract the audio from the video & use a audio to text model (i.e. whisper) to get the transcripts
    """
    reg_exp = re.compile(YT_REGEX)
    match = reg_exp.match(url)
    # check if the url is a valid youtube url
    if match:
        video_id = match.group(1)
        print("Valid YouTube URL. Video ID:", video_id)
    else:
        raise ValueError(f"Youtube url {url} is invalid")

    langs = ["en"] if langs is None else langs
    # get transcripts from youtube video if present
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, cookies=cookies_path, languages=langs)
    except Exception as excep:  # should use a audio to text model here instead
        msg = f"{excep}: Youtube url {url} video has disabled transcriptions."
        raise ValueError(msg) from excep
    formatter = TextFormatter()
    txt = formatter.format_transcript(transcript)

    return txt


if __name__ == "__main__":
    URL = "https://youtu.be/h4NegwC_az8"  # has transcript
    URL = "https://youtu.be/q8ir8rVl2Z4?list=RDq8ir8rVl2Z4"  # no transcript
    text = get_text_transcript_from_yt_video(URL)
    print(text)
