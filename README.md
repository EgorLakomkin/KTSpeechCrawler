# KT-Speech-Crawler: Automatic Dataset Construction for Speech Recognition from YouTube Videos

## Google Colab
https://colab.research.google.com/drive/1JVKzB9N2FIcxlib1kXuGlfeIuudkM9Vr


## Installation
```
git clone https://github.com/EgorLakomkin/KTSpeechCrawler
pip install -r requirements.txt
```

## Running crawler
```
chmod a+x ./crawler/en_corpus.sh
./crawler/en_corpus.sh <dir_with_intermediate_results> <dir_for_resulting_samples>
```
## Browsing samples
```
python server.py --corpus <dir_for_resulting_samples>
Goto: http://localhost:8888/
```
## Citation

@article{lakomkin2018kt,
  title={KT-Speech-Crawler: Automatic Dataset Construction for Speech Recognition from YouTube Videos},
  author={Lakomkin, Egor and Magg, Sven and Weber, Cornelius and Wermter, Stefan},
  journal={EMNLP 2018},
  pages={90},
  year={2018}
}
