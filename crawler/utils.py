import os
import subprocess


def extract_audio_part_segment(movie_file, timing_start, timing_end, res_filename,  sample_rate = 16000):
    start_h, start_m, start_s, start_msec = timing_start.hour, timing_start.minute, \
                                            timing_start.second, timing_start.microsecond // 1000
    end_h, end_m, end_s, end_msec = timing_end.hour, timing_end.minute, \
                                    timing_end.second, timing_end.microsecond // 1000
    DEVNULL = open(os.devnull, 'wb')
    if os.path.exists(res_filename):
        os.remove(res_filename)
    p = subprocess.Popen(["ffmpeg",  "-i", movie_file,"-acodec",
                        "pcm_s16le", "-ac", "1", "-ar", str(sample_rate),
                        "-ss", "{:02d}:{:02d}:{:02d}.{:03d}".format(start_h, start_m, start_s, start_msec),
                        "-to", "{:02d}:{:02d}:{:02d}.{:03d}".format(end_h, end_m, end_s, end_msec),  res_filename],
                        stdout=DEVNULL, stderr=DEVNULL)
    out, err = p.communicate()
    p.terminate()
    return None

def get_ts_seconds(time_obj):
    return time_obj.hour*60*60 + time_obj.minute*60 + time_obj.second + time_obj.microsecond  / 1000000
