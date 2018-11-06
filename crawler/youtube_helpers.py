import hashlib
import json
import os
import io
from webvtt import WebVTT
import copy
import tempfile
import shutil
from crawler.utils import extract_audio_part_segment, get_ts_seconds
from path import Path
import datetime
# from datetime import datetime
import re
import random
import numpy as np
import unicodedata
import speech_recognition as sr
from Levenshtein import *
from tqdm import tqdm

everything_cool = re.compile(r"^[A-Za-z0-9\,\.\-\?\"\'\’\!\“\s\;\:\“\”\–\‘\’\’\/\\]+$", re.IGNORECASE)
leave_chars = re.compile(r"[^a-z\s\']", re.IGNORECASE)
# numbers are ignored
html_tags = re.compile(r'<.*?>')


def striphtml(data):
    return html_tags.sub(' ', data)


YT_PREFIX = "YTgenerated___"


def get_all_subtitles(dir):
    # entries = os.listdir(dir)
    for filename in Path(dir).walkfiles("*.en.vtt"):
        # if filename.find(".vtt") != -1:
        if filename.find(YT_PREFIX) != -1:
            continue
        yield os.path.join(dir, filename)


def parse_ts(ts_string):
    if ' ' in ts_string:
        ts_string = ts_string.split()[0]
    ts = datetime.datetime.strptime(ts_string, '%H:%M:%S.%f')
    return ts


def if_phrase_is_bad(phrase):
    if len(phrase) < 5:
        return True
    if phrase[0] in set(["(", "[", "*", "♪", "&", "♬", "♫"]):
        return True
    if phrase.find(':') != -1:
        return True
    return False


def get_hash(content):
    return hashlib.sha224(content.encode('utf-8')).hexdigest()


def timedelta_dt(t1, t2):
    dt1 = datetime.timedelta(hours=t1.hour, minutes=t1.minute, seconds=t1.second, microseconds=t1.microsecond)
    dt2 = datetime.timedelta(hours=t2.hour, minutes=t2.minute, seconds=t2.second, microseconds=t2.microsecond)
    return dt2 - dt1


#        video_file = get_video_file(subtitle_file)

def load_all_subtitles(subtitle_file):
    subs = WebVTT().read(subtitle_file).captions  # pysrt.open(subtitle_file)
    res = []
    for s_idx, s in enumerate(subs):
        start_ts = parse_ts(s.start).time()
        end_ts = parse_ts(s.end).time()
        phrase = s.text
        phrase = phrase.replace('\n', ' ')
        delta = timedelta_dt(start_ts, end_ts)
        res.append(
            {"ts_start": start_ts, "ts_end": end_ts,
             "original_phrase": phrase,
             "sub_file": subtitle_file,
             "duration": delta.total_seconds(),
             "idx" : s_idx}
        )
    return res


def get_video_file(subtitle_file):
    naive_video_file = subtitle_file.replace(".en.vtt", ".mp4")
    webm_video_file = subtitle_file.replace(".en.vtt", ".webm")
    if os.path.exists(naive_video_file) or os.path.exists(webm_video_file):
        return naive_video_file
    else:
        dumb_youtube_file = subtitle_file.replace(".en.vtt", "")
        if os.path.exists(dumb_youtube_file):
            print("Renaming file {} --> {}".format(dumb_youtube_file, naive_video_file))
            shutil.move(dumb_youtube_file, naive_video_file)
            return naive_video_file
        else:
            raise Exception("Video file does not exists {}".format(dumb_youtube_file))


def merge_subtitles(subs, min_dist=1.5, max_dist=6.0):
    res = []
    for s_idx in range(len(subs)):
        s = subs[s_idx]
        if s_idx == 0:
            res.append(s)
        else:
            prev_s = res[-1]
            distance = timedelta_dt(prev_s["ts_end"], s["ts_start"])
            distance_sec = distance.total_seconds()
            assert distance_sec >= 0.0
            merged_dist = timedelta_dt(prev_s["ts_start"], s["ts_end"], )
            if distance_sec < min_dist and merged_dist.total_seconds() < max_dist:
                # merge
                new_s = copy.deepcopy(prev_s)
                new_s["ts_end"] = s["ts_end"]
                new_s["original_phrase"] = prev_s["original_phrase"] + " " + s["original_phrase"]
                new_delta = timedelta_dt(new_s["ts_start"], new_s["ts_end"])
                new_s["duration"] = new_delta.total_seconds()
                res[-1] = new_s
            else:
                res.append(s)
    return res


