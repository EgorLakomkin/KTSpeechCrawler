import re
from crawler.youtube_helpers import remove_overlapping_subtitles, \
    normalize_subtitle, leave_alphanum_characters, merge_subtitles, _get_transcript_google_web_asr
import random
from Levenshtein import ratio

class Pipeline:
    """
    Pipeline class storing and applying list of filters to the input video

    """
    def __init__(self,  lst_components):
        super(Pipeline, self).__init__()
        self.lst_components = lst_components

    def __call__(self, data):
        result = data
        for component in self.lst_components:
            result = component(result)
        return result

class BaseFilter():

    def validate(self, input):
        raise NotImplementedError

    def __call__(self, input):
        raise NotImplementedError

class OverlappingSubtitlesRemover(BaseFilter):
    def __init__(self):
        super(OverlappingSubtitlesRemover, self).__init__()

    def __call__(self, input):
        subtitles = input['subtitles']
        input['subtitles'] =  remove_overlapping_subtitles(subtitles)
        return input


class SubtitleMerger(BaseFilter):
    def __init__(self, min_gap_to_split_sec = 1.0, max_len_merged_sec = 15):
        super(SubtitleMerger, self).__init__()
        self.min_gap_to_split_sec = min_gap_to_split_sec
        self.max_len_merged_sec = max_len_merged_sec

    def __call__(self, input):
        subtitles = input['subtitles']
        input['subtitles'] = merge_subtitles(subtitles, min_dist=self.min_gap_to_split_sec,
                                             max_dist=self.max_len_merged_sec)
        return input


DEFAULT_BLACKLIST_CHARACTERS = set(["♪", "♬", "♫", ])

class SubtitleCaptionTextFilter(BaseFilter):
    def __init__(self, blacklisted_chars=None):
        super(SubtitleCaptionTextFilter, self).__init__()
        self.blacklist_chars = blacklisted_chars or DEFAULT_BLACKLIST_CHARACTERS

    def __call__(self, input):
        subtitles = input['subtitles']
        input['subtitles'] = list(filter(lambda s: all(s['original_phrase'].find(c) == -1
                                                  for c in self.blacklist_chars),
                                                  subtitles))
        return input

class MinNumberSubtitlesFilter(BaseFilter):
    def __init__(self, threshold=3):
        self.threshold = threshold

    def validate(self, input):
        assert 'subtitles' in input

    def __call__(self, input):
        return len(input['subtitles']) > self.threshold


class GoogleASRCheck(BaseFilter):
    def __init__(self, num_samples_to_check=3, wer_threshold=0.25):
        pass

class CaptionRegexMatcher(BaseFilter):

    def __init__(self, regexp):
        super(CaptionRegexMatcher, self).__init__()
        self.regexp = regexp

    def __call__(self, input):
        subtitles = input['subtitles']
        input['subtitles'] = list(filter(lambda s: re.match(self.regexp, s['original_phrase']) is not None, subtitles))
        return input


class CaptionNormalizer(BaseFilter):
    def __call__(self, input):
        for sub_info in input['subtitles']:
            sub_info['original_phrase'] =  normalize_subtitle(sub_info["original_phrase"])
        return input

class CaptionLengthFilter(BaseFilter):

    def __init__(self, min_length=None, max_length=None):
        super(CaptionLengthFilter, self).__init__()
        self.min_filter_func = lambda x: len(x.split()) >= min_length if min_length else lambda x: True
        self.max_filter_func = lambda x: len(x.split()) <= max_length if max_length else lambda x: True


    def __call__(self, input):
        subtitles = input['subtitles']
        input['subtitles'] = list(filter(lambda s: self.min_filter_func(s['original_phrase'])
                                  and self.max_filter_func(s['original_phrase']), subtitles))
        return input

class CaptionDurationFilter(BaseFilter):
    def __init__(self, min_length=None, max_length=None):
        super(CaptionDurationFilter, self).__init__()
        self.min_filter_func = lambda x: x['duration'] >= min_length if min_length else lambda x: True
        self.max_filter_func = lambda x: x['duration'] <= max_length if max_length else lambda x: True


    def __call__(self, input):
        subtitles = input['subtitles']
        input['subtitles'] = list(filter(lambda s: self.min_filter_func(s)
                                  and self.max_filter_func(s), subtitles))
        return input

class CaptionLeaveOnlyAlphaNumCharacters(BaseFilter):

    def __call__(self, input):
        for sub_info in input['subtitles']:
            sub_info['original_phrase'] =  leave_alphanum_characters(sub_info["original_phrase"])
        return input

class GoogleRandomSubsetWERFilter(BaseFilter):

    def __init__(self, num_samples_to_test=3, mean_wer_threshold = 0.3):
        super(GoogleRandomSubsetWERFilter, self).__init__()
        self.num_samples_to_test = num_samples_to_test
        self.mean_wer_threshold = mean_wer_threshold

    def __call__(self, input):
        subtitles = input["subtitles"]
        subset = random.sample(subtitles, self.num_samples_to_test)

        transcripts = [(s, _get_transcript_google_web_asr(s)) for s in subset]
        transcripts = [(t, s) for (t, s) in transcripts if s is not None]
        if len(transcripts) == 0:
            #filter removes all the subtitles, as potentially unreliable sample
            subtitles = []
        else:
            overlap_ratio = [ratio(t["phrase"].lower(), s.lower()) for (t, s) in transcripts]
            passed_threshold =  sum(overlap_ratio) / len(overlap_ratio) > self.mean_wer_threshold
            if not passed_threshold:
                #removing all subtitles, as potentially unreliable
                subtitles = []
        input["subtitles"] = subtitles
        return input

if __name__ == "__main__":
    from crawler.youtube_helpers import load_all_subtitles
    subtitles = load_all_subtitles("./../video/2oNoBDMGGioHow_to_Make_a_Picnic_Table_-_Plans_and_Instructions.en.vtt")
    print(len(subtitles))
    input = {
        'subtitles' : subtitles,
        'video_file' : ''
    }
    good_chars_regexp = re.compile(r"^[A-Za-z0-9\,\.\-\?\"\'\’\!\“\s\;\:\“\”\–\‘\’\’\/\\]+$", re.IGNORECASE)
    pipeline = Pipeline([
        OverlappingSubtitlesRemover(),
        SubtitleCaptionTextFilter(),
        CaptionNormalizer(),
        CaptionRegexMatcher(good_chars_regexp),
        CaptionLengthFilter(min_length=5),
        CaptionLeaveOnlyAlphaNumCharacters(),
        SubtitleMerger(max_len_merged_sec=10),
        CaptionDurationFilter(min_length=1, max_length=20.0)
    ])
    processed_subtitles = pipeline(input)
    print(len(processed_subtitles['subtitles']))
    for s in processed_subtitles['subtitles']:
        print(s["original_phrase"])