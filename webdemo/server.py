import os
from path import Path
import random
from flask import Flask, jsonify, render_template
from flask import request
import shutil
import json
from tqdm import tqdm
from scipy.io.wavfile import read
import numpy as np
import json

app = Flask(__name__)
MIN_SUM_AMPLITUTDE = 1e-2
#ANNOTATIONS_FILE = "annotations.json"

def select_random_sample(all_files):
    while True:
        data = random.choice(all_files)
        if not os.path.exists(data["txt"]) or not os.path.exists(data["wav"]):
            continue
        phrase = open(data["txt"]).read().strip()
        if len(phrase) < 10:
            continue
        rate, wav_data = read(data["wav"])
        if len(wav_data) < 16000 // 2 or np.sum(np.abs(wav_data)) < MIN_SUM_AMPLITUTDE:
            continue
        break
    return data



@app.route("/annotate", methods=['POST'])
def annotate():
    #with open(ANNOTATIONS_FILE, 'a+') as f:
    #    f.write(json.dumps(data) + "\n")
    #    f.flush()
    return jsonify({"result" : "OK"})

@app.route('/',methods=['GET'])
def render_random():
    dataset = [select_random_sample(all_files) for i in range(8)]
    res = []
    for d_idx, d in enumerate(dataset):
        wav_file = d['wav']
        txt = d['txt']
        metadata_file = d["meta"]
        with open(metadata_file, "r") as f:
            metadata = json.loads(f.read())
        shutil.copy( wav_file, os.path.join("./static", os.path.basename(wav_file)) )
        res.append({
            "wav" : os.path.basename(wav_file),
            "txt" : open(txt).read().strip(),
            "metadata" : metadata,
            "index" : d_idx
        })
    return render_template('index.html', samples={ "data" : res})

def iterate_corpus(directory):
    wav_dir = os.path.join(directory, "wav")
    for f in tqdm(Path(wav_dir).walkfiles("*.wav")):
        txt_dir = f.dirname().replace("/wav/", "/txt/")
        txt_file = os.path.join(txt_dir, f.basename().replace(".wav", ".txt"))
        metadata_dir =  f.dirname().replace("/wav/", "/metadata/")
        metadata_file = os.path.join(metadata_dir, f.basename().replace(".wav", ".json"))
        if os.path.exists(txt_file) and os.path.exists(metadata_file):
            yield {
                "wav" : str(f),
                "txt" : txt_file,
                "meta" : metadata_file
            }

def find_files(directory):
    res = []
    for data in iterate_corpus(directory):
        res.append(data)
    return res

def dump_medatadata_corpus(dir, filename):
    total_length = 0.0
    with open(filename, "w") as f:
        for data in iterate_corpus(dir):
            try:
                phrase = open(data["txt"]).read().strip()
                if len(phrase) < 10:
                    continue
                rate, wav_data = read(data["wav"])
                assert rate == 16000, "rate is wrong {}".format(data["wav"])
                if len(wav_data) < 16000//2 or np.sum(np.abs(wav_data)) < MIN_SUM_AMPLITUTDE:
                    continue
                if os.path.exists(data["wav"]) and os.path.exists(data["txt"]):
                    f.write("{},{}\n".format(data["wav"], data["txt"]))
                    total_length += len(wav_data) / rate
            except:
                print("Exception", data["wav"])
                continue
    print("total duration: {:.2f}h".format(total_length / 60 / 60))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=str)
    parser.add_argument("--port", type=int, default=8888)
    parser.add_argument('--dump', dest='dump', action='store_true', help='Dump manifest file')
    parser.add_argument('--dump-file', default=None)
    parser.set_defaults(dump=False)

    opt = parser.parse_args()
    assert os.path.exists(opt.corpus), "Cannot find corpus directory"
    if opt.dump:
        print("dumping file")
        dump_medatadata_corpus(opt.corpus, opt.dump_file)

    all_files = find_files(opt.corpus)
    print("Total files", len(all_files))
    app.run(host='0.0.0.0',
            port=opt.port, debug=True, use_reloader=False, )