def check_sub_overlap(sub1, sub2):
    sub1_start, sub1_end = sub1["ts_start"], sub1["ts_end"]
    sub2_start, sub2_end = sub2["ts_start"], sub2["ts_end"]
    if sub1_end > sub2_start and sub1_end < sub2_end:
        return True
    if sub2_end > sub1_start and sub2_end < sub1_end:
        return True
    return False


def remove_overlapping_subtitles(subs, width=3):
    bad_indices = set([])
    for s_idx in range(len(subs)):
        s = subs[s_idx]
        for i in range(-width, width + 1):
            if s_idx + i >= 0 and s_idx + i < len(subs) and i != 0:
                candidate_sub = subs[s_idx + i]
                if check_sub_overlap(candidate_sub, s):
                    bad_indices.add(s_idx)
                    bad_indices.add(s_idx + i)
    if len(bad_indices) > 0:
        print("bad indices: {}".format(len(bad_indices)))
    return [s for s_idx, s in enumerate(subs) if s_idx not in bad_indices]


def filter_too_close_subtitles(subtitles, min_threshold=1.5):
    res = []
    for i, s in enumerate(subtitles):
        if i > 0:
            prev_s = subtitles[i - 1]
            distance = get_ts_seconds(s["ts_start"]) - get_ts_seconds(prev_s["ts_end"])
            if distance > min_threshold:
                res.append(s)
        else:
            res.append(s)
    return res


def int_to_en(num):
    d = {0: 'zero', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
         6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten',
         11: 'eleven', 12: 'twelve', 13: 'thirteen', 14: 'fourteen',
         15: 'fifteen', 16: 'sixteen', 17: 'seventeen', 18: 'eighteen',
         19: 'nineteen', 20: 'twenty',
         30: 'thirty', 40: 'forty', 50: 'fifty', 60: 'sixty',
         70: 'seventy', 80: 'eighty', 90: 'ninety'}
    k = 1000
    m = k * 1000
    b = m * 1000
    t = b * 1000

    assert (0 <= num)

    if (num < 20):
        return d[num]

    if (num < 100):
        if num % 10 == 0:
            return d[num]
        else:
            return d[num // 10 * 10] + ' ' + d[num % 10]
    if (num < k):
        if num % 100 == 0:
            return d[num // 100] + ' hundred'
        else:
            return d[num // 100] + ' hundred and ' + int_to_en(num % 100)


def normalize_numbers(input_str):
    input_str = input_str.replace('%', " percent ")
    numbers = re.findall(r'\s([\d]+)\s', input_str)
    for number in numbers:
        if len(number) <= 3:
            number_str = int_to_en(int(number))
            input_str = input_str.replace(number, number_str)

    return input_str


def normalize_subtitle(input_str):
    input_str = ' ' + input_str + ' '
    input_str = input_str.replace(',', ' ').replace('.', ' ')
    input_str = re.sub(r"([a-z])\-([a-z])", r"\1\2", input_str, 0, re.IGNORECASE)
    input_str = input_str.replace("- ", " ")
    input_str = input_str.replace("— ", " ")
    input_str = input_str.replace('’', '\'').replace('‘', '\'').replace('ʻ', '\'').replace('´', '\'').replace("&nbsp;",
                                                                                                              ' ')
    # substitute speaker info
    input_str = re.sub('<[^<]+?>', ' ', input_str)
    input_str = re.sub(r"[A-Z]\w+\:", " ", input_str)
    input_str = re.sub(r'\[.*\]', ' ', input_str)
    input_str = re.sub(r'\(.*\)', ' ', input_str)
    input_str = re.sub(r'\*.*\*', ' ', input_str)
    input_str = unicodedata.normalize('NFKD', input_str)

    input_str = normalize_numbers(input_str)
    return input_str.strip()


def leave_alphanum_characters(input_string):
    input_string = re.sub(leave_chars, ' ', input_string.lower())
    input_string = re.sub('\s+', ' ', input_string)
    input_string = input_string.upper()
    return input_string.strip()


def if_contain_bad_symbols(phrase):
    for symbol in set(["♪", "♬", "♫", ]):
        if phrase.find(symbol) != -1:
            return True
    return False


def parse_subtitle(subtitle_file, max_duration=15, min_duration=3, min_threshold=1.5, min_transcript_len=3):
    all_subtitles = load_all_subtitles(subtitle_file)
    print("{} overall subtitles".format(len(all_subtitles)))
    all_subtitles = remove_overlapping_subtitles(all_subtitles)
    print("{} without overlap subtitles".format(len(all_subtitles)))
    # filter bad
    all_subtitles = [s for s in all_subtitles if not if_contain_bad_symbols(s["original_phrase"])]
    for s in all_subtitles:
        s["phrase"] = normalize_subtitle(s["original_phrase"])
    not_cool = [s for s in all_subtitles if not re.match(everything_cool, s["phrase"])]
    all_subtitles = [s for s in all_subtitles if re.match(everything_cool, s["phrase"])
                     and len(s["phrase"].strip()) >= min_transcript_len]
    for s in all_subtitles:
        s["phrase"] = leave_alphanum_characters(s["phrase"])
    print("{} after filtering".format(len(all_subtitles)))

    all_subtitles = merge_subtitles(all_subtitles, min_dist=1.0, max_dist=max_duration)
    print("{} merged".format(len(all_subtitles)))
    # all_subtitles = filter_too_close_subtitles(all_subtitles, min_threshold=min_threshold)
    all_subtitles = list(filter(lambda x: x["duration"] <= max_duration
                                          and x["duration"] >= min_duration, all_subtitles))

    # not_cool = list(filter(lambda x: not re.match(everything_cool, x["original_phrase"]), all_subtitles))
    print("not cool", "\n".join([p["original_phrase"] for p in not_cool[:5]]))
    # all_subtitles = list(filter(lambda x: re.match(everything_cool, x["original_phrase"]), all_subtitles))
    # print("{} with everything cool".format(len(all_subtitles)))

    for idx in range(len(all_subtitles)):
        s = all_subtitles[idx]
        s["hash"] = get_hash(subtitle_file + s["phrase"] + str(s["ts_start"]))
    return all_subtitles


def getsize(filename):
    """Return the size of a file, reported by os.stat()."""
    return os.stat(filename).st_size


def _load_annotations(ann_f):
    if os.path.exists(ann_f):
        with open(ann_f) as f:
            res = json.load(f)
            # print(res["tags"])
            # print("title")
    else:
        print("{} does not exists".format(ann_f))


def get_closest_captions(src_caption, lst_dest_captions):
    src_start_ts, src_end_ts = src_caption.start_in_seconds, src_caption.end_in_seconds
    res = []
    for dest_caption in lst_dest_captions:
        dest_start_ts, dest_end_ts = dest_caption.start_in_seconds, dest_caption.end_in_seconds
        if (src_start_ts >= dest_start_ts and src_start_ts <= dest_end_ts) or (
                src_end_ts >= dest_start_ts and src_end_ts <= dest_end_ts):
            res.append(dest_caption)
    return res


def _get_transcript_google_web_asr(t):
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            extract_audio_part_segment(t["video_file"], t["ts_start"], t["ts_end"], f.name)

            r = sr.Recognizer()
            with sr.AudioFile(f.name) as source:
                audio = r.record(source)

                return r.recognize_google(audio)
    except Exception as e:
        print(e)
        return None


def google_speech_test(timings, threshold=0.65, samples=2, min_duration=2.5):
    timings = [t for t in timings if t["duration"] > min_duration]
    if len(timings) < samples:
        return False
    subset = random.sample(timings, samples)

    transcripts = [(s, _get_transcript_google_web_asr(s)) for s in subset]
    transcripts = [(t, s) for (t, s) in transcripts if s is not None]

    if len(transcripts) == 0:
        print("empty transcripts!")
        return False
    print([(t["phrase"].lower(), s.lower()) for (t, s) in transcripts])
    overlap_ratio = [ratio(t["phrase"].lower(), s.lower()) for (t, s) in transcripts]
    return np.mean(overlap_ratio) > threshold
